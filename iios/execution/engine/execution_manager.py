"""iios/execution/engine/execution_manager.py
==================================================
ExecutionManager — facade over ExecutionEngine and ExecutionRegistry.

Provides a single entry point for managing multiple concurrent
execution sessions from higher-level components (workflow, scheduler).

Responsibilities
----------------
• Start / stop the underlying engine and registry.
• Submit execution requests.
• Cancel active executions.
• Query active, completed, and failed executions.
• Expose aggregate statistics.
• Manage event listeners.

IIOS v1.0 framework: LifecycleAwareMixin, logging, audit, error handling.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import DEFAULT_MAX_EXECUTIONS, MANAGER_SYSTEM_ID, VERSION
from .execution_engine import ExecutionEngine
from .execution_events import ExecutionEvent
from .execution_factory import ExecutionFactory
from .execution_registry import ExecutionRecord, RegistryStatistics
from .execution_request import ExecutionRequest
from .execution_result import ExecutionResult

if TYPE_CHECKING:
    from iios.decisions.models.decision import Decision
    from iios.execution.lifecycle.order_registry import OrderRegistry
    from iios.investment.portfolio.integration.portfolio_snapshot import (
        PortfolioIntelligenceSnapshot,
    )
    from iios.investment.strategy.core.strategy_snapshot import StrategySnapshot

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID,
                          component="ExecutionManager")


class ExecutionManager(LifecycleAwareMixin):
    """
    Facade that owns and manages ExecutionEngine lifetime.

    Start the manager to initialise the engine; stop it to shut down cleanly.

    Usage
    -----
        manager = ExecutionManager()
        manager.start()

        result = manager.submit(request, order_registry=registry)

        stats = manager.statistics()
        manager.stop()

    Parameters
    ----------
    max_executions : int
        Maximum concurrent executions forwarded to ExecutionRegistry.
    """

    SYSTEM_ID = MANAGER_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_executions: int = DEFAULT_MAX_EXECUTIONS) -> None:
        super().__init__()
        self._engine  = ExecutionEngine(max_executions=max_executions)
        self._factory = ExecutionFactory()

    # ── LifecycleAwareMixin hooks ─────────────────────────────────────────────

    def _on_start(self) -> None:
        self._engine.start()
        _log.info("ExecutionManager started.")
        _audit.log_lifecycle_event(MANAGER_SYSTEM_ID, "stopped", "started", VERSION)

    def _on_stop(self) -> None:
        self._engine.stop()
        _log.info("ExecutionManager stopped.")
        _audit.log_lifecycle_event(MANAGER_SYSTEM_ID, "started", "stopped", VERSION)

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    # ── Factory delegation ────────────────────────────────────────────────────

    def create_request(
        self,
        *,
        order_id:     str,
        decision_id:  str,
        portfolio_id: str,
        strategy_id:  str,
        **kwargs: Any,
    ) -> ExecutionRequest:
        """
        Build and validate an ExecutionRequest.

        Delegates to ExecutionFactory.create_request().
        """
        return self._factory.create_request(
            order_id     = order_id,
            decision_id  = decision_id,
            portfolio_id = portfolio_id,
            strategy_id  = strategy_id,
            **kwargs,
        )

    # ── Submission ────────────────────────────────────────────────────────────

    def submit(
        self,
        request:            ExecutionRequest,
        *,
        order_registry:     "Optional[OrderRegistry]"              = None,
        portfolio_snapshot: "Optional[PortfolioIntelligenceSnapshot]" = None,
        decision:           "Optional[Decision]"                   = None,
        strategy_snapshot:  "Optional[StrategySnapshot]"           = None,
    ) -> ExecutionResult:
        """
        Submit an ExecutionRequest for processing.

        Delegates to ExecutionEngine.submit().
        """
        return self._engine.submit(
            request,
            order_registry     = order_registry,
            portfolio_snapshot = portfolio_snapshot,
            decision           = decision,
            strategy_snapshot  = strategy_snapshot,
        )

    # ── Cancellation ──────────────────────────────────────────────────────────

    def cancel(self, execution_id: str, *, reason: str = "") -> bool:
        """Cancel an active execution. Returns True if cancelled."""
        return self._engine.cancel(execution_id, reason=reason)

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_record(self, execution_id: str) -> ExecutionRecord:
        return self._engine.get_record(execution_id)

    def get_active(self) -> list[ExecutionRecord]:
        return self._engine.get_active()

    def statistics(self) -> RegistryStatistics:
        return self._engine.statistics()

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_listener(self, listener: Callable[[ExecutionEvent], None]) -> None:
        self._engine.add_listener(listener)

    def remove_listener(self, listener: Callable[[ExecutionEvent], None]) -> None:
        self._engine.remove_listener(listener)
