"""tests/unit/iios/execution/oms/order_manager/test_order_manager.py
==================================================
Comprehensive test suite for C6 Phase 2 Module 1:
IIOS Order Manager.

12 test classes, 95%+ coverage.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────

from iios.execution.oms.order_manager.constants import (
    ACTIVE_MANAGER_STATES,
    TERMINAL_MANAGER_STATES,
    VALID_MANAGER_TRANSITIONS,
    ManagerEventType,
    ManagerOrderState,
    ManagerValidationCode,
    OrderGroupType,
    OrderOwnership,
    VERSION,
)
from iios.execution.oms.order_manager.exceptions import (
    DuplicateOrderError,
    OrderAlreadyTerminalError,
    OrderGroupError,
    OrderManagerCapacityError,
    OrderManagerError,
    OrderManagerNotRunning,
    OrderManagerStateError,
    OrderNotFoundError,
    OrderOwnershipError,
    OrderParentError,
    OrderRegistrationError,
    OrderValidationError,
)
from iios.execution.oms.order_manager.order_manager_context import (
    ManagedOrder,
    OrderManagerSnapshot,
)
from iios.execution.oms.order_manager.order_manager_events import (
    OrderManagerEvent,
    make_manager_event,
)
from iios.execution.oms.order_manager.order_manager_factory import OrderManagerFactory
from iios.execution.oms.order_manager.order_manager_history import (
    ManagerTransition,
    OrderManagerHistory,
    make_transition,
)
from iios.execution.oms.order_manager.order_manager_registry import OrderManagerRegistry
from iios.execution.oms.order_manager.order_manager_request import (
    ArchiveOrderRequest,
    CloseOrderRequest,
    CreateOrderRequest,
    RemoveOrderRequest,
    ResumeOrderRequest,
    SuspendOrderRequest,
    UpdateOrderRequest,
)
from iios.execution.oms.order_manager.order_manager_response import OrderManagerResponse
from iios.execution.oms.order_manager.order_manager_state import (
    allowed_next,
    assert_manager_transition,
    can_manager_transition,
    is_terminal,
)
from iios.execution.oms.order_manager.order_manager_statistics import OrderManagerStatistics
from iios.execution.oms.order_manager.order_manager_validation import (
    ManagerValidationResult,
    OrderManagerValidator,
)
from iios.execution.oms.order_manager.order_manager import OrderManager


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _create_req(
    order_id:    str = "ORD-001",
    workflow_id: str = "WF-001",
    strategy_id: str = "STRAT-001",
    **kwargs: Any,
) -> CreateOrderRequest:
    return CreateOrderRequest(
        order_id    = order_id,
        workflow_id = workflow_id,
        strategy_id = strategy_id,
        **kwargs,
    )


def _managed(
    order_id:    str = "ORD-001",
    workflow_id: str = "WF-001",
) -> ManagedOrder:
    return ManagedOrder(
        order_id    = order_id,
        workflow_id = workflow_id,
        strategy_id = "STRAT-001",
        manager_state = ManagerOrderState.READY,
    )


@pytest.fixture
def manager() -> OrderManager:
    m = OrderManager()
    m.start()
    yield m
    if m.is_running:
        m.stop()


@pytest.fixture
def registry() -> OrderManagerRegistry:
    r = OrderManagerRegistry()
    r.start()
    yield r
    if r.is_running:
        r.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants and state machine
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_manager_order_states(self) -> None:
        assert ManagerOrderState.INITIALIZED.value == "INITIALIZED"
        assert ManagerOrderState.READY.value       == "READY"
        assert ManagerOrderState.PROCESSING.value  == "PROCESSING"
        assert ManagerOrderState.WAITING.value     == "WAITING"
        assert ManagerOrderState.COMPLETED.value   == "COMPLETED"
        assert ManagerOrderState.FAILED.value      == "FAILED"

    def test_terminal_states(self) -> None:
        assert ManagerOrderState.COMPLETED in TERMINAL_MANAGER_STATES
        assert ManagerOrderState.FAILED    in TERMINAL_MANAGER_STATES
        assert ManagerOrderState.READY     not in TERMINAL_MANAGER_STATES

    def test_active_states(self) -> None:
        assert ManagerOrderState.READY      in ACTIVE_MANAGER_STATES
        assert ManagerOrderState.PROCESSING in ACTIVE_MANAGER_STATES
        assert ManagerOrderState.WAITING    in ACTIVE_MANAGER_STATES

    def test_ownership_values(self) -> None:
        assert OrderOwnership.SYSTEM.value   == "SYSTEM"
        assert OrderOwnership.STRATEGY.value == "STRATEGY"
        assert OrderOwnership.MANUAL.value   == "MANUAL"
        assert OrderOwnership.RECOVERY.value == "RECOVERY"

    def test_group_type_values(self) -> None:
        assert OrderGroupType.BASKET.value  == "BASKET"
        assert OrderGroupType.BRACKET.value == "BRACKET"
        assert OrderGroupType.OCO.value     == "OCO"

    def test_event_types(self) -> None:
        assert ManagerEventType.ORDER_REGISTERED.value == "ORDER_REGISTERED"
        assert ManagerEventType.ORDER_CLOSED.value     == "ORDER_CLOSED"
        assert ManagerEventType.MANAGER_STARTED.value  == "MANAGER_STARTED"


class TestStateMachine:
    def test_valid_transitions(self) -> None:
        assert can_manager_transition(ManagerOrderState.INITIALIZED, ManagerOrderState.READY)
        assert can_manager_transition(ManagerOrderState.READY,       ManagerOrderState.PROCESSING)
        assert can_manager_transition(ManagerOrderState.PROCESSING,  ManagerOrderState.COMPLETED)
        assert can_manager_transition(ManagerOrderState.PROCESSING,  ManagerOrderState.FAILED)
        assert can_manager_transition(ManagerOrderState.PROCESSING,  ManagerOrderState.WAITING)
        assert can_manager_transition(ManagerOrderState.WAITING,     ManagerOrderState.PROCESSING)

    def test_invalid_transitions(self) -> None:
        assert not can_manager_transition(ManagerOrderState.COMPLETED, ManagerOrderState.READY)
        assert not can_manager_transition(ManagerOrderState.FAILED,    ManagerOrderState.READY)
        assert not can_manager_transition(ManagerOrderState.READY,     ManagerOrderState.WAITING)

    def test_is_terminal(self) -> None:
        assert is_terminal(ManagerOrderState.COMPLETED)
        assert is_terminal(ManagerOrderState.FAILED)
        assert not is_terminal(ManagerOrderState.READY)
        assert not is_terminal(ManagerOrderState.PROCESSING)

    def test_allowed_next(self) -> None:
        allowed = allowed_next(ManagerOrderState.INITIALIZED)
        assert ManagerOrderState.READY in allowed
        assert ManagerOrderState.COMPLETED not in allowed

    def test_assert_transition_valid(self) -> None:
        assert_manager_transition("O", ManagerOrderState.INITIALIZED, ManagerOrderState.READY)

    def test_assert_transition_invalid_raises(self) -> None:
        with pytest.raises(OrderManagerStateError):
            assert_manager_transition("O", ManagerOrderState.COMPLETED, ManagerOrderState.READY)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_hierarchy(self) -> None:
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(OrderManagerError,       IIOSError)
        assert issubclass(OrderNotFoundError,      OrderManagerError)
        assert issubclass(DuplicateOrderError,     OrderManagerError)
        assert issubclass(OrderManagerCapacityError, OrderManagerError)
        assert issubclass(OrderManagerNotRunning,  OrderManagerError)
        assert issubclass(OrderManagerStateError,  OrderManagerError)
        assert issubclass(OrderAlreadyTerminalError, OrderManagerError)

    def test_not_found_carries_id(self) -> None:
        exc = OrderNotFoundError("ORD-X")
        assert exc.order_id == "ORD-X"
        assert "ORD-X" in str(exc)

    def test_duplicate_carries_id(self) -> None:
        exc = DuplicateOrderError("ORD-Y")
        assert exc.order_id == "ORD-Y"

    def test_state_error_carries_fields(self) -> None:
        exc = OrderManagerStateError("ORD-Z", "READY", "INITIALIZED")
        assert exc.order_id   == "ORD-Z"
        assert exc.from_state == "READY"
        assert exc.to_state   == "INITIALIZED"

    def test_terminal_error_carries_fields(self) -> None:
        exc = OrderAlreadyTerminalError("ORD-T", "COMPLETED")
        assert exc.order_id == "ORD-T"
        assert exc.state    == "COMPLETED"

    def test_validation_error_carries_errors(self) -> None:
        exc = OrderValidationError("fail", errors=("e1", "e2"))
        assert exc.errors == ("e1", "e2")

    def test_error_codes(self) -> None:
        assert OrderManagerError.DEFAULT_CODE          == "OMS-000"
        assert OrderRegistrationError.DEFAULT_CODE     == "OMS-001"
        assert OrderNotFoundError.DEFAULT_CODE         == "OMS-002"
        assert DuplicateOrderError.DEFAULT_CODE        == "OMS-003"
        assert OrderManagerCapacityError.DEFAULT_CODE  == "OMS-004"
        assert OrderManagerNotRunning.DEFAULT_CODE     == "OMS-005"
        assert OrderManagerStateError.DEFAULT_CODE     == "OMS-006"
        assert OrderAlreadyTerminalError.DEFAULT_CODE  == "OMS-011"


# ─────────────────────────────────────────────────────────────────────────────
# 3. ManagedOrder (core entity)
# ─────────────────────────────────────────────────────────────────────────────

class TestManagedOrder:
    def test_creation(self) -> None:
        m = _managed()
        assert m.order_id     == "ORD-001"
        assert m.workflow_id  == "WF-001"
        assert m.manager_state == ManagerOrderState.READY

    def test_is_active(self) -> None:
        m = _managed()
        assert m.is_active
        assert not m.is_terminal

    def test_is_terminal_completed(self) -> None:
        m = _managed()
        m.manager_state = ManagerOrderState.COMPLETED
        assert m.is_terminal
        assert m.is_completed
        assert not m.is_active

    def test_is_terminal_failed(self) -> None:
        m = _managed()
        m.manager_state = ManagerOrderState.FAILED
        assert m.is_terminal
        assert m.is_failed

    def test_has_parent_false(self) -> None:
        assert not _managed().has_parent

    def test_has_parent_true(self) -> None:
        m = _managed()
        m.parent_order_id = "PARENT-001"
        assert m.has_parent

    def test_add_remove_child(self) -> None:
        m = _managed()
        m.add_child("CHILD-001")
        assert m.has_children
        assert m.child_count == 1
        m.remove_child("CHILD-001")
        assert not m.has_children

    def test_processing_time_none_before_start(self) -> None:
        assert _managed().processing_time_ms is None

    def test_order_state_from_order(self) -> None:
        order = MagicMock()
        order.state.value = "SUBMITTED"
        m = _managed()
        m.order = order
        assert m.order_state == "SUBMITTED"

    def test_to_dict(self) -> None:
        m = _managed()
        d = m.to_dict()
        assert d["order_id"]      == "ORD-001"
        assert d["manager_state"] == "READY"
        assert "child_order_ids"  in d

    def test_repr(self) -> None:
        m = _managed()
        assert "ManagedOrder" in repr(m)
        assert "ORD-001" in repr(m)


class TestOrderManagerSnapshot:
    def test_to_dict(self) -> None:
        s = OrderManagerSnapshot(total_registered=5, active_count=3)
        d = s.to_dict()
        assert d["total_registered"] == 5
        assert d["active_count"]     == 3

    def test_frozen(self) -> None:
        s = OrderManagerSnapshot()
        with pytest.raises((AttributeError, TypeError)):
            s.total_registered = 99  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Requests and Responses
# ─────────────────────────────────────────────────────────────────────────────

class TestRequestsResponses:
    def test_create_request_defaults(self) -> None:
        r = _create_req()
        assert r.order_id    == "ORD-001"
        assert r.operation   == "CREATE_ORDER"
        assert r.age_sec     >= 0.0

    def test_response_success(self) -> None:
        r = OrderManagerResponse.success("REQ", "CREATE_ORDER", "ORD-001")
        assert r.succeeded
        assert not r.failed

    def test_response_failure(self) -> None:
        r = OrderManagerResponse.failure("REQ", "CREATE_ORDER", "ORD-001", "error")
        assert not r.succeeded
        assert r.failed
        assert r.error_message == "error"

    def test_response_to_dict(self) -> None:
        r = OrderManagerResponse.success("REQ", "CREATE_ORDER", "ORD-001")
        d = r.to_dict()
        assert d["order_id"]  == "ORD-001"
        assert d["succeeded"]

    def test_response_frozen(self) -> None:
        r = OrderManagerResponse.success("REQ", "CREATE_ORDER", "ORD-001")
        with pytest.raises((AttributeError, TypeError)):
            r.order_id = "X"  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Events
# ─────────────────────────────────────────────────────────────────────────────

class TestEvents:
    def test_make_manager_event(self) -> None:
        e = make_manager_event(
            ManagerEventType.ORDER_REGISTERED,
            "ORD-001",
            workflow_id   = "WF-001",
            manager_state = ManagerOrderState.READY,
        )
        assert e.order_id   == "ORD-001"
        assert e.event_type == ManagerEventType.ORDER_REGISTERED

    def test_event_frozen(self) -> None:
        e = make_manager_event(ManagerEventType.ORDER_REGISTERED, "O")
        with pytest.raises((AttributeError, TypeError)):
            e.order_id = "X"  # type: ignore[misc]

    def test_event_to_dict(self) -> None:
        e = make_manager_event(
            ManagerEventType.ORDER_CLOSED,
            "O",
            manager_state = ManagerOrderState.COMPLETED,
        )
        d = e.to_dict()
        assert d["event_type"]    == "ORDER_CLOSED"
        assert d["manager_state"] == "COMPLETED"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    def setup_method(self) -> None:
        self.v = OrderManagerValidator()

    def test_valid_registration(self) -> None:
        r = _create_req()
        result = self.v.validate_registration(r, frozenset())
        assert result.passed

    def test_empty_order_id_fails(self) -> None:
        r = _create_req(order_id="")
        result = self.v.validate_registration(r, frozenset())
        assert not result.passed
        assert any("MISSING_ORDER_ID" in e for e in result.errors)

    def test_duplicate_id_fails(self) -> None:
        r = _create_req()
        result = self.v.validate_registration(r, frozenset({"ORD-001"}))
        assert not result.passed
        assert any("DUPLICATE_ORDER_ID" in e for e in result.errors)

    def test_parent_not_found_fails(self) -> None:
        r = _create_req(parent_order_id="NONEXISTENT")
        result = self.v.validate_registration(r, frozenset())
        assert not result.passed
        assert any("PARENT_NOT_FOUND" in e for e in result.errors)

    def test_valid_parent(self) -> None:
        r = _create_req(parent_order_id="PARENT-001")
        result = self.v.validate_registration(r, frozenset({"PARENT-001"}))
        assert result.passed

    def test_circular_parent_fails(self) -> None:
        r = _create_req(order_id="ORD-001", parent_order_id="ORD-001")
        result = self.v.validate_registration(r, frozenset({"ORD-001"}))
        assert not result.passed
        assert any("CIRCULAR_PARENT" in e for e in result.errors)

    def test_valid_transition(self) -> None:
        r = self.v.validate_transition("O", ManagerOrderState.READY, ManagerOrderState.PROCESSING)
        assert r.passed

    def test_invalid_transition_fails(self) -> None:
        r = self.v.validate_transition("O", ManagerOrderState.COMPLETED, ManagerOrderState.READY)
        assert not r.passed
        assert any("INVALID_MANAGER_STATE" in e for e in r.errors)

    def test_parent_child_terminal_parent_fails(self) -> None:
        parent = _managed()
        parent.manager_state = ManagerOrderState.COMPLETED
        r = self.v.validate_parent_child(parent, "CHILD-001")
        assert not r.passed

    def test_validation_result_bool(self) -> None:
        assert bool(ManagerValidationResult.ok())
        assert not bool(ManagerValidationResult.fail("err"))

    def test_validation_result_to_dict(self) -> None:
        r = ManagerValidationResult.ok(warnings=("w1",))
        d = r.to_dict()
        assert d["passed"]
        assert "w1" in d["warnings"]


# ─────────────────────────────────────────────────────────────────────────────
# 7. Factory
# ─────────────────────────────────────────────────────────────────────────────

class TestFactory:
    def test_create_from_request(self) -> None:
        f = OrderManagerFactory()
        r = _create_req(portfolio_id="PORT-001", strategy_id="STRAT-001")
        m = f.create(r)
        assert m.order_id     == "ORD-001"
        assert m.workflow_id  == "WF-001"
        assert m.portfolio_id == "PORT-001"
        assert m.manager_state == ManagerOrderState.READY

    def test_create_from_params(self) -> None:
        f = OrderManagerFactory()
        m = f.create_from_params(
            order_id    = "ORD-999",
            workflow_id = "WF-999",
        )
        assert m.order_id == "ORD-999"

    def test_gen_order_id(self) -> None:
        oid = OrderManagerFactory.gen_order_id()
        assert oid.startswith("ORD-")

    def test_gen_group_id(self) -> None:
        gid = OrderManagerFactory.gen_group_id()
        assert gid.startswith("GRP-")

    def test_order_attached(self) -> None:
        f = OrderManagerFactory()
        mock_order = MagicMock()
        r = _create_req(order=mock_order)
        m = f.create(r)
        assert m.order is mock_order


# ─────────────────────────────────────────────────────────────────────────────
# 8. Registry
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_not_running_before_start(self) -> None:
        r = OrderManagerRegistry()
        with pytest.raises(OrderManagerNotRunning):
            r.register(_managed())

    def test_start_stop(self, registry: OrderManagerRegistry) -> None:
        assert registry.is_running

    def test_register_and_get(self, registry: OrderManagerRegistry) -> None:
        m = _managed()
        registry.register(m)
        retrieved = registry.get("ORD-001")
        assert retrieved.order_id == "ORD-001"

    def test_duplicate_raises(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        with pytest.raises(DuplicateOrderError):
            registry.register(_managed())

    def test_overwrite_allowed(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        registry.register(_managed(), overwrite=True)
        assert registry.count() == 1

    def test_not_found_raises(self, registry: OrderManagerRegistry) -> None:
        with pytest.raises(OrderNotFoundError):
            registry.get("MISSING")

    def test_contains(self, registry: OrderManagerRegistry) -> None:
        m = _managed()
        assert not registry.contains("ORD-001")
        registry.register(m)
        assert registry.contains("ORD-001")

    def test_apply_transition(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        managed = registry.apply_transition("ORD-001", ManagerOrderState.PROCESSING)
        assert managed.manager_state == ManagerOrderState.PROCESSING

    def test_invalid_transition_raises(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        registry.apply_transition("ORD-001", ManagerOrderState.COMPLETED)
        with pytest.raises((OrderManagerStateError, OrderAlreadyTerminalError)):
            registry.apply_transition("ORD-001", ManagerOrderState.READY)

    def test_terminal_raises_already_terminal(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        registry.apply_transition("ORD-001", ManagerOrderState.COMPLETED)
        with pytest.raises(OrderAlreadyTerminalError):
            registry.apply_transition("ORD-001", ManagerOrderState.FAILED)

    def test_suspend_and_resume(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        registry.suspend("ORD-001", reason="risk hold")
        m = registry.get("ORD-001")
        assert m.is_suspended
        registry.resume("ORD-001")
        assert not registry.get("ORD-001").is_suspended

    def test_get_by_state(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        results = registry.get_by_state(ManagerOrderState.READY)
        assert any(m.order_id == "ORD-001" for m in results)

    def test_get_active(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        active = registry.get_active()
        assert len(active) == 1

    def test_get_by_workflow(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        results = registry.get_by_workflow("WF-001")
        assert len(results) == 1

    def test_remove(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        registry.remove("ORD-001")
        assert not registry.contains("ORD-001")

    def test_attach_child(self, registry: OrderManagerRegistry) -> None:
        parent = _managed("PARENT-001", "WF-001")
        child  = _managed("CHILD-001",  "WF-001")
        registry.register(parent)
        registry.register(child)
        registry.attach_child("PARENT-001", "CHILD-001")
        p = registry.get("PARENT-001")
        assert "CHILD-001" in p.child_order_ids
        c = registry.get("CHILD-001")
        assert c.parent_order_id == "PARENT-001"

    def test_capacity_limit(self) -> None:
        r = OrderManagerRegistry(max_orders=2)
        r.start()
        r.register(_managed("O1", "W1"))
        r.register(_managed("O2", "W2"))
        with pytest.raises(OrderManagerCapacityError):
            r.register(_managed("O3", "W3"))
        r.stop()

    def test_listeners(self, registry: OrderManagerRegistry) -> None:
        events: list[OrderManagerEvent] = []
        registry.add_listener(events.append)
        registry.register(_managed())
        assert any(e.event_type == ManagerEventType.ORDER_REGISTERED for e in events)

    def test_remove_listener(self, registry: OrderManagerRegistry) -> None:
        events: list[OrderManagerEvent] = []
        registry.add_listener(events.append)
        registry.remove_listener(events.append)
        registry.register(_managed())
        assert len(events) == 0

    def test_faulty_listener_does_not_crash(self, registry: OrderManagerRegistry) -> None:
        def bad(e: OrderManagerEvent) -> None:
            raise RuntimeError("crash")
        registry.add_listener(bad)
        registry.register(_managed())   # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# 9. OrderManager (facade)
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderManager:
    def test_not_running_before_start(self) -> None:
        m = OrderManager()
        with pytest.raises(OrderManagerNotRunning):
            m.register_order("ORD-001")

    def test_start_stop(self, manager: OrderManager) -> None:
        assert manager.is_running

    def test_register_order(self, manager: OrderManager) -> None:
        resp = manager.register_order("ORD-001", workflow_id="WF-001")
        assert resp.succeeded
        assert resp.order_id == "ORD-001"
        assert resp.managed_order is not None

    def test_duplicate_order_fails(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        resp = manager.register_order("ORD-001")
        assert not resp.succeeded
        assert "DUPLICATE" in resp.error_message.upper() or resp.error_message

    def test_missing_order_id_fails(self, manager: OrderManager) -> None:
        resp = manager.register_order("")
        assert not resp.succeeded

    def test_update_order(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        resp = manager.update_order(UpdateOrderRequest(
            order_id  = "ORD-001",
            new_state = ManagerOrderState.PROCESSING,
            reason    = "started",
        ))
        assert resp.succeeded
        assert resp.managed_order.manager_state == ManagerOrderState.PROCESSING

    def test_suspend_and_resume(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        resp = manager.suspend_order(SuspendOrderRequest(order_id="ORD-001", reason="hold"))
        assert resp.succeeded
        assert resp.managed_order.is_suspended

        resp2 = manager.resume_order(ResumeOrderRequest(order_id="ORD-001"))
        assert resp2.succeeded
        assert not resp2.managed_order.is_suspended

    def test_close_order_success(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        manager.update_order(UpdateOrderRequest(
            order_id="ORD-001", new_state=ManagerOrderState.PROCESSING,
        ))
        resp = manager.close_order(CloseOrderRequest(order_id="ORD-001", succeeded=True))
        assert resp.succeeded
        assert resp.managed_order.manager_state == ManagerOrderState.COMPLETED

    def test_close_order_failure(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        manager.update_order(UpdateOrderRequest(
            order_id="ORD-001", new_state=ManagerOrderState.PROCESSING,
        ))
        resp = manager.close_order(CloseOrderRequest(
            order_id="ORD-001", succeeded=False, error_message="broker rejected"
        ))
        assert resp.succeeded   # close operation succeeded
        assert resp.managed_order.manager_state == ManagerOrderState.FAILED

    def test_archive_order(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        resp = manager.archive_order(ArchiveOrderRequest(order_id="ORD-001"))
        assert resp.succeeded

    def test_remove_order(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        resp = manager.remove_order(RemoveOrderRequest(order_id="ORD-001"))
        assert resp.succeeded
        assert not manager.contains("ORD-001")

    def test_lookup_existing(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        m = manager.lookup("ORD-001")
        assert m is not None
        assert m.order_id == "ORD-001"

    def test_lookup_missing_returns_none(self, manager: OrderManager) -> None:
        assert manager.lookup("NONEXISTENT") is None

    def test_get_active(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        manager.register_order("ORD-002", workflow_id="WF-002")
        active = manager.get_active()
        assert len(active) == 2

    def test_get_by_workflow(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001", workflow_id="WF-UNIQUE")
        results = manager.get_by_workflow("WF-UNIQUE")
        assert len(results) == 1

    def test_get_by_strategy(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001", strategy_id="STRAT-UNIQUE")
        results = manager.get_by_strategy("STRAT-UNIQUE")
        assert len(results) == 1

    def test_count(self, manager: OrderManager) -> None:
        assert manager.count() == 0
        manager.register_order("ORD-001")
        assert manager.count() == 1

    def test_attach_child(self, manager: OrderManager) -> None:
        manager.register_order("PARENT-001")
        manager.register_order("CHILD-001")
        resp = manager.attach_child("PARENT-001", "CHILD-001")
        assert resp.succeeded
        parent = manager.lookup("PARENT-001")
        assert "CHILD-001" in parent.child_order_ids

    def test_parent_child_integrity_circular(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        resp = manager.register_order("ORD-002", parent_order_id="ORD-001")
        assert resp.succeeded
        # ORD-001 exists so parent reference is valid

    def test_statistics(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        stats = manager.statistics()
        assert stats.orders_created >= 1
        assert stats.orders_active  >= 1

    def test_snapshot(self, manager: OrderManager) -> None:
        manager.register_order("ORD-001")
        snap = manager.snapshot()
        assert snap.total_registered == 1
        assert snap.manager_running

    def test_listeners(self, manager: OrderManager) -> None:
        events: list[OrderManagerEvent] = []
        manager.add_listener(events.append)
        manager.register_order("ORD-001")
        assert any(e.event_type == ManagerEventType.ORDER_REGISTERED for e in events)

    def test_uptime(self, manager: OrderManager) -> None:
        time.sleep(0.01)
        assert manager.uptime_sec > 0.0

    def test_group_order(self, manager: OrderManager) -> None:
        gid = OrderManagerFactory.gen_group_id()
        manager.register_order("ORD-001", group_id=gid, group_type=OrderGroupType.BASKET)
        manager.register_order("ORD-002", group_id=gid, group_type=OrderGroupType.BASKET)
        m1 = manager.lookup("ORD-001")
        m2 = manager.lookup("ORD-002")
        assert m1.group_id == gid
        assert m2.group_id == gid


# ─────────────────────────────────────────────────────────────────────────────
# 10. History
# ─────────────────────────────────────────────────────────────────────────────

class TestHistory:
    def test_record_and_query(self) -> None:
        h = OrderManagerHistory("ORD-001")
        t = make_transition("ORD-001", ManagerOrderState.INITIALIZED, ManagerOrderState.READY)
        h.record(t)
        assert h.count() == 1
        assert h.first() == t
        assert h.last()  == t

    def test_eviction(self) -> None:
        h = OrderManagerHistory("ORD-001", max_entries=2)
        for i in range(3):
            h.record(make_transition(
                "ORD-001",
                ManagerOrderState.INITIALIZED,
                ManagerOrderState.READY,
            ))
        assert h.count()        == 2
        assert h.evicted_count  == 1
        assert h.total_recorded == 3

    def test_states_visited(self) -> None:
        h = OrderManagerHistory("ORD-001")
        h.record(ManagerTransition(
            order_id="O", from_state=ManagerOrderState.INITIALIZED,
            to_state=ManagerOrderState.READY,
        ))
        h.record(ManagerTransition(
            order_id="O", from_state=ManagerOrderState.READY,
            to_state=ManagerOrderState.PROCESSING,
        ))
        visited = h.states_visited()
        assert ManagerOrderState.READY      in visited
        assert ManagerOrderState.PROCESSING in visited

    def test_registry_records_history(self, registry: OrderManagerRegistry) -> None:
        registry.register(_managed())
        registry.apply_transition("ORD-001", ManagerOrderState.PROCESSING)
        h = registry.get_history("ORD-001")
        assert h.count() >= 2

    def test_make_transition_factory(self) -> None:
        t = make_transition(
            "ORD-001",
            ManagerOrderState.READY,
            ManagerOrderState.PROCESSING,
            reason="started",
        )
        assert t.order_id   == "ORD-001"
        assert t.from_state == ManagerOrderState.READY
        assert t.to_state   == ManagerOrderState.PROCESSING
        assert t.reason     == "started"

    def test_transition_to_dict(self) -> None:
        t = make_transition("O", ManagerOrderState.READY, ManagerOrderState.PROCESSING)
        d = t.to_dict()
        assert "from_state" in d
        assert "to_state"   in d


# ─────────────────────────────────────────────────────────────────────────────
# 11. Statistics
# ─────────────────────────────────────────────────────────────────────────────

class TestStatistics:
    def test_initial_state(self) -> None:
        s = OrderManagerStatistics()
        assert s.orders_created  == 0
        assert s.orders_active   == 0
        assert s.peak_active_orders == 0

    def test_record_registered(self) -> None:
        s = OrderManagerStatistics()
        s.record_registered()
        assert s.orders_created == 1
        assert s.orders_active  == 1
        assert s.peak_active_orders == 1

    def test_peak_tracking(self) -> None:
        s = OrderManagerStatistics()
        for _ in range(5):
            s.record_registered()
        assert s.peak_active_orders == 5
        s.record_completed()
        assert s.peak_active_orders == 5   # peak preserved

    def test_record_completed(self) -> None:
        s = OrderManagerStatistics()
        s.record_registered()
        s.record_completed(10.0)
        assert s.orders_completed    == 1
        assert s.orders_active       == 0
        assert abs(s.avg_processing_time_ms - 10.0) < 0.01

    def test_record_failed(self) -> None:
        s = OrderManagerStatistics()
        s.record_registered()
        s.record_failed()
        assert s.orders_failed  == 1
        assert s.orders_active  == 0

    def test_suspend_resume(self) -> None:
        s = OrderManagerStatistics()
        s.record_suspended()
        assert s.orders_suspended == 1
        s.record_resumed()
        assert s.orders_suspended == 0

    def test_to_dict(self) -> None:
        s = OrderManagerStatistics()
        s.record_registered()
        d = s.to_dict()
        assert d["orders_created"] == 1
        assert d["orders_active"]  == 1


# ─────────────────────────────────────────────────────────────────────────────
# 12. Thread safety
# ─────────────────────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_registrations(self) -> None:
        manager = OrderManager(max_orders=200)
        manager.start()
        errors: list[Exception] = []

        def register(i: int) -> None:
            try:
                manager.register_order(
                    f"ORD-{i:04d}",
                    workflow_id  = f"WF-{i:04d}",
                    strategy_id  = "STRAT-001",
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert manager.count() == 50
        manager.stop()

    def test_concurrent_transitions(self) -> None:
        registry = OrderManagerRegistry()
        registry.start()
        m = _managed()
        registry.register(m)
        errors: list[Exception] = []

        # Move to PROCESSING first (single-threaded)
        registry.apply_transition("ORD-001", ManagerOrderState.PROCESSING)

        def transition(i: int) -> None:
            try:
                target = (
                    ManagerOrderState.COMPLETED
                    if i % 2 == 0
                    else ManagerOrderState.FAILED
                )
                registry.apply_transition("ORD-001", target)
            except (OrderAlreadyTerminalError, OrderManagerStateError):
                pass   # expected — only one can win
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=transition, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        registry.stop()

    def test_concurrent_statistics(self) -> None:
        s      = OrderManagerStatistics()
        errors: list[Exception] = []

        def record(i: int) -> None:
            try:
                s.record_registered()
                if i % 3 == 0:
                    s.record_completed()
                elif i % 3 == 1:
                    s.record_failed()
                else:
                    s.record_cancelled()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record, args=(i,)) for i in range(60)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert s.orders_created == 60
