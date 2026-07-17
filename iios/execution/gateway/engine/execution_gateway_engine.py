"""iios/execution/gateway/engine/execution_gateway_engine.py
==================================================
ExecutionGatewayEngine — the primary public API for the IIOS
Execution Gateway Engine.

Coordinates the complete gateway workflow for execution requests
approved by the Execution Risk subsystem.

Non-responsibilities
--------------------
  No broker-specific logic.
  No routing algorithms.
  No exchange connectivity.
  No risk calculations.

Public interface
----------------
  engine = ExecutionGatewayEngine()
  engine.start()

  ctx      = engine.make_context(execution_id=..., order_id=..., ...)
  response = engine.submit_request(ctx)

  engine.cancel_request(request_id, reason="…")
  engine.retry_request(request_id)
  snap     = engine.snapshot()
  stats    = engine.statistics()

  engine.stop()

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState as FrameworkState
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_QUEUE_SIZE,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_RETRY_DELAY_SECS,
    DEFAULT_SESSION_TIMEOUT_SECS,
    ENGINE_SYSTEM_ID,
    VERSION,
    EngineState,
)
from .exceptions import GatewayEngineNotRunningError
from .gateway_context import EngineGatewayContext, make_engine_gateway_context
from .gateway_dispatcher import BrokerAbstractionProtocol, RoutingFrameworkProtocol
from .gateway_events import GatewayEngineEvent
from .gateway_manager import GatewayManager
from .gateway_request import EngineGatewayRequest
from .gateway_response import GatewayResponse
from .gateway_snapshot import GatewayEngineSnapshot
from .gateway_statistics import GatewayEngineStatistics

_log   = get_logger(__name__, engine_id=ENGINE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)


class ExecutionGatewayEngine(LifecycleAwareMixin):
    """
    Primary public API for the Execution Gateway Engine.

    Responsibilities
    ----------------
    * Accept and validate execution requests.
    * Coordinate the full gateway workflow via GatewayManager.
    * Maintain request history and statistics.
    * Publish domain events to registered listeners.
    * Expose query methods for monitoring and observability.

    Non-responsibilities
    --------------------
    * No broker-specific logic.
    * No routing algorithms.
    * No exchange connectivity.
    * No risk calculations.

    Usage
    -----
    engine = ExecutionGatewayEngine()
    engine.start()

    ctx = engine.make_context(
        execution_id="EX-001",
        order_id="ORD-001",
        portfolio_id="PORT-A",
        strategy_id="STRAT-1",
        symbol="NIFTY25JAN25CE",
        side="BUY",
        quantity=50,
        price=200.0,
    )
    response = engine.submit_request(ctx)

    print(response.is_accepted)      # True in paper / simulated mode
    print(response.lifecycle_request_id)   # M1 lifecycle ID

    engine.stop()
    """

    SYSTEM_ID = ENGINE_SYSTEM_ID
    VERSION   = VERSION

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
        self._lock    = threading.RLock()
        self._manager = GatewayManager(
            max_requests=max_requests,
            max_queue_size=max_queue_size,
            max_sessions=max_sessions,
            max_history=max_history,
            session_timeout=session_timeout,
            retry_delay=retry_delay,
            broker=broker,
            router=router,
        )

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != FrameworkState.RUNNING:
            raise GatewayEngineNotRunningError()

    def _on_start(self) -> None:
        self._manager.start()
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, FrameworkState.STOPPED, FrameworkState.RUNNING, VERSION
        )
        _log.info("ExecutionGatewayEngine started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, FrameworkState.RUNNING, FrameworkState.STOPPED, VERSION
        )
        _log.info(
            "ExecutionGatewayEngine stopped.",
            requests=self._manager.request_count,
        )
        self._manager.stop()

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == FrameworkState.RUNNING

    # ── Context factory ───────────────────────────────────────────────────────

    def make_context(
        self,
        execution_id: str,
        order_id:     str,
        portfolio_id: str,
        strategy_id:  str,
        **kwargs: Any,
    ) -> EngineGatewayContext:
        """
        Convenience factory for ``EngineGatewayContext``.

        Auto-generates ``request_id`` unless supplied as a keyword argument.
        All other ``EngineGatewayContext`` fields may be passed as kwargs.
        """
        return make_engine_gateway_context(
            execution_id=execution_id,
            order_id=order_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            **kwargs,
        )

    # ── Core operations ───────────────────────────────────────────────────────

    def submit_request(self, context: EngineGatewayContext) -> GatewayResponse:
        """
        Submit an execution request through the full gateway workflow.

        Executes the 10-step workflow:
          Receive → Validate → Register → Queue → Dispatch → Respond.

        Returns a ``GatewayResponse`` regardless of outcome.

        Raises
        ------
        GatewayEngineNotRunningError
            If the engine has not been started.
        GatewayRequestSubmissionError
            If the context fails validation or the queue is at capacity.
        """
        self._assert_running()
        return self._manager.process_request(context)

    def cancel_request(self, request_id: str, *, reason: str = "") -> bool:
        """
        Cancel an active request by its engine-level ``request_id``.

        Returns True if the request was found and cancellation was initiated.
        """
        self._assert_running()
        return self._manager.cancel_request(request_id, reason=reason)

    def retry_request(self, request_id: str) -> GatewayResponse:
        """
        Retry a failed request.

        Re-submits the original context through the full workflow.
        The request must be in FAILED state and must have retries remaining.

        Raises
        ------
        GatewayRequestSubmissionError
            If the request is not in FAILED state or has no retries remaining.
        """
        self._assert_running()
        return self._manager.retry_request(request_id)

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[GatewayEngineEvent], None]
    ) -> None:
        """Register a listener to receive all engine domain events."""
        self._manager.add_event_listener(listener)

    def remove_event_listener(
        self, listener: Callable[[GatewayEngineEvent], None]
    ) -> None:
        """Unregister a previously registered event listener."""
        self._manager.remove_event_listener(listener)

    # ── Broker / router registration ──────────────────────────────────────────

    def register_broker(self, broker: BrokerAbstractionProtocol) -> None:
        """
        Register a Broker Abstraction (M3) implementation.

        Replaces the default SimulatedDispatch.
        The broker must implement ``BrokerAbstractionProtocol``.
        """
        self._manager.register_broker(broker)

    def register_router(self, router: RoutingFrameworkProtocol) -> None:
        """
        Register a Routing Framework (M4) implementation.

        Replaces the default null router.
        The router must implement ``RoutingFrameworkProtocol``.
        """
        self._manager.register_router(router)

    # ── Query ─────────────────────────────────────────────────────────────────

    def all_requests(self) -> List[EngineGatewayRequest]:
        """All registered engine requests (active + terminal)."""
        return self._manager.all_requests()

    def active_requests(self) -> List[EngineGatewayRequest]:
        """Requests in active (non-terminal) states."""
        return self._manager.active_requests()

    def completed_requests(self) -> List[EngineGatewayRequest]:
        """Requests that completed successfully."""
        return self._manager.completed_requests()

    def failed_requests(self) -> List[EngineGatewayRequest]:
        """Requests that failed."""
        return self._manager.failed_requests()

    def cancelled_requests(self) -> List[EngineGatewayRequest]:
        """Requests that were cancelled."""
        return self._manager.cancelled_requests()

    def by_execution_id(self, execution_id: str) -> List[EngineGatewayRequest]:
        """Requests matching a given execution_id."""
        return self._manager.by_execution_id(execution_id)

    def by_portfolio_id(self, portfolio_id: str) -> List[EngineGatewayRequest]:
        """Requests matching a given portfolio_id."""
        return self._manager.by_portfolio_id(portfolio_id)

    def by_strategy_id(self, strategy_id: str) -> List[EngineGatewayRequest]:
        """Requests matching a given strategy_id."""
        return self._manager.by_strategy_id(strategy_id)

    # ── Observability ─────────────────────────────────────────────────────────

    def snapshot(self) -> GatewayEngineSnapshot:
        """
        Build and return a point-in-time snapshot of the engine state.

        Includes queue depths, request counts by status, recent activity,
        and a copy of the current statistics.
        """
        return self._manager.snapshot()

    def statistics(self) -> GatewayEngineStatistics:
        """Return a copy of the current engine statistics."""
        return self._manager.statistics()

    @property
    def request_count(self) -> int:
        """Total number of registered requests (all statuses)."""
        return self._manager.request_count

    @property
    def engine_state(self) -> EngineState:
        """Current operational state of the engine."""
        return self._manager.engine_state

    @property
    def has_live_broker(self) -> bool:
        """True if a real broker abstraction is registered (not simulated)."""
        return self._manager.dispatcher.has_broker

    @property
    def has_router(self) -> bool:
        """True if a routing framework is registered."""
        return self._manager.dispatcher.has_router

    def __repr__(self) -> str:
        return (
            f"ExecutionGatewayEngine("
            f"running={self.is_running}, "
            f"requests={self.request_count}, "
            f"version={self.VERSION!r})"
        )
