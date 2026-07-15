"""iios/investment/portfolio/rebalancing/rebalance_rules.py

Individual rebalancing rules. Each rule is a pure function that returns
(triggered: bool, reason: str).
"""
from __future__ import annotations

from typing import Tuple

from iios.investment.portfolio.rebalancing.allocation_drift import AllocationDrift
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    DRIFT_THRESHOLD_MODERATE, TAX_RATE_LTCG, TAX_RATE_STCG,
    CurrentPosition, DriftLevel,
)
from iios.investment.portfolio.rebalancing.risk_drift import RiskDrift

Rule = Tuple[bool, str]


# ---------------------------------------------------------------------------
# Threshold rule
# ---------------------------------------------------------------------------

def evaluate_threshold_rule(
    allocation_drift: AllocationDrift,
    drift_threshold:  float = DRIFT_THRESHOLD_MODERATE,
) -> Rule:
    """Trigger if any position's drift exceeds the threshold."""
    if allocation_drift.max_abs_drift >= drift_threshold:
        return (True,
                f"Max position drift {allocation_drift.max_abs_drift:.1%} "
                f"≥ threshold {drift_threshold:.1%}")
    return (False,
            f"Max drift {allocation_drift.max_abs_drift:.1%} below threshold {drift_threshold:.1%}")


# ---------------------------------------------------------------------------
# Calendar rule
# ---------------------------------------------------------------------------

def evaluate_calendar_rule(
    days_since_last_rebalance: int,
    frequency_days:            int,
    min_days_since_rebalance:  int = 14,
) -> Rule:
    """Trigger if enough time has elapsed since last rebalance."""
    if frequency_days <= 0:
        return (False, "Calendar rule disabled (frequency_days=0)")
    if days_since_last_rebalance < min_days_since_rebalance:
        return (False,
                f"Too soon: only {days_since_last_rebalance}d since last rebalance "
                f"(min {min_days_since_rebalance}d)")
    if days_since_last_rebalance >= frequency_days:
        return (True,
                f"Calendar trigger: {days_since_last_rebalance}d ≥ {frequency_days}d frequency")
    remaining = frequency_days - days_since_last_rebalance
    return (False, f"Calendar: {remaining}d remaining until next scheduled rebalance")


# ---------------------------------------------------------------------------
# Risk rule
# ---------------------------------------------------------------------------

def evaluate_risk_rule(
    risk_drift:        RiskDrift,
    max_portfolio_risk:float = 0.65,
    min_liquidity:     float = 0.50,
) -> Rule:
    """Trigger if portfolio risk or liquidity breaches institutional limits."""
    reasons = []
    if risk_drift.current_risk > max_portfolio_risk:
        reasons.append(
            f"Portfolio risk {risk_drift.current_risk:.2f} > limit {max_portfolio_risk:.2f}"
        )
    if risk_drift.current_liquidity < min_liquidity:
        reasons.append(
            f"Portfolio liquidity {risk_drift.current_liquidity:.2f} < floor {min_liquidity:.2f}"
        )
    if reasons:
        return (True, "; ".join(reasons))
    return (False, "Risk and liquidity within institutional limits")


# ---------------------------------------------------------------------------
# Volatility rule
# ---------------------------------------------------------------------------

def evaluate_volatility_rule(
    portfolio_vol:  float,
    vol_threshold:  float = 0.20,
) -> Rule:
    """Trigger if portfolio annual vol exceeds threshold."""
    if portfolio_vol > vol_threshold:
        return (True,
                f"Portfolio vol {portfolio_vol:.1%} > threshold {vol_threshold:.1%}")
    return (False,
            f"Portfolio vol {portfolio_vol:.1%} within tolerance")


# ---------------------------------------------------------------------------
# Tax rule
# ---------------------------------------------------------------------------

def evaluate_tax_rule(
    positions:             list,
    min_tax_saving:        float = 0.005,
    avoid_stcg_sells:      bool  = True,
) -> Rule:
    """
    Trigger if there is material tax advantage in rebalancing
    (e.g. harvesting losses or deferring STCG).
    """
    if not positions:
        return (False, "No positions to evaluate for tax rule")

    # Count positions with unrealized losses (tax-loss harvesting)
    harvestable = [
        p for p in positions
        if isinstance(p, CurrentPosition)
        and p.unrealized_gain < -min_tax_saving
    ]
    if harvestable:
        total_loss = sum(abs(p.unrealized_gain) for p in harvestable)
        return (True,
                f"Tax-loss harvesting: {len(harvestable)} positions with "
                f"total unrealized loss {total_loss:.1%}")

    # Check STCG avoidance
    if avoid_stcg_sells:
        stcg_exposure = [
            p for p in positions
            if isinstance(p, CurrentPosition) and not p.is_ltcg_eligible
        ]
        if stcg_exposure:
            stcg_w = sum(p.current_weight for p in stcg_exposure)
            if stcg_w > 0.20:
                return (False,
                        f"STCG avoidance: {stcg_w:.1%} of portfolio < 1 year; "
                        "delay until LTCG eligibility")

    return (False, "No material tax benefit identified")


# ---------------------------------------------------------------------------
# Cash-flow rule
# ---------------------------------------------------------------------------

def evaluate_cashflow_rule(
    net_cash_flow_pct: float,
    min_cashflow:      float = 0.05,
) -> Rule:
    """
    Trigger if there is a material cash inflow/outflow requiring allocation.
    """
    if abs(net_cash_flow_pct) >= min_cashflow:
        direction = "inflow" if net_cash_flow_pct > 0 else "outflow"
        return (True,
                f"Cash-flow trigger: {abs(net_cash_flow_pct):.1%} net {direction}")
    return (False,
            f"Cash flow {net_cash_flow_pct:.1%} below {min_cashflow:.1%} threshold")


# ---------------------------------------------------------------------------
# Minimum benefit-cost rule (blocking rule — prevents unnecessary rebalances)
# ---------------------------------------------------------------------------

def evaluate_benefit_cost_rule(
    expected_benefit: float,
    estimated_cost:   float,
    min_ratio:        float = 1.5,
) -> Rule:
    """
    Returns triggered=True ONLY if benefit ≥ min_ratio × cost.
    Returns triggered=False to BLOCK rebalance if benefit insufficient.
    """
    if estimated_cost <= 1e-10:
        return (True, "Zero cost — rebalancing is essentially free")
    ratio = expected_benefit / estimated_cost
    if ratio >= min_ratio:
        return (True, f"Benefit/cost ratio {ratio:.2f} ≥ {min_ratio:.2f}")
    return (False,
            f"Benefit/cost ratio {ratio:.2f} < {min_ratio:.2f}; "
            "rebalancing not cost-effective")
