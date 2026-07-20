"""
decision_session_manager.py — iios.decision.engine
====================================================
Thin adapter between the Decision Engine and the Decision Lifecycle (M1).

The session manager translates engine workflow operations into
DecisionLifecycle state transitions so the engine never calls the lifecycle
directly.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from iios.common.logging.logging_manager import get_logger

from iios.decision.lifecycle import (
    DecisionLifecycle,
    DecisionSession,
    DecisionState,
)
from iios.decision.lifecycle.constants import (
    ACTOR_ENGINE,
)

from .exceptions import DecisionSessionError

_log = get_logger(__name__)


class DecisionSessionManager:
    """
    Manages decision lifecycle sessions on behalf of the Decision Engine.

    Wraps :class:`~iios.decision.lifecycle.DecisionLifecycle` (M1) and
    exposes only the operations the engine needs, translating failures into
    :class:`DecisionSessionError`.

    Parameters
    ----------
    lifecycle : A started :class:`DecisionLifecycle` instance.
    """

    def __init__(self, lifecycle: DecisionLifecycle) -> None:
        self._lifecycle = lifecycle

    # ------------------------------------------------------------------
    # Session creation
    # ------------------------------------------------------------------
    def create_session(
        self,
        decision_id:  str,
        *,
        workflow_id:  str = "",
        portfolio_id: str = "",
        strategy_id:  str = "",
        metadata:     dict | None = None,
    ) -> DecisionSession:
        """Create and register a new decision session (CREATED state)."""
        try:
            return self._lifecycle.create(
                decision_id,
                workflow_id  = workflow_id,
                portfolio_id = portfolio_id,
                strategy_id  = strategy_id,
                metadata     = metadata,
                actor        = ACTOR_ENGINE,
            )
        except Exception as exc:
            raise DecisionSessionError(detail=f"create failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------
    def initialize(self, session_id: str, reason: str = "") -> DecisionSession:
        try:
            return self._lifecycle.initialize(session_id, actor=ACTOR_ENGINE, reason=reason)
        except Exception as exc:
            raise DecisionSessionError(session_id, detail=f"initialize: {exc}") from exc

    def collect(self, session_id: str, reason: str = "") -> DecisionSession:
        try:
            return self._lifecycle.collect(session_id, actor=ACTOR_ENGINE, reason=reason)
        except Exception as exc:
            raise DecisionSessionError(session_id, detail=f"collect: {exc}") from exc

    def evaluate(self, session_id: str, reason: str = "") -> DecisionSession:
        try:
            return self._lifecycle.evaluate(session_id, actor=ACTOR_ENGINE, reason=reason)
        except Exception as exc:
            raise DecisionSessionError(session_id, detail=f"evaluate: {exc}") from exc

    def ready(self, session_id: str, reason: str = "") -> DecisionSession:
        try:
            return self._lifecycle.ready(session_id, actor=ACTOR_ENGINE, reason=reason)
        except Exception as exc:
            raise DecisionSessionError(session_id, detail=f"ready: {exc}") from exc

    def activate(self, session_id: str, reason: str = "") -> DecisionSession:
        try:
            return self._lifecycle.activate(session_id, actor=ACTOR_ENGINE, reason=reason)
        except Exception as exc:
            raise DecisionSessionError(session_id, detail=f"activate: {exc}") from exc

    def complete(self, session_id: str, reason: str = "") -> DecisionSession:
        try:
            return self._lifecycle.complete(session_id, actor=ACTOR_ENGINE, reason=reason)
        except Exception as exc:
            raise DecisionSessionError(session_id, detail=f"complete: {exc}") from exc

    def fail(self, session_id: str, reason: str = "") -> DecisionSession:
        try:
            return self._lifecycle.fail(session_id, reason=reason, actor=ACTOR_ENGINE)
        except Exception as exc:
            raise DecisionSessionError(session_id, detail=f"fail: {exc}") from exc

    def archive(self, session_id: str, reason: str = "") -> DecisionSession:
        try:
            return self._lifecycle.archive(session_id, actor=ACTOR_ENGINE, reason=reason)
        except Exception as exc:
            raise DecisionSessionError(session_id, detail=f"archive: {exc}") from exc

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def get_session(self, session_id: str) -> DecisionSession | None:
        return self._lifecycle.find_any(session_id)

    def active_sessions(self) -> list[DecisionSession]:
        return self._lifecycle.all_active()

    def session_count(self) -> int:
        return self._lifecycle._registry.active_count()

    # ------------------------------------------------------------------
    # Lifecycle passthrough
    # ------------------------------------------------------------------
    @property
    def lifecycle(self) -> DecisionLifecycle:
        return self._lifecycle
