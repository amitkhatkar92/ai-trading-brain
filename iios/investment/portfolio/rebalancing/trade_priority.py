"""iios/investment/portfolio/rebalancing/trade_priority.py

Trade prioritization: assign and sort position changes by urgency.
"""
from __future__ import annotations

from typing import List

from iios.investment.portfolio.rebalancing.position_changes import PositionChange
from iios.investment.portfolio.rebalancing.rebalance_policy import RebalancePolicy
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    DRIFT_THRESHOLD_CRITICAL, DRIFT_THRESHOLD_MODERATE,
    DRIFT_THRESHOLD_SIGNIFICANT, DriftLevel,
    PolicyType, TradePriority, TradeSide,
)


# Priority order (ascending)
_PRIORITY_ORDER = {
    TradePriority.LOW:       0,
    TradePriority.MEDIUM:    1,
    TradePriority.HIGH:      2,
    TradePriority.URGENT:    3,
    TradePriority.IMMEDIATE: 4,
}


def assign_trade_priority(
    change:      PositionChange,
    policy:      RebalancePolicy,
) -> TradePriority:
    """
    Assign execution priority to a single position change.

    Rules (highest score wins):
    - Critical drift                → IMMEDIATE
    - Full exits (not in target)    → URGENT
    - New positions (in target)     → HIGH
    - STCG sell when tax_aware      → LOW (defer if possible)
    - Significant drift             → HIGH
    - Moderate drift                → MEDIUM
    - Minor drift                   → LOW
    - Illiquid position             → reduce priority by one step
    """
    params = policy.parameters

    # Critical drift always takes highest priority
    if change.abs_change >= DRIFT_THRESHOLD_CRITICAL:
        p = TradePriority.IMMEDIATE
    elif change.is_full_exit:
        p = TradePriority.URGENT
    elif change.is_new_position:
        p = TradePriority.HIGH
    elif change.abs_change >= DRIFT_THRESHOLD_SIGNIFICANT:
        p = TradePriority.HIGH
    elif change.abs_change >= DRIFT_THRESHOLD_MODERATE:
        p = TradePriority.MEDIUM
    else:
        p = TradePriority.LOW

    # Tax-aware downgrade: if selling STCG and policy wants to avoid, lower priority
    if (params.tax_aware
            and params.avoid_stcg_sells
            and change.trade_side == TradeSide.SELL
            and not change.is_ltcg_eligible
            and not change.is_full_exit):
        p = _downgrade(p)

    # Illiquidity penalty: positions with low liquidity are harder to execute
    if change.liquidity < 0.40:
        p = _downgrade(p)

    return p


def prioritize_trades(
    changes: List[PositionChange],
    policy:  RebalancePolicy,
) -> List[PositionChange]:
    """
    Assign priorities and sort trades: highest priority first.
    Within same priority, sort buys before sells (to deploy cash first),
    then by abs_change descending.
    """
    prioritized = []
    for c in changes:
        prio = assign_trade_priority(c, policy)
        # Rebuild with assigned priority (frozen dataclass → new instance)
        updated = PositionChange(
            symbol           = c.symbol,
            trade_side       = c.trade_side,
            current_weight   = c.current_weight,
            target_weight    = c.target_weight,
            weight_change    = c.weight_change,
            abs_change       = c.abs_change,
            drift_level      = c.drift_level,
            holding_days     = c.holding_days,
            unrealized_gain  = c.unrealized_gain,
            is_ltcg_eligible = c.is_ltcg_eligible,
            applicable_tax   = c.applicable_tax,
            is_new_position  = c.is_new_position,
            is_full_exit     = c.is_full_exit,
            is_partial       = c.is_partial,
            priority         = prio,
            sector           = c.sector,
            asset_class      = c.asset_class,
            liquidity        = c.liquidity,
        )
        prioritized.append(updated)

    # Sort: highest priority first, then buys before sells, then by abs_change desc
    return sorted(
        prioritized,
        key=lambda x: (
            -_PRIORITY_ORDER[x.priority],
            0 if x.trade_side == TradeSide.BUY else 1,
            -x.abs_change,
        ),
    )


def _downgrade(priority: TradePriority) -> TradePriority:
    """Lower priority by one step (floor at LOW)."""
    order_list = [TradePriority.LOW, TradePriority.MEDIUM, TradePriority.HIGH,
                  TradePriority.URGENT, TradePriority.IMMEDIATE]
    idx = order_list.index(priority)
    return order_list[max(0, idx - 1)]
