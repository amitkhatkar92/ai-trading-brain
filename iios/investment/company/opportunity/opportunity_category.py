"""iios/investment/company/opportunity/opportunity_category.py
Classification result dataclass and supporting structures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.opportunity.opportunity_profile import OpportunityCategory


@dataclass
class ClassificationResult:
    """Output of ClassificationEngine for a single company evaluation."""
    primary:    OpportunityCategory
    secondary:  List[OpportunityCategory] = field(default_factory=list)
    confidence: float = 0.5    # 0-1
    rationale:  List[str] = field(default_factory=list)

    @property
    def all_categories(self) -> List[OpportunityCategory]:
        return [self.primary] + [c for c in self.secondary if c != self.primary]

    @property
    def is_actionable(self) -> bool:
        return self.primary not in (
            OpportunityCategory.WATCHLIST,
            OpportunityCategory.OBSERVATION_ONLY,
            OpportunityCategory.UNCLASSIFIED,
        )

    @property
    def is_value_oriented(self) -> bool:
        return self.primary in (
            OpportunityCategory.UNDERVALUED_QUALITY,
            OpportunityCategory.DEEP_VALUE,
            OpportunityCategory.RECOVERY,
            OpportunityCategory.TURNAROUND,
        )

    @property
    def is_growth_oriented(self) -> bool:
        return self.primary in (
            OpportunityCategory.HIGH_GROWTH,
            OpportunityCategory.COMPOUNDER,
            OpportunityCategory.INNOVATION_LEADER,
            OpportunityCategory.DIVIDEND_GROWTH,
        )

    @property
    def is_quality_oriented(self) -> bool:
        return self.primary in (
            OpportunityCategory.WIDE_MOAT,
            OpportunityCategory.COMPOUNDER,
            OpportunityCategory.CAPITAL_ALLOCATOR,
            OpportunityCategory.UNDERVALUED_QUALITY,
        )

    @property
    def is_income_oriented(self) -> bool:
        return self.primary in (
            OpportunityCategory.INCOME,
            OpportunityCategory.DIVIDEND_GROWTH,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary":     self.primary.value,
            "secondary":   [c.value for c in self.secondary],
            "confidence":  round(self.confidence, 3),
            "rationale":   self.rationale,
            "is_actionable":      self.is_actionable,
            "is_value_oriented":  self.is_value_oriented,
            "is_growth_oriented": self.is_growth_oriented,
        }


# ── Category metadata ─────────────────────────────────────────────────────────

_CATEGORY_DESCRIPTIONS: Dict[OpportunityCategory, str] = {
    OpportunityCategory.UNDERVALUED_QUALITY:
        "High-quality business trading at a discount to intrinsic value",
    OpportunityCategory.HIGH_GROWTH:
        "Company demonstrating above-average revenue or EPS growth trajectory",
    OpportunityCategory.COMPOUNDER:
        "High-ROIC business with reinvestment moat and compounding earnings power",
    OpportunityCategory.TURNAROUND:
        "Company recovering from prior losses or operational distress",
    OpportunityCategory.RECOVERY:
        "Business in earnings recovery phase following a cyclical or operational trough",
    OpportunityCategory.DEEP_VALUE:
        "Significantly discounted to tangible asset value or earnings power",
    OpportunityCategory.INCOME:
        "High and sustainable dividend yield with durable cash generation",
    OpportunityCategory.DIVIDEND_GROWTH:
        "Consistent dividend growth backed by expanding earnings and cash flows",
    OpportunityCategory.WIDE_MOAT:
        "Durable competitive advantage protecting above-average returns on capital",
    OpportunityCategory.CAPITAL_ALLOCATOR:
        "Management track record of exceptional capital deployment and shareholder returns",
    OpportunityCategory.INNOVATION_LEADER:
        "R&D-driven growth with expanding addressable market and margin trajectory",
    OpportunityCategory.CYCLICAL_RECOVERY:
        "Cyclical business near the trough with improving demand fundamentals",
    OpportunityCategory.SPECIAL_SITUATION:
        "Value creation event: spin-off, restructuring, merger arbitrage, or demerger",
    OpportunityCategory.WATCHLIST:
        "Interesting characteristics but insufficient conviction for active tracking",
    OpportunityCategory.OBSERVATION_ONLY:
        "Passive monitoring only; signal below conviction threshold",
    OpportunityCategory.UNCLASSIFIED:
        "Insufficient data for classification",
}


def get_category_description(category: OpportunityCategory) -> str:
    return _CATEGORY_DESCRIPTIONS.get(category, "Unknown category")
