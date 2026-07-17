"""iios/execution/gateway/engine/gateway_manager.py
==================================================
GatewayManager — LifecycleAwareMixin orchestrator for the
Execution Gateway Engine workflow.

Implements the 10-step gateway workflow:
  1.  Receive Request
  2.  Validate Context
  3.  Validate Gateway State
  4.  Register Request
  5.  Queue Request
  6.  Dispatch to Broker Abstraction
  7.  Receive Dispatch Result
  8.  Update Lifecycle
  9.  Publish Gateway Snapshot
  10. Return Response

Coordinates:
  GatewayEngineRegistry   — request storage
  GatewayOperationQueue   — FIFO / priority / retry / cancel queues
  GatewayDispatcher       — broker abstraction delegation
  GatewaySessionManager   — session tracking
  GatewayStateManager     — engine operational state
  GatewayEngineStatistics — aggregated counters
  GatewayEngineHistory    — operation and response history
  EngineGatewayValidator  — context and request validation
  GatewayLifecycle (M1)   — domain lifecycle state machine

NON-RESPONSIBILITIES
  No broker-specific logic.
  No routing algorithms.
  No exchange connectivity.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState as FrameworkState
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.gateway.lifecycle import GatewayLifecycle

from .constants import (
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_QUEUE_SIZE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_RETRY_DELAY_SECS,
    DEFAULT_SESSION_TIMEOUT_SECS,
    MANAGER_SYSTEM_ID,
    VERSION,
    DispatchOutcome,
    EngineState,
    QueueType,
    RequestStatus,
)
from .exceptions import (
    GatewayDispatchError,
    GatewayEngineNotRunningError,
    GatewayEngineRequestNotFoundError,
    GatewayRequestSubmissionError,
    GatewayValidationFailedError,
)
from .gateway_context import EngineGatewayContext
from .gateway_dispatcher import BrokerAbstractionProtocol, GatewayDispatcher, RoutingFrameworkProtocol
from .gateway_statistics import GatewayEngineStatistics
from .gateway_events import (
    GatewayEngineEvent,
    make_dispatch_completed_event,
    make_dispatch_failed_event,
    make_gateway_started_event,
    make_gateway_stopped_event,
    make_request_dispatched_event,
    make_request_queued_event,
    make_request_received_event,
)
from .gateway_factory import GatewayEngineFactory
from .gateway_history import GatewayEngineHistory
from .constants import OperationType
from .gateway_operation import make_gateway_operation
from .gateway_operation_queue import GatewayOperationQueue
from .gateway_registry import GatewayEngineRegistry
from .gateway_request import EngineGatewayRequest
from .gateway_response import GatewayResponse
from .gateway_session import GatewaySessionManager
from .gateway_snapshot import GatewayEngineSnapshot
from .gateway_state_manager import GatewayStateManager
from .gateway_validation import EngineGatewayValidator

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)


class GatewayManager(LifecycleAwareMixin):
    """
    Orchestrator for the Execution Gateway Engine workflow.

    GatewayManager is the internal coordinator owned by
    ``ExecutionGatewayEngine``.  It coordinates all subsystems and
    implements the 10-step processing workflow.

    Responsibilities
    ----------------
    * Validate incoming contexts.
    * Create and register engine requests.
    * Manage sessions.
    * Drive the M1 GatewayLifecycle state machine.
    * Queue and dispatch requests via GatewayDispatcher.
    * Record statistics and history.
    * Publish domain events to registered listeners.

    Non-responsibilities
    --------------------
    * No broker-specific logic.
    * No routing algorithms.
    * No exchange connectivity.
    """

    def __init__(
        self,
        max_requests:    int   = DEFAULT_MAX_REQUESTS,
        max_queue_size:  int   = DEFAULT_MAX_QUEUE_SIZE,
        max_sessions:    int   = DEFAULT_MAX_SESSIONS,
        max_history:     int   = DEFAULT_MAX_HISTORY,
        session_timeout: float = DEFAULT_SESSION_TIMEOUT_SECS,
        retry_delay:     float = DEFAULT_RETRY_DELAY_SECS,
        broker:          Optional[BrokerAbstractionProtocol] = None,
        router:          Optional[RoutingFrameworkProtocol]  = None,
    ) -> None:
        super().__init__()
        self._retry_delay     = max(0.0, retry_delay)
        self._lock            = threading.RLock()

        # ── Subsystems ────────────────────────────────────────────────────────
        self._registry     = GatewayEngineRegistry(max_requests=max_requests)
        self._queue        = GatewayOperationQueue(max_size=max_queue_size)
        self._sessions     = GatewaySessionManager(
            max_sessions=max_sessions,
            timeout_secs=session_timeout,
        )
        self._dispatcher   = GatewayDispatcher(broker=broker, router=router)
        self._engine_state = GatewayStateManager()
        self._stats        = GatewayEngineStatistics()
        self._history      = GatewayEngineHistory(max_size=max_history)
        self._validator    = EngineGatewayValidator()
        self._factory      = GatewayEngineFactory()
        self._lifecycle    = GatewayLifecycle(max_requests=max_requests)

        # ── Event listeners ───────────────────────────────────────────────────
        self._event_listeners: List[Callable[[GatewayEngineEvent], None]] = []

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != FrameworkState.RUNNING:
            raise GatewayEngineNotRunningError()

    def _on_start(self) -> None:
        self._registry.start()
        self._lifecycle.start()
        self._engine_state.transition(EngineState.IDLE, reason="manager started")
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, FrameworkState.STOPPED, FrameworkState.RUNNING, VERSION
        )
        _log.info("GatewayManager started.", version=VERSION)
        self._fire_event(make_gateway_started_event(actor=ACTOR_MANAGER))

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, FrameworkState.RUNNING, FrameworkState.STOPPED, VERSION
        )
        _log.info(
            "GatewayManager stopped.",
            requests_received=self._stats.requests_received,
            requests_completed=self._stats.requests_completed,
        )
        self._fire_event(make_gateway_stopped_event(actor=ACTOR_MANAGER))
        self._lifecycle.stop()
        self._registry.stop()
        self._engine_state.transition(EngineState.STOPPED, reason="manager stopped")

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == FrameworkState.RUNNING

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[GatewayEngineEvent], None]
    ) -> None:
        with self._lock:
            if listener not in self._event_listeners:
                self._event_listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[GatewayEngineEvent], None]
    ) -> None:
        with self._lock:
            try:
                self._event_listeners.remove(listener)
            except ValueError:
                pass

    def _fire_event(self, event: GatewayEngineEvent) -> None:
        with self._lock:
            listeners = list(self._event_listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "Event listener raised an exception.",
                    event_type=event.event_type.value,
                    error=str(exc),
                )

    # ── Broker / router registration ──────────────────────────────────────────

    def register_broker(self, broker: BrokerAbstractionProtocol) -> None:
        """Replace the active broker abstraction (delegates to dispatcher)."""
        self._dispatcher.register_broker(broker)

    def register_router(self, router: RoutingFrameworkProtocol) -> None:
        """Replace the active routing framework (delegates to dispatcher)."""
        self._dispatcher.register_router(router)

    # ── Main workflow: process_request ────────────────────────────────────────

    def process_request(self, context: EngineGatewayContext) -> GatewayResponse:
        """
        Execute the 10-step gateway workflow for a single context.

        Returns a ``GatewayResponse`` regardless of outcome.
        Raises ``GatewayEngineNotRunningError`` if the manager is not started.
        """
        self._assert_running()
        start_time = time.time()

        # ── Step 1: Receive Request ───────────────────────────────────────────
        with self._lock:
            self._stats.record_received()

        # ── Step 2: Validate Context ──────────────────────────────────────────
        self._engine_state.transition(
            EngineState.VALIDATING, reason=f"validating {context.request_id}"
        )
        validation = self._validator.validate_context(context)
        if not validation.is_valid:
            self._engine_state.transition(EngineState.IDLE, reason="validation failed")
            raise GatewayRequestSubmissionError(
                reason="; ".join(validation.errors)
            )

        # ── Step 3: Validate Gateway State ────────────────────────────────────
        capacity_check = self._validator.validate_queue_capacity(
            self._queue
        )
        if not capacity_check.is_valid:
            self._engine_state.transition(EngineState.IDLE, reason="capacity check failed")
            raise GatewayRequestSubmissionError(
                reason="; ".join(capacity_check.errors)
            )

        # ── Step 4: Register Request ──────────────────────────────────────────
        session = self._sessions.create_session(
            portfolio_id=context.portfolio_id,
            strategy_id=context.strategy_id,
            execution_id=context.execution_id,
        )
        request = self._factory.create_request(
            context,
            session_id=session.session_id,
            max_retries=DEFAULT_MAX_RETRIES,
            queue_type=QueueType.PRIORITY if context.is_high_priority else QueueType.FIFO,
        )
        self._registry.register(request)
        self._sessions.add_request_to_session(session.session_id, request.request_id)

        # Create M1 lifecycle request
        lc_request = self._lifecycle.create(
            execution_id=context.execution_id,
            order_id=context.order_id,
            portfolio_id=context.portfolio_id,
            strategy_id=context.strategy_id,
            workflow_id=context.workflow_id,
            position_id=context.position_id,
            decision_id=context.decision_id,
            correlation_id=context.correlation_id,
        )
        request.set_lifecycle_request_id(lc_request.gateway_id)

        self._fire_event(make_request_received_event(
            request_id=request.request_id,
            execution_id=context.execution_id,
            portfolio_id=context.portfolio_id,
            strategy_id=context.strategy_id,
            gateway_id=lc_request.gateway_id,
        ))

        # Drive M1 lifecycle: CREATED → RECEIVED → VALIDATING → READY
        self._lifecycle.receive(lc_request.gateway_id)
        self._lifecycle.start_validation(lc_request.gateway_id)
        self._lifecycle.mark_ready(lc_request.gateway_id)

        # ── Step 5: Queue Request ─────────────────────────────────────────────
        self._engine_state.transition(EngineState.QUEUING, reason=request.request_id)
        if context.is_high_priority:
            self._queue.enqueue_priority(request)
        else:
            self._queue.enqueue_fifo(request)

        request.set_status(RequestStatus.QUEUED)
        request.mark_queued()

        queue_sizes = self._queue.sizes()
        queue_depth = queue_sizes.get(request.queue_type.value, 0)
        with self._lock:
            self._stats.record_queued(0.0)  # queue time measured at dispatch

        self._lifecycle.queue(lc_request.gateway_id)

        self._fire_event(make_request_queued_event(
            request_id=request.request_id,
            execution_id=context.execution_id,
            portfolio_id=context.portfolio_id,
            strategy_id=context.strategy_id,
            gateway_id=lc_request.gateway_id,
            metadata={"queue_depth": queue_depth},
        ))

        # ── Step 6: Dispatch to Broker Abstraction ────────────────────────────
        self._engine_state.transition(EngineState.DISPATCHING, reason=request.request_id)
        request.set_status(RequestStatus.DISPATCHING)
        request.mark_dispatched()

        queued_at        = request.queued_at or start_time
        dispatched_at    = request.dispatched_at or time.time()
        queue_wait_ms    = max(0.0, (dispatched_at - queued_at) * 1_000.0)

        self._lifecycle.start_routing(lc_request.gateway_id)

        with self._lock:
            self._stats.record_dispatched(queue_wait_ms)

        self._fire_event(make_request_dispatched_event(
            request_id=request.request_id,
            execution_id=context.execution_id,
            portfolio_id=context.portfolio_id,
            strategy_id=context.strategy_id,
            gateway_id=lc_request.gateway_id,
        ))

        # ── Step 7: Receive Dispatch Result ───────────────────────────────────
        try:
            dispatch_result = self._dispatcher.dispatch(request)
        except Exception as exc:  # noqa: BLE001
            _log.error(
                "Dispatcher raised an unexpected exception.",
                request_id=request.request_id,
                error=str(exc),
            )
            dispatch_result = None

        # ── Step 8: Update Lifecycle ──────────────────────────────────────────
        lifecycle_ms = max(0.0, (time.time() - start_time) * 1_000.0)

        if dispatch_result is not None and dispatch_result.accepted:
            # ── SUCCESS PATH ──────────────────────────────────────────────────
            request.set_dispatch_result(
                outcome=dispatch_result.outcome,
                result=dispatch_result.result_metadata,
            )
            request.mark_completed()
            request.set_status(RequestStatus.COMPLETED)

            self._lifecycle.dispatch(lc_request.gateway_id)
            self._lifecycle.complete(lc_request.gateway_id)
            self._lifecycle.archive(lc_request.gateway_id)

            dispatch_ms = max(0.0, (time.time() - dispatched_at) * 1_000.0)
            with self._lock:
                self._stats.record_completed(lifecycle_ms)

            op = make_gateway_operation(
                OperationType.COMPLETE_REQUEST,
                request_id=request.request_id,
                session_id=session.session_id,
                started_at=start_time,
                is_success=True,
            )
            self._history.append_operation(op)

            self._engine_state.transition(EngineState.COMPLETING, reason="dispatch accepted")
            self._engine_state.transition(EngineState.IDLE, reason="request completed")

            self._fire_event(make_dispatch_completed_event(
                request_id=request.request_id,
                execution_id=context.execution_id,
                portfolio_id=context.portfolio_id,
                strategy_id=context.strategy_id,
                gateway_id=lc_request.gateway_id,
                metadata={
                    "external_id": dispatch_result.external_id,
                    "outcome":     dispatch_result.outcome.value,
                },
            ))

            # ── Step 9: Publish Gateway Snapshot (no-op; snapshot is on-demand) ─

            # ── Step 10: Return Response ──────────────────────────────────────
            response = self._factory.create_response(request, is_success=True)

        else:
            # ── FAILURE PATH ──────────────────────────────────────────────────
            outcome       = DispatchOutcome.REJECTED
            error_code    = "EGE-003"
            error_message = "Dispatch rejected by broker abstraction."

            if dispatch_result is not None:
                outcome = dispatch_result.outcome
                error_code    = dispatch_result.error_code or "EGE-003"
                error_message = dispatch_result.error_message or "Dispatch rejected."
                request.set_dispatch_result(
                    outcome=outcome,
                    result=dispatch_result.result_metadata,
                )
            else:
                error_message = "Dispatch raised an unexpected exception."

            request.set_error(code=error_code, message=error_message)
            request.mark_completed()
            request.set_status(RequestStatus.FAILED)

            try:
                self._lifecycle.dispatch(lc_request.gateway_id)
                self._lifecycle.fail(
                    lc_request.gateway_id, reason=error_message
                )
                self._lifecycle.archive(lc_request.gateway_id)
            except Exception as lc_exc:  # noqa: BLE001
                _log.warning(
                    "Lifecycle update failed after dispatch failure.",
                    error=str(lc_exc),
                )

            with self._lock:
                self._stats.record_failed(lifecycle_ms)

            op = make_gateway_operation(
                OperationType.DISPATCH_REQUEST,
                request_id=request.request_id,
                session_id=session.session_id,
                started_at=start_time,
                is_success=False,
                error_message=error_message,
            )
            self._history.append_operation(op)

            self._engine_state.transition(EngineState.FAILED, reason="dispatch failed")
            self._engine_state.transition(EngineState.IDLE, reason="reset after failure")

            self._fire_event(make_dispatch_failed_event(
                request_id=request.request_id,
                execution_id=context.execution_id,
                portfolio_id=context.portfolio_id,
                strategy_id=context.strategy_id,
                gateway_id=lc_request.gateway_id,
                metadata={"error_code": error_code, "error_message": error_message},
            ))

            response = self._factory.create_response(
                request,
                is_success=False,
                error_code=error_code,
                error_message=error_message,
            )

        self._history.append_response(response)
        return response

    # ── Cancel request ────────────────────────────────────────────────────────

    def cancel_request(self, request_id: str, *, reason: str = "") -> bool:
        """
        Cancel an active request by request_id.

        Returns True if the request was found and cancellation was initiated.
        """
        self._assert_running()

        request = self._registry.get_optional(request_id)
        if request is None:
            _log.warning("Cancel called for unknown request.", request_id=request_id)
            return False

        if request.is_terminal:
            _log.debug(
                "Cancel called on terminal request — no-op.",
                request_id=request_id,
                status=request.status.value,
            )
            return False

        # Cancel via dispatcher (best-effort)
        try:
            self._dispatcher.cancel(request_id, reason=reason)
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "Dispatcher cancel raised; continuing with local cancel.",
                request_id=request_id,
                error=str(exc),
            )

        # Mark request cancelled
        request.set_status(RequestStatus.CANCELLED)
        request.mark_completed()
        request.set_error("EGE-CANCEL", reason or "Cancelled by caller.")

        # Update M1 lifecycle
        lc_id = request.lifecycle_request_id
        if lc_id:
            try:
                lc_request = self._lifecycle.get(lc_id)
                if lc_request.is_active:
                    self._lifecycle.cancel(lc_id, reason=reason or "Cancelled by caller.")
                    self._lifecycle.archive(lc_id)
            except Exception as lc_exc:  # noqa: BLE001
                _log.warning(
                    "Lifecycle cancel failed.",
                    lc_id=lc_id,
                    error=str(lc_exc),
                )

        lifecycle_ms = max(0.0, (time.time() - request.created_at) * 1_000.0)
        with self._lock:
            self._stats.record_cancelled(lifecycle_ms)

        _log.info(
            "Request cancelled.",
            request_id=request_id,
            reason=reason,
        )
        return True

    # ── Retry request ─────────────────────────────────────────────────────────

    def retry_request(self, request_id: str) -> GatewayResponse:
        """
        Retry a failed request if retry attempts remain.

        Re-submits the original context through the full 10-step workflow.
        """
        self._assert_running()

        request = self._registry.get(request_id)

        if not request.is_failed:
            raise GatewayRequestSubmissionError(
                reason=f"Request '{request_id}' is not in FAILED state "
                       f"(current: {request.status.value})"
            )

        if not request.can_retry:
            raise GatewayRequestSubmissionError(
                reason=f"Request '{request_id}' has exhausted all retries "
                       f"({request.retry_count}/{request.max_retries})"
            )

        request.increment_retry()
        request.set_status(RequestStatus.RETRYING)

        with self._lock:
            self._stats.record_retry()

        _log.info(
            "Retrying request.",
            request_id=request_id,
            retry_count=request.retry_count,
            max_retries=request.max_retries,
        )

        return self.process_request(request.context)

    # ── Query ─────────────────────────────────────────────────────────────────

    def all_requests(self) -> List[EngineGatewayRequest]:
        return self._registry.all()

    def active_requests(self) -> List[EngineGatewayRequest]:
        return self._registry.active()

    def completed_requests(self) -> List[EngineGatewayRequest]:
        return self._registry.completed()

    def failed_requests(self) -> List[EngineGatewayRequest]:
        return self._registry.failed()

    def cancelled_requests(self) -> List[EngineGatewayRequest]:
        return self._registry.cancelled()

    def by_portfolio_id(self, portfolio_id: str) -> List[EngineGatewayRequest]:
        return self._registry.by_portfolio_id(portfolio_id)

    def by_strategy_id(self, strategy_id: str) -> List[EngineGatewayRequest]:
        return self._registry.by_strategy_id(strategy_id)

    def by_execution_id(self, execution_id: str) -> List[EngineGatewayRequest]:
        return self._registry.by_execution_id(execution_id)

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> GatewayEngineSnapshot:
        """Build and return a point-in-time snapshot of manager state."""
        requests = self._registry.all()
        active_sessions = len(self._sessions.active_sessions())
        with self._lock:
            stats = self._stats.copy()
        return self._factory.create_snapshot(
            engine_state=self._engine_state.current(),
            requests=requests,
            queue_sizes=self._queue.sizes(),
            statistics=stats,
            active_sessions=active_sessions,
        )

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> GatewayEngineStatistics:
        """Return a copy of the current engine statistics."""
        with self._lock:
            return self._stats.copy()

    # ── Observability ─────────────────────────────────────────────────────────

    @property
    def engine_state(self) -> EngineState:
        return self._engine_state.current()

    @property
    def dispatcher(self) -> GatewayDispatcher:
        return self._dispatcher

    @property
    def request_count(self) -> int:
        return self._registry.count
