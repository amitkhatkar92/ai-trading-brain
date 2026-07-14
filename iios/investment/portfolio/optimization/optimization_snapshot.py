"""iios/investment/portfolio/optimization/optimization_snapshot.py
   iios/investment/portfolio/optimization/optimization_history.py
   (two files combined — snapshot + history)

Snapshot: point-in-time record of an optimization run.
History:  bounded, thread-safe per-portfolio history of snapshots.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.optimization.optimization_types import (
    OptimizationMethod,
    OptimizationRunStatus,
)


# ===========================================================================
# Snapshot
# ===========================================================================

@dataclass(frozen=True)
class OptimizedHolding:
    """Lightweight position record within an OptimizationSnapshot."""

    symbol:           str   = ""
    prior_weight:     float = 0.0
    optimized_weight: float = 0.0
    weight_change:    float = 0.0
    sector:           str   = "unknown"
    asset_class:      str   = "equity"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":           self.symbol,
            "prior_weight":     round(self.prior_weight, 6),
            "optimized_weight": round(self.optimized_weight, 6),
            "weight_change":    round(self.weight_change, 6),
            "sector":           self.sector,
            "asset_class":      self.asset_class,
        }


@dataclass(frozen=True)
class OptimizationSnapshot:
    """
    Immutable point-in-time record of an optimization run.
    Stored in OptimizationHistory for audit and comparison.
    """

    snapshot_id:           str                         = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:          str                         = ""
    plan_id:               str                         = ""
    allocation_plan_id:    str                         = ""
    blueprint_id:          str                         = ""
    plan_version:          int                         = 1
    result_id:             str                         = ""

    # Capital
    total_capital:         float                       = 0.0
    optimized_invested:    float                       = 0.0
    cash_capital:          float                       = 0.0
    utilisation_rate:      float                       = 0.0
    currency:              str                         = "INR"

    # Holdings
    holdings:              Tuple[OptimizedHolding, ...] = field(default_factory=tuple)

    # Objective summary
    method:                OptimizationMethod          = OptimizationMethod.MAXIMUM_SHARPE
    prior_objective_value: float                       = 0.0
    optimized_objective_value: float                   = 0.0
    objective_improvement: float                       = 0.0
    sharpe_proxy:          float                       = 0.0
    diversification_ratio: float                       = 0.0
    total_turnover:        float                       = 0.0

    # Quality
    quality_score:         float                       = 0.0
    is_valid:              bool                        = False
    is_ready:              bool                        = False

    snapshotted_at:        float                       = field(default_factory=time.time)
    metadata:              Dict[str, Any]              = field(default_factory=dict)

    @property
    def total_holdings(self) -> int:
        return len(self.holdings)

    @property
    def symbols(self) -> Tuple[str, ...]:
        return tuple(h.symbol for h in self.holdings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":              self.snapshot_id,
            "portfolio_id":             self.portfolio_id,
            "plan_id":                  self.plan_id,
            "allocation_plan_id":       self.allocation_plan_id,
            "blueprint_id":             self.blueprint_id,
            "plan_version":             self.plan_version,
            "total_capital":            round(self.total_capital, 2),
            "optimized_invested":       round(self.optimized_invested, 2),
            "cash_capital":             round(self.cash_capital, 2),
            "utilisation_rate":         round(self.utilisation_rate, 4),
            "currency":                 self.currency,
            "method":                   self.method.value,
            "prior_objective_value":    round(self.prior_objective_value, 6),
            "optimized_objective_value":round(self.optimized_objective_value, 6),
            "objective_improvement":    round(self.objective_improvement, 6),
            "sharpe_proxy":             round(self.sharpe_proxy, 6),
            "diversification_ratio":    round(self.diversification_ratio, 4),
            "total_turnover":           round(self.total_turnover, 6),
            "quality_score":            round(self.quality_score, 4),
            "is_valid":                 self.is_valid,
            "is_ready":                 self.is_ready,
            "total_holdings":           self.total_holdings,
            "snapshotted_at":           self.snapshotted_at,
            "holdings":                 [h.to_dict() for h in self.holdings],
            "metadata":                 dict(self.metadata),
        }


# ===========================================================================
# History record
# ===========================================================================

@dataclass(frozen=True)
class OptimizationRecord:
    """Lightweight audit record alongside each snapshot."""

    record_id:            str   = ""
    portfolio_id:         str   = ""
    plan_id:              str   = ""
    allocation_plan_id:   str   = ""
    plan_version:         int   = 1
    status:               str   = "converged"
    method:               str   = "maximum_sharpe"
    total_capital:        float = 0.0
    optimized_invested:   float = 0.0
    utilisation_rate:     float = 0.0
    positions_count:      int   = 0
    objective_improvement:float = 0.0
    quality_score:        float = 0.0
    is_valid:             bool  = False
    is_ready:             bool  = False
    created_at:           float = 0.0
    recorded_at:          float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":             self.record_id,
            "portfolio_id":          self.portfolio_id,
            "plan_id":               self.plan_id,
            "allocation_plan_id":    self.allocation_plan_id,
            "plan_version":          self.plan_version,
            "status":                self.status,
            "method":                self.method,
            "total_capital":         round(self.total_capital, 2),
            "optimized_invested":    round(self.optimized_invested, 2),
            "utilisation_rate":      round(self.utilisation_rate, 4),
            "positions_count":       self.positions_count,
            "objective_improvement": round(self.objective_improvement, 6),
            "quality_score":         round(self.quality_score, 4),
            "is_valid":              self.is_valid,
            "is_ready":              self.is_ready,
            "created_at":            self.created_at,
            "recorded_at":           self.recorded_at,
        }


# ===========================================================================
# History store
# ===========================================================================

class OptimizationHistory:
    """Thread-safe, bounded history of OptimizationSnapshots for one portfolio."""

    def __init__(self, portfolio_id: str, max_snapshots: int = 200) -> None:
        self._portfolio_id  = portfolio_id
        self._max_snapshots = max(1, max_snapshots)
        self._snapshots: List[OptimizationSnapshot] = []
        self._records:   List[OptimizationRecord]   = []
        self._lock = threading.RLock()

    def record(
        self,
        snapshot:      OptimizationSnapshot,
        *,
        status:        str   = "converged",
        quality_score: float = 0.0,
    ) -> OptimizationRecord:
        rec = OptimizationRecord(
            record_id            = str(uuid.uuid4()),
            portfolio_id         = snapshot.portfolio_id,
            plan_id              = snapshot.plan_id,
            allocation_plan_id   = snapshot.allocation_plan_id,
            plan_version         = snapshot.plan_version,
            status               = status,
            method               = snapshot.method.value,
            total_capital        = snapshot.total_capital,
            optimized_invested   = snapshot.optimized_invested,
            utilisation_rate     = snapshot.utilisation_rate,
            positions_count      = snapshot.total_holdings,
            objective_improvement= snapshot.objective_improvement,
            quality_score        = quality_score,
            is_valid             = snapshot.is_valid,
            is_ready             = snapshot.is_ready,
            created_at           = snapshot.snapshotted_at,
        )
        with self._lock:
            self._snapshots.append(snapshot)
            self._records.append(rec)
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots.pop(0)
                self._records.pop(0)
        return rec

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def latest(self) -> Optional[OptimizationSnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def latest_record(self) -> Optional[OptimizationRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def all_snapshots(self) -> List[OptimizationSnapshot]:
        with self._lock:
            return list(self._snapshots)

    def all_records(self) -> List[OptimizationRecord]:
        with self._lock:
            return list(self._records)

    def recent(self, n: int) -> List[OptimizationSnapshot]:
        with self._lock:
            return list(self._snapshots[-n:])

    def best(self) -> Optional[OptimizationSnapshot]:
        with self._lock:
            if not self._snapshots:
                return None
            return max(self._snapshots, key=lambda s: s.objective_improvement)

    def reset(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._records.clear()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "portfolio_id":  self._portfolio_id,
                "max_snapshots": self._max_snapshots,
                "count":         len(self._snapshots),
                "records":       [r.to_dict() for r in self._records],
            }
