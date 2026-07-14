"""iios/investment/decision/committee/committee_session.py
CommitteeSession — manages a single full deliberation session.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from iios.investment.decision.committee.challenge_engine import ChallengeEngine
from iios.investment.decision.committee.committee_confidence import CommitteeConfidenceCalculator
from iios.investment.decision.committee.committee_constants import (
    MIN_EVIDENCE_ITEMS_FOR_DELIBERATION,
    MIN_MEMBERS_FOR_QUORUM,
    CommitteePosition,
    SessionState,
)
from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.committee_findings import CommitteeFindingsBuilder
from iios.investment.decision.committee.committee_quality import CommitteeQualityEvaluator
from iios.investment.decision.committee.committee_recommendations import build_committee_stance
from iios.investment.decision.committee.committee_report import (
    CommitteeReport,
    build_committee_report,
)
from iios.investment.decision.committee.committee_round import RoundResult
from iios.investment.decision.committee.committee_state import CommitteeState
from iios.investment.decision.committee.discussion_engine import DiscussionEngine
from iios.investment.decision.committee.executive_summary import ExecutiveSummaryBuilder
from iios.investment.decision.committee.member_registry import MemberRegistry
from iios.investment.decision.committee.minority_reports import MinorityReportBuilder
from iios.investment.decision.committee.voting_engine import VotingEngine


class CommitteeSession:
    """
    Orchestrates the full deliberation lifecycle for one decision:
      1. Convene
      2. Opening review
      3. Challenge round
      4. Deliberation
      5. Vote
      6. Report
    """

    def __init__(
        self,
        decision_id: str,
        ctx:         CommitteeContext,
        registry:    Optional[MemberRegistry] = None,
        version:     int                      = 1,
    ) -> None:
        self._session_id = str(uuid.uuid4())
        self._decision_id = decision_id
        self._ctx         = ctx
        self._registry    = registry or MemberRegistry.default_committee()
        self._version     = version
        self._state       = CommitteeState(self._session_id, decision_id)

        self._discussion  = DiscussionEngine()
        self._voting      = VotingEngine()
        self._challenge   = ChallengeEngine()
        self._minority    = MinorityReportBuilder()
        self._findings_b  = CommitteeFindingsBuilder()
        self._exec_sum    = ExecutiveSummaryBuilder()
        self._quality     = CommitteeQualityEvaluator()
        self._conf_calc   = CommitteeConfidenceCalculator()

        self._rounds:     List[RoundResult] = []
        self._report:     Optional[CommitteeReport] = None

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def report(self) -> Optional[CommitteeReport]:
        return self._report

    @property
    def state(self) -> SessionState:
        return self._state.current_state

    def run(self) -> CommitteeReport:
        """Execute the full committee deliberation and return the CommitteeReport."""
        import time
        t0 = time.perf_counter()

        try:
            self._state.transition(SessionState.CONVENED)

            # ── Fast-exit: insufficient evidence ──────────────────────────────
            if self._ctx.evidence.item_count <= MIN_EVIDENCE_ITEMS_FOR_DELIBERATION:
                report = self._insufficient_evidence_report(
                    duration_ms=(time.perf_counter() - t0) * 1000.0
                )
                self._report = report
                self._state.transition(SessionState.CONCLUDED)
                return report

            # ── Fast-exit: quorum check ────────────────────────────────────────
            if self._registry.voting_member_count() < MIN_MEMBERS_FOR_QUORUM:
                report = self._insufficient_evidence_report(
                    duration_ms=(time.perf_counter() - t0) * 1000.0
                )
                self._report = report
                self._state.transition(SessionState.CONCLUDED)
                return report

            members = self._registry.all_members()

            # ── Round 1: Opening Review ────────────────────────────────────────
            self._state.transition(SessionState.REVIEWING)
            rn = self._state.advance_round()
            r1 = self._discussion.run_opening_review(members, self._ctx, rn)
            self._rounds.append(r1)

            opinions1 = list(r1.opinions)

            # ── Round 2: Challenge ─────────────────────────────────────────────
            self._state.transition(SessionState.DELIBERATING)
            challenges = self._challenge.generate(opinions1, self._ctx)
            resolved   = self._challenge.count_resolved(challenges)

            for _ in challenges:
                self._state.record_challenge()
            for _ in range(resolved):
                self._state.record_resolved_challenge()

            rn = self._state.advance_round()
            r2 = self._discussion.run_challenge_round(opinions1, self._ctx, rn)
            self._rounds.append(r2)

            # ── Round 3: Deliberation ─────────────────────────────────────────
            rn = self._state.advance_round()
            r3 = self._discussion.run_deliberation(
                members, opinions1,
                len(challenges), resolved,
                self._ctx, rn,
            )
            self._rounds.append(r3)

            opinions3 = list(r3.opinions)

            # ── Round 4: Final Vote ────────────────────────────────────────────
            self._state.transition(SessionState.VOTING)
            rn = self._state.advance_round()
            r4 = self._discussion.run_final_vote(opinions3, rn)
            self._rounds.append(r4)

            for op in opinions3:
                self._state.record_opinion(op)

            vote_summary = self._voting.conduct_vote(members, opinions3)
            # tie-break if exactly 50%
            if abs(vote_summary.support_fraction - 0.50) < 0.001:
                vote_summary = self._voting.tie_break(vote_summary, members, opinions3)

            # ── Position determination ─────────────────────────────────────────
            position = self._determine_position(vote_summary)

            # ── Minority reports ───────────────────────────────────────────────
            minority_reports = self._minority.build(opinions3, vote_summary)

            # ── Findings ──────────────────────────────────────────────────────
            findings = self._findings_b.build(opinions3, self._ctx)

            # ── Stance ────────────────────────────────────────────────────────
            stance = build_committee_stance(
                position         = position,
                support_fraction = vote_summary.support_fraction,
                consensus_level  = vote_summary.consensus_level,
                risk_concerns    = tuple(findings.key_risks[:5]),
                open_questions   = tuple(findings.open_questions[:5]),
            )

            # ── Scores ─────────────────────────────────────────────────────────
            total_dur = (time.perf_counter() - t0) * 1000.0
            quality_score   = self._quality.evaluate(
                opinions3, vote_summary, self._rounds,
                len(challenges), resolved, self._ctx,
            )
            conf_score = self._conf_calc.calculate(
                vote_summary, opinions3, self._ctx,
                len(challenges), resolved,
            )

            # ── Executive Summary ─────────────────────────────────────────────
            exec_sum = self._exec_sum.build(
                position, vote_summary, self._ctx,
                len(minority_reports), len(challenges),
            )

            # ── Build report ──────────────────────────────────────────────────
            report = build_committee_report(
                session_id               = self._session_id,
                decision_id              = self._decision_id,
                subject_id               = self._ctx.subject_id,
                subject_type             = self._ctx.subject_type,
                version                  = self._version,
                position                 = position,
                stance                   = stance,
                committee_score          = quality_score,
                committee_confidence     = conf_score,
                vote_summary             = vote_summary,
                opinions                 = opinions3,
                minority_reports         = minority_reports,
                rounds                   = self._rounds,
                challenge_count          = len(challenges),
                resolved_count           = resolved,
                findings                 = findings,
                executive_summary        = exec_sum,
                evidence_snapshot_id     = self._ctx.evidence.snapshot_id,
                reasoning_snapshot_id    = self._ctx.reasoning.snapshot_id,
                confidence_snapshot_id   = self._ctx.confidence.snapshot_id,
                risk_snapshot_id         = self._ctx.risk.snapshot_id,
                explanation_snapshot_id  = self._ctx.explanation.snapshot_id,
                participating_members    = [m.member_id for m in members],
                duration_ms              = total_dur,
            )
            self._report = report
            self._state.transition(SessionState.CONCLUDED)
            return report

        except Exception:
            self._state.transition(SessionState.FAILED)
            raise

    # ── Private ────────────────────────────────────────────────────────────────

    def _determine_position(self, vote_summary) -> CommitteePosition:
        if self._ctx.risk.blocks_execution:
            return CommitteePosition.BLOCKED
        if self._ctx.evidence.item_count <= MIN_EVIDENCE_ITEMS_FOR_DELIBERATION:
            return CommitteePosition.INSUFFICIENT_EVIDENCE
        from iios.investment.decision.committee.committee_constants import ConsensusLevel
        if vote_summary.consensus_level == ConsensusLevel.NO_CONSENSUS:
            return CommitteePosition.DEFER_PENDING_EVIDENCE
        if vote_summary.support_fraction > 0.50:
            return CommitteePosition.PROCEED_TO_RECOMMENDATION
        return CommitteePosition.BLOCKED

    def _insufficient_evidence_report(self, duration_ms: float) -> CommitteeReport:
        from iios.investment.decision.committee.committee_constants import (
            ConsensusLevel,
            VoteType,
        )
        from iios.investment.decision.committee.weighted_voting import VoteSummary
        from iios.investment.decision.committee.committee_findings import CommitteeFindings
        from iios.investment.decision.committee.committee_recommendations import CommitteeStance
        import datetime as dt

        position = CommitteePosition.INSUFFICIENT_EVIDENCE

        # Empty vote summary
        vs = VoteSummary(
            total_votes=0, support_count=0, oppose_count=0, abstain_count=0,
            support_weight=0.0, oppose_weight=0.0, abstain_weight=0.0,
            total_weight=0.0, decisive_weight=0.0, support_fraction=0.0,
            consensus_level=ConsensusLevel.NO_CONSENSUS,
            avg_support_confidence=0.0, avg_oppose_confidence=0.0,
        )
        findings = CommitteeFindings(
            supporting_observations=(), opposing_observations=(),
            key_risks=("Insufficient evidence for deliberation",),
            open_questions=("Collect additional evidence items before re-submission",),
            evidence_assessment=f"Evidence items: {self._ctx.evidence.item_count} (minimum: {MIN_EVIDENCE_ITEMS_FOR_DELIBERATION+1})",
            reasoning_assessment="No deliberation conducted",
            confidence_assessment="N/A",
            risk_assessment=f"Overall risk: {self._ctx.risk.overall_risk:.1f}/100",
        )
        stance = CommitteeStance(
            position=position, consensus_level=ConsensusLevel.NO_CONSENSUS,
            support_fraction=0.0, forwarding_approved=False,
            required_conditions=("Collect minimum required evidence items",),
            governing_concerns=("Insufficient evidence for committee deliberation",),
        )
        exec_sum = f"COMMITTEE REVIEW: {self._ctx.subject_id}\n\nSuspended: insufficient evidence ({self._ctx.evidence.item_count} items)."

        return build_committee_report(
            session_id=self._session_id, decision_id=self._decision_id,
            subject_id=self._ctx.subject_id, subject_type=self._ctx.subject_type,
            version=self._version, position=position, stance=stance,
            committee_score=0.0, committee_confidence=0.0,
            vote_summary=vs, opinions=[], minority_reports=[],
            rounds=[], challenge_count=0, resolved_count=0,
            findings=findings, executive_summary=exec_sum,
            evidence_snapshot_id=self._ctx.evidence.snapshot_id,
            reasoning_snapshot_id=self._ctx.reasoning.snapshot_id,
            confidence_snapshot_id=self._ctx.confidence.snapshot_id,
            risk_snapshot_id=self._ctx.risk.snapshot_id,
            explanation_snapshot_id=self._ctx.explanation.snapshot_id,
            participating_members=[], duration_ms=duration_ms,
        )
