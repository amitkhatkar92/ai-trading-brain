"""
market_session_manager.py — iios.market.engine
=================================================
Thin orchestration wrapper around the M1 MarketLifecycle.

Drives lifecycle sessions through the prescribed sequence:
  create → initialize → collect → validate_session → mark_ready
       → start_analysis → [start_monitoring] → complete / fail

No business logic here.  Every method delegates to MarketLifecycle.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger
from iios.market.lifecycle import (
    MarketLifecycle,
    MarketSession,
    MarketType,
    MarketScope,
)

from .exceptions import MarketSessionError

_log = get_logger(__name__)


class MarketSessionManager:
    """
    Manages lifecycle sessions for market workflows.

    Wraps :class:`iios.market.lifecycle.MarketLifecycle` and exposes the
    canonical transition sequence required by the Market Engine.

    Parameters
    ----------
    lifecycle : Injected MarketLifecycle instance.
    """

    def __init__(self, lifecycle: Optional[MarketLifecycle] = None) -> None:
        self._lifecycle = lifecycle or MarketLifecycle()
        self._lock      = threading.Lock()
        self._active: Dict[str, MarketSession] = {}

    # ------------------------------------------------------------------
    # Start / stop
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the underlying lifecycle (idempotent)."""
        state = self._lifecycle.lifecycle_state().value
        if state not in ("running",):
            self._lifecycle.start()

    def stop(self) -> None:
        """Fail all active sessions then stop the underlying lifecycle."""
        with self._lock:
            sessions = list(self._active.values())
            self._active.clear()
        for session in sessions:
            try:
                self._lifecycle.fail(session.session_id, reason="engine stopped")
            except Exception:   # noqa: BLE001
                pass
        try:
            self._lifecycle.stop()
        except Exception:       # noqa: BLE001
            pass
        _log.debug(
            f"MarketSessionManager stopped ({len(sessions)} sessions failed)"
        )

    # ------------------------------------------------------------------
    # Session lifecycle methods
    # ------------------------------------------------------------------

    def create_session(
        self,
        market_analysis_id: str,
        exchange:           str,
        *,
        market_type:  MarketType  = MarketType.EQUITY,
        market_scope: MarketScope = MarketScope.DOMESTIC,
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> MarketSession:
        """Create and register a new market session."""
        try:
            session = self._lifecycle.create(
                market_analysis_id,
                exchange        = exchange,
                market_type     = market_type,
                market_scope    = market_scope,
                metadata        = dict(metadata or {}),
            )
            with self._lock:
                self._active[session.session_id] = session
            return session
        except Exception as exc:
            raise MarketSessionError(
                str(exc), session_id=f"market:{market_analysis_id}"
            ) from exc

    def initialize_session(self, session: MarketSession) -> MarketSession:
        """Transition session → INITIALIZING."""
        try:
            return self._lifecycle.initialize(session.session_id)
        except Exception as exc:
            raise MarketSessionError(str(exc), session_id=session.session_id) from exc

    def collect_session(self, session: MarketSession) -> MarketSession:
        """Transition session → COLLECTING."""
        try:
            return self._lifecycle.collect(session.session_id)
        except Exception as exc:
            raise MarketSessionError(str(exc), session_id=session.session_id) from exc

    def validate_session(self, session: MarketSession) -> MarketSession:
        """Transition session → VALIDATING."""
        try:
            return self._lifecycle.validate_session(session.session_id)
        except Exception as exc:
            raise MarketSessionError(str(exc), session_id=session.session_id) from exc

    def ready_session(self, session: MarketSession) -> MarketSession:
        """Transition session → READY."""
        try:
            return self._lifecycle.mark_ready(session.session_id)
        except Exception as exc:
            raise MarketSessionError(str(exc), session_id=session.session_id) from exc

    def start_analysis_session(self, session: MarketSession) -> MarketSession:
        """Transition session → ANALYZING."""
        try:
            return self._lifecycle.start_analysis(session.session_id)
        except Exception as exc:
            raise MarketSessionError(str(exc), session_id=session.session_id) from exc

    def start_monitoring_session(self, session: MarketSession) -> MarketSession:
        """Transition session → MONITORING (optional phase)."""
        try:
            return self._lifecycle.start_monitoring(session.session_id)
        except Exception as exc:
            raise MarketSessionError(str(exc), session_id=session.session_id) from exc

    def complete_session(self, session: MarketSession) -> MarketSession:
        """Transition session → COMPLETED."""
        try:
            completed = self._lifecycle.complete(session.session_id)
            with self._lock:
                self._active.pop(session.session_id, None)
            return completed
        except Exception as exc:
            raise MarketSessionError(str(exc), session_id=session.session_id) from exc

    def fail_session(
        self,
        session: MarketSession,
        *,
        error: str = "",
    ) -> None:
        """Transition session → FAILED and remove from active tracking."""
        try:
            self._lifecycle.fail(session.session_id, reason=error or "engine error")
        except Exception:   # noqa: BLE001
            pass
        finally:
            with self._lock:
                self._active.pop(session.session_id, None)

    def archive_session(self, session: MarketSession) -> None:
        """Transition session → ARCHIVED."""
        try:
            self._lifecycle.archive(session.session_id)
        except Exception:   # noqa: BLE001
            pass
        finally:
            with self._lock:
                self._active.pop(session.session_id, None)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def active_session_count(self) -> int:
        with self._lock:
            return len(self._active)

    def active_sessions(self):
        with self._lock:
            return list(self._active.values())
