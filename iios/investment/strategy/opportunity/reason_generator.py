"""iios/investment/strategy/opportunity/reason_generator.py
ReasonGenerator — converts EvidenceBundle into structured human-readable reasons.
"""
from __future__ import annotations

from typing import List

from iios.investment.strategy.opportunity.evidence_collector import Evidence, EvidenceBundle


class ReasonGenerator:
    """
    Generates ordered lists of reasons from an EvidenceBundle.
    Output is deterministic: ordered by confidence descending.
    """

    def why_selected(self, bundle: EvidenceBundle) -> List[str]:
        """Top reasons FOR recommending this strategy."""
        sorted_ev = sorted(bundle.supporting, key=lambda e: e.confidence, reverse=True)
        return [e.fact for e in sorted_ev[:6]]

    def why_caution(self, bundle: EvidenceBundle) -> List[str]:
        """Top reasons for CAUTION about this recommendation."""
        sorted_ev = sorted(bundle.contradicting, key=lambda e: e.confidence, reverse=True)
        return [e.fact for e in sorted_ev[:4]]

    def neutral_observations(self, bundle: EvidenceBundle) -> List[str]:
        """Neutral observations to inform decision-making."""
        return [e.fact for e in bundle.neutral[:4]]

    def confidence_explanation(self, bundle: EvidenceBundle) -> str:
        nc = bundle.net_confidence
        if nc >= 0.80:
            return f"High recommendation confidence ({nc:.0%}): strong supporting evidence with minimal contradiction."
        if nc >= 0.60:
            return f"Moderate recommendation confidence ({nc:.0%}): majority of signals are supportive."
        if nc >= 0.40:
            return f"Low-moderate confidence ({nc:.0%}): mixed signals — review caution factors carefully."
        return f"Low confidence ({nc:.0%}): significant contradicting evidence present."

    def generate_headline(
        self, strategy_name: str, opportunity_type: str, rank: int
    ) -> str:
        ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(rank, f"{rank}th")
        return (
            f"{strategy_name} is the {ordinal} ranked strategy for "
            f"'{opportunity_type}' opportunity."
        )
