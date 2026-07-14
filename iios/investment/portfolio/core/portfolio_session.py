"""iios/investment/portfolio/core/portfolio_session.py

Portfolio session management for the Institutional Portfolio Framework.
A session represents one continuous active period for a portfolio.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from iios.investment.portfolio.core.portfolio_types import PortfolioLifecycleState


class SessionState(str, Enum):
    """Operational state of an individual portfolio session."""

    OPEN    = "open"
    CLOSED  = "closed"
    EXPIRED = "expired"
    FAILED  = "failed"

    @property
    def is_active(self) -> bool:
        return self == SessionState.OPEN


@dataclass(frozen=True)
class PortfolioSessionRecord:
    """
    Immutable record produced when a session is closed or expires.
    Retained for audit and performance attribution.
    """

    session_id:         str              = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str              = ""
    session_state:      SessionState     = SessionState.CLOSED
    lifecycle_state_at_open:  PortfolioLifecycleState = PortfolioLifecycleState.ACTIVE
    lifecycle_state_at_close: PortfolioLifecycleState = PortfolioLifecycleState.ACTIVE
    opened_at:          float            = field(default_factory=time.time)
    closed_at:          Optional[float]  = None
    duration_seconds:   float            = 0.0
    rebalance_count:    int              = 0
    evaluate_count:     int              = 0
    monitor_count:      int              = 0
    error_count:        int              = 0
    close_reason:       str              = ""

    @property
    def is_healthy(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict:
        return {
            "session_id":                  self.session_id,
            "portfolio_id":                self.portfolio_id,
            "session_state":               self.session_state.value,
            "lifecycle_state_at_open":     self.lifecycle_state_at_open.value,
            "lifecycle_state_at_close":    self.lifecycle_state_at_close.value,
            "opened_at":                   self.opened_at,
            "closed_at":                   self.closed_at,
            "duration_seconds":            self.duration_seconds,
            "rebalance_count":             self.rebalance_count,
            "evaluate_count":              self.evaluate_count,
            "error_count":                 self.error_count,
            "close_reason":                self.close_reason,
        }


class PortfolioSession:
    """
    Active session for a single portfolio.  Mutable during its lifetime.
    Produces an immutable PortfolioSessionRecord upon close.
    """

    def __init__(
        self,
        portfolio_id:  str,
        lifecycle_state: PortfolioLifecycleState = PortfolioLifecycleState.ACTIVE,
    ) -> None:
        self._session_id       = str(uuid.uuid4())
        self._portfolio_id     = portfolio_id
        self._state            = SessionState.OPEN
        self._lifecycle_open   = lifecycle_state
        self._lock             = threading.RLock()
        self._opened_at        = time.time()
        self._rebalance_count  = 0
        self._evaluate_count   = 0
        self._monitor_count    = 0
        self._error_count      = 0

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def state(self) -> SessionState:
        with self._lock:
            return self._state

    @property
    def is_open(self) -> bool:
        return self.state == SessionState.OPEN

    @property
    def opened_at(self) -> float:
        return self._opened_at

    # ------------------------------------------------------------------
    # Instrumentation
    # ------------------------------------------------------------------

    def record_rebalance(self) -> None:
        with self._lock:
            self._rebalance_count += 1

    def record_evaluate(self) -> None:
        with self._lock:
            self._evaluate_count += 1

    def record_monitor(self) -> None:
        with self._lock:
            self._monitor_count += 1

    def record_error(self) -> None:
        with self._lock:
            self._error_count += 1

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def close(
        self,
        lifecycle_state: PortfolioLifecycleState = PortfolioLifecycleState.ACTIVE,
        *,
        reason: str      = "",
        failed: bool     = False,
        expired: bool    = False,
    ) -> PortfolioSessionRecord:
        with self._lock:
            if self._state != SessionState.OPEN:
                raise RuntimeError(
                    f"Session {self._session_id!r} is already {self._state.value}"
                )
            closed_at = time.time()
            final_state = (
                SessionState.FAILED   if failed  else
                SessionState.EXPIRED  if expired else
                SessionState.CLOSED
            )
            self._state = final_state
            return PortfolioSessionRecord(
                session_id                = self._session_id,
                portfolio_id              = self._portfolio_id,
                session_state             = final_state,
                lifecycle_state_at_open   = self._lifecycle_open,
                lifecycle_state_at_close  = lifecycle_state,
                opened_at                 = self._opened_at,
                closed_at                 = closed_at,
                duration_seconds          = closed_at - self._opened_at,
                rebalance_count           = self._rebalance_count,
                evaluate_count            = self._evaluate_count,
                monitor_count             = self._monitor_count,
                error_count               = self._error_count,
                close_reason              = reason,
            )


class SessionManager:
    """
    Thread-safe manager for all active portfolio sessions.
    Maintains a limited history of closed session records.
    """

    def __init__(self, history_limit: int = 500) -> None:
        self._lock:    threading.RLock                          = threading.RLock()
        self._active:  Dict[str, PortfolioSession]               = {}   # session_id → session
        self._by_pid:  Dict[str, str]                            = {}   # portfolio_id → session_id
        self._history: List[PortfolioSessionRecord]              = []
        self._hist_limit = history_limit

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def open_session(
        self,
        portfolio_id:    str,
        lifecycle_state: PortfolioLifecycleState = PortfolioLifecycleState.ACTIVE,
    ) -> PortfolioSession:
        """Open a new session; closes any existing open session for the portfolio."""
        with self._lock:
            # Close existing session if present
            if portfolio_id in self._by_pid:
                old_sid = self._by_pid[portfolio_id]
                if old_sid in self._active:
                    old_session = self._active.pop(old_sid)
                    if old_session.is_open:
                        rec = old_session.close(reason="superseded by new session")
                        self._add_history(rec)
                del self._by_pid[portfolio_id]

            session = PortfolioSession(portfolio_id, lifecycle_state)
            self._active[session.session_id] = session
            self._by_pid[portfolio_id]        = session.session_id
            return session

    def close_session(
        self,
        portfolio_id:    str,
        lifecycle_state: PortfolioLifecycleState = PortfolioLifecycleState.ARCHIVED,
        *,
        reason: str = "",
        failed: bool = False,
    ) -> Optional[PortfolioSessionRecord]:
        with self._lock:
            sid = self._by_pid.pop(portfolio_id, None)
            if sid is None:
                return None
            session = self._active.pop(sid, None)
            if session is None or not session.is_open:
                return None
            rec = session.close(lifecycle_state, reason=reason, failed=failed)
            self._add_history(rec)
            return rec

    def get_active_session(self, portfolio_id: str) -> Optional[PortfolioSession]:
        with self._lock:
            sid = self._by_pid.get(portfolio_id)
            return self._active.get(sid) if sid else None

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def recent_records(self, n: int) -> List[PortfolioSessionRecord]:
        with self._lock:
            return list(self._history)[-n:]

    def records_for(self, portfolio_id: str) -> List[PortfolioSessionRecord]:
        with self._lock:
            return [r for r in self._history if r.portfolio_id == portfolio_id]

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_history(self, rec: PortfolioSessionRecord) -> None:
        self._history.append(rec)
        if len(self._history) > self._hist_limit:
            self._history = self._history[-self._hist_limit:]
