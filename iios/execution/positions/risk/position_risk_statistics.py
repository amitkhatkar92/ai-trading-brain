"""iios/execution/positions/risk/position_risk_statistics.py
==================================================
RiskStatistics — aggregated counters and derived metrics for the
IIOS Position Risk module.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict


@dataclass
class RiskStatistics:
    """
    Mutable statistics accumulator for the Position Risk Manager.

    Counters are incremented by ``PositionRiskManager`` as operations complete.
    Thread safety is the caller's responsibility.
    """

    # ── Operation counters ────────────────────────────────────────────────────
    total_evaluations:  int = 0
    total_updates:      int = 0
    total_registered:   int = 0
    total_unregistered: int = 0

    # ── Risk event counters ───────────────────────────────────────────────────
    warning_count:      int = 0
    critical_count:     int = 0
    liquidation_events: int = 0
    stop_loss_events:   int = 0
    take_profit_events: int = 0
    recovery_events:    int = 0

    # ── Live state counts ─────────────────────────────────────────────────────
    positions_normal:     int = 0
    positions_watch:      int = 0
    positions_warning:    int = 0
    positions_critical:   int = 0
    positions_liquidated: int = 0

    # ── Timing ────────────────────────────────────────────────────────────────
    total_eval_time_ms: float = 0.0
    last_updated_at:    float = field(default_factory=time.time)

    # ── Accumulation for averages ─────────────────────────────────────────────
    _total_exposure:      Decimal = field(default_factory=lambda: Decimal("0"), repr=False)
    _total_margin_usage:  Decimal = field(default_factory=lambda: Decimal("0"), repr=False)
    _total_drawdown:      Decimal = field(default_factory=lambda: Decimal("0"), repr=False)
    _sample_count:        int     = field(default=0, repr=False)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def average_eval_time_ms(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.total_eval_time_ms / self.total_evaluations

    @property
    def average_exposure(self) -> Decimal:
        if self._sample_count == 0:
            return Decimal("0")
        return self._total_exposure / self._sample_count

    @property
    def average_margin_usage(self) -> Decimal:
        if self._sample_count == 0:
            return Decimal("0")
        return self._total_margin_usage / self._sample_count

    @property
    def average_drawdown(self) -> Decimal:
        if self._sample_count == 0:
            return Decimal("0")
        return self._total_drawdown / self._sample_count

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def record_evaluation(self, elapsed_ms: float = 0.0) -> None:
        self.total_evaluations  += 1
        self.total_eval_time_ms += elapsed_ms
        self.last_updated_at     = time.time()

    def record_update(self) -> None:
        self.total_updates  += 1
        self.last_updated_at = time.time()

    def record_registered(self) -> None:
        self.total_registered += 1
        self.last_updated_at   = time.time()

    def record_unregistered(self) -> None:
        self.total_unregistered += 1
        self.last_updated_at    = time.time()

    def record_warning(self) -> None:
        self.warning_count  += 1
        self.last_updated_at = time.time()

    def record_critical(self) -> None:
        self.critical_count += 1
        self.last_updated_at = time.time()

    def record_liquidation(self) -> None:
        self.liquidation_events += 1
        self.last_updated_at     = time.time()

    def record_stop_loss(self) -> None:
        self.stop_loss_events += 1
        self.last_updated_at   = time.time()

    def record_take_profit(self) -> None:
        self.take_profit_events += 1
        self.last_updated_at    = time.time()

    def record_recovery(self) -> None:
        self.recovery_events += 1
        self.last_updated_at  = time.time()

    def record_sample(
        self,
        exposure:      Decimal,
        margin_usage:  Decimal,
        drawdown:      Decimal,
    ) -> None:
        """Record a data sample for running averages."""
        self._total_exposure     += exposure
        self._total_margin_usage += margin_usage
        self._total_drawdown     += drawdown
        self._sample_count       += 1
        self.last_updated_at      = time.time()

    def update_live_counts(
        self,
        normal:     int,
        watch:      int,
        warning:    int,
        critical:   int,
        liquidated: int,
    ) -> None:
        self.positions_normal     = normal
        self.positions_watch      = watch
        self.positions_warning    = warning
        self.positions_critical   = critical
        self.positions_liquidated = liquidated
        self.last_updated_at      = time.time()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_evaluations":    self.total_evaluations,
            "total_updates":        self.total_updates,
            "total_registered":     self.total_registered,
            "total_unregistered":   self.total_unregistered,
            "warning_count":        self.warning_count,
            "critical_count":       self.critical_count,
            "liquidation_events":   self.liquidation_events,
            "stop_loss_events":     self.stop_loss_events,
            "take_profit_events":   self.take_profit_events,
            "recovery_events":      self.recovery_events,
            "positions_normal":     self.positions_normal,
            "positions_watch":      self.positions_watch,
            "positions_warning":    self.positions_warning,
            "positions_critical":   self.positions_critical,
            "positions_liquidated": self.positions_liquidated,
            "average_eval_time_ms": self.average_eval_time_ms,
            "average_exposure":     str(self.average_exposure),
            "average_margin_usage": str(self.average_margin_usage),
            "average_drawdown":     str(self.average_drawdown),
            "last_updated_at":      self.last_updated_at,
        }
