"""iios/investment/decision/committee/committee_recommendations.py
CommitteeStance — the committee's procedural recommendation about what happens next.

NOTE: This is NOT a Buy/Sell/Hold recommendation.
It describes only whether the committee is satisfied that the decision package
is ready to be forwarded to the Recommendation Engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from iios.investment.decision.committee.committee_constants import (
    CommitteePosition,
    ConsensusLevel,
)


@dataclass(frozen=True)
class CommitteeStance:
    """
    Procedural stance of the committee. Contains NO investment recommendations.
    The committee only decides whether the package is ready for the next stage.
    """
    position:              CommitteePosition
    consensus_level:       ConsensusLevel
    support_fraction:      float    # 0–1
    forwarding_approved:   bool     # True when position == PROCEED_TO_RECOMMENDATION
    required_conditions:   Tuple[str, ...]   # what must change for a DEFER to resolve
    governing_concerns:    Tuple[str, ...]   # concerns that led to BLOCKED / DEFER

    @property
    def is_actionable(self) -> bool:
        return self.forwarding_approved

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position":            self.position.value,
            "consensus_level":     self.consensus_level.value,
            "support_fraction":    round(self.support_fraction, 4),
            "forwarding_approved": self.forwarding_approved,
            "required_conditions": list(self.required_conditions),
            "governing_concerns":  list(self.governing_concerns),
        }


def build_committee_stance(
    position:         CommitteePosition,
    support_fraction: float,
    consensus_level:  ConsensusLevel,
    risk_concerns:    Tuple[str, ...],
    open_questions:   Tuple[str, ...],
) -> CommitteeStance:
    forwarding = position == CommitteePosition.PROCEED_TO_RECOMMENDATION
    conditions: Tuple[str, ...] = ()
    concerns   = risk_concerns

    if position == CommitteePosition.DEFER_PENDING_EVIDENCE:
        conditions = tuple(open_questions[:5]) if open_questions else (
            "Resolve open questions and resubmit with additional evidence",
        )
    elif position == CommitteePosition.INSUFFICIENT_EVIDENCE:
        conditions = ("Collect minimum required evidence items before resubmission",)
    elif position == CommitteePosition.BLOCKED:
        conditions = ("Resolve blocking risk/compliance issues before resubmission",)

    return CommitteeStance(
        position            = position,
        consensus_level     = consensus_level,
        support_fraction    = support_fraction,
        forwarding_approved = forwarding,
        required_conditions = conditions,
        governing_concerns  = concerns[:5],
    )
