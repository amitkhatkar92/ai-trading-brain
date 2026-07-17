"""iios/execution/monitoring/lifecycle/monitoring_factory.py
==================================================
MonitoringFactory — creates MonitoringSession objects from context.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import FACTORY_SYSTEM_ID, VERSION
from .exceptions import MonitoringLifecycleNotRunningError
from .monitoring_context import MonitoringContext
from .monitoring_session import MonitoringSession

_log = get_logger(__name__)


class MonitoringFactory(LifecycleAwareMixin):
    """
    Lifecycle-aware factory for MonitoringSession objects.

    Creates domain objects from MonitoringContext.  Performs no
    validation — validation is delegated to MonitoringValidator.
    """

    def __init__(self) -> None:
        super().__init__()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("MonitoringFactory starting.", system_id=FACTORY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("MonitoringFactory stopping.", system_id=FACTORY_SYSTEM_ID)

    # ── Internal guard ────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        state = self.lifecycle_state()
        if state not in (EngineState.RUNNING, "running"):
            raise MonitoringLifecycleNotRunningError()

    # ── Factory methods ───────────────────────────────────────────────────────

    def create(self, context: MonitoringContext) -> MonitoringSession:
        """
        Create a new MonitoringSession from ``context``.

        Returns a session in CREATED state.
        """
        self._assert_running()
        session = MonitoringSession(
            execution_session_id=context.execution_session_id,
            portfolio_id=context.portfolio_id,
            gateway_id=context.gateway_id,
            workflow_id=context.workflow_id,
            strategy_id=context.strategy_id,
            order_id=context.order_id,
            monitoring_version=context.monitoring_version,
            metadata=dict(context.metadata),
        )
        _log.info(
            "MonitoringSession created.",
            session_id=session.session_id,
            execution_session_id=context.execution_session_id,
            portfolio_id=context.portfolio_id,
        )
        return session

    def create_from_params(
        self,
        execution_session_id: str,
        portfolio_id: str,
        *,
        gateway_id:         str | None = None,
        workflow_id:        str | None = None,
        strategy_id:        str | None = None,
        order_id:           str | None = None,
        monitoring_version: int = 1,
    ) -> MonitoringSession:
        """Convenience wrapper — build context inline then create."""
        from .monitoring_context import make_monitoring_context
        context = make_monitoring_context(
            execution_session_id=execution_session_id,
            portfolio_id=portfolio_id,
            gateway_id=gateway_id,
            workflow_id=workflow_id,
            strategy_id=strategy_id,
            order_id=order_id,
            monitoring_version=monitoring_version,
        )
        return self.create(context)
