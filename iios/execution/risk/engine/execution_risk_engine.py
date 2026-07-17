"""iios/execution/risk/engine/execution_risk_engine.py
==================================================
RiskEngine — public facade for the Execution Risk Engine subsystem.

The engine is the ONLY public entry point for execution risk evaluation.
All internal complexity is hidden behind this facade.

Non-responsibilities
--------------------
* Does NOT implement risk rules — rules are external (M3+).
* Does NOT communicate with brokers.
* Does NOT execute orders.
* Does NOT manage portfolios.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_MAX_EVALUATIONS,
    DEFAULT_MAX_HISTORY,
    ENGINE_SYSTEM_ID,
    VERSION,
)
from .exceptions import RiskEngineNotRunningError
from .execution_risk_events import RiskEngineEvent
from .execution_risk_history import EngineRiskHistory
from .execution_risk_manager import RiskManager
from .execution_risk_request import (
    EvaluationRequest,
    QueryEvaluationRequest,
    RiskRuleProtocol,
)
from .execution_risk_result import EvaluationResult
from .execution_risk_snapshot import RiskEngineSnapshot
from .execution_risk_statistics import EngineRiskStatistics

_log   = get_logger(__name__, engine_id=ENGINE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)


class RiskEngine(LifecycleAwareMixin):
    """
    Public facade for the IIOS Execution Risk Engine.

    Lifecycle
    ---------
    engine = RiskEngine()
    engine.start()         # start before any operation
    engine.register_rule(my_rule)
    result = engine.evaluate(request)
    engine.stop()

    Threading
    ---------
    All public methods are thread-safe.  Concurrent ``evaluate()`` calls
    are serialised within the manager's internal lock.
    """

    def __init__(
        self,
        max_evaluations: int = DEFAULT_MAX_EVALUATIONS,
        max_history:     int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._manager = RiskManager(
            max_evaluations=max_evaluations,
            max_history=max_history,
        )

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RiskEngineNotRunningError()

    def _on_start(self) -> None:
        self._manager.start()
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("RiskEngine started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("RiskEngine stopping.", version=VERSION)
        self._manager.stop()

    # ── Rule management ───────────────────────────────────────────────────────

    def register_rule(self, rule: RiskRuleProtocol) -> None:
        """Register a risk rule.  Rules are applied in registration order."""
        self._assert_running()
        self._manager.register_rule(rule)

    def deregister_rule(self, rule_name: str) -> None:
        """Remove a previously registered rule."""
        self._assert_running()
        self._manager.deregister_rule(rule_name)

    def registered_rules(self) -> List[str]:
        """Return the names of all registered rules."""
        self._assert_running()
        return self._manager.registered_rules()

    @property
    def rule_count(self) -> int:
        """Number of registered rules."""
        return self._manager.rule_count

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """
        Evaluate execution risk for *request*.

        Drives the M1 ExecutionRisk lifecycle:
          CREATED → PENDING_EVALUATION → EVALUATING → PASSED/WARNING/BLOCKED/FAILED

        Returns
        -------
        EvaluationResult
            Always returns — never raises for business failures.
            Raises only for infrastructure failures (not-running, etc.).
        """
        self._assert_running()
        return self._manager.evaluate(request)

    def archive(self, evaluation_id: str) -> EvaluationResult:
        """Transition an evaluation to ARCHIVED state."""
        self._assert_running()
        return self._manager.archive(evaluation_id)

    def query(self, request: QueryEvaluationRequest) -> EvaluationResult:
        """Query the registry for evaluations matching *request*."""
        self._assert_running()
        return self._manager.query(request)

    # ── Observability ─────────────────────────────────────────────────────────

    @property
    def evaluation_count(self) -> int:
        """Total evaluations currently in the registry."""
        self._assert_running()
        return self._manager._registry.count

    def snapshot(self) -> RiskEngineSnapshot:
        """Return a point-in-time snapshot of the engine state."""
        self._assert_running()
        return self._manager.snapshot()

    def statistics(self) -> EngineRiskStatistics:
        """Return a copy of current engine statistics."""
        self._assert_running()
        return self._manager.statistics()

    def history(self) -> EngineRiskHistory:
        """Return the operation history store."""
        self._assert_running()
        return self._manager.history()

    def events(self) -> List[RiskEngineEvent]:
        """Return all domain events emitted since start."""
        self._assert_running()
        return self._manager.events()
