"""iios/execution/lifecycle/order_statistics.py
==================================================
OrderStatistics — live execution metrics for a single order.

Updated on every state transition and fill event.
All mutations are thread-safe.

Tracked metrics
---------------
fill_pct            Percentage of quantity filled (0.0–100.0).
execution_time_sec  Seconds from first submission to complete fill.
state_durations     Seconds accumulated in each OrderState.
retry_count         Number of RECOVERING transitions entered.
cancellation_count  Number of CANCEL_PENDING transitions entered.
partial_fill_count  Number of PARTIALLY_FILLED transitions entered.
failure_count       Number of FAILED transitions entered.
rejection_count     Number of REJECTED transitions entered.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional, Tuple

from .order_state import OrderState
from .order_transition import OrderTransition


@dataclass
class OrderStatistics:
    """
    Thread-safe lifecycle metrics for one order.

    Parameters
    ----------
    order_id : str
    created_at : float
        Unix timestamp at order creation.
    """
    order_id:   str
    created_at: float

    # Fill metrics
    fill_pct:           float = 0.0
    partial_fill_count: int   = 0

    # Key timestamps
    submitted_at:    Optional[float] = None
    acknowledged_at: Optional[float] = None
    first_fill_at:   Optional[float] = None
    filled_at:       Optional[float] = None
    last_updated:    float            = field(default_factory=time.time)

    # Error / recovery counters
    retry_count:        int = 0
    cancellation_count: int = 0
    failure_count:      int = 0
    rejection_count:    int = 0

    # Internal state-duration tracking
    _state_durations:   dict[str, float]                     = field(
        default_factory=dict, repr=False
    )
    _current_state_entry: Optional[Tuple[OrderState, float]] = field(
        default=None, repr=False
    )
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ── State transition handler ──────────────────────────────────────────────

    def on_transition(self, transition: OrderTransition) -> None:
        """Update statistics when a state transition occurs."""
        with self._lock:
            now = transition.occurred_at

            # Close duration for the outgoing state
            if self._current_state_entry is not None:
                prev_state, entered_at = self._current_state_entry
                key     = prev_state.value
                elapsed = max(0.0, now - entered_at)
                self._state_durations[key] = (
                    self._state_durations.get(key, 0.0) + elapsed
                )

            # Open tracking for the incoming state
            self._current_state_entry = (transition.to_state, now)
            self.last_updated = now

            to = transition.to_state
            if to == OrderState.SUBMITTED and self.submitted_at is None:
                self.submitted_at = now
            elif to == OrderState.ACKNOWLEDGED and self.acknowledged_at is None:
                self.acknowledged_at = now
            elif to == OrderState.PARTIALLY_FILLED:
                self.partial_fill_count += 1
            elif to == OrderState.RECOVERING:
                self.retry_count += 1
            elif to == OrderState.CANCEL_PENDING:
                self.cancellation_count += 1
            elif to == OrderState.FAILED:
                self.failure_count += 1
            elif to == OrderState.REJECTED:
                self.rejection_count += 1

    # ── Fill handler ──────────────────────────────────────────────────────────

    def on_fill(
        self,
        fill_qty:    Decimal,
        total_qty:   Decimal,
        filled_qty:  Decimal,
        occurred_at: float,
    ) -> None:
        """Update statistics when a fill is applied to the order."""
        with self._lock:
            if self.first_fill_at is None:
                self.first_fill_at = occurred_at

            self.fill_pct = (
                float(filled_qty / total_qty * 100) if total_qty > 0 else 0.0
            )

            if filled_qty >= total_qty:
                self.filled_at = occurred_at

            self.last_updated = occurred_at

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def execution_time_sec(self) -> Optional[float]:
        """Seconds from first submission to complete fill; None until filled."""
        if self.submitted_at is None or self.filled_at is None:
            return None
        return max(0.0, self.filled_at - self.submitted_at)

    @property
    def state_durations(self) -> dict[str, float]:
        """
        Copy of accumulated seconds spent in each state.
        The current (open) state's running duration is NOT included here;
        use to_dict() to see a snapshot including the current state's elapsed.
        """
        with self._lock:
            return dict(self._state_durations)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            durations = dict(self._state_durations)
            # Add live duration for the current open state
            if self._current_state_entry is not None:
                state, entered = self._current_state_entry
                key = state.value
                elapsed = max(0.0, time.time() - entered)
                durations[key] = durations.get(key, 0.0) + elapsed

        return {
            "order_id":           self.order_id,
            "fill_pct":           round(self.fill_pct, 4),
            "partial_fill_count": self.partial_fill_count,
            "execution_time_sec": self.execution_time_sec,
            "submitted_at":       self.submitted_at,
            "acknowledged_at":    self.acknowledged_at,
            "first_fill_at":      self.first_fill_at,
            "filled_at":          self.filled_at,
            "last_updated":       self.last_updated,
            "retry_count":        self.retry_count,
            "cancellation_count": self.cancellation_count,
            "failure_count":      self.failure_count,
            "rejection_count":    self.rejection_count,
            "state_durations":    durations,
        }
