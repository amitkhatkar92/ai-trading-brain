"""iios/execution/oms/order_manager/order_manager_registry.py
==================================================
OrderManagerRegistry — IIOS v1.0 thread-safe store of ManagedOrder
objects with secondary indexes and event dispatch.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_REGISTRY,
    ACTOR_SYSTEM,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_MANAGED_ORDERS,
    ManagerOrderState,
    ManagerEventType,
    REGISTRY_SYSTEM_ID,
    TERMINAL_MANAGER_STATES,
    VERSION,
)
from .exceptions import (
    DuplicateOrderError,
    OrderAlreadyTerminalError,
    OrderManagerCapacityError,
    OrderManagerNotRunning,
    OrderManagerStateError,
    OrderNotFoundError,
)
from .order_manager_context import ManagedOrder
from .order_manager_events import OrderManagerEvent, ManagerEventType, make_manager_event
from .order_manager_history import (
    OrderManagerHistory,
    ManagerTransition,
    make_transition,
)
from .order_manager_state import assert_manager_transition
from .order_manager_statistics import OrderManagerStatistics

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID,
                          component="OrderManagerRegistry")


class OrderManagerRegistry(LifecycleAwareMixin):
    """
    IIOS v1.0 registry for ManagedOrder objects.

    Thread-safe. Lifecycle-aware. Secondary indexes by workflow,
    portfolio, strategy, state. Event dispatch on transitions.
    """

    SYSTEM_ID = REGISTRY_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_orders: int = DEFAULT_MAX_MANAGED_ORDERS) -> None:
        self._orders:        dict[str, ManagedOrder]            = {}
        self._histories:     dict[str, OrderManagerHistory]     = {}
        self._by_workflow:   dict[str, list[str]]               = {}
        self._by_portfolio:  dict[str, list[str]]               = {}
        self._by_strategy:   dict[str, list[str]]               = {}
        self._by_state:      dict[ManagerOrderState, list[str]] = {
            s: [] for s in ManagerOrderState
        }
        self._max_orders     = max_orders
        self._lock           = threading.RLock()
        self._listeners:     list[Callable[[OrderManagerEvent], None]] = []
        self._stats          = OrderManagerStatistics()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION
        )
        _log.info("OrderManagerRegistry started.", capacity=self._max_orders)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION
        )
        _log.info("OrderManagerRegistry stopped.", registered=len(self._orders))

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    def _assert_running(self) -> None:
        if not self.is_running:
            raise OrderManagerNotRunning(
                "OrderManagerRegistry must be started before use."
            )

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        managed: ManagedOrder,
        overwrite: bool = False,
    ) -> ManagedOrder:
        self._assert_running()
        oid = managed.order_id
        with self._lock:
            if oid in self._orders and not overwrite:
                raise DuplicateOrderError(oid)
            if (
                len(self._orders) >= self._max_orders
                and oid not in self._orders
            ):
                raise OrderManagerCapacityError(
                    f"Registry capacity reached ({self._max_orders})"
                )
            self._orders[oid] = managed
            history = OrderManagerHistory(oid, max_entries=DEFAULT_MAX_HISTORY)
            self._histories[oid] = history

            # Initial transition record
            transition = make_transition(
                oid,
                ManagerOrderState.INITIALIZED,
                managed.manager_state,
                actor=ACTOR_REGISTRY,
                reason="registered",
            )
            history.record(transition)

            # Update indexes
            self._by_workflow.setdefault(managed.workflow_id, []).append(oid)
            self._by_portfolio.setdefault(managed.portfolio_id, []).append(oid)
            self._by_strategy.setdefault(managed.strategy_id, []).append(oid)
            self._by_state[managed.manager_state].append(oid)

        self._stats.record_registered()
        _log.info("ManagedOrder registered.", order_id=oid)
        _audit.log_workflow_event(
            self.SYSTEM_ID, "register", "ORDER_REGISTERED",
            actor=ACTOR_REGISTRY, order_id=oid,
        )
        self._dispatch(make_manager_event(
            ManagerEventType.ORDER_REGISTERED,
            oid,
            workflow_id   = managed.workflow_id,
            manager_state = managed.manager_state,
            actor         = ACTOR_REGISTRY,
        ))
        return managed

    def apply_transition(
        self,
        order_id:  str,
        to_state:  ManagerOrderState,
        *,
        actor:  str = ACTOR_SYSTEM,
        reason: str = "",
    ) -> ManagedOrder:
        """Transition a managed order's OMS state."""
        self._assert_running()
        with self._lock:
            managed = self._get_or_raise(order_id)
            if managed.is_terminal:
                raise OrderAlreadyTerminalError(order_id, managed.manager_state.value)
            from_state = managed.manager_state
            assert_manager_transition(order_id, from_state, to_state)

            # Mutate
            managed.manager_state = to_state
            now = time.time()
            if to_state == ManagerOrderState.PROCESSING and managed.processing_started_at is None:
                managed.processing_started_at = now
            if to_state in TERMINAL_MANAGER_STATES:
                managed.completed_at = now

            # Update state index
            if order_id in self._by_state[from_state]:
                self._by_state[from_state].remove(order_id)
            self._by_state[to_state].append(order_id)

            # History
            t = make_transition(order_id, from_state, to_state, actor=actor, reason=reason)
            self._histories[order_id].record(t)

        # Stats
        if to_state == ManagerOrderState.COMPLETED:
            pm = managed.processing_time_ms or 0.0
            self._stats.record_completed(pm)
        elif to_state == ManagerOrderState.FAILED:
            self._stats.record_failed()

        # Event
        self._dispatch(make_manager_event(
            self._event_for_state(to_state),
            order_id,
            workflow_id   = managed.workflow_id,
            manager_state = to_state,
            actor         = actor,
            reason        = reason,
        ))
        return managed

    def suspend(self, order_id: str, reason: str = "") -> ManagedOrder:
        self._assert_running()
        with self._lock:
            managed = self._get_or_raise(order_id)
            managed.is_suspended  = True
            managed.suspend_reason = reason
        self._stats.record_suspended()
        self._dispatch(make_manager_event(
            ManagerEventType.ORDER_SUSPENDED,
            order_id,
            reason=reason,
        ))
        return managed

    def resume(self, order_id: str, reason: str = "") -> ManagedOrder:
        self._assert_running()
        with self._lock:
            managed = self._get_or_raise(order_id)
            managed.is_suspended  = False
            managed.suspend_reason = ""
        self._stats.record_resumed()
        self._dispatch(make_manager_event(
            ManagerEventType.ORDER_RESUMED,
            order_id,
            reason=reason,
        ))
        return managed

    def archive(self, order_id: str) -> ManagedOrder:
        self._assert_running()
        with self._lock:
            managed = self._get_or_raise(order_id)
        self._stats.record_archived()
        self._dispatch(make_manager_event(ManagerEventType.ORDER_ARCHIVED, order_id))
        return managed

    def remove(self, order_id: str) -> ManagedOrder:
        self._assert_running()
        with self._lock:
            managed = self._get_or_raise(order_id)
            del self._orders[order_id]
            del self._histories[order_id]
            # Clean up indexes
            for bucket in self._by_state.values():
                if order_id in bucket:
                    bucket.remove(order_id)
            for d in (self._by_workflow, self._by_portfolio, self._by_strategy):
                for bucket in d.values():
                    if order_id in bucket:
                        bucket.remove(order_id)
        self._dispatch(make_manager_event(ManagerEventType.ORDER_REMOVED, order_id))
        return managed

    def attach_child(
        self,
        parent_id: str,
        child_id:  str,
    ) -> ManagedOrder:
        self._assert_running()
        with self._lock:
            parent = self._get_or_raise(parent_id)
            _      = self._get_or_raise(child_id)
            parent.add_child(child_id)
            child = self._get_or_raise(child_id)
            child.parent_order_id = parent_id
        return parent

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, order_id: str) -> ManagedOrder:
        self._assert_running()
        with self._lock:
            return self._get_or_raise(order_id)

    def contains(self, order_id: str) -> bool:
        with self._lock:
            return order_id in self._orders

    def count(self) -> int:
        with self._lock:
            return len(self._orders)

    def get_history(self, order_id: str) -> OrderManagerHistory:
        self._assert_running()
        with self._lock:
            if order_id not in self._histories:
                raise OrderNotFoundError(order_id)
            return self._histories[order_id]

    def get_by_state(self, state: ManagerOrderState) -> list[ManagedOrder]:
        self._assert_running()
        with self._lock:
            ids = list(self._by_state.get(state, []))
            return [self._orders[oid] for oid in ids if oid in self._orders]

    def get_active(self) -> list[ManagedOrder]:
        result: list[ManagedOrder] = []
        from .constants import ACTIVE_MANAGER_STATES
        for state in ACTIVE_MANAGER_STATES:
            result.extend(self.get_by_state(state))
        return result

    def get_by_workflow(self, workflow_id: str) -> list[ManagedOrder]:
        self._assert_running()
        with self._lock:
            ids = self._by_workflow.get(workflow_id, [])
            return [self._orders[oid] for oid in ids if oid in self._orders]

    def get_by_strategy(self, strategy_id: str) -> list[ManagedOrder]:
        self._assert_running()
        with self._lock:
            ids = self._by_strategy.get(strategy_id, [])
            return [self._orders[oid] for oid in ids if oid in self._orders]

    def all_order_ids(self) -> list[str]:
        with self._lock:
            return list(self._orders.keys())

    def statistics(self) -> OrderManagerStatistics:
        return self._stats

    def snapshot_counts(self) -> dict[str, int]:
        with self._lock:
            return {
                "total":     len(self._orders),
                "active":    sum(len(v) for k, v in self._by_state.items()
                                 if k in ACTIVE_MANAGER_STATES_LOCAL),
                "completed": len(self._by_state.get(ManagerOrderState.COMPLETED, [])),
                "failed":    len(self._by_state.get(ManagerOrderState.FAILED, [])),
                "suspended": sum(
                    1 for m in self._orders.values() if m.is_suspended
                ),
            }

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(self, fn: Callable[[OrderManagerEvent], None]) -> None:
        with self._lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[OrderManagerEvent], None]) -> None:
        with self._lock:
            self._listeners = [f for f in self._listeners if f != fn]

    def _dispatch(self, event: OrderManagerEvent) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:
                _log.warning("Event listener raised — continuing.")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_raise(self, order_id: str) -> ManagedOrder:
        managed = self._orders.get(order_id)
        if managed is None:
            raise OrderNotFoundError(order_id)
        return managed

    @staticmethod
    def _event_for_state(state: ManagerOrderState) -> ManagerEventType:
        return {
            ManagerOrderState.READY:      ManagerEventType.ORDER_REGISTERED,
            ManagerOrderState.PROCESSING: ManagerEventType.ORDER_UPDATED,
            ManagerOrderState.WAITING:    ManagerEventType.ORDER_UPDATED,
            ManagerOrderState.COMPLETED:  ManagerEventType.ORDER_CLOSED,
            ManagerOrderState.FAILED:     ManagerEventType.ORDER_CLOSED,
        }.get(state, ManagerEventType.ORDER_UPDATED)


# Module-level constant for use inside snapshot_counts
from .constants import ACTIVE_MANAGER_STATES as ACTIVE_MANAGER_STATES_LOCAL  # noqa: E402
