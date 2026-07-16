"""iios/execution/positions/risk/position_risk_state.py
==================================================
PositionRiskState — the core domain object for execution-time
position risk tracking.

Tracks all risk metrics for a single trading position:
unrealized/realized exposure, margin, drawdown, stop-loss/take-profit
trigger flags, liquidation state, and the current risk level.

Thread-safe via internal RLock.
NOT a LifecycleAwareMixin — pure domain object.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_RISK,
    ELEVATED_RISK_LEVELS,
    TERMINAL_RISK_LEVELS,
    VERSION,
    RiskLevel,
)


class PositionRiskState:
    """
    Execution-time risk state for a single position.

    Responsibilities
    ----------------
    * Hold all risk metrics for one position.
    * Track peak PnL and compute execution drawdown.
    * Maintain trigger flags (stop-loss, take-profit, liquidation).
    * Thread-safe mutation through update methods.
    * Produce a ``to_dict()`` snapshot for serialisation.

    Non-responsibilities
    --------------------
    * No state machine enforcement (RiskMonitor decides transitions).
    * No broker logic.
    * No portfolio calculations.
    * No risk limit storage (RiskLimits is held by the registry).
    """

    __slots__ = (
        # identity
        "_state_id", "_position_id", "_portfolio_id",
        "_strategy_id", "_instrument",
        # risk level
        "_risk_level",
        # PnL
        "_unrealized_pnl", "_realized_pnl",
        # peak / drawdown
        "_peak_pnl", "_execution_drawdown", "_execution_drawdown_pct",
        # exposure
        "_current_exposure",
        # margin
        "_margin_used", "_margin_available",
        # trigger flags
        "_stop_loss_triggered", "_take_profit_triggered",
        "_liquidation_warning", "_liquidation_state",
        # timing
        "_created_at", "_updated_at", "_last_evaluated_at",
        # concurrency
        "_lock",
    )

    def __init__(
        self,
        position_id:  str,
        portfolio_id: str = "",
        strategy_id:  str = "",
        instrument:   str = "",
    ) -> None:
        now = time.time()

        self._state_id   = str(uuid.uuid4())
        self._position_id = position_id
        self._portfolio_id = portfolio_id
        self._strategy_id  = strategy_id
        self._instrument   = instrument

        self._risk_level = RiskLevel.NORMAL

        # PnL
        self._unrealized_pnl = Decimal("0")
        self._realized_pnl   = Decimal("0")

        # Peak / drawdown
        self._peak_pnl              = Decimal("0")
        self._execution_drawdown     = Decimal("0")
        self._execution_drawdown_pct = Decimal("0")

        # Exposure
        self._current_exposure = Decimal("0")

        # Margin
        self._margin_used      = Decimal("0")
        self._margin_available = Decimal("0")

        # Trigger flags
        self._stop_loss_triggered  = False
        self._take_profit_triggered = False
        self._liquidation_warning  = False
        self._liquidation_state    = False

        # Timing
        self._created_at      = now
        self._updated_at      = now
        self._last_evaluated_at = now

        self._lock = threading.RLock()

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def state_id(self) -> str:
        return self._state_id

    @property
    def position_id(self) -> str:
        return self._position_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def instrument(self) -> str:
        return self._instrument

    # ── Risk level ────────────────────────────────────────────────────────────

    @property
    def risk_level(self) -> RiskLevel:
        with self._lock:
            return self._risk_level

    def set_risk_level(self, level: RiskLevel) -> None:
        with self._lock:
            self._risk_level = level
            self._updated_at = time.time()

    @property
    def is_elevated(self) -> bool:
        with self._lock:
            return self._risk_level in ELEVATED_RISK_LEVELS

    @property
    def is_liquidated(self) -> bool:
        with self._lock:
            return self._risk_level in TERMINAL_RISK_LEVELS

    # ── PnL ───────────────────────────────────────────────────────────────────

    @property
    def unrealized_pnl(self) -> Decimal:
        with self._lock:
            return self._unrealized_pnl

    @property
    def realized_pnl(self) -> Decimal:
        with self._lock:
            return self._realized_pnl

    @property
    def total_pnl(self) -> Decimal:
        with self._lock:
            return self._unrealized_pnl + self._realized_pnl

    def update_pnl(
        self,
        unrealized: Decimal,
        realized:   Decimal,
    ) -> None:
        """
        Update PnL fields and recalculate peak and execution drawdown.

        Peak tracks the highest unrealized PnL seen. Drawdown is computed
        from peak when peak > 0.
        """
        with self._lock:
            self._unrealized_pnl = unrealized
            self._realized_pnl   = realized

            # Update peak
            if unrealized > self._peak_pnl:
                self._peak_pnl = unrealized

            # Compute execution drawdown
            if self._peak_pnl > Decimal("0"):
                self._execution_drawdown = self._peak_pnl - unrealized
                if self._execution_drawdown < Decimal("0"):
                    self._execution_drawdown = Decimal("0")
                self._execution_drawdown_pct = (
                    self._execution_drawdown / self._peak_pnl
                )
            else:
                self._execution_drawdown     = Decimal("0")
                self._execution_drawdown_pct = Decimal("0")

            self._updated_at = time.time()

    # ── Peak / drawdown ───────────────────────────────────────────────────────

    @property
    def peak_pnl(self) -> Decimal:
        with self._lock:
            return self._peak_pnl

    @property
    def execution_drawdown(self) -> Decimal:
        """Absolute drawdown from peak unrealized PnL."""
        with self._lock:
            return self._execution_drawdown

    @property
    def execution_drawdown_pct(self) -> Decimal:
        """Drawdown as a fraction of peak PnL (0–1).  0 if peak <= 0."""
        with self._lock:
            return self._execution_drawdown_pct

    # ── Exposure ──────────────────────────────────────────────────────────────

    @property
    def current_exposure(self) -> Decimal:
        with self._lock:
            return self._current_exposure

    def update_exposure(self, exposure: Decimal) -> None:
        with self._lock:
            self._current_exposure = exposure
            self._updated_at       = time.time()

    # ── Margin ────────────────────────────────────────────────────────────────

    @property
    def margin_used(self) -> Decimal:
        with self._lock:
            return self._margin_used

    @property
    def margin_available(self) -> Decimal:
        with self._lock:
            return self._margin_available

    @property
    def margin_utilization_pct(self) -> Decimal:
        """Fraction of total margin consumed (0–1).  0 if no margin set."""
        with self._lock:
            total = self._margin_used + self._margin_available
            if total <= Decimal("0"):
                return Decimal("0")
            return self._margin_used / total

    def update_margin(self, used: Decimal, available: Decimal) -> None:
        with self._lock:
            self._margin_used      = used
            self._margin_available = available
            self._updated_at       = time.time()

    # ── Trigger flags ─────────────────────────────────────────────────────────

    @property
    def stop_loss_triggered(self) -> bool:
        with self._lock:
            return self._stop_loss_triggered

    def trigger_stop_loss(self) -> None:
        with self._lock:
            self._stop_loss_triggered = True
            self._updated_at          = time.time()

    @property
    def take_profit_triggered(self) -> bool:
        with self._lock:
            return self._take_profit_triggered

    def trigger_take_profit(self) -> None:
        with self._lock:
            self._take_profit_triggered = True
            self._updated_at            = time.time()

    @property
    def liquidation_warning(self) -> bool:
        with self._lock:
            return self._liquidation_warning

    def set_liquidation_warning(self, flag: bool) -> None:
        with self._lock:
            self._liquidation_warning = flag
            self._updated_at          = time.time()

    @property
    def liquidation_state(self) -> bool:
        with self._lock:
            return self._liquidation_state

    def set_liquidation_state(self, flag: bool) -> None:
        with self._lock:
            self._liquidation_state = flag
            if flag:
                self._risk_level = RiskLevel.LIQUIDATED
            self._updated_at = time.time()

    # ── Timing ────────────────────────────────────────────────────────────────

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        with self._lock:
            return self._updated_at

    @property
    def last_evaluated_at(self) -> float:
        with self._lock:
            return self._last_evaluated_at

    @property
    def execution_duration_s(self) -> float:
        """Seconds elapsed since this risk state was created."""
        return time.time() - self._created_at

    def mark_evaluated(self) -> None:
        with self._lock:
            self._last_evaluated_at = time.time()
            self._updated_at        = time.time()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state_id":               self._state_id,
                "position_id":            self._position_id,
                "portfolio_id":           self._portfolio_id,
                "strategy_id":            self._strategy_id,
                "instrument":             self._instrument,
                "risk_level":             self._risk_level.value,
                "unrealized_pnl":         str(self._unrealized_pnl),
                "realized_pnl":           str(self._realized_pnl),
                "total_pnl":              str(self._unrealized_pnl + self._realized_pnl),
                "peak_pnl":               str(self._peak_pnl),
                "execution_drawdown":     str(self._execution_drawdown),
                "execution_drawdown_pct": str(self._execution_drawdown_pct),
                "current_exposure":       str(self._current_exposure),
                "margin_used":            str(self._margin_used),
                "margin_available":       str(self._margin_available),
                "margin_utilization_pct": str(
                    self._margin_used / (self._margin_used + self._margin_available)
                    if (self._margin_used + self._margin_available) > 0
                    else Decimal("0")
                ),
                "stop_loss_triggered":    self._stop_loss_triggered,
                "take_profit_triggered":  self._take_profit_triggered,
                "liquidation_warning":    self._liquidation_warning,
                "liquidation_state":      self._liquidation_state,
                "created_at":             self._created_at,
                "updated_at":             self._updated_at,
                "last_evaluated_at":      self._last_evaluated_at,
                "execution_duration_s":   time.time() - self._created_at,
                "version":                VERSION,
            }

    def __repr__(self) -> str:
        return (
            f"PositionRiskState(position_id={self._position_id!r}, "
            f"risk_level={self._risk_level.value!r}, "
            f"unrealized_pnl={self._unrealized_pnl})"
        )
