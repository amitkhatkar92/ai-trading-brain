"""iios/investment/portfolio/integration/consistency_rules.py

Pure cross-engine consistency rule functions.
Each returns (triggered: bool, reason: str).
All thresholds are explicit parameters — no hardcoded values.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

Rule = Tuple[bool, str]


def check_allocation_weights_sum(
    allocation_data: Dict[str, Any],
    tolerance:       float,
) -> Rule:
    """Allocation weights (equity + bond + cash + alternative) should sum to ~1.0."""
    equity = allocation_data.get("equity_weight",      0.0)
    bond   = allocation_data.get("bond_weight",        0.0)
    cash   = allocation_data.get("cash_weight",        0.0)
    alt    = allocation_data.get("alternative_weight", 0.0)
    total  = equity + bond + cash + alt
    if abs(total - 1.0) > tolerance:
        return (True,
                f"Allocation weights sum {total:.4f}, expected 1.0 ± {tolerance:.4f}")
    return (False, f"Allocation weights sum OK ({total:.4f})")


def check_construction_allocation_position_count(
    construction_n_positions: int,
    allocation_n_positions:   Optional[int],
    tolerance:                int,
) -> Rule:
    """Construction and allocation should agree on approximate position count."""
    if allocation_n_positions is None:
        return (False, "Allocation position count not provided — skipping")
    diff = abs(construction_n_positions - allocation_n_positions)
    if diff > tolerance:
        return (True,
                f"Position count mismatch: construction={construction_n_positions}, "
                f"allocation={allocation_n_positions} (diff {diff} > {tolerance})")
    return (False, f"Position counts consistent ({construction_n_positions} vs {allocation_n_positions})")


def check_optimization_vs_construction_quality(
    optimization_quality: float,
    construction_quality: float,
    max_gap:              float,
) -> Rule:
    """Optimization quality should not be drastically below construction quality."""
    gap = construction_quality - optimization_quality
    if gap > max_gap:
        return (True,
                f"Optimization quality {optimization_quality:.3f} is {gap:.3f} below "
                f"construction quality {construction_quality:.3f} (threshold {max_gap:.3f})")
    return (False, "Optimization and construction quality consistent")


def check_risk_performance_drawdown(
    risk_max_drawdown:        float,
    performance_max_drawdown: float,
    tolerance:                float,
) -> Rule:
    """Risk and performance engines should agree on maximum drawdown."""
    diff = abs(risk_max_drawdown - performance_max_drawdown)
    if diff > tolerance:
        return (True,
                f"Drawdown mismatch: risk={risk_max_drawdown:.3f}, "
                f"performance={performance_max_drawdown:.3f} (diff {diff:.3f} > {tolerance:.3f})")
    return (False, "Drawdown values consistent across risk and performance engines")


def check_rebalancing_vs_allocation_drift(
    rebalancing_drift_level: str,
    allocation_equity_drift: float,
    significant_threshold:   float,
) -> Rule:
    """If allocation shows significant drift, rebalancing should acknowledge it."""
    drift_significant = abs(allocation_equity_drift) > significant_threshold
    rebal_acknowledges = rebalancing_drift_level in ("significant", "critical")
    if drift_significant and not rebal_acknowledges:
        return (True,
                f"Allocation equity drift {allocation_equity_drift:.1%} is significant "
                f"but rebalancing drift_level='{rebalancing_drift_level}'")
    return (False, "Rebalancing acknowledges allocation drift correctly")


def check_recommendation_vs_risk_budget(
    recommendation_action:   str,
    risk_budget_utilization: float,
    risk_threshold:          float,
) -> Rule:
    """Aggressive positioning recommendation should not appear when risk budget is near limit."""
    if risk_budget_utilization > risk_threshold and recommendation_action == "aggressive_positioning":
        return (True,
                f"Aggressive positioning recommended while risk budget is "
                f"{risk_budget_utilization:.1%} (> {risk_threshold:.1%})")
    return (False, "Recommendation aligned with risk budget posture")


def check_diversification_hhi(
    hhi:           float,
    hhi_threshold: float,
) -> Rule:
    """Portfolio concentration HHI should not exceed the institutional threshold."""
    if hhi > hhi_threshold:
        return (True,
                f"Concentration HHI {hhi:.3f} exceeds threshold {hhi_threshold:.3f}")
    return (False, f"HHI {hhi:.3f} within acceptable range")
