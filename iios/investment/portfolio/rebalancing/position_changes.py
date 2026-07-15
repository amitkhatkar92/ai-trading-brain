"""iios/investment/portfolio/rebalancing/position_changes.py

PositionChange: required weight adjustment per position.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.rebalancing.rebalancing_types import (
    MIN_TRADE_SIZE_PCT, CurrentPosition, DriftLevel,
    TargetPosition, TradeSide, TradePriority,
    classify_drift_level,
)


@dataclass(frozen=True)
class PositionChange:
    """Required weight adjustment for a single position."""

    symbol:           str
    trade_side:       TradeSide
    current_weight:   float = 0.0
    target_weight:    float = 0.0
    weight_change:    float = 0.0    # target - current (positive = buy, negative = sell)
    abs_change:       float = 0.0
    drift_level:      DriftLevel = DriftLevel.NONE

    # Tax-aware attributes
    holding_days:     int   = 365
    unrealized_gain:  float = 0.0
    is_ltcg_eligible: bool  = False
    applicable_tax:   float = 0.0    # estimated tax cost fraction

    # Classification
    is_new_position:  bool  = False   # buy into new symbol
    is_full_exit:     bool  = False   # sell entire position
    is_partial:       bool  = True

    # Assigned priority (set by trade_priority module)
    priority:         TradePriority = TradePriority.MEDIUM

    sector:           str  = ""
    asset_class:      str  = "equity"
    liquidity:        float = 0.70

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":          self.symbol,
            "trade_side":      self.trade_side.value,
            "current_weight":  round(self.current_weight, 4),
            "target_weight":   round(self.target_weight, 4),
            "weight_change":   round(self.weight_change, 4),
            "drift_level":     self.drift_level.value,
            "priority":        self.priority.value,
            "is_ltcg":         self.is_ltcg_eligible,
        }


def compute_position_changes(
    current:      List[CurrentPosition],
    target:       List[TargetPosition],
    min_trade_size: float = MIN_TRADE_SIZE_PCT,
) -> List[PositionChange]:
    """
    Compute the required position changes from current to target.

    Ignores changes smaller than ``min_trade_size`` to avoid noisy micro-trades.
    """
    from iios.investment.portfolio.rebalancing.rebalancing_types import (
        TAX_RATE_LTCG, TAX_RATE_STCG, LTCG_HOLDING_DAYS,
    )

    cur_map: Dict[str, CurrentPosition] = {p.symbol: p for p in current}
    tgt_map: Dict[str, TargetPosition]  = {p.symbol: p for p in target}
    all_symbols = sorted(set(cur_map.keys()) | set(tgt_map.keys()))

    changes: List[PositionChange] = []
    for sym in all_symbols:
        cur_w  = cur_map[sym].current_weight if sym in cur_map else 0.0
        tgt_w  = tgt_map[sym].target_weight  if sym in tgt_map else 0.0
        delta  = tgt_w - cur_w               # positive = buy, negative = sell
        abs_d  = abs(delta)

        if abs_d < min_trade_size:
            continue   # skip micro-trades

        side   = TradeSide.BUY if delta > 0 else TradeSide.SELL
        level  = classify_drift_level(abs(cur_w - tgt_w))

        # Tax attributes (only relevant for sells)
        cur_pos        = cur_map.get(sym)
        holding_days   = cur_pos.holding_days   if cur_pos else LTCG_HOLDING_DAYS
        unreal_gain    = cur_pos.unrealized_gain if cur_pos else 0.0
        ltcg           = holding_days >= LTCG_HOLDING_DAYS
        tax_rate       = TAX_RATE_LTCG if ltcg else TAX_RATE_STCG
        # Tax cost = gain × tax_rate × |sell fraction|  (estimated, per unit of portfolio)
        est_tax = max(0.0, unreal_gain * tax_rate * abs_d) if side == TradeSide.SELL else 0.0

        tgt_pos = tgt_map.get(sym)
        changes.append(PositionChange(
            symbol           = sym,
            trade_side       = side,
            current_weight   = round(cur_w, 6),
            target_weight    = round(tgt_w, 6),
            weight_change    = round(delta, 6),
            abs_change       = round(abs_d, 6),
            drift_level      = level,
            holding_days     = holding_days,
            unrealized_gain  = round(unreal_gain, 6),
            is_ltcg_eligible = ltcg,
            applicable_tax   = round(est_tax, 6),
            is_new_position  = sym not in cur_map,
            is_full_exit     = sym not in tgt_map,
            is_partial       = sym in cur_map and sym in tgt_map,
            sector           = (cur_pos.sector    if cur_pos else
                                tgt_pos.sector    if tgt_pos else ""),
            asset_class      = (cur_pos.asset_class if cur_pos else
                                tgt_pos.asset_class  if tgt_pos else "equity"),
            liquidity        = float(cur_pos.liquidity if cur_pos else
                                     tgt_pos.liquidity if tgt_pos else 0.70),
        ))

    return changes
