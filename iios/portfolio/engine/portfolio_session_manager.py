"""
portfolio_session_manager.py — iios.portfolio.engine
=====================================================
Manages portfolio lifecycle sessions within the engine context.

Wraps C10 M1 :class:`PortfolioLifecycle` to provide session lifecycle
management for the Portfolio Engine.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.portfolio.lifecycle import (
    PortfolioLifecycle,
    PortfolioObjective,
    PortfolioScope,
    PortfolioSession,
    PortfolioState,
    PortfolioType,
)

from .constants import (
    ACTOR_ENGINE,
    DEFAULT_MAX_CONCURRENT_SESSIONS,
)
from .exceptions import PortfolioSessionError

_log = get_logger(__name__)


class PortfolioSessionManager:
    """
    Manages :class:`PortfolioSession` objects within the engine context.

    Wraps the M1 :class:`PortfolioLifecycle` engine to provide a simplified
    interface for the Portfolio Engine's session operations.

    The session manager delegates ALL session state transitions to the
    underlying lifecycle engine — it does not implement its own state machine.

    Parameters
    ----------
    max_active_sessions :   Maximum concurrent active sessions.
    max_archived_sessions : Maximum archived sessions in memory.
    """

    def __init__(
        self,
        max_active_sessions:   int = DEFAULT_MAX_CONCURRENT_SESSIONS,
        max_archived_sessions: int = 10_000,
    ) -> None:
        self._lifecycle = PortfolioLifecycle(
            max_active_sessions   = max_active_sessions,
            max_archived_sessions = max_archived_sessions,
        )
        self._lifecycle.start()

    # ------------------------------------------------------------------
    # Session creation
    # ------------------------------------------------------------------

    def create_session(
        self,
        portfolio_id: str,
        *,
        session_id:           Optional[str]          = None,
        portfolio_name:       str                    = "",
        portfolio_type:       PortfolioType           = PortfolioType.CUSTOM,
        portfolio_scope:      PortfolioScope          = PortfolioScope.INSTITUTIONAL,
        portfolio_objective:  PortfolioObjective      = PortfolioObjective.CUSTOM,
        portfolio_currency:   str                    = "INR",
        metadata:             Optional[Dict[str, Any]] = None,
        actor:                str                    = ACTOR_ENGINE,
    ) -> PortfolioSession:
        """
        Create a new portfolio session in CREATED state.

        Raises
        ------
        PortfolioSessionError
            On creation failure.
        """
        try:
            return self._lifecycle.create(
                portfolio_id,
                session_id          = session_id,
                portfolio_name      = portfolio_name,
                portfolio_type      = portfolio_type,
                portfolio_scope     = portfolio_scope,
                portfolio_objective = portfolio_objective,
                portfolio_currency  = portfolio_currency,
                metadata            = metadata,
                actor               = actor,
            )
        except Exception as exc:
            raise PortfolioSessionError(
                str(exc), session_id=session_id or ""
            ) from exc

    # ------------------------------------------------------------------
    # State-transition wrappers
    # ------------------------------------------------------------------

    def initialize_session(self, session_id: str, *, actor: str = ACTOR_ENGINE) -> PortfolioSession:
        try:
            return self._lifecycle.initialize(session_id, actor=actor)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    def load_session(self, session_id: str, *, actor: str = ACTOR_ENGINE) -> PortfolioSession:
        try:
            return self._lifecycle.load(session_id, actor=actor)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    def validate_session(self, session_id: str, *, actor: str = ACTOR_ENGINE) -> PortfolioSession:
        try:
            return self._lifecycle.validate_session(session_id, actor=actor)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    def ready_session(self, session_id: str, *, actor: str = ACTOR_ENGINE) -> PortfolioSession:
        try:
            return self._lifecycle.ready(session_id, actor=actor)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    def activate_session(self, session_id: str, *, actor: str = ACTOR_ENGINE) -> PortfolioSession:
        try:
            return self._lifecycle.activate(session_id, actor=actor)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    def pause_session(self, session_id: str, *, actor: str = ACTOR_ENGINE) -> PortfolioSession:
        try:
            return self._lifecycle.pause(session_id, actor=actor)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    def resume_session(self, session_id: str, *, actor: str = ACTOR_ENGINE) -> PortfolioSession:
        try:
            return self._lifecycle.resume(session_id, actor=actor)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    def complete_session(self, session_id: str, *, actor: str = ACTOR_ENGINE) -> PortfolioSession:
        try:
            return self._lifecycle.complete(session_id, actor=actor)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    def fail_session(
        self, session_id: str, reason: str = "", *, actor: str = ACTOR_ENGINE
    ) -> PortfolioSession:
        try:
            return self._lifecycle.fail(session_id, reason=reason, actor=actor)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    def archive_session(self, session_id: str, *, actor: str = ACTOR_ENGINE) -> PortfolioSession:
        try:
            return self._lifecycle.archive(session_id, actor=actor)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> PortfolioSession:
        try:
            return self._lifecycle.get_session(session_id)
        except Exception as exc:
            raise PortfolioSessionError(str(exc), session_id=session_id) from exc

    def find_session(self, session_id: str) -> Optional[PortfolioSession]:
        return self._lifecycle.find_session(session_id)

    def sessions_for_portfolio(self, portfolio_id: str) -> List[PortfolioSession]:
        return self._lifecycle.sessions_for_portfolio(portfolio_id)

    def session_statistics(self) -> dict:
        return self._lifecycle.statistics()

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Stop the underlying lifecycle engine."""
        try:
            self._lifecycle.stop()
        except Exception:
            pass  # best-effort

    @property
    def lifecycle(self) -> PortfolioLifecycle:
        return self._lifecycle
