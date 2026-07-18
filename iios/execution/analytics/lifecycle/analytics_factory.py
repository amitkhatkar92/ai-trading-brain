"""
iios/execution/analytics/lifecycle/analytics_factory.py
=======================================================
AnalyticsFactory — LifecycleAwareMixin that creates AnalyticsSession
objects from contexts or raw parameters.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_LIFECYCLE,
    FACTORY_SYSTEM_ID,
    VERSION,
    AnalyticsMode,
    AnalyticsScope,
    AnalyticsState,
    AnalyticsTrigger,
)
from .exceptions import AnalyticsNotRunningError
from .analytics_context import AnalyticsContext
from .analytics_session import AnalyticsSession

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsFactory(LifecycleAwareMixin):
    """
    Creates AnalyticsSession instances.

    Must be started before use.  Stateless beyond lifecycle tracking.
    """

    def _on_start(self) -> None:
        _log.info("AnalyticsFactory started.", system_id=FACTORY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("AnalyticsFactory stopped.", system_id=FACTORY_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise AnalyticsNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def create(self, context: AnalyticsContext) -> AnalyticsSession:
        """Create a new AnalyticsSession from an AnalyticsContext."""
        self._assert_running()
        session = AnalyticsSession(
            execution_session_id = context.execution_session_id,
            analytics_scope      = context.analytics_scope,
            analytics_mode       = context.analytics_mode,
            analytics_trigger    = context.analytics_trigger,
            analytics_reason     = "",
            workflow_id          = context.workflow_id,
            portfolio_id         = context.portfolio_id,
            strategy_id          = context.strategy_id,
            analytics_version    = context.analytics_version,
            metadata             = dict(context.metadata),
        )
        _log.debug(
            "AnalyticsSession created.",
            session_id           = session.session_id,
            execution_session_id = session.execution_session_id,
            scope                = session.analytics_scope.value,
        )
        return session

    def create_from_params(
        self,
        execution_session_id: str,
        *,
        analytics_scope:    AnalyticsScope   = AnalyticsScope.EXECUTION,
        analytics_mode:     AnalyticsMode    = AnalyticsMode.ON_DEMAND,
        analytics_trigger:  AnalyticsTrigger = AnalyticsTrigger.AUTOMATIC,
        analytics_reason:   str              = "",
        workflow_id:        str              = "",
        portfolio_id:       str              = "",
        strategy_id:        str              = "",
        analytics_version:  int              = 1,
    ) -> AnalyticsSession:
        """Create a new AnalyticsSession from explicit parameters."""
        self._assert_running()
        session = AnalyticsSession(
            execution_session_id = execution_session_id,
            analytics_scope      = analytics_scope,
            analytics_mode       = analytics_mode,
            analytics_trigger    = analytics_trigger,
            analytics_reason     = analytics_reason,
            workflow_id          = workflow_id,
            portfolio_id         = portfolio_id,
            strategy_id          = strategy_id,
            analytics_version    = analytics_version,
        )
        _log.debug(
            "AnalyticsSession created (from params).",
            session_id           = session.session_id,
            execution_session_id = session.execution_session_id,
        )
        return session
