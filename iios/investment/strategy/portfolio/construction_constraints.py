"""iios/investment/strategy/portfolio/construction_constraints.py
ConstructionConstraints — parameter set for portfolio construction.
Pluggable: different portfolios may use different constraint profiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ConstructionConstraints:
    """
    Controls permissible weight ranges and strategy count limits.
    All weight values in [0, 1].
    """
    # Weight limits
    min_weight:     float = 0.02   # floor for any active strategy
    max_weight:     float = 0.40   # ceiling for any active strategy
    max_concentration: float = 0.60  # top-3 strategies combined weight limit

    # Count limits
    min_strategies: int   = 2
    max_strategies: int   = 50

    # Eligibility gate
    require_approved: bool = False  # if True, only "approved" strategies allowed
    min_eval_score:   float = 0.0   # minimum evaluation score to be included

    # Rebalancing sensitivity
    rebalance_threshold: float = 0.05  # trigger rebalance if drift > 5%

    # Policy name
    policy_name: str = "default"

    def validate_strategy_count(self, n: int) -> bool:
        return self.min_strategies <= n <= self.max_strategies

    def validate_weight(self, w: float) -> bool:
        return self.min_weight <= w <= self.max_weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":      self.policy_name,
            "min_weight":       self.min_weight,
            "max_weight":       self.max_weight,
            "min_strategies":   self.min_strategies,
            "max_strategies":   self.max_strategies,
            "min_eval_score":   self.min_eval_score,
            "rebalance_threshold": self.rebalance_threshold,
        }


# ── built-in profiles ──────────────────────────────────────────────────────────

DEFAULT_CONSTRAINTS = ConstructionConstraints(policy_name="default")

CONCENTRATED_CONSTRAINTS = ConstructionConstraints(
    min_weight=0.05,
    max_weight=0.60,
    max_concentration=0.80,
    min_strategies=2,
    max_strategies=10,
    policy_name="concentrated",
)

DIVERSIFIED_CONSTRAINTS = ConstructionConstraints(
    min_weight=0.02,
    max_weight=0.25,
    max_concentration=0.50,
    min_strategies=5,
    max_strategies=50,
    policy_name="diversified",
)

INSTITUTIONAL_CONSTRAINTS = ConstructionConstraints(
    min_weight=0.02,
    max_weight=0.30,
    max_concentration=0.55,
    min_strategies=5,
    max_strategies=30,
    require_approved=True,
    min_eval_score=55.0,
    rebalance_threshold=0.04,
    policy_name="institutional",
)
