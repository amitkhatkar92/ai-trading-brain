"""iios/investment/portfolio/construction/selection_policy.py

Selection policy governing how recommendations are scored, ranked,
and chosen as portfolio candidates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.portfolio.construction.construction_types import (
    ConstructionDirection,
    SelectionCriterion,
)


@dataclass(frozen=True)
class SelectionPolicy:
    """
    Immutable parameter set controlling how InvestmentRecommendations are
    scored and ranked before weight assignment.

    The policy encodes:
      • quality thresholds (minimum conviction / confidence / risk)
      • ranking criterion (which score dimension drives ordering)
      • tie-breaking rules (deterministic — alphabetical by symbol)
      • expiry handling
    """

    policy_name:        str                = "default"

    # Ranking / scoring
    primary_criterion:  SelectionCriterion = SelectionCriterion.COMPOSITE
    conviction_weight:  float              = 0.40   # share in composite score
    confidence_weight:  float              = 0.40
    quality_weight:     float              = 0.20   # quality_score = conf*(1-risk)

    # Quality gates — recommendations below these thresholds are excluded
    min_conviction:     float              = 0.30
    min_confidence:     float              = 0.30
    max_risk_score:     float              = 0.80

    # Holding-count limits
    max_long_holdings:  int                = 30
    max_short_holdings: int                = 0

    # Expiry
    exclude_expired:    bool               = True

    # Duplicates — if the same symbol appears with multiple recs, keep best only
    deduplicate:        bool               = True

    def score(self, rec: Any) -> float:
        """Compute a selection score for a single InvestmentRecommendation."""
        if self.primary_criterion == SelectionCriterion.CONVICTION:
            return rec.conviction
        if self.primary_criterion == SelectionCriterion.CONFIDENCE:
            return rec.confidence
        if self.primary_criterion == SelectionCriterion.RISK_ADJUSTED:
            return rec.quality_score
        # COMPOSITE
        return (
            self.conviction_weight  * rec.conviction
            + self.confidence_weight * rec.confidence
            + self.quality_weight   * rec.quality_score
        )

    def passes_quality_gates(self, rec: Any) -> bool:
        """Return True if a recommendation meets all quality thresholds."""
        if self.exclude_expired and rec.is_expired:
            return False
        if rec.conviction < self.min_conviction:
            return False
        if rec.confidence < self.min_confidence:
            return False
        if rec.risk_score > self.max_risk_score:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":       self.policy_name,
            "primary_criterion": self.primary_criterion.value,
            "conviction_weight": self.conviction_weight,
            "confidence_weight": self.confidence_weight,
            "quality_weight":    self.quality_weight,
            "min_conviction":    self.min_conviction,
            "min_confidence":    self.min_confidence,
            "max_risk_score":    self.max_risk_score,
            "max_long_holdings": self.max_long_holdings,
            "max_short_holdings":self.max_short_holdings,
            "exclude_expired":   self.exclude_expired,
            "deduplicate":       self.deduplicate,
        }


# ---------------------------------------------------------------------------
# Built-in policies
# ---------------------------------------------------------------------------

CONSERVATIVE_POLICY = SelectionPolicy(
    policy_name="conservative",
    primary_criterion=SelectionCriterion.RISK_ADJUSTED,
    min_conviction=0.50,
    min_confidence=0.55,
    max_risk_score=0.55,
    max_long_holdings=20,
)

BALANCED_POLICY = SelectionPolicy(
    policy_name="balanced",
    primary_criterion=SelectionCriterion.COMPOSITE,
    min_conviction=0.35,
    min_confidence=0.35,
    max_risk_score=0.70,
    max_long_holdings=30,
)

AGGRESSIVE_POLICY = SelectionPolicy(
    policy_name="aggressive",
    primary_criterion=SelectionCriterion.CONVICTION,
    min_conviction=0.20,
    min_confidence=0.20,
    max_risk_score=0.90,
    max_long_holdings=50,
)

INCOME_POLICY = SelectionPolicy(
    policy_name="income",
    primary_criterion=SelectionCriterion.COMPOSITE,
    min_conviction=0.40,
    min_confidence=0.40,
    max_risk_score=0.60,
    max_long_holdings=25,
)


_BUILT_IN_POLICIES: Dict[str, SelectionPolicy] = {
    "conservative": CONSERVATIVE_POLICY,
    "balanced":     BALANCED_POLICY,
    "aggressive":   AGGRESSIVE_POLICY,
    "income":       INCOME_POLICY,
}


def get_policy(name: str) -> Optional[SelectionPolicy]:
    """Retrieve a built-in policy by name."""
    return _BUILT_IN_POLICIES.get(name)
