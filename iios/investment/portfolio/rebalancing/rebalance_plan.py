"""iios/investment/portfolio/rebalancing/rebalance_plan.py

RebalancePlan: the primary output of the Portfolio Rebalancing Engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.portfolio.rebalancing.rebalancing_types import (
    RebalanceGrade, RebalanceLevel, RebalanceStatus,
    RebalanceTrigger, TradePriority, now_utc,
)


@dataclass(frozen=True)
class RebalancePlan:
    """
    Complete, auditable rebalancing plan for a portfolio.

    This is the canonical output of PortfolioRebalancingEngine.evaluate().
    Does NOT contain trade execution logic.
    """

    plan_id:              str                = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str                = ""
    version:              int                = 1
    created_at:           str                = field(default_factory=now_utc)

    # Policy context
    policy_id:            str                = ""
    policy_name:          str                = ""
    trigger:              RebalanceTrigger   = RebalanceTrigger.NONE
    status:               RebalanceStatus    = RebalanceStatus.PENDING

    # Position counts
    n_positions_current:  int                = 0
    n_positions_target:   int                = 0

    # Trade summary
    n_buys:               int                = 0
    n_sells:              int                = 0
    total_turnover:       float              = 0.0
    buy_turnover:         float              = 0.0
    sell_turnover:        float              = 0.0

    # Cost summary
    total_transaction_cost_pct: float        = 0.0
    total_market_impact_pct:    float        = 0.0
    total_tax_cost_pct:         float        = 0.0
    total_cost_pct:             float        = 0.0

    # Drift summary
    pre_rebalance_drift:        float        = 0.0
    expected_post_drift:        float        = 0.0
    expected_drift_reduction:   float        = 0.0   # fraction [0, 1]

    # Benefits
    expected_return_benefit:    float        = 0.0
    net_benefit_pct:            float        = 0.0
    months_to_breakeven:        float        = 0.0

    # Quality
    rebalance_score:            float        = 0.0
    performance_grade:          RebalanceGrade = RebalanceGrade.F
    performance_level:          RebalanceLevel = RebalanceLevel.POOR
    is_recommended:             bool         = False

    # Validation
    is_valid:                   bool         = True
    n_validation_warnings:      int          = 0
    primary_validation_failure: str          = ""

    # Attribution
    primary_drift_driver:       str          = ""
    most_drifted_position:      str          = ""
    most_drifted_sector:        str          = ""

    # Priority
    overall_priority:           TradePriority = TradePriority.MEDIUM

    # Forecast context
    forecast_confidence:        float        = 0.0

    # Metadata
    metadata:                   Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id":               self.plan_id,
            "portfolio_id":          self.portfolio_id,
            "version":               self.version,
            "created_at":            self.created_at,
            "trigger":               self.trigger.value,
            "status":                self.status.value,
            "n_buys":                self.n_buys,
            "n_sells":               self.n_sells,
            "total_turnover":        round(self.total_turnover, 4),
            "total_cost_pct":        round(self.total_cost_pct, 5),
            "pre_rebalance_drift":   round(self.pre_rebalance_drift, 4),
            "expected_drift_reduction": round(self.expected_drift_reduction, 4),
            "rebalance_score":       round(self.rebalance_score, 4),
            "grade":                 self.performance_grade.value,
            "is_recommended":        self.is_recommended,
            "is_valid":              self.is_valid,
            "overall_priority":      self.overall_priority.value,
        }
