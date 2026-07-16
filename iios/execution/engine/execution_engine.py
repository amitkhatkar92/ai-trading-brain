"""iios/execution/engine/execution_engine.py
==================================================
ExecutionEngine — the Institutional Execution Engine.

Responsibilities
----------------
1. Accept ExecutionRequest.
2. Validate request (identifiers, expiry, mode).
3. Resolve Order and assemble ExecutionContext.
4. Validate context (order state, portfolio, decision).
5. Coordinate Order lifecycle (advance to PENDING_SUBMISSION).
6. Select execution mode.
7. Publish ExecutionSnapshot.
8. Return ExecutionResult.

State machine (per execution)
------------------------------
IDLE → VALIDATING → PREPARING → READY → EXECUTING → COMPLETED
                 ↓           ↓       ↓           ↓
               FAILED      FAILED  CANCELLED   FAILED
Any state → CANCELLED (if cancel() is called before terminal)

This engine does NOT communicate with brokers and does NOT place trades.
It only coordinates execution workflow.

IIOS v1.0 framework: LifecycleAwareMixin, logging, audit, error handling.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE, ACTOR_SYSTEM, ENGINE_SYSTEM_ID, DEFAULT_MAX_EXECUTIONS,
    VERSION,
)
from .exceptions import (
    ExecutionCancelledError, ExecutionEngineNotRunningError,
    ExecutionPreparationError, ExecutionValidationError,
)
from .execution_events import (
    ExecutionEvent, ExecutionEventType, make_execution_event,
)
from .execution_factory import ExecutionFactory
from .execution_registry import ExecutionRecord, ExecutionRegistry
from .execution_request import ExecutionRequest
from .execution_result import ExecutionResult
from .execution_snapshot import ExecutionSnapshot
from .execution_state import EngineExecutionState
from .execution_statistics import EngineStatistics
from .execution_validation import ExecutionValidator

if TYPE_CHECKING:
    from iios.decisions.models.decision import Decision
    from iios.execution.lifecycle.order_registry import OrderRegistry
    from iios.investment.portfolio.integration.portfolio_snapshot import (
        PortfolioIntelligenceSnapshot,
    )
    from iios.investment.strategy.core.strategy_snapshot import StrategySnapshot

_log   = get_logger(__name__, engine_id=ENGINE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID,
                          component="ExecutionEngine")


class ExecutionEngine(LifecycleAwareMixin):
    """
    Institutional Execution Engine.

    Coordinates the execution workflow for a single request:
    validation → preparation → lifecycle coordination → snapshot → result.

    Does NOT communicate with brokers.
    Does NOT place trades.
    Does NOT implement execution algorithms.

    Usage
    -----
        engine = ExecutionEngine()
        engine.start()

        request = factory.create_request(
            order_id     = "ORD-001",
            decision_id  = "DEC-001",
            portfolio_id = "PORT-001",
            strategy_id  = "STRAT-001",
        )

        result = engine.submit(
            request,
            order_registry     = order_registry,
            portfolio_snapshot = portfolio_snap,
        )

        engine.stop()

    Parameters
    ----------
    max_executions : int
        Maximum concurrent executions the registry accepts.
    """

    SYSTEM_ID = ENGINE_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_executions: int = DEFAULT_MAX_EXECUTIONS) -> None:
        super().__init__()
        self._factory   = ExecutionFactory()
        self._validator = ExecutionValidator()
        self._registry  = ExecutionRegistry(max_executions=max_executions)
        self._listeners: list[Callable[[ExecutionEvent], None]] = []
        self._lock = threading.Lock()

    # ── LifecycleAwareMixin hooks ─────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        _log.info("ExecutionEngine started.")
        _audit.log_lifecycle_event(ENGINE_SYSTEM_ID, "stopped", "started", VERSION)

    def _on_stop(self) -> None:
        self._registry.stop()
        _log.info("ExecutionEngine stopped.")
        _audit.log_lifecycle_event(ENGINE_SYSTEM_ID, "started", "stopped", VERSION)

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_listener(self, listener: Callable[[ExecutionEvent], None]) -> None:
        """Register a callback invoked after every engine event."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)
        self._registry.add_listener(listener)

    def remove_listener(self, listener: Callable[[ExecutionEvent], None]) -> None:
        """Unregister a callback."""
        with self._lock:
            self._listeners = [l for l in self._listeners if l != listener]
        self._registry.remove_listener(listener)

    # ── Main entry point ──────────────────────────────────────────────────────

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

        Drives the execution through:
        IDLE → VALIDATING → PREPARING → READY → EXECUTING → COMPLETED

        On any failure the execution transitions to FAILED and an
        ExecutionResult with succeeded=False is returned (no exception raised
        unless the engine itself is not running).

        Parameters
        ----------
        request            : The execution request.
        order_registry     : Optional M1 OrderRegistry for order resolution.
        portfolio_snapshot : Optional portfolio intelligence snapshot.
        decision           : Optional decision object.
        strategy_snapshot  : Optional strategy snapshot.

        Returns
        -------
        ExecutionResult

        Raises
        ------
        ExecutionEngineNotRunningError
            If the engine has not been started.
        """
        self._assert_engine_running()

        execution_id = (
            request.execution_id
            if request.execution_id
            else self._factory.gen_execution_id()
        )
        started_at = time.time()

        _log.info(
            "ExecutionEngine.submit called.",
            execution_id   = execution_id,
            request_id     = request.request_id,
            order_id       = request.order_id,
            execution_mode = request.execution_mode.value,
        )

        # ── Register ──────────────────────────────────────────────────────────
        try:
            record = self._registry.register(
                execution_id = execution_id,
                request_id   = request.request_id,
                order_id     = request.order_id,
                portfolio_id = request.portfolio_id,
                strategy_id  = request.strategy_id,
            )
        except Exception as exc:
            _get_err_mgr().report_failure(
                self.SYSTEM_ID, exc,
                ErrorContext(engine_id=self.SYSTEM_ID, operation="submit",
                             stage="register"),
            )
            _log.exception("Failed to register execution.", exc=exc)
            return ExecutionResult.failure(
                execution_id  = execution_id,
                request_id    = request.request_id,
                order_id      = request.order_id,
                started_at    = started_at,
                error_message = str(exc),
                error_code    = "EX-004",
            )

        # ── IDLE → VALIDATING ─────────────────────────────────────────────────
        self._advance(record, EngineExecutionState.VALIDATING,
                      "starting request validation")

        validation_result = self._validator.validate_request(request)
        if not validation_result.passed:
            _log.warning(
                "ExecutionRequest validation failed.",
                execution_id = execution_id,
                errors       = validation_result.errors,
            )
            self._advance(record, EngineExecutionState.FAILED,
                          "request validation failed")
            result = ExecutionResult.failure(
                execution_id      = execution_id,
                request_id        = request.request_id,
                order_id          = request.order_id,
                started_at        = started_at,
                error_message     = "; ".join(validation_result.errors),
                error_code        = "EX-002",
                validation_errors = validation_result.errors,
            )
            self._registry.set_result(execution_id, result)
            self._dispatch(make_execution_event(
                execution_id, ExecutionEventType.EXECUTION_FAILED,
                state  = EngineExecutionState.FAILED,
                result = result,
            ))
            return result

        # ── VALIDATING → PREPARING ────────────────────────────────────────────
        self._advance(record, EngineExecutionState.PREPARING,
                      "validation passed; assembling context")

        try:
            context = self._factory.create_context(
                request            = request,
                execution_id       = execution_id,
                order_registry     = order_registry,
                portfolio_snapshot = portfolio_snapshot,
                decision           = decision,
                strategy_snapshot  = strategy_snapshot,
            )
        except Exception as exc:
            _log.exception("Context preparation failed.", exc=exc)
            self._advance(record, EngineExecutionState.FAILED,
                          f"context preparation error: {exc}")
            result = ExecutionResult.failure(
                execution_id  = execution_id,
                request_id    = request.request_id,
                order_id      = request.order_id,
                started_at    = started_at,
                error_message = f"Preparation failed: {exc}",
                error_code    = "EX-003",
            )
            self._registry.set_result(execution_id, result)
            self._dispatch(make_execution_event(
                execution_id, ExecutionEventType.EXECUTION_FAILED,
                state  = EngineExecutionState.FAILED,
                result = result,
            ))
            return result

        context_result = self._validator.validate_context(context)
        if not context_result.passed:
            _log.warning(
                "ExecutionContext validation failed.",
                execution_id = execution_id,
                errors       = context_result.errors,
            )
            self._advance(record, EngineExecutionState.FAILED,
                          "context validation failed")
            result = ExecutionResult.failure(
                execution_id      = execution_id,
                request_id        = request.request_id,
                order_id          = request.order_id,
                started_at        = started_at,
                error_message     = "; ".join(context_result.errors),
                error_code        = "EX-002",
                validation_errors = context_result.errors,
            )
            self._registry.set_result(execution_id, result)
            self._dispatch(make_execution_event(
                execution_id, ExecutionEventType.EXECUTION_FAILED,
                state  = EngineExecutionState.FAILED,
                result = result,
            ))
            return result

        self._registry.set_context(execution_id, context)

        # ── PREPARING → READY ─────────────────────────────────────────────────
        self._advance(record, EngineExecutionState.READY,
                      "context validated and ready")

        # Coordinate order lifecycle — advance to PENDING_SUBMISSION
        if context.order is not None and order_registry is not None:
            self._coordinate_order_lifecycle(context, order_registry)

        # Publish the READY snapshot
        ready_snapshot = self._build_snapshot(record, context, started_at)
        self._dispatch(make_execution_event(
            execution_id, ExecutionEventType.EXECUTION_PREPARED,
            state    = EngineExecutionState.READY,
            snapshot = ready_snapshot,
        ))

        # ── READY → EXECUTING ─────────────────────────────────────────────────
        self._advance(record, EngineExecutionState.EXECUTING,
                      "execution phase started")
        self._dispatch(make_execution_event(
            execution_id, ExecutionEventType.EXECUTION_READY,
            state    = EngineExecutionState.EXECUTING,
            snapshot = ready_snapshot,
        ))

        # ── EXECUTING → COMPLETED ─────────────────────────────────────────────
        self._advance(record, EngineExecutionState.COMPLETED,
                      "execution workflow complete")

        final_snapshot = self._build_snapshot(record, context, started_at,
                                              succeeded=True)
        result = ExecutionResult.success(
            execution_id = execution_id,
            request_id   = request.request_id,
            order_id     = request.order_id,
            started_at   = started_at,
            snapshot_id  = final_snapshot.snapshot_id,
        )
        self._registry.set_result(execution_id, result)

        self._dispatch(make_execution_event(
            execution_id, ExecutionEventType.EXECUTION_COMPLETED,
            state    = EngineExecutionState.COMPLETED,
            snapshot = final_snapshot,
            result   = result,
        ))

        _log.info(
            "Execution completed successfully.",
            execution_id = execution_id,
            duration_ms  = round(result.duration_ms, 1),
        )
        _audit.log_workflow_event(
            workflow_id  = self.SYSTEM_ID,
            stage        = "submit",
            event        = "execution_completed",
            execution_id = execution_id,
            order_id     = request.order_id,
        )
        return result

    # ── Cancellation ──────────────────────────────────────────────────────────

    def cancel(
        self,
        execution_id: str,
        *,
        reason: str = "cancelled by caller",
        actor:  str = ACTOR_ENGINE,
    ) -> bool:
        """
        Cancel an active execution.

        Returns
        -------
        bool
            True if the cancellation was applied; False if the execution
            was already in a terminal state.
        """
        self._assert_engine_running()
        try:
            record = self._registry.get(execution_id)
        except Exception:
            return False

        from .execution_state import CANCELLABLE_ENGINE_STATES
        if record.state not in CANCELLABLE_ENGINE_STATES:
            return False

        self._registry.apply_transition(
            execution_id, EngineExecutionState.CANCELLED,
            reason = reason,
            actor  = actor,
        )
        result = ExecutionResult.cancelled(
            execution_id = execution_id,
            request_id   = record.request_id,
            order_id     = record.order_id,
            started_at   = record.created_at,
            reason       = reason,
        )
        self._registry.set_result(execution_id, result)
        self._dispatch(make_execution_event(
            execution_id, ExecutionEventType.EXECUTION_CANCELLED,
            state  = EngineExecutionState.CANCELLED,
            result = result,
        ))
        _log.info("Execution cancelled.", execution_id=execution_id, reason=reason)
        return True

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_record(self, execution_id: str) -> ExecutionRecord:
        """Retrieve an execution record by ID."""
        return self._registry.get(execution_id)

    def get_active(self) -> list[ExecutionRecord]:
        return self._registry.get_active()

    def statistics(self):
        return self._registry.statistics()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _advance(
        self,
        record:   ExecutionRecord,
        to_state: EngineExecutionState,
        reason:   str = "",
        actor:    str = ACTOR_ENGINE,
    ) -> None:
        """Advance *record* to *to_state* via the registry."""
        self._registry.apply_transition(
            record.execution_id, to_state,
            reason = reason,
            actor  = actor,
        )

    def _dispatch(self, event: ExecutionEvent) -> None:
        """Dispatch an event to all engine-level listeners."""
        self._registry.dispatch(event)

    def _build_snapshot(
        self,
        record:     ExecutionRecord,
        context:    Any,
        started_at: float,
        *,
        succeeded:     Optional[bool] = None,
        error_message: str = "",
    ) -> ExecutionSnapshot:
        now = time.time()
        return ExecutionSnapshot(
            execution_id          = record.execution_id,
            request_id            = record.request_id,
            order_id              = context.order_id if context else record.order_id,
            portfolio_id          = context.portfolio_id if context else record.portfolio_id,
            strategy_id           = context.strategy_id if context else record.strategy_id,
            execution_state       = record.state,
            execution_mode        = context.execution_mode.value if context else "PAPER",
            is_terminal           = record.state in (
                EngineExecutionState.COMPLETED,
                EngineExecutionState.FAILED,
                EngineExecutionState.CANCELLED,
            ),
            context_completeness  = context.completeness if context else 0.0,
            has_order             = context.has_order if context else False,
            has_portfolio         = context.has_portfolio if context else False,
            has_decision          = context.has_decision if context else False,
            has_strategy          = context.has_strategy if context else False,
            captured_at           = now,
            started_at            = started_at,
            duration_ms_so_far    = (now - started_at) * 1_000,
            succeeded             = succeeded,
            error_message         = error_message,
        )

    def _coordinate_order_lifecycle(self, context: Any, order_registry: Any) -> None:
        """
        Advance the Order to PENDING_SUBMISSION so the broker adapter
        (future module) can pick it up.

        Called during the READY phase.  Failures are logged as warnings
        and do not abort the execution — the broker adapter will handle
        the order state independently.
        """
        try:
            from iios.execution.lifecycle.order_state import OrderState
            from iios.execution.lifecycle.constants import ACTOR_SYSTEM as ORDER_ACTOR
            order = context.order
            if order is None:
                return
            # Only advance if the order is in VALIDATED state
            if order.state == OrderState.VALIDATED:
                order_registry.apply_transition(
                    order.order_id,
                    OrderState.PENDING_SUBMISSION,
                    reason = f"execution engine {context.execution_id} — ready for broker",
                    actor  = ORDER_ACTOR,
                )
                _log.info(
                    "Order advanced to PENDING_SUBMISSION.",
                    order_id     = order.order_id,
                    execution_id = context.execution_id,
                )
        except Exception as exc:
            _log.warning(
                "Could not coordinate order lifecycle; "
                "broker adapter will handle independently.",
                exc      = exc,
                order_id = getattr(context.order, "order_id", "unknown"),
            )

    def _assert_engine_running(self) -> None:
        if not self.is_running:
            raise ExecutionEngineNotRunningError(
                "ExecutionEngine is not running. Call start() first.",
                code = "EX-008",
            )
