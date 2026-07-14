"""iios/investment/decision/committee/committee_findings.py
CommitteeFindings — structured observations from the committee deliberation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.committee_member import MemberOpinion
from iios.investment.decision.committee.committee_constants import VoteType


@dataclass(frozen=True)
class CommitteeFindings:
    """Structured findings produced by the committee after deliberation."""
    supporting_observations: Tuple[str, ...]
    opposing_observations:   Tuple[str, ...]
    key_risks:               Tuple[str, ...]
    open_questions:          Tuple[str, ...]
    evidence_assessment:     str
    reasoning_assessment:    str
    confidence_assessment:   str
    risk_assessment:         str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supporting_observations": list(self.supporting_observations),
            "opposing_observations":   list(self.opposing_observations),
            "key_risks":               list(self.key_risks),
            "open_questions":          list(self.open_questions),
            "evidence_assessment":     self.evidence_assessment,
            "reasoning_assessment":    self.reasoning_assessment,
            "confidence_assessment":   self.confidence_assessment,
            "risk_assessment":         self.risk_assessment,
        }


class CommitteeFindingsBuilder:
    """Assembles CommitteeFindings from opinions + context."""

    def build(
        self,
        opinions: List[MemberOpinion],
        ctx:      CommitteeContext,
    ) -> CommitteeFindings:
        supporting: List[str] = []
        opposing:   List[str] = []
        risks:      List[str] = []
        questions:  List[str] = []

        for op in opinions:
            if op.effective_vote == VoteType.SUPPORT:
                for obs in op.observations:
                    supporting.append(f"[{op.specialist_type.value}] {obs}")
            elif op.effective_vote == VoteType.OPPOSE:
                for obs in op.observations:
                    opposing.append(f"[{op.specialist_type.value}] {obs}")
            for ch in op.challenges:
                if "risk" in ch.lower() or "block" in ch.lower():
                    risks.append(f"[{op.specialist_type.value}] {ch}")
                else:
                    questions.append(f"[{op.specialist_type.value}] {ch}")

        ev   = ctx.evidence
        conf = ctx.confidence
        risk = ctx.risk
        expl = ctx.explanation

        ev_assess   = (
            f"Evidence quality: {ev.quality_score:.1f}/100. "
            f"Item count: {ev.item_count}. "
            f"Coverage: {ev.coverage_fraction:.0%}. "
            f"Freshness: {ev.overall_freshness:.2f}."
        )
        reas_assess = (
            f"Reasoning steps: {expl.explanation.reasoning_step_count}. "
            f"Logic consistency: {expl.explanation.logic_consistency:.2f}. "
            f"Explainability: {expl.explainability_score:.1f}/100."
        )
        conf_assess = (
            f"Overall confidence: {conf.overall_confidence:.1f}/100 "
            f"({conf.confidence_level.value}). "
            f"Calibration: {conf.calibration_status.value}."
        )
        risk_assess = (
            f"Overall risk: {risk.overall_risk:.1f}/100 ({risk.risk_level.value}). "
            f"Blocks execution: {risk.blocks_execution}."
        )

        return CommitteeFindings(
            supporting_observations = tuple(supporting[:15]),   # cap for readability
            opposing_observations   = tuple(opposing[:15]),
            key_risks               = tuple(risks[:10]),
            open_questions          = tuple(questions[:10]),
            evidence_assessment     = ev_assess,
            reasoning_assessment    = reas_assess,
            confidence_assessment   = conf_assess,
            risk_assessment         = risk_assess,
        )
