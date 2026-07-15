"""iios/investment/portfolio/rebalancing/allocation_drift.py

Allocation drift analysis: per-position and aggregate.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.rebalancing.rebalancing_types import (
    DRIFT_THRESHOLD_MINOR, DRIFT_THRESHOLD_MODERATE,
    CurrentPosition, DriftLevel, TargetPosition,
    classify_drift_level, now_utc,
)


@dataclass(frozen=True)
class PositionDrift:
    """Drift analysis for a single position."""

    symbol:             str
    current_weight:     float = 0.0
    target_weight:      float = 0.0
    drift:              float = 0.0    # current - target (signed)
    abs_drift:          float = 0.0
    drift_level:        DriftLevel = DriftLevel.NONE
    requires_rebalance: bool = False   # abs_drift ≥ MODERATE threshold
    is_new_position:    bool = False   # in target but not current
    is_exit_position:   bool = False   # in current but not target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":             self.symbol,
            "current_weight":     round(self.current_weight, 4),
            "target_weight":      round(self.target_weight, 4),
            "drift":              round(self.drift, 4),
            "drift_level":        self.drift_level.value,
            "requires_rebalance": self.requires_rebalance,
        }


@dataclass(frozen=True)
class AllocationDrift:
    """Aggregate allocation drift report for a portfolio."""

    result_id:              str        = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:           str        = ""
    created_at:             str        = field(default_factory=now_utc)

    # Aggregate metrics
    total_abs_drift:        float      = 0.0   # Σ |drift_i| (sum of signed over/under-weights)
    max_abs_drift:          float      = 0.0   # largest single position drift
    mean_abs_drift:         float      = 0.0
    drift_level:            DriftLevel = DriftLevel.NONE

    # Counts
    n_positions_current:    int        = 0
    n_positions_target:     int        = 0
    n_drifted:              int        = 0    # abs_drift > minor threshold
    n_requires_rebalance:   int        = 0    # abs_drift ≥ moderate threshold
    n_new_positions:        int        = 0    # in target but not current
    n_exit_positions:       int        = 0    # in current but not target

    # Per-position detail
    position_drifts:        tuple      = field(default_factory=tuple)  # tuple[PositionDrift]

    # Rebalance recommendation
    rebalance_recommended:  bool       = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_abs_drift":      round(self.total_abs_drift, 4),
            "max_abs_drift":        round(self.max_abs_drift, 4),
            "drift_level":          self.drift_level.value,
            "n_drifted":            self.n_drifted,
            "n_requires_rebalance": self.n_requires_rebalance,
            "n_new_positions":      self.n_new_positions,
            "rebalance_recommended":self.rebalance_recommended,
            "positions":            [d.to_dict() for d in self.position_drifts[:20]],
        }


def compute_allocation_drift(
    current:      List[CurrentPosition],
    target:       List[TargetPosition],
    portfolio_id: str = "",
) -> AllocationDrift:
    """
    Compute allocation drift between current holdings and target allocation.

    For positions in target but not current: drift = -target_weight (need to buy).
    For positions in current but not target: drift = +current_weight (need to sell).
    """
    cur_map: Dict[str, CurrentPosition] = {p.symbol: p for p in current}
    tgt_map: Dict[str, TargetPosition]  = {p.symbol: p for p in target}
    all_symbols = sorted(set(cur_map.keys()) | set(tgt_map.keys()))

    position_drifts: List[PositionDrift] = []
    for sym in all_symbols:
        cur_w = cur_map[sym].current_weight if sym in cur_map else 0.0
        tgt_w = tgt_map[sym].target_weight  if sym in tgt_map else 0.0
        drift  = cur_w - tgt_w
        abs_d  = abs(drift)
        level  = classify_drift_level(abs_d)
        position_drifts.append(PositionDrift(
            symbol             = sym,
            current_weight     = round(cur_w, 6),
            target_weight      = round(tgt_w, 6),
            drift              = round(drift, 6),
            abs_drift          = round(abs_d, 6),
            drift_level        = level,
            requires_rebalance = abs_d >= DRIFT_THRESHOLD_MODERATE,
            is_new_position    = sym not in cur_map and sym in tgt_map,
            is_exit_position   = sym in cur_map and sym not in tgt_map,
        ))

    n = len(position_drifts)
    if n == 0:
        return AllocationDrift(portfolio_id=portfolio_id)

    total_abs = sum(d.abs_drift for d in position_drifts)
    max_abs   = max(d.abs_drift for d in position_drifts)
    mean_abs  = total_abs / n
    n_drifted = sum(1 for d in position_drifts if d.abs_drift > DRIFT_THRESHOLD_MINOR)
    n_req     = sum(1 for d in position_drifts if d.requires_rebalance)
    n_new     = sum(1 for d in position_drifts if d.is_new_position)
    n_exit    = sum(1 for d in position_drifts if d.is_exit_position)
    level     = classify_drift_level(max_abs)

    return AllocationDrift(
        portfolio_id          = portfolio_id,
        total_abs_drift       = round(total_abs, 6),
        max_abs_drift         = round(max_abs, 6),
        mean_abs_drift        = round(mean_abs, 6),
        drift_level           = level,
        n_positions_current   = len(current),
        n_positions_target    = len(target),
        n_drifted             = n_drifted,
        n_requires_rebalance  = n_req,
        n_new_positions       = n_new,
        n_exit_positions      = n_exit,
        position_drifts       = tuple(sorted(position_drifts, key=lambda d: d.abs_drift, reverse=True)),
        rebalance_recommended = n_req > 0,
    )
