"""iios/investment/decision/committee/committee_report.py
CommitteeReport — the canonical, immutable output of one committee session.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from iios.investment.decision.committee.committee_constants import (
    CommitteeGrade,
    CommitteePosition,
    ConsensusLevel,
)
from iios.investment.decision.committee.committee_findings import CommitteeFindings
from iios.investment.decision.committee.committee_member import MemberOpinion
from iios.investment.decision.committee.committee_recommendations import CommitteeStance
from iios.investment.decision.committee.committee_round import RoundResult
from iios.investment.decision.committee.minority_reports import MinorityReport
from iios.investment.decision.committee.weighted_voting import VoteSummary


@dataclass(frozen=True)
class CommitteeReport:
    """
    Canonical, immutable, versioned output of one committee deliberation.
    Contains NO investment recommendations (buy/sell/hold).
    """
    report_id:          str
    session_id:         str
    decision_id:        str
    subject_id:         str
    subject_type:       str
    version:            int
    # ── Committee decision ─────────────────────────────────────────────────
    position:           CommitteePosition
    stance:             CommitteeStance
    committee_score:    float              # 0–100 overall readiness score
    committee_grade:    CommitteeGrade
    committee_confidence: float            # 0–100 committee's own confidence
    # ── Voting ─────────────────────────────────────────────────────────────
    vote_summary:       VoteSummary
    opinions:           Tuple[MemberOpinion, ...]
    minority_reports:   Tuple[MinorityReport, ...]
    # ── Deliberation ───────────────────────────────────────────────────────
    rounds:             Tuple[RoundResult, ...]
    challenge_count:    int
    resolved_count:     int
    # ── Content ────────────────────────────────────────────────────────────
    findings:           CommitteeFindings
    executive_summary:  str
    # ── Snapshot IDs ──────────────────────────────────────────────────────
    evidence_snapshot_id:     str
    reasoning_snapshot_id:    str
    confidence_snapshot_id:   str
    risk_snapshot_id:         str
    explanation_snapshot_id:  str
    # ── Metadata ───────────────────────────────────────────────────────────
    participating_members: Tuple[str, ...]
    duration_ms:        float
    created_at:         datetime

    @property
    def is_approved(self) -> bool:
        return self.position == CommitteePosition.PROCEED_TO_RECOMMENDATION

    @property
    def minority_count(self) -> int:
        return len(self.minority_reports)

    @property
    def is_high_quality(self) -> bool:
        return self.committee_grade in {CommitteeGrade.A, CommitteeGrade.B}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "session_id":         self.session_id,
            "decision_id":        self.decision_id,
            "subject_id":         self.subject_id,
            "subject_type":       self.subject_type,
            "version":            self.version,
            "position":           self.position.value,
            "committee_score":    round(self.committee_score, 2),
            "committee_grade":    self.committee_grade.value,
            "committee_confidence": round(self.committee_confidence, 2),
            "vote_summary":       self.vote_summary.to_dict(),
            "minority_count":     self.minority_count,
            "minority_reports":   [m.to_dict() for m in self.minority_reports],
            "challenge_count":    self.challenge_count,
            "resolved_count":     self.resolved_count,
            "rounds_count":       len(self.rounds),
            "findings":           self.findings.to_dict(),
            "executive_summary":  self.executive_summary,
            "participating_members": list(self.participating_members),
            "evidence_snapshot_id":    self.evidence_snapshot_id,
            "reasoning_snapshot_id":   self.reasoning_snapshot_id,
            "confidence_snapshot_id":  self.confidence_snapshot_id,
            "risk_snapshot_id":        self.risk_snapshot_id,
            "explanation_snapshot_id": self.explanation_snapshot_id,
            "duration_ms":        round(self.duration_ms, 2),
            "created_at":         self.created_at.isoformat(),
            "is_approved":        self.is_approved,
            "stance":             self.stance.to_dict(),
        }


def build_committee_report(
    session_id:       str,
    decision_id:      str,
    subject_id:       str,
    subject_type:     str,
    version:          int,
    position:         CommitteePosition,
    stance:           CommitteeStance,
    committee_score:  float,
    committee_confidence: float,
    vote_summary:     VoteSummary,
    opinions:         List[MemberOpinion],
    minority_reports: List[MinorityReport],
    rounds:           List[RoundResult],
    challenge_count:  int,
    resolved_count:   int,
    findings:         CommitteeFindings,
    executive_summary: str,
    evidence_snapshot_id:    str,
    reasoning_snapshot_id:   str,
    confidence_snapshot_id:  str,
    risk_snapshot_id:        str,
    explanation_snapshot_id: str,
    participating_members:   List[str],
    duration_ms:      float,
) -> CommitteeReport:
    return CommitteeReport(
        report_id                = str(uuid.uuid4()),
        session_id               = session_id,
        decision_id              = decision_id,
        subject_id               = subject_id,
        subject_type             = subject_type,
        version                  = version,
        position                 = position,
        stance                   = stance,
        committee_score          = round(committee_score, 4),
        committee_grade          = CommitteeGrade.from_score(committee_score),
        committee_confidence     = round(committee_confidence, 4),
        vote_summary             = vote_summary,
        opinions                 = tuple(opinions),
        minority_reports         = tuple(minority_reports),
        rounds                   = tuple(rounds),
        challenge_count          = challenge_count,
        resolved_count           = resolved_count,
        findings                 = findings,
        executive_summary        = executive_summary,
        evidence_snapshot_id     = evidence_snapshot_id,
        reasoning_snapshot_id    = reasoning_snapshot_id,
        confidence_snapshot_id   = confidence_snapshot_id,
        risk_snapshot_id         = risk_snapshot_id,
        explanation_snapshot_id  = explanation_snapshot_id,
        participating_members    = tuple(participating_members),
        duration_ms              = round(duration_ms, 2),
        created_at               = datetime.now(timezone.utc),
    )
