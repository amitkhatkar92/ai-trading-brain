"""iios/execution/risk/integration/execution_risk_integration_manager.py
==================================================
ExecutionRiskIntegrationManager — facade over
ExecutionRiskIntegrationEngine.

This is the entry point for all consumer code that needs execution
risk evaluation.  It owns exactly one integration engine instance and
delegates all public operations to it.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import MANAGER_SYSTEM_ID, VERSION
from .exceptions import IntegrationNotRunningError
from .execution_risk_context import ExecutionContext
from .execution_risk_events import IntegrationEvent
from .execution_risk_factory import IntegrationRequestFactory
from .execution_risk_health import SubsystemHealth
from .execution_risk_integration_engine import ExecutionRiskIntegrationEngine
from .execution_risk_integration_snapshot import ExecutionRiskIntegrationSnapshot
from .execution_risk_request import ExecutionRiskRequest
from .execution_risk_response import ExecutionRiskResponse
from .execution_risk_statistics import IntegrationStatistics
from .execution_risk_status import SubsystemStatus
from .execution_risk_validation import ValidationReport

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)


class ExecutionRiskIntegrationManager(LifecycleAwareMixin):
    """
    Facade over ExecutionRiskIntegrationEngine.

    Usage
    -----
    manager = ExecutionRiskIntegrationManager()
    manager.start()

    # Register M3 rules (optional — evaluates with zero rules if none registered)
    manager.register_rule(my_rule)

    # Evaluate
    ctx      = manager.create_context("EX-1", "ORD-1", portfolio_id="PORT-1")
    request  = manager.create_request(ctx)
    response = manager.evaluate(request)

    if response.approved:
        proceed_with_execution()
    else:
        handle_blocked(response)

    manager.stop()
    """

    SYSTEM_ID = MANAGER_SYSTEM_ID
    VERSION   = VERSION

    def __init__(
        self,
        max_history:        int   = 10_000,
        max_evaluations:    int   = 10_000,
        max_snapshots:      int   = 100_000,
        max_snapshot_cache: int   = 2_000,
    ) -> None:
        super().__init__()
        self._engine = ExecutionRiskIntegrationEngine(
            max_history=max_history,
            max_evaluations=max_evaluations,
            max_snapshots=max_snapshots,
            max_snapshot_cache=max_snapshot_cache,
        )

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._engine.start()
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("ExecutionRiskIntegrationManager started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("ExecutionRiskIntegrationManager stopped.")
        self._engine.stop()

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    # ── Rule management ───────────────────────────────────────────────────────

    def register_rule(self, rule: Any) -> None:
        """Register a risk rule.  Delegates to M2 RiskEngine."""
        self._engine.register_rule(rule)

    def deregister_rule(self, rule_name: str) -> None:
        """Deregister a risk rule.  Delegates to M2 RiskEngine."""
        self._engine.deregister_rule(rule_name)

    def registered_rules(self) -> List[str]:
        """Return names of all registered rules."""
        return self._engine.registered_rules()

    # ── Primary API ───────────────────────────────────────────────────────────

    def evaluate(self, request: ExecutionRiskRequest) -> ExecutionRiskResponse:
        """
        Evaluate execution risk for *request*.

        Returns ExecutionRiskResponse.  Never raises for business failures.
        Raises IntegrationNotRunningError if not started.
        """
        return self._engine.evaluate(request)

    def validate(self, request: ExecutionRiskRequest) -> ValidationReport:
        """Validate *request* without running a risk evaluation."""
        return self._engine.validate(request)

    # ── Observability ─────────────────────────────────────────────────────────

    def health(self) -> SubsystemHealth:
        return self._engine.health()

    def status(self) -> SubsystemStatus:
        return self._engine.status()

    def statistics(self) -> IntegrationStatistics:
        return self._engine.statistics()

    def snapshot(self) -> ExecutionRiskIntegrationSnapshot:
        return self._engine.snapshot()

    def history(self, n: int = 50) -> List[ExecutionRiskResponse]:
        return self._engine.history(n)

    def query(
        self,
        *,
        execution_id:  str | None = None,
        order_id:      str | None = None,
        portfolio_id:  str | None = None,
        strategy_id:   str | None = None,
        approved_only: bool       = False,
        blocked_only:  bool       = False,
        limit:         int        = 1_000,
    ) -> List[ExecutionRiskResponse]:
        return self._engine.query(
            execution_id=execution_id,
            order_id=order_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            approved_only=approved_only,
            blocked_only=blocked_only,
            limit=limit,
        )

    def events(self) -> List[IntegrationEvent]:
        return self._engine.events()

    # ── Convenience factory ───────────────────────────────────────────────────

    def create_context(
        self,
        execution_id: str,
        order_id:     str,
        **kw,
    ) -> ExecutionContext:
        """Create an ExecutionContext for use with create_request()."""
        return IntegrationRequestFactory.create_context(execution_id, order_id, **kw)

    def create_request(
        self,
        execution_context: ExecutionContext,
        **kw,
    ) -> ExecutionRiskRequest:
        """Build an ExecutionRiskRequest from an ExecutionContext."""
        return IntegrationRequestFactory.create_request(execution_context, **kw)
