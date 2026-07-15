"""iios/investment/portfolio/rebalancing/rebalance_forecast.py

Forward-looking benefit forecast for rebalancing plans.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.rebalancing.allocation_drift import AllocationDrift
from iios.investment.portfolio.rebalancing.execution_estimator import ExecutionEstimate
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    DRIFT_THRESHOLD_CRITICAL, CurrentPosition, TargetPosition,
)
from iios.investment.portfolio.rebalancing.trade_planner import TradePlan


@dataclass(frozen=True)
class RebalanceForecast:
    """Expected benefits from executing the rebalancing plan."""

    forecast_id:           str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:          str   = ""

    # Drift outcomes
    current_total_drift:   float = 0.0
    expected_post_drift:   float = 0.0
    expected_drift_reduction_pct: float = 0.0   # [0, 1]

    # Return impact
    expected_return_benefit:  float = 0.0   # annualized return improvement proxy
    expected_risk_benefit:    float = 0.0   # risk reduction proxy

    # Cost vs benefit
    total_cost_pct:        float = 0.0
    net_benefit_pct:       float = 0.0   # benefit - cost
    months_to_breakeven:   float = 0.0   # how long to recover rebalancing costs

    # Confidence
    forecast_confidence:   float = 0.0
    is_reliable:           bool  = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_total_drift":         round(self.current_total_drift, 4),
            "expected_post_drift":         round(self.expected_post_drift, 4),
            "expected_drift_reduction_pct":round(self.expected_drift_reduction_pct, 4),
            "expected_return_benefit":     round(self.expected_return_benefit, 4),
            "total_cost_pct":              round(self.total_cost_pct, 4),
            "net_benefit_pct":             round(self.net_benefit_pct, 4),
            "months_to_breakeven":         round(self.months_to_breakeven, 1),
            "forecast_confidence":         round(self.forecast_confidence, 4),
        }


def forecast_rebalance_benefit(
    alloc_drift:   AllocationDrift,
    trade_plan:    TradePlan,
    execution_est: Optional[ExecutionEstimate] = None,
    portfolio_id:  str = "",
) -> RebalanceForecast:
    """
    Estimate the forward-looking benefits of executing the rebalancing plan.

    Return benefit proxy: each percentage point of drift costs ~2–3bps per year
    in tracking error drag on expected returns.
    """
    if execution_est is None:
        execution_est = trade_plan.execution_estimate

    pre_drift   = alloc_drift.total_abs_drift
    post_drift  = _estimate_post_drift(alloc_drift, trade_plan)
    reduction   = (pre_drift - post_drift) / max(pre_drift, 1e-10)

    # Return benefit proxy: drift × 0.0003 annual return drag per unit drift
    # (i.e. 1% drift → 3bps performance drag if not corrected)
    return_benefit = (pre_drift - post_drift) * 0.03   # annualized
    risk_benefit   = (pre_drift - post_drift) * 0.015  # annualized risk reduction

    total_cost = execution_est.total_cost_pct if execution_est else 0.0
    net_benefit = return_benefit - total_cost

    # Months to breakeven: cost / (monthly benefit)
    monthly_benefit = return_benefit / 12.0
    breakeven = total_cost / max(monthly_benefit, 1e-10)
    breakeven = min(breakeven, 120.0)   # cap at 10 years

    # Confidence: based on number of positions and quality of drift data
    n_conf = min(1.0, alloc_drift.n_positions_current / 10.0)
    confidence = 0.6 * n_conf + 0.4 * min(1.0, pre_drift / DRIFT_THRESHOLD_CRITICAL)

    return RebalanceForecast(
        portfolio_id                 = portfolio_id,
        current_total_drift          = round(pre_drift, 4),
        expected_post_drift          = round(post_drift, 4),
        expected_drift_reduction_pct = round(reduction, 4),
        expected_return_benefit      = round(return_benefit, 6),
        expected_risk_benefit        = round(risk_benefit, 6),
        total_cost_pct               = round(total_cost, 6),
        net_benefit_pct              = round(net_benefit, 6),
        months_to_breakeven          = round(breakeven, 1),
        forecast_confidence          = round(confidence, 4),
        is_reliable                  = confidence >= 0.50 and alloc_drift.n_positions_current >= 3,
    )


def _estimate_post_drift(drift: AllocationDrift, plan: TradePlan) -> float:
    """Estimate residual drift after executing trades."""
    change_map = {c.symbol: c.abs_change for c in plan.changes}
    residual = 0.0
    for pd in drift.position_drifts:
        applied  = change_map.get(pd.symbol, 0.0)
        remaining = max(0.0, pd.abs_drift - applied)
        residual += remaining
    return residual
