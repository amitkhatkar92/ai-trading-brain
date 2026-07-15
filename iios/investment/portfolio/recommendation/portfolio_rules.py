"""iios/investment/portfolio/recommendation/portfolio_rules.py

Pure rule functions for portfolio condition evaluation.
Each function returns (triggered: bool, reason: str).
All thresholds are explicit parameters — no hardcoded values.
"""
from __future__ import annotations

from typing import Tuple

Rule = Tuple[bool, str]


# ---------------------------------------------------------------------------
# Risk rules
# ---------------------------------------------------------------------------

def evaluate_risk_overextension(
    risk_budget_utilization: float,
    threshold:               float,
) -> Rule:
    """Trigger if risk budget utilization exceeds threshold."""
    if risk_budget_utilization > threshold:
        return (True,
                f"Risk budget {risk_budget_utilization:.1%} exceeds threshold {threshold:.1%}")
    return (False,
            f"Risk budget {risk_budget_utilization:.1%} within limit {threshold:.1%}")


def evaluate_var_breach(
    var_utilization: float,
    threshold:       float,
) -> Rule:
    """Trigger if Value-at-Risk utilization exceeds critical threshold."""
    if var_utilization > threshold:
        return (True,
                f"VaR utilization {var_utilization:.1%} exceeds critical {threshold:.1%}")
    return (False, f"VaR utilization {var_utilization:.1%} within limit")


def evaluate_drawdown_severity(
    max_drawdown: float,
    threshold:    float,
) -> Rule:
    """Trigger if maximum drawdown exceeds severe threshold."""
    if max_drawdown > threshold:
        return (True,
                f"Maximum drawdown {max_drawdown:.1%} exceeds severe threshold {threshold:.1%}")
    return (False, f"Drawdown {max_drawdown:.1%} within tolerance")


def evaluate_risk_capacity(
    risk_budget_utilization: float,
    low_threshold:           float,
) -> Rule:
    """Trigger if risk budget is underutilized — capacity to increase exposure."""
    if risk_budget_utilization < low_threshold:
        return (True,
                f"Risk budget only {risk_budget_utilization:.1%} utilized — "
                f"capacity to increase exposure (threshold {low_threshold:.1%})")
    return (False, f"Risk budget {risk_budget_utilization:.1%} ≥ low threshold")


# ---------------------------------------------------------------------------
# Allocation rules
# ---------------------------------------------------------------------------

def evaluate_equity_overweight(
    equity_drift: float,
    threshold:    float,
) -> Rule:
    """Trigger if equity is overweight relative to target (positive drift)."""
    if equity_drift > threshold:
        return (True,
                f"Equity overweight by {equity_drift:.1%} (threshold {threshold:.1%})")
    return (False, f"Equity drift {equity_drift:.1%} within limit")


def evaluate_equity_underweight(
    equity_drift: float,
    threshold:    float,
) -> Rule:
    """Trigger if equity is underweight relative to target (negative drift)."""
    if equity_drift < -threshold:
        return (True,
                f"Equity underweight by {abs(equity_drift):.1%} (threshold {threshold:.1%})")
    return (False, f"Equity drift {equity_drift:.1%} within limit")


def evaluate_cash_excess(
    cash_weight:     float,
    high_threshold:  float,
) -> Rule:
    """Trigger if cash allocation is excessively high."""
    if cash_weight > high_threshold:
        return (True,
                f"Cash {cash_weight:.1%} exceeds high threshold {high_threshold:.1%} — deploy capital")
    return (False, f"Cash {cash_weight:.1%} within limit")


def evaluate_cash_deficiency(
    cash_weight:    float,
    low_threshold:  float,
) -> Rule:
    """Trigger if cash allocation is critically low — limited defensive buffer."""
    if cash_weight < low_threshold:
        return (True,
                f"Cash {cash_weight:.1%} below minimum {low_threshold:.1%} — raise defensive buffer")
    return (False, f"Cash {cash_weight:.1%} adequate")


def evaluate_international_underweight(
    international_weight: float,
    threshold:            float,
) -> Rule:
    """Trigger if international allocation is below institutional minimum."""
    if international_weight < threshold:
        return (True,
                f"International exposure {international_weight:.1%} below "
                f"minimum {threshold:.1%}")
    return (False, f"International exposure {international_weight:.1%} adequate")


# ---------------------------------------------------------------------------
# Diversification rules
# ---------------------------------------------------------------------------

def evaluate_concentration(
    hhi:       float,
    threshold: float,
) -> Rule:
    """Trigger if Herfindahl-Hirschman Index exceeds concentration threshold."""
    if hhi > threshold:
        return (True,
                f"HHI {hhi:.3f} exceeds concentration threshold {threshold:.3f} — reduce concentration")
    return (False, f"HHI {hhi:.3f} within diversification limit")


def evaluate_insufficient_positions(
    effective_positions: float,
    min_positions:       float,
) -> Rule:
    """Trigger if effective number of positions is too low."""
    if effective_positions < min_positions:
        return (True,
                f"Effective positions {effective_positions:.1f} < minimum {min_positions:.1f}")
    return (False, f"Effective positions {effective_positions:.1f} adequate")


