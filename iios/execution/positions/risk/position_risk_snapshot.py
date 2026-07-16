"""iios/execution/positions/risk/position_risk_snapshot.py
==================================================
RiskSnapshot — immutable point-in-time snapshot of a PositionRiskState.
RiskBookSnapshot — immutable snapshot of all tracked positions.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

from .constants import VERSION, RiskLevel
from .position_risk_statistics import RiskStatistics

if TYPE_CHECKING:
    from .position_risk_state import PositionRiskState


@dataclass(frozen=True)
class RiskSnapshot:
    """
    Immutable, point-in-time snapshot of a single ``PositionRiskState``.

    All Decimal values are stored as strings to preserve precision.
    """

    snapshot_id:            str
    position_id:            str
    portfolio_id:           str
    strategy_id:            str
    instrument:             str
    risk_level:             str
    unrealized_pnl:         str
    realized_pnl:           str
    total_pnl:              str
    peak_pnl:               str
    execution_drawdown:     str
    execution_drawdown_pct: str
    current_exposure:       str
    margin_used:            str
    margin_available:       str
    margin_utilization_pct: str
    stop_loss_triggered:    bool
    take_profit_triggered:  bool
    liquidation_warning:    bool
    liquidation_state:      bool
    created_at:             float
    updated_at:             float
    last_evaluated_at:      float
    execution_duration_s:   float
    taken_at:               float
    version:                str = VERSION
    metadata:               Dict[str, Any] = field(default_factory=dict, compare=False)

    @classmethod
    def from_state(cls, state: "PositionRiskState") -> "RiskSnapshot":
        d = state.to_dict()
        return cls(
            snapshot_id=str(uuid.uuid4()),
            position_id=d["position_id"],
            portfolio_id=d["portfolio_id"],
            strategy_id=d["strategy_id"],
            instrument=d["instrument"],
            risk_level=d["risk_level"],
            unrealized_pnl=d["unrealized_pnl"],
            realized_pnl=d["realized_pnl"],
            total_pnl=d["total_pnl"],
            peak_pnl=d["peak_pnl"],
            execution_drawdown=d["execution_drawdown"],
            execution_drawdown_pct=d["execution_drawdown_pct"],
            current_exposure=d["current_exposure"],
            margin_used=d["margin_used"],
            margin_available=d["margin_available"],
            margin_utilization_pct=d["margin_utilization_pct"],
            stop_loss_triggered=d["stop_loss_triggered"],
            take_profit_triggered=d["take_profit_triggered"],
            liquidation_warning=d["liquidation_warning"],
            liquidation_state=d["liquidation_state"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            last_evaluated_at=d["last_evaluated_at"],
            execution_duration_s=d["execution_duration_s"],
            taken_at=time.time(),
        )

    @property
    def is_elevated(self) -> bool:
        from .constants import ELEVATED_RISK_LEVELS
        return RiskLevel(self.risk_level) in ELEVATED_RISK_LEVELS

    @property
    def is_liquidated(self) -> bool:
        from .constants import TERMINAL_RISK_LEVELS
        return RiskLevel(self.risk_level) in TERMINAL_RISK_LEVELS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":            self.snapshot_id,
            "position_id":            self.position_id,
            "portfolio_id":           self.portfolio_id,
            "strategy_id":            self.strategy_id,
            "instrument":             self.instrument,
            "risk_level":             self.risk_level,
            "unrealized_pnl":         self.unrealized_pnl,
            "realized_pnl":           self.realized_pnl,
            "total_pnl":              self.total_pnl,
            "peak_pnl":               self.peak_pnl,
            "execution_drawdown":     self.execution_drawdown,
            "execution_drawdown_pct": self.execution_drawdown_pct,
            "current_exposure":       self.current_exposure,
            "margin_used":            self.margin_used,
            "margin_available":       self.margin_available,
            "margin_utilization_pct": self.margin_utilization_pct,
            "stop_loss_triggered":    self.stop_loss_triggered,
            "take_profit_triggered":  self.take_profit_triggered,
            "liquidation_warning":    self.liquidation_warning,
            "liquidation_state":      self.liquidation_state,
            "created_at":             self.created_at,
            "updated_at":             self.updated_at,
            "last_evaluated_at":      self.last_evaluated_at,
            "execution_duration_s":   self.execution_duration_s,
            "taken_at":               self.taken_at,
            "version":                self.version,
        }


@dataclass(frozen=True)
class RiskBookSnapshot:
    """
    Full, immutable snapshot of ALL risk states in the registry.

    Produced by ``PositionRiskManager.book_snapshot()``.
    """

    snapshot_id:      str
    total_positions:  int
    normal_count:     int
    watch_count:      int
    warning_count:    int
    critical_count:   int
    liquidation_count: int
    snapshots:        Tuple[RiskSnapshot, ...]
    statistics:       RiskStatistics
    taken_at:         float
    version:          str = VERSION
    metadata:         Dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def is_empty(self) -> bool:
        return self.total_positions == 0

    @property
    def has_elevated(self) -> bool:
        return (self.warning_count + self.critical_count + self.liquidation_count) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "total_positions":   self.total_positions,
            "normal_count":      self.normal_count,
            "watch_count":       self.watch_count,
            "warning_count":     self.warning_count,
            "critical_count":    self.critical_count,
            "liquidation_count": self.liquidation_count,
            "has_elevated":      self.has_elevated,
            "statistics":        self.statistics.to_dict(),
            "taken_at":          self.taken_at,
            "version":           self.version,
        }


# ── Factories ─────────────────────────────────────────────────────────────────

def make_risk_snapshot(state: "PositionRiskState") -> RiskSnapshot:
    return RiskSnapshot.from_state(state)


def make_risk_book_snapshot(
    states:     List["PositionRiskState"],
    statistics: RiskStatistics,
) -> RiskBookSnapshot:
    normal_count    = sum(1 for s in states if s.risk_level == RiskLevel.NORMAL)
    watch_count     = sum(1 for s in states if s.risk_level == RiskLevel.WATCH)
    warning_count   = sum(1 for s in states if s.risk_level == RiskLevel.WARNING)
    critical_count  = sum(1 for s in states if s.risk_level == RiskLevel.CRITICAL)
    liq_count       = sum(1 for s in states if s.risk_level in (
        RiskLevel.LIQUIDATION_PENDING, RiskLevel.LIQUIDATED
    ))
    return RiskBookSnapshot(
        snapshot_id=str(uuid.uuid4()),
        total_positions=len(states),
        normal_count=normal_count,
        watch_count=watch_count,
        warning_count=warning_count,
        critical_count=critical_count,
        liquidation_count=liq_count,
        snapshots=tuple(RiskSnapshot.from_state(s) for s in states),
        statistics=statistics,
        taken_at=time.time(),
    )
