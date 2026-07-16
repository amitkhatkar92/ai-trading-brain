"""iios/execution/oms/order_manager/order_manager.py
==================================================
OrderManager — the central IIOS v1.0 coordinator of all orders
inside the OMS layer.

Responsibilities:
  - Create and register ManagedOrder objects
  - Track active, completed, cancelled, and rejected orders
  - Manage parent-child order relationships
  - Manage grouped orders
  - Publish manager events
  - Produce OrderManagerResponse for every operation

The Order Manager does NOT:
  - Communicate with brokers
  - Perform order routing
  - Persist orders to storage
  - Evaluate risk
  - Implement execution algorithms

IIOS v1.0: LifecycleAwareMixin, logging, audit, error handling.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional, TYPE_CHECKING

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    DEFAULT_MAX_MANAGED_ORDERS,
    MANAGER_SYSTEM_ID,
    ManagerEventType,
    ManagerOrderState,
    OrderGroupType,
    OrderOwnership,
    TERMINAL_MANAGER_STATES,
    VERSION,
)
from .exceptions import (
    OrderAlreadyTerminalError,
    OrderManagerError,
    OrderManagerNotRunning,
    OrderManagerStateError,
    OrderNotFoundError,
    OrderRegistrationError,
    OrderValidationError,
)
from .order_manager_context import ManagedOrder, OrderManagerSnapshot
from .order_manager_events import OrderManagerEvent, make_manager_event
from .order_manager_factory import OrderManagerFactory
from .order_manager_history import OrderManagerHistory
from .order_manager_registry import OrderManagerRegistry
from .order_manager_request import (
    ArchiveOrderRequest,
    CloseOrderRequest,
    CreateOrderRequest,
    LookupOrderRequest,
    OrderManagerRequest,
    RemoveOrderRequest,
    ResumeOrderRequest,
    SuspendOrderRequest,
    UpdateOrderRequest,
)
from .order_manager_response import OrderManagerResponse
from .order_manager_statistics import OrderManagerStatistics
from .order_manager_validation import OrderManagerValidator

if TYPE_CHECKING:
    from iios.execution.lifecycle.order import Order

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID,
                          component="OrderManager")


class OrderManager(LifecycleAwareMixin):
    """
    IIOS v1.0 central coordinator for all order management.

    Owns:
      - OrderManagerRegistry  — stores ManagedOrder objects
      - OrderManagerFactory   — creates ManagedOrder objects
      - OrderManagerValidator — validates operations
    """

    SYSTEM_ID = MANAGER_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_orders: int = DEFAULT_MAX_MANAGED_ORDERS) -> None:
        self._registry  = OrderManagerRegistry(max_orders=max_orders)
        self._factory   = OrderManagerFactory()
        self._validator = OrderManagerValidator()
        self._started_at: float = 0.0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        self._started_at = time.time()
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION
        )
        _log.info("OrderManager started.")
        self._dispatch(make_manager_event(ManagerEventType.MANAGER_STARTED))

    def _on_stop(self) -> None:
        if self._registry.is_running:
            self._registry.stop()
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION
        )
        _log.info("OrderManager stopped.")
        self._dispatch(make_manager_event(ManagerEventType.MANAGER_STOPPED))

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    def _assert_running(self) -> None:
        if not self.is_running:
            raise OrderManagerNotRunning(
                "OrderManager must be started before use."
            )

    # ── Create Order ──────────────────────────────────────────────────────────

    def create_order(
        self,
        request: CreateOrderRequest,
    ) -> OrderManagerResponse:
        """
        Create a new ManagedOrder and register it.

        Returns
        -------
        OrderManagerResponse  with managed_order set on success.
        """
        self._assert_running()
        t0 = time.time()

        # Validate registration
        existing = frozenset(self._registry.all_order_ids())
        val = self._validator.validate_registration(request, existing)
        if not val:
            return OrderManagerResponse.failure(
                request.request_id,
                request.operation,
                request.order_id,
                f"Validation failed: {'; '.join(val.errors)}",
                error_code = "OMS-007",
                duration_ms = (time.time() - t0) * 1_000,
            )

        # Create
        try:
            managed = self._factory.create(request)
            self._registry.register(managed)
        except Exception as exc:
            return OrderManagerResponse.failure(
                request.request_id,
                request.operation,
                request.order_id,
                str(exc),
                error_code  = "OMS-001",
                duration_ms = (time.time() - t0) * 1_000,
            )

        return OrderManagerResponse.success(
            request.request_id,
            request.operation,
            request.order_id,
            managed,
            duration_ms = (time.time() - t0) * 1_000,
        )

    def register_order(
        self,
        order_id:        str,
        workflow_id:     str        = "",
        execution_id:    str        = "",
        portfolio_id:    str        = "",
        strategy_id:     str        = "",
        decision_id:     str        = "",
        correlation_id:  str        = "",
        order:           Optional[Any] = None,
        ownership:       OrderOwnership = OrderOwnership.STRATEGY,
        owner_id:        str        = "",
        parent_order_id: str        = "",
        group_id:        str        = "",
        group_type:      Optional[OrderGroupType] = None,
        tags:            frozenset[str] = frozenset(),
    ) -> OrderManagerResponse:
        """Convenience: create + register from named parameters."""
        req = CreateOrderRequest(
            order_id        = order_id,
            workflow_id     = workflow_id,
            execution_id    = execution_id,
            portfolio_id    = portfolio_id,
            strategy_id     = strategy_id,
            decision_id     = decision_id,
            correlation_id  = correlation_id,
            order           = order,
            ownership       = ownership,
            owner_id        = owner_id,
            parent_order_id = parent_order_id,
            group_id        = group_id,
            group_type      = group_type,
            tags            = tags,
        )
        return self.create_order(req)

    # ── Update Order ──────────────────────────────────────────────────────────

    def update_order(
        self,
        request: UpdateOrderRequest,
    ) -> OrderManagerResponse:
        """Transition a managed order's OMS state."""
        self._assert_running()
        t0 = time.time()
        if request.new_state is None:
            return OrderManagerResponse.failure(
                request.request_id,
                request.operation,
                request.order_id,
                "new_state must be provided",
                error_code  = "OMS-007",
                duration_ms = (time.time() - t0) * 1_000,
            )
        try:
            managed = self._registry.apply_transition(
                request.order_id,
                request.new_state,
                actor  = request.actor,
                reason = request.reason,
            )
            if request.error_message:
                managed.error_message = request.error_message
                managed.error_code    = request.error_code
                managed.error_count   += 1
        except (OrderNotFoundError, OrderManagerStateError, OrderAlreadyTerminalError) as exc:
            return OrderManagerResponse.failure(
                request.request_id,
                request.operation,
                request.order_id,
                str(exc),
                error_code  = exc.code,
                duration_ms = (time.time() - t0) * 1_000,
            )
        return OrderManagerResponse.success(
            request.request_id,
            request.operation,
            request.order_id,
            managed,
            duration_ms = (time.time() - t0) * 1_000,
        )

    # ── Suspend / Resume ──────────────────────────────────────────────────────

    def suspend_order(self, request: SuspendOrderRequest) -> OrderManagerResponse:
        self._assert_running()
        t0 = time.time()
        try:
            managed = self._registry.suspend(request.order_id, request.reason)
        except (OrderNotFoundError, OrderAlreadyTerminalError) as exc:
            return OrderManagerResponse.failure(
                request.request_id, request.operation, request.order_id,
                str(exc), error_code=exc.code,
                duration_ms=(time.time() - t0) * 1_000,
            )
        return OrderManagerResponse.success(
            request.request_id, request.operation, request.order_id,
            managed, duration_ms=(time.time() - t0) * 1_000,
        )

    def resume_order(self, request: ResumeOrderRequest) -> OrderManagerResponse:
        self._assert_running()
        t0 = time.time()
        try:
            managed = self._registry.resume(request.order_id, request.reason)
        except OrderNotFoundError as exc:
            return OrderManagerResponse.failure(
                request.request_id, request.operation, request.order_id,
                str(exc), error_code=exc.code,
                duration_ms=(time.time() - t0) * 1_000,
            )
        return OrderManagerResponse.success(
            request.request_id, request.operation, request.order_id,
            managed, duration_ms=(time.time() - t0) * 1_000,
        )

    # ── Close / Archive / Remove ──────────────────────────────────────────────

    def close_order(self, request: CloseOrderRequest) -> OrderManagerResponse:
        t_state = (
            ManagerOrderState.COMPLETED
            if request.succeeded
            else ManagerOrderState.FAILED
        )
        return self.update_order(UpdateOrderRequest(
            request_id    = request.request_id,
            order_id      = request.order_id,
            new_state     = t_state,
            reason        = request.reason,
            actor         = request.requested_by,
            error_message = request.error_message,
        ))

    def archive_order(self, request: ArchiveOrderRequest) -> OrderManagerResponse:
        self._assert_running()
        t0 = time.time()
        try:
            managed = self._registry.archive(request.order_id)
        except OrderNotFoundError as exc:
            return OrderManagerResponse.failure(
                request.request_id, request.operation, request.order_id,
                str(exc), error_code=exc.code,
                duration_ms=(time.time() - t0) * 1_000,
            )
        return OrderManagerResponse.success(
            request.request_id, request.operation, request.order_id,
            managed, duration_ms=(time.time() - t0) * 1_000,
        )

    def remove_order(self, request: RemoveOrderRequest) -> OrderManagerResponse:
        self._assert_running()
        t0 = time.time()
        try:
            managed = self._registry.remove(request.order_id)
        except OrderNotFoundError as exc:
            return OrderManagerResponse.failure(
                request.request_id, request.operation, request.order_id,
                str(exc), error_code=exc.code,
                duration_ms=(time.time() - t0) * 1_000,
            )
        return OrderManagerResponse.success(
            request.request_id, request.operation, request.order_id,
            managed, duration_ms=(time.time() - t0) * 1_000,
        )

    # ── Lookup ────────────────────────────────────────────────────────────────

    def lookup(self, order_id: str) -> Optional[ManagedOrder]:
        self._assert_running()
        try:
            return self._registry.get(order_id)
        except OrderNotFoundError:
            return None

    def contains(self, order_id: str) -> bool:
        self._assert_running()
        return self._registry.contains(order_id)

    def get_active(self) -> list[ManagedOrder]:
        self._assert_running()
        return self._registry.get_active()

    def get_by_workflow(self, workflow_id: str) -> list[ManagedOrder]:
        self._assert_running()
        return self._registry.get_by_workflow(workflow_id)

    def get_by_strategy(self, strategy_id: str) -> list[ManagedOrder]:
        self._assert_running()
        return self._registry.get_by_strategy(strategy_id)

    def get_history(self, order_id: str) -> OrderManagerHistory:
        self._assert_running()
        return self._registry.get_history(order_id)

    def count(self) -> int:
        self._assert_running()
        return self._registry.count()

    # ── Parent-child ──────────────────────────────────────────────────────────

    def attach_child(
        self,
        parent_id: str,
        child_id:  str,
    ) -> OrderManagerResponse:
        self._assert_running()
        t0 = time.time()
        try:
            parent = self._registry.attach_child(parent_id, child_id)
        except (OrderNotFoundError, OrderAlreadyTerminalError) as exc:
            return OrderManagerResponse.failure(
                "", "ATTACH_CHILD", child_id,
                str(exc), error_code=exc.code,
                duration_ms=(time.time() - t0) * 1_000,
            )
        return OrderManagerResponse.success(
            "", "ATTACH_CHILD", child_id,
            parent, duration_ms=(time.time() - t0) * 1_000,
        )

    # ── Statistics / snapshot ─────────────────────────────────────────────────

    def statistics(self) -> OrderManagerStatistics:
        self._assert_running()
        return self._registry.statistics()

    def snapshot(self) -> OrderManagerSnapshot:
        self._assert_running()
        counts = self._registry.snapshot_counts()
        stats  = self._registry.statistics()
        return OrderManagerSnapshot(
            total_registered = counts["total"],
            active_count     = counts["active"],
            completed_count  = counts["completed"],
            failed_count     = counts["failed"],
            suspended_count  = counts["suspended"],
            peak_active      = stats.peak_active_orders,
            manager_running  = self.is_running,
        )

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, fn: Callable[[OrderManagerEvent], None]) -> None:
        self._registry.add_listener(fn)

    def remove_listener(self, fn: Callable[[OrderManagerEvent], None]) -> None:
        self._registry.remove_listener(fn)

    def _dispatch(self, event: OrderManagerEvent) -> None:
        self._registry._dispatch(event)

    # ── Misc ──────────────────────────────────────────────────────────────────

    @property
    def uptime_sec(self) -> float:
        if self._started_at == 0.0:
            return 0.0
        return time.time() - self._started_at