def evaluate_sector_concentration(
    max_sector_weight: float,
    threshold:         float,
) -> Rule:
    """Trigger if any single sector dominates."""
    if max_sector_weight > threshold:
        return (True,
                f"Sector concentration {max_sector_weight:.1%} exceeds {threshold:.1%} — reduce sector exposure")
    return (False, f"Sector concentration {max_sector_weight:.1%} within limit")


# ---------------------------------------------------------------------------
# Performance rules
# ---------------------------------------------------------------------------

def evaluate_sharpe_deterioration(
    sharpe_ratio: float,
    threshold:    float,
) -> Rule:
    """Trigger if Sharpe ratio falls below institutional minimum."""
    if sharpe_ratio < threshold:
        return (True,
                f"Sharpe ratio {sharpe_ratio:.3f} below minimum {threshold:.3f} — review required")
    return (False, f"Sharpe ratio {sharpe_ratio:.3f} ≥ minimum")


def evaluate_information_ratio_poor(
    information_ratio: float,
    threshold:         float,
) -> Rule:
    """Trigger if information ratio is negative or below threshold."""
    if information_ratio < threshold:
        return (True,
                f"Information ratio {information_ratio:.3f} below threshold {threshold:.3f}")
    return (False, f"Information ratio {information_ratio:.3f} acceptable")


def evaluate_calmar_deterioration(
    calmar_ratio: float,
    threshold:    float,
) -> Rule:
    """Trigger if Calmar ratio (return/max_drawdown) falls below threshold."""
    if calmar_ratio < threshold:
        return (True,
                f"Calmar ratio {calmar_ratio:.3f} below threshold {threshold:.3f}")
    return (False, f"Calmar ratio {calmar_ratio:.3f} adequate")


# ---------------------------------------------------------------------------
# Quality rules
# ---------------------------------------------------------------------------

def evaluate_construction_quality(
    construction_quality: float,
    minimum:              float,
) -> Rule:
    """Trigger if portfolio construction quality falls below minimum."""
    if construction_quality < minimum:
        return (True,
                f"Construction quality {construction_quality:.3f} below minimum {minimum:.3f}")
    return (False, f"Construction quality {construction_quality:.3f} acceptable")


def evaluate_optimization_quality(
    optimization_quality: float,
    minimum:              float,
) -> Rule:
    """Trigger if optimization quality falls below minimum (not at efficient frontier)."""
    if optimization_quality < minimum:
        return (True,
                f"Optimization quality {optimization_quality:.3f} below minimum {minimum:.3f} — not at efficient frontier")
    return (False, f"Optimization quality {optimization_quality:.3f} acceptable")


# ---------------------------------------------------------------------------
# Rebalancing rules
# ---------------------------------------------------------------------------

def evaluate_rebalance_trigger(
    rebalance_recommended: bool,
    drift_level:           str,
    significant_levels:    tuple = ("significant", "critical"),
) -> Rule:
    """Trigger if rebalancing engine recommends rebalancing."""
    if rebalance_recommended:
        return (True,
                f"Rebalancing engine recommends rebalance (drift level: {drift_level})")
    if drift_level in significant_levels:
        return (True,
                f"Significant drift detected (level: {drift_level}) — consider rebalancing")
    return (False, f"No rebalancing trigger (drift: {drift_level})")


# ---------------------------------------------------------------------------
# Composite / positioning rules
# ---------------------------------------------------------------------------

def evaluate_defensive_signal(
    risk_budget_utilization: float,
    max_drawdown:            float,
    risk_threshold:          float,
    drawdown_threshold:      float,
) -> Rule:
    """Trigger if multiple risk signals point to defensive positioning."""
    risk_high = risk_budget_utilization > risk_threshold
    dd_severe = max_drawdown > drawdown_threshold
    if risk_high and dd_severe:
        return (True,
                f"Defensive positioning triggered: risk {risk_budget_utilization:.1%} and "
                f"drawdown {max_drawdown:.1%} both elevated")
    if risk_high:
        return (False, f"Risk high but drawdown {max_drawdown:.1%} manageable")
    if dd_severe:
        return (False, f"Drawdown elevated but risk {risk_budget_utilization:.1%} manageable")
    return (False, "No defensive trigger")


def evaluate_hedge_signal(
    var_utilization:     float,
    max_drawdown:        float,
    var_threshold:       float,
    drawdown_threshold:  float,
) -> Rule:
    """Trigger if VaR utilization or drawdown is severe enough to warrant hedging."""
    if var_utilization > var_threshold:
        return (True,
                f"Hedge signal: VaR utilization {var_utilization:.1%} > {var_threshold:.1%}")
    if max_drawdown > drawdown_threshold:
        return (True,
                f"Hedge signal: severe drawdown {max_drawdown:.1%} > {drawdown_threshold:.1%}")
    return (False, "No hedge trigger")


def evaluate_aggressive_signal(
    risk_budget_utilization: float,
    sharpe_ratio:            float,
    low_risk_threshold:      float,
    good_sharpe_threshold:   float,
) -> Rule:
    """Trigger if portfolio has headroom AND strong performance metrics."""
    has_capacity  = risk_budget_utilization < low_risk_threshold
    good_perf     = sharpe_ratio >= good_sharpe_threshold
    if has_capacity and good_perf:
        return (True,
                f"Aggressive positioning: risk capacity {risk_budget_utilization:.1%} with "
                f"strong Sharpe {sharpe_ratio:.2f}")
    return (False, "Insufficient signal for aggressive positioning")
