"""iios/execution/risk/integration/execution_risk_integration_engine.py
==================================================
ExecutionRiskIntegrationEngine — the ONLY public interface to the
Execution Risk subsystem.

This engine owns and coordinates:
  M2  — RiskEngine        (rule evaluation)
  M4  — RiskControlManager (control decisions)
  M5  — SnapshotRegistry  (snapshot publication)

It does NOT own M1 or M3 directly:
  M1 ExecutionRisk lifecycle is managed internally by M2's RiskManager.
  M3 rules are registered externally via register_rule() and
  forwarded to M2.

The engine performs NO risk calculations and NO rule evaluation.
It ONLY coordinates the evaluation workflow.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import threading
import time
import uuid
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

# M2 — Execution Risk Engine
from iios.execution.risk.engine import (
    EvaluationRequest,
    RiskEngine,
    RuleOutcome,
)

# M4 — Execution Risk Controls
from iios.execution.risk.controls import RiskControlManager

# M5 — Execution Risk Snapshot
from iios.execution.risk.snapshot import (
    SnapshotBuilder,
    SnapshotFactory,
    SnapshotRegistry,
    SnapshotStatus,
)

from .constants import (
    APPROVED_ACTIONS,
    DEFAULT_MAX_HISTORY,
    ENGINE_SYSTEM_ID,
    VERSION,
    ComponentType,
    EvaluationMode,
    _M2_OUTCOME_TO_RISK_STATE,
)
from .exceptions import (
    EvaluationFailedError,
    IntegrationNotRunningError,
    RequestValidationError,
)
from .execution_risk_context import ExecutionContext
from .execution_risk_events import (
    IntegrationEvent,
    make_evaluation_completed_event,
    make_evaluation_requested_event,
    make_health_updated_event,
    make_snapshot_published_event,
    make_subsystem_started_event,
    make_subsystem_stopped_event,
    make_validation_completed_event,
)
from .execution_risk_health import SubsystemHealth, check_component_health, make_subsystem_health
from .execution_risk_history import IntegrationHistory
from .execution_risk_integration_snapshot import (
    ExecutionRiskIntegrationSnapshot,
    make_integration_snapshot,
)
from .execution_risk_registry import ComponentRegistry
from .execution_risk_request import ExecutionRiskRequest
from .execution_risk_response import ExecutionRiskResponse
from .execution_risk_statistics import IntegrationStatistics
from .execution_risk_status import SubsystemStatus
from .execution_risk_validation import IntegrationValidator, ValidationReport

_log   = get_logger(__name__, engine_id=ENGINE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)


class ExecutionRiskIntegrationEngine(LifecycleAwareMixin):
    """
    Central coordinator for the Execution Risk subsystem.

    Public API
    ----------
    evaluate(request)   → ExecutionRiskResponse
    validate(request)   → ValidationReport
    register_rule(rule) → None
    health()            → SubsystemHealth
    status()            → SubsystemStatus
    statistics()        → IntegrationStatistics
    snapshot()          → ExecutionRiskIntegrationSnapshot
    history(n)          → List[ExecutionRiskResponse]
    query(...)          → List[ExecutionRiskResponse]
    events()            → List[IntegrationEvent]

    Lifecycle
    ---------
    engine = ExecutionRiskIntegrationEngine()
    engine.start()                    # starts M2, M4, M5
    response = engine.evaluate(req)   # full evaluation workflow
    engine.stop()                     # stops M5, M4, M2
    """

    SYSTEM_ID = ENGINE_SYSTEM_ID
    VERSION   = VERSION

    def __init__(
        self,
        max_history:           int   = DEFAULT_MAX_HISTORY,
        max_evaluations:       int   = 10_000,
        max_snapshots:         int   = 100_000,
        max_snapshot_cache:    int   = 2_000,
    ) -> None:
        super().__init__()

        # ── M2 — risk evaluation engine ───────────────────────────────────────
        self._risk_engine = RiskEngine(
            max_evaluations=max_evaluations,
            max_history=max_history,
        )

        # ── M4 — control decision manager ─────────────────────────────────────
        self._controls_manager = RiskControlManager()

        # ── M5 — snapshot registry ────────────────────────────────────────────
        self._snapshot_registry = SnapshotRegistry(
            max_store_size=max_snapshots,
            max_cache_size=max_snapshot_cache,
        )

        # ── Integration layer state ───────────────────────────────────────────
        self._component_registry = ComponentRegistry()
        self._history            = IntegrationHistory(max_size=max_history)
        self._statistics         = IntegrationStatistics()
        self._events:            List[IntegrationEvent] = []
        self._lock               = threading.RLock()
        self._uptime_start:      float = 0.0

        # Register components for health inspection
        self._component_registry.register(ComponentType.ENGINE,   self._risk_engine)
        self._component_registry.register(ComponentType.CONTROLS, self._controls_manager)
        self._component_registry.register(ComponentType.SNAPSHOT, self._snapshot_registry)

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise IntegrationNotRunningError()

    def _on_start(self) -> None:
        self._uptime_start = time.time()
        self._risk_engine.start()
        self._controls_manager.start()
        self._snapshot_registry.start()

        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("ExecutionRiskIntegrationEngine started.", version=VERSION)
        self._emit(make_subsystem_started_event())

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info(
            "ExecutionRiskIntegrationEngine stopping.",
            evaluations=self._statistics.requests_processed,
        )
        self._emit(make_subsystem_stopped_event())

        # Stop in reverse dependency order
        self._snapshot_registry.stop()
        self._controls_manager.stop()
        self._risk_engine.stop()

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    # ── Rule management ───────────────────────────────────────────────────────

    def register_rule(self, rule: Any) -> None:
        """Register a risk rule with M2 RiskEngine."""
        self._assert_running()
        self._risk_engine.register_rule(rule)

    def deregister_rule(self, rule_name: str) -> None:
        """Deregister a risk rule from M2 RiskEngine."""
        self._assert_running()
        self._risk_engine.deregister_rule(rule_name)

    def registered_rules(self) -> List[str]:
        """Return names of all registered rules."""
        self._assert_running()
        return self._risk_engine.registered_rules()

    # ── Primary API ───────────────────────────────────────────────────────────

    def evaluate(self, request: ExecutionRiskRequest) -> ExecutionRiskResponse:
        """
        Evaluate execution risk for *request*.

        Workflow
        --------
        1. Validate request
        2. Emit EVALUATION_REQUESTED event
        3. Invoke M2 rule engine → EvaluationResult
        4. Invoke M4 controls → RiskControlDecision
        5. Build M5 snapshot → ExecutionRiskSnapshot
        6. Register & publish M5 snapshot
        7. Build & return ExecutionRiskResponse
        8. Update statistics, history, emit events

        Returns
        -------
        ExecutionRiskResponse
            Always returns — wraps infrastructure errors in blocked responses.

        Raises
        ------
        IntegrationNotRunningError
            If the engine has not been started.
        """
        self._assert_running()
        start_ts = time.perf_counter()

        # ── 1. Validate ───────────────────────────────────────────────────────
        val = IntegrationValidator.validate_request(request)
        if not val.is_valid:
            elapsed = (time.perf_counter() - start_ts) * 1_000.0
            with self._lock:
                self._statistics.record_validation_failure()
                self._emit(make_validation_completed_event(
                    request_id=request.request_id, is_valid=False
                ))
            _log.warning(
                "Request validation failed.",
                request_id=request.request_id,
                errors=val.errors,
            )
            return self._build_validation_error_response(request, val, elapsed)

        # ── 2. Emit requested event ────────────────────────────────────────────
        self._emit(make_evaluation_requested_event(
            request_id=request.request_id,
            execution_id=request.execution_id,
        ))

        # ── 3-7. Execute evaluation workflow ─────────────────────────────────
        try:
            response = self._execute_evaluation(request, start_ts)
        except Exception as exc:
            elapsed = (time.perf_counter() - start_ts) * 1_000.0
            _log.error(
                "Evaluation workflow raised an exception.",
                request_id=request.request_id,
                error=str(exc),
            )
            with self._lock:
                self._statistics.record_evaluation_error()
            return self._build_exception_response(request, exc, elapsed)

        # ── 8. Update statistics, history, emit completed event ───────────────
        with self._lock:
            self._statistics.record_request(
                response.elapsed_ms, response.action, response.approved
            )
            if response.was_overridden:
                self._statistics.record_override()
            self._history.append(response)
            self._emit(make_evaluation_completed_event(
                request_id=request.request_id,
                response_id=response.response_id,
                execution_id=request.execution_id,
                approved=response.approved,
                elapsed_ms=response.elapsed_ms,
            ))

        return response

    def validate(self, request: ExecutionRiskRequest) -> ValidationReport:
        """Validate *request* without executing a risk evaluation."""
        return IntegrationValidator.validate_request(request)

    # ── Observability ─────────────────────────────────────────────────────────

    def health(self) -> SubsystemHealth:
        """Return current subsystem health."""
        state_val = self.lifecycle_state().value
        components = {
            ct.value: comp
            for ct, comp in self._component_registry.all().items()
        }
        h = make_subsystem_health(components, subsystem_state=state_val)
        self._emit(make_health_updated_event(overall_healthy=h.overall_healthy))
        return h

    def status(self) -> SubsystemStatus:
        """Return the integration subsystem status."""
        state = self.lifecycle_state()
        return {
            EngineState.CREATED:     SubsystemStatus.UNINITIALIZED,
            EngineState.INITIALIZED: SubsystemStatus.INITIALIZED,
            EngineState.STARTING:    SubsystemStatus.INITIALIZING,
            EngineState.RUNNING:     SubsystemStatus.RUNNING,
            EngineState.PAUSED:      SubsystemStatus.DEGRADED,
            EngineState.STOPPING:    SubsystemStatus.STOPPING,
            EngineState.STOPPED:     SubsystemStatus.STOPPED,
            EngineState.FAILED:      SubsystemStatus.FAILED,
            EngineState.RESTARTING:  SubsystemStatus.INITIALIZING,
            EngineState.SHUTDOWN:    SubsystemStatus.SHUTDOWN,
        }.get(state, SubsystemStatus.UNINITIALIZED)

    def statistics(self) -> IntegrationStatistics:
        """Return a copy of current statistics."""
        with self._lock:
            return self._statistics.copy()

    def snapshot(self) -> ExecutionRiskIntegrationSnapshot:
        """Return a point-in-time diagnostic snapshot of the subsystem."""
        state_val   = self.lifecycle_state().value
        is_running  = self.lifecycle_state() == EngineState.RUNNING
        h           = make_subsystem_health(
            {ct.value: comp for ct, comp in self._component_registry.all().items()},
            subsystem_state=state_val,
        )
        with self._lock:
            stats_dict   = self._statistics.to_dict()
            recent_evts  = [e.to_dict() for e in self._events[-20:]]
            eval_count   = self._statistics.requests_processed

        snap_count = self._snapshot_registry.snapshot_count if is_running else 0
        uptime_sec = time.time() - self._uptime_start if self._uptime_start else 0.0

        return make_integration_snapshot(
            subsystem_state=state_val,
            is_running=is_running,
            is_healthy=h.overall_healthy,
            component_health={k: v.to_dict() for k, v in h.component_health.items()},
            statistics=stats_dict,
            recent_events=recent_evts,
            evaluation_count=eval_count,
            snapshot_count=snap_count,
            uptime_sec=uptime_sec,
            version=VERSION,
        )

    def history(self, n: int = 50) -> List[ExecutionRiskResponse]:
        """Return the *n* most recent evaluation responses."""
        return self._history.latest(n)

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
        """
        Query history with optional filters.

        Filters are ANDed together.  Returns at most *limit* results.
        """
        results = self._history.all()

        if execution_id:
            results = [r for r in results if r.execution_id == execution_id]
        if order_id:
            results = [r for r in results if r.order_id == order_id]
        if portfolio_id:
            results = [r for r in results if r.portfolio_id == portfolio_id]
        if strategy_id:
            results = [r for r in results if r.strategy_id == strategy_id]
        if approved_only:
            results = [r for r in results if r.approved]
        if blocked_only:
            results = [r for r in results if r.is_blocked]

        return results[:limit]

    def events(self) -> List[IntegrationEvent]:
        """Return a copy of all emitted events."""
        with self._lock:
            return list(self._events)

    # ── Private: evaluation workflow ─────────────────────────────────────────

    def _execute_evaluation(
        self,
        request:  ExecutionRiskRequest,
        start_ts: float,
    ) -> ExecutionRiskResponse:
        ctx = request.execution_context

        # ── Step 1: Build M2 EvaluationRequest ────────────────────────────────
        m2_request = self._build_m2_request(request)

        # ── Step 2: Invoke M2 RiskEngine ──────────────────────────────────────
        eval_result = self._risk_engine.evaluate(m2_request)

        # Handle M2 evaluation failure
        if not eval_result.succeeded:
            elapsed = (time.perf_counter() - start_ts) * 1_000.0
            _log.warning(
                "M2 evaluation returned failure.",
                request_id=request.request_id,
                error_code=eval_result.error_code,
                error_message=eval_result.error_message,
            )
            fallback_snapshot = SnapshotFactory.create_block_snapshot(
                risk_id=eval_result.evaluation_id or request.request_id,
                execution_id=ctx.execution_id,
                order_id=ctx.order_id,
                portfolio_id=ctx.portfolio_id,
                strategy_id=ctx.strategy_id,
                extra_metadata={
                    "evaluation_error": eval_result.error_message,
                    "error_code":       eval_result.error_code,
                },
            )
            return ExecutionRiskResponse(
                response_id=str(uuid.uuid4()),
                request_id=request.request_id,
                execution_id=ctx.execution_id,
                order_id=ctx.order_id,
                portfolio_id=ctx.portfolio_id,
                strategy_id=ctx.strategy_id,
                correlation_id=request.effective_correlation_id,
                approved=False,
                action="BLOCK",
                risk_state="BLOCKED",
                snapshot=fallback_snapshot,
                validation_passed=True,
                error_message=eval_result.error_message,
                elapsed_ms=elapsed,
                responded_at=time.time(),
            )

        # ── Step 3: Derive risk state from M2 outcome ─────────────────────────
        outcome_obj = eval_result.outcome
        outcome_val = str(getattr(outcome_obj, "value", outcome_obj) or "PASSED")
        risk_state  = _M2_OUTCOME_TO_RISK_STATE.get(outcome_val, "BLOCKED")

        # ── Step 4: Extract M2 rule results ───────────────────────────────────
        rule_results = list(eval_result.rule_results)

        # ── Step 5: Invoke M4 RiskControlManager ──────────────────────────────
        decision = self._controls_manager.evaluate_rule_results(
            rule_results,
            evaluation_id=eval_result.evaluation_id,
            execution_id=ctx.execution_id,
            order_id=ctx.order_id,
            portfolio_id=ctx.portfolio_id,
            strategy_id=ctx.strategy_id,
            correlation_id=request.effective_correlation_id,
        )

        action_obj = decision.action
        action_val = str(getattr(action_obj, "value", action_obj) or "BLOCK")

        # Adjust risk_state when EMERGENCY_STOP is triggered
        if action_val == "EMERGENCY_STOP":
            risk_state = "BLOCKED"

        # ── Step 6: Build M1 lifecycle proxy for M5 builder ───────────────────
        lifecycle_proxy = self._build_lifecycle_proxy(
            risk_id=eval_result.evaluation_id,
            ctx=ctx,
            request=request,
            risk_state=risk_state,
        )

        # ── Step 7: Build M5 snapshot ─────────────────────────────────────────
        m5_snapshot = (
            SnapshotBuilder()
            .with_lifecycle(lifecycle_proxy)
            .with_engine_result(eval_result)
            .with_rule_results(rule_results)
            .with_control_decision(decision)
            .with_correlation_id(request.effective_correlation_id)
            .build()
        )

        # ── Step 8: Register & publish M5 snapshot ─────────────────────────────
        self._snapshot_registry.register(m5_snapshot)
        published_snapshot = self._snapshot_registry.publish(
            m5_snapshot.snapshot_id,
            published_by=ENGINE_SYSTEM_ID,
        )

        self._emit(make_snapshot_published_event(
            snapshot_id=published_snapshot.snapshot_id,
            risk_id=eval_result.evaluation_id,
        ))

        # ── Step 9: Build integration response ────────────────────────────────
        elapsed   = (time.perf_counter() - start_ts) * 1_000.0
        approved  = action_val in APPROVED_ACTIONS

        return ExecutionRiskResponse(
            response_id=str(uuid.uuid4()),
            request_id=request.request_id,
            execution_id=ctx.execution_id,
            order_id=ctx.order_id,
            portfolio_id=ctx.portfolio_id,
            strategy_id=ctx.strategy_id,
            correlation_id=request.effective_correlation_id,
            approved=approved,
            action=action_val,
            risk_state=risk_state,
            snapshot=published_snapshot,
            validation_passed=True,
            error_message="",
            elapsed_ms=elapsed,
            responded_at=time.time(),
        )

    # ── Private: construction helpers ─────────────────────────────────────────

    def _build_m2_request(self, request: ExecutionRiskRequest) -> EvaluationRequest:
        """Build an M2 EvaluationRequest from an integration ExecutionRiskRequest."""
        from iios.execution.risk.lifecycle import RiskCategory

        ctx = request.execution_context

        # Map risk_category string → M1 RiskCategory enum
        rc = getattr(RiskCategory, request.risk_category, None) or RiskCategory.EXECUTION

        return EvaluationRequest(
            correlation_id=request.effective_correlation_id,
            actor=ENGINE_SYSTEM_ID,
            execution_id=ctx.execution_id,
            order_id=ctx.order_id,
            position_id=ctx.position_id,
            portfolio_id=ctx.portfolio_id,
            strategy_id=ctx.strategy_id,
            decision_id=ctx.decision_id,
            workflow_id=ctx.workflow_id,
            risk_category=rc,
            execution_snapshot=dict(ctx.execution_snapshot),
            position_snapshot=dict(ctx.position_snapshot),
            risk_limits=dict(ctx.risk_limits),
            metadata=dict(request.metadata),
        )

    @staticmethod
    def _build_lifecycle_proxy(
        risk_id:    str,
        ctx:        ExecutionContext,
        request:    ExecutionRiskRequest,
        risk_state: str,
    ) -> SimpleNamespace:
        """
        Create a SimpleNamespace that satisfies M5 SnapshotBuilder.with_lifecycle().

        M5 builder uses getattr() on this object to extract identifiers.
        """
        state_proxy    = SimpleNamespace(value=risk_state)
        category_proxy = SimpleNamespace(value=request.risk_category)

        return SimpleNamespace(
            risk_id=risk_id,
            execution_id=ctx.execution_id,
            order_id=ctx.order_id,
            position_id=ctx.position_id,
            portfolio_id=ctx.portfolio_id,
            workflow_id=ctx.workflow_id,
            strategy_id=ctx.strategy_id,
            correlation_id=request.effective_correlation_id,
            state=state_proxy,
            risk_category=category_proxy,
        )

    def _build_validation_error_response(
        self,
        request:  ExecutionRiskRequest,
        val:      ValidationReport,
        elapsed:  float,
    ) -> ExecutionRiskResponse:
        fallback_snapshot = SnapshotFactory.create_block_snapshot(
            risk_id=request.request_id,
            execution_id=request.execution_id,
            order_id=request.order_id,
            portfolio_id=request.portfolio_id,
            strategy_id=request.strategy_id,
            extra_metadata={"validation_errors": list(val.errors)},
        )
        return ExecutionRiskResponse(
            response_id=str(uuid.uuid4()),
            request_id=request.request_id,
            execution_id=request.execution_id,
            order_id=request.order_id,
            portfolio_id=request.portfolio_id,
            strategy_id=request.strategy_id,
            correlation_id=request.effective_correlation_id,
            approved=False,
            action="BLOCK",
            risk_state="BLOCKED",
            snapshot=fallback_snapshot,
            validation_passed=False,
            error_message="; ".join(val.errors),
            elapsed_ms=elapsed,
            responded_at=time.time(),
        )

    def _build_exception_response(
        self,
        request:  ExecutionRiskRequest,
        exc:      Exception,
        elapsed:  float,
    ) -> ExecutionRiskResponse:
        fallback_snapshot = SnapshotFactory.create_block_snapshot(
            risk_id=request.request_id,
            execution_id=request.execution_id,
            order_id=request.order_id,
            portfolio_id=request.portfolio_id,
            strategy_id=request.strategy_id,
            extra_metadata={"exception": str(exc)},
        )
        return ExecutionRiskResponse(
            response_id=str(uuid.uuid4()),
            request_id=request.request_id,
            execution_id=request.execution_id,
            order_id=request.order_id,
            portfolio_id=request.portfolio_id,
            strategy_id=request.strategy_id,
            correlation_id=request.effective_correlation_id,
            approved=False,
            action="BLOCK",
            risk_state="BLOCKED",
            snapshot=fallback_snapshot,
            validation_passed=True,
            error_message=str(exc),
            elapsed_ms=elapsed,
            responded_at=time.time(),
        )

    # ── Private: event emitter ────────────────────────────────────────────────

    def _emit(self, event: IntegrationEvent) -> None:
        """Append an event to the internal event log."""
        # Called under lock from within evaluate(); also called from lifecycle
        # hooks which are not locked — use a try/except to avoid deadlock risk.
        try:
            self._events.append(event)
        except Exception:
            pass
