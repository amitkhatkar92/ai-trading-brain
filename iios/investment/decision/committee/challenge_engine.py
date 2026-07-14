"""iios/investment/decision/committee/challenge_engine.py
ChallengeEngine — generates and resolves challenges between specialists.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.committee.committee_constants import (
    CHALLENGE_SEVERITY_THRESHOLD,
    ChallengeType,
    VoteType,
)
from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.committee_member import MemberOpinion


@dataclass(frozen=True)
class Challenge:
    challenge_id:    str
    challenger_id:   str
    challenge_type:  ChallengeType
    target_domain:   str          # dimension being challenged
    severity:        float        # 0–100
    description:     str
    rebuttal_score:  float        # 0–100 (how well evidence rebuts the challenge)
    is_resolved:     bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id":   self.challenge_id,
            "challenger_id":  self.challenger_id,
            "challenge_type": self.challenge_type.value,
            "target_domain":  self.target_domain,
            "severity":       round(self.severity, 2),
            "description":    self.description,
            "rebuttal_score": round(self.rebuttal_score, 2),
            "is_resolved":    self.is_resolved,
        }


class ChallengeEngine:
    """
    Generates Challenges based on specialist opinions and resolves them
    against the CommitteeContext.
    """

    def generate(
        self,
        opinions: List[MemberOpinion],
        ctx:      CommitteeContext,
    ) -> List[Challenge]:
        challenges: List[Challenge] = []
        cid_seq = 0

        for opinion in opinions:
            for raw_challenge in opinion.challenges:
                cid_seq += 1
                c_type, severity = self._classify_challenge(raw_challenge, ctx)
                rebuttal = self._compute_rebuttal(c_type, ctx)
                is_resolved = rebuttal >= severity

                challenges.append(Challenge(
                    challenge_id   = f"CH-{cid_seq:04d}",
                    challenger_id  = opinion.member_id,
                    challenge_type = c_type,
                    target_domain  = opinion.specialist_type.value,
                    severity       = severity,
                    description    = raw_challenge,
                    rebuttal_score = rebuttal,
                    is_resolved    = is_resolved,
                ))

        return challenges

    def count_resolved(self, challenges: List[Challenge]) -> int:
        return sum(1 for c in challenges if c.is_resolved)

    # ── Private ────────────────────────────────────────────────────────────────

    def _classify_challenge(
        self, text: str, ctx: CommitteeContext,
    ) -> Tuple[ChallengeType, float]:
        t = text.lower()
        if "compliance" in t or "policy" in t or "block" in t:
            return ChallengeType.COMPLIANCE_CONCERN, 90.0
        if "insufficient" in t or "thin" in t or "no " in t:
            return ChallengeType.INSUFFICIENT_EVIDENCE, 70.0
        if "low confidence" in t or "uncertain" in t:
            return ChallengeType.LOW_CONFIDENCE, 60.0
        if "high risk" in t or "elevated" in t:
            return ChallengeType.HIGH_RISK, 65.0
        if "stale" in t or "outdated" in t:
            return ChallengeType.STALE_EVIDENCE, 55.0
        if "inconsistent" in t or "reasoning" in t:
            return ChallengeType.INCONSISTENT_REASONING, 50.0
        if "quality" in t:
            return ChallengeType.EVIDENCE_QUALITY, 55.0
        return ChallengeType.MISSING_DOMAIN, 45.0

    def _compute_rebuttal(self, c_type: ChallengeType, ctx: CommitteeContext) -> float:
        """
        How well the available evidence rebuts this challenge type.
        Returns 0–100.  If rebuttal >= severity the challenge is resolved.
        """
        if c_type == ChallengeType.COMPLIANCE_CONCERN:
            # Only the actual policy status can rebut this
            from iios.investment.decision.risk.risk_constants import RiskPolicyStatus
            if ctx.risk.blocks_execution:
                return 0.0  # cannot be rebutted
            if ctx.risk.policy_status == RiskPolicyStatus.VIOLATION:
                return 0.0
            return 80.0

        if c_type == ChallengeType.INSUFFICIENT_EVIDENCE:
            count = ctx.evidence.item_count
            return min(100.0, count * 12.0)  # 9 items → 100%

        if c_type == ChallengeType.LOW_CONFIDENCE:
            return ctx.confidence.overall_confidence

        if c_type == ChallengeType.HIGH_RISK:
            # Rebuttal: risk is actually low
            return max(0.0, 100.0 - ctx.risk.overall_risk)

        if c_type == ChallengeType.STALE_EVIDENCE:
            return min(100.0, ctx.evidence.overall_freshness * 100.0)

        if c_type == ChallengeType.INCONSISTENT_REASONING:
            return min(100.0, ctx.explanation.explanation.logic_consistency * 100.0)

        if c_type == ChallengeType.EVIDENCE_QUALITY:
            return ctx.evidence.quality_score

        # MISSING_DOMAIN
        return max(0.0, ctx.evidence.quality_score - 10.0)
