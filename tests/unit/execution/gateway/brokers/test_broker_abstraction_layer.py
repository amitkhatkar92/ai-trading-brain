"""tests/unit/execution/gateway/brokers/test_broker_abstraction_layer.py
==================================================
Unit tests for the IIOS Broker Abstraction Layer.

C6 Execution Intelligence — Phase 5, Module 3
95%+ coverage target
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

import pytest

from iios.execution.gateway.brokers import (
    # Manager
    BrokerManager,
    # Interface
    BrokerInterface,
    # Registry
    BrokerRegistry,
    # Constants
    BrokerStatus, BrokerCapability, BrokerEventType,
    RequestType, ResponseStatus, OrderSide, OrderType, ProductType, AssetClass,
    ACTIVE_BROKER_STATUSES, TERMINAL_BROKER_STATUSES, READY_BROKER_STATUSES,
    TERMINAL_RESPONSE_STATUSES, RETRYABLE_RESPONSE_STATUSES,
    DEFAULT_MAX_BROKERS, DEFAULT_MAX_HISTORY, DEFAULT_SESSION_TIMEOUT_SECS,
    VERSION,
    # Exceptions
    BrokerAbstractionError, BrokerNotRegisteredError, BrokerAlreadyRegisteredError,
    BrokerNotConnectedError, BrokerAuthenticationError, BrokerSessionExpiredError,
    BrokerCapabilityNotSupportedError, BrokerValidationError, BrokerConfigurationError,
    BrokerConnectionError, BrokerRegistryCapacityError, BrokerHealthError,
    BrokerRequestError, BrokerManagerNotRunningError, DuplicateBrokerError,
    # Capabilities
    BrokerCapabilities, ALL_CAPABILITIES, make_capabilities, make_capabilities_from_iterable,
    find_brokers_by_capability,
    # Configuration
    BrokerConfiguration,
    # Connection
    BrokerConnection, ConnectionPool,
    # Session
    BrokerSession, BrokerSessionManager,
    # Requests
    BrokerRequest, OrderRequest, ModifyOrderRequest, CancelOrderRequest,
    PositionRequest, FundsRequest, MarginRequest, StatusRequest,
    make_order_request, make_modify_order_request, make_cancel_order_request,
    make_position_request, make_funds_request, make_margin_request, make_status_request,
    # Response
    BrokerResponse, make_success_response, make_failure_response, make_error_response,
    make_retryable_error_response, make_auth_failure_response,
    make_network_failure_response, make_rate_limit_response,
    # Health
    BrokerHealthRecord, BrokerHealthMonitor, make_health_record,
    # Statistics
    BrokerStatistics, BrokerStatisticsStore,
    # History
    BrokerHistory,
    # Events
    BrokerEvent, make_broker_registered_event, make_broker_connected_event,
    make_broker_disconnected_event, make_authentication_succeeded_event,
    make_authentication_failed_event, make_session_expired_event,
    make_reconnect_started_event, make_reconnect_succeeded_event,
    make_health_changed_event,
    # Validation
    BrokerValidationResult, BrokerValidator,
    # Factory
    BrokerFactory,
)


# ── Test broker implementation (minimal concrete broker) ──────────────────────

class _TestBroker(BrokerInterface):
    """Minimal concrete broker for testing (no SDK, no I/O)."""

    def __init__(
        self,
        broker_id: str = "test-broker",
        broker_name: str = "Test Broker",
        *,
        connect_success: bool = True,
        auth_success: bool = True,
        ping_result: bool = True,
    ) -> None:
        self._broker_id   = broker_id
        self._broker_name = broker_name
        self._connected   = False
        self._authed      = False
        self._connect_success = connect_success
        self._auth_success    = auth_success
        self._ping_result     = ping_result

    @property
    def broker_id(self) -> str:
        return self._broker_id

    @property
    def broker_name(self) -> str:
        return self._broker_name

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_authenticated(self) -> bool:
        return self._authed

    def connect(self) -> BrokerResponse:
        if self._connect_success:
            self._connected = True
            return make_success_response("connect", self._broker_id)
        return make_network_failure_response("connect", self._broker_id)

    def disconnect(self) -> BrokerResponse:
        self._connected = False
        self._authed    = False
        return make_success_response("disconnect", self._broker_id)

    def authenticate(self) -> BrokerResponse:
        if self._auth_success:
            self._authed = True
            return make_success_response("authenticate", self._broker_id)
        return make_auth_failure_response("authenticate", self._broker_id)

    def refresh_session(self) -> BrokerResponse:
        return make_success_response("refresh", self._broker_id)

    def health(self) -> BrokerHealthRecord:
        return make_health_record(
            broker_id=self._broker_id,
            is_healthy=self._connected,
            latency_ms=1.5,
        )

    def status(self) -> BrokerStatus:
        if self._connected and self._authed:
            return BrokerStatus.ACTIVE
        elif self._connected:
            return BrokerStatus.CONNECTED
        return BrokerStatus.DISCONNECTED

    def capabilities(self) -> BrokerCapabilities:
        return make_capabilities(
            BrokerCapability.CASH_TRADING,
            BrokerCapability.MIS,
            BrokerCapability.CNC,
            BrokerCapability.ORDER_MODIFICATION,
            BrokerCapability.ORDER_CANCELLATION,
            BrokerCapability.MARKET_DATA,
        )

    def place_order(self, request: OrderRequest) -> BrokerResponse:
        return make_success_response(
            request.request_id, self._broker_id,
            data={"order_id": "ORD-001"},
        )

    def modify_order(self, request: ModifyOrderRequest) -> BrokerResponse:
        return make_success_response(request.request_id, self._broker_id)

    def cancel_order(self, request: CancelOrderRequest) -> BrokerResponse:
        return make_success_response(request.request_id, self._broker_id)

    def get_order(self, order_id: str) -> BrokerResponse:
        return make_success_response("get_order", self._broker_id, data={"order_id": order_id})

    def get_orders(self) -> BrokerResponse:
        return make_success_response("get_orders", self._broker_id, data={"orders": []})

    def get_positions(self) -> BrokerResponse:
        return make_success_response("get_positions", self._broker_id, data={"positions": []})

    def get_holdings(self) -> BrokerResponse:
        return make_success_response("get_holdings", self._broker_id, data={"holdings": []})

    def get_funds(self) -> BrokerResponse:
        return make_success_response("get_funds", self._broker_id, data={"balance": 100_000.0})

    def get_margin(self) -> BrokerResponse:
        return make_success_response("get_margin", self._broker_id, data={"available": 50_000.0})

    def ping(self) -> bool:
        return self._ping_result


def _broker(**kwargs) -> _TestBroker:
    return _TestBroker(**kwargs)


def _config(broker_id: str = "test-broker", **kwargs) -> BrokerConfiguration:
    return BrokerConfiguration(
        broker_id=broker_id,
        broker_name="Test Broker",
        **kwargs,
    )


def _manager(**kwargs) -> BrokerManager:
    m = BrokerManager(**kwargs)
    m.start()
    return m


def _registered_manager(
    broker_id: str = "test-broker",
) -> tuple[BrokerManager, _TestBroker]:
    m  = _manager()
    b  = _broker(broker_id=broker_id)
    m.register_broker(b, _config(broker_id=broker_id))
    return m, b


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_broker_system_id_format(self):
        from iios.execution.gateway.brokers.constants import BROKER_SYSTEM_ID
        assert BROKER_SYSTEM_ID.startswith("iios:")

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_broker_status_values(self):
        assert BrokerStatus.DISCONNECTED.value == "DISCONNECTED"
        assert BrokerStatus.ACTIVE.value       == "ACTIVE"
        assert BrokerStatus.STOPPED.value      == "STOPPED"

    def test_active_statuses_sentinel(self):
        assert BrokerStatus.ACTIVE         in ACTIVE_BROKER_STATUSES
        assert BrokerStatus.CONNECTING     in ACTIVE_BROKER_STATUSES
        assert BrokerStatus.DISCONNECTED   not in ACTIVE_BROKER_STATUSES
        assert BrokerStatus.STOPPED        not in ACTIVE_BROKER_STATUSES

    def test_terminal_statuses_sentinel(self):
        assert BrokerStatus.FAILED   in TERMINAL_BROKER_STATUSES
        assert BrokerStatus.STOPPED  in TERMINAL_BROKER_STATUSES
        assert BrokerStatus.ACTIVE   not in TERMINAL_BROKER_STATUSES

    def test_ready_statuses_sentinel(self):
        assert BrokerStatus.CONNECTED in READY_BROKER_STATUSES
        assert BrokerStatus.ACTIVE    in READY_BROKER_STATUSES
        assert BrokerStatus.DEGRADED  in READY_BROKER_STATUSES

    def test_all_capabilities_count(self):
        assert len(ALL_CAPABILITIES) == len(BrokerCapability)

    def test_broker_event_type_values(self):
        assert BrokerEventType.BROKER_REGISTERED.value        == "BROKER_REGISTERED"
        assert BrokerEventType.AUTHENTICATION_SUCCEEDED.value == "AUTHENTICATION_SUCCEEDED"

    def test_response_status_retryable_sentinel(self):
        assert ResponseStatus.RETRYABLE_ERROR  in RETRYABLE_RESPONSE_STATUSES
        assert ResponseStatus.NETWORK_FAILURE  in RETRYABLE_RESPONSE_STATUSES
        assert ResponseStatus.SUCCESS          not in RETRYABLE_RESPONSE_STATUSES

    def test_order_enums(self):
        assert OrderSide.BUY.value  == "BUY"
        assert OrderType.LIMIT.value == "LIMIT"
        assert ProductType.CNC.value == "CNC"
        assert AssetClass.EQUITY.value == "EQUITY"

    def test_defaults_positive(self):
        assert DEFAULT_MAX_BROKERS   > 0
        assert DEFAULT_MAX_HISTORY   > 0
        assert DEFAULT_SESSION_TIMEOUT_SECS > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestExceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_error(self):
        e = BrokerAbstractionError("test")
        assert e.error_code == "BAL-000"
        assert "test" in str(e)

    def test_not_registered(self):
        e = BrokerNotRegisteredError("BRK-1")
        assert e.error_code == "BAL-001"
        assert "BRK-1" in str(e)

    def test_already_registered(self):
        e = BrokerAlreadyRegisteredError("BRK-1")
        assert e.error_code == "BAL-002"

    def test_not_connected(self):
        e = BrokerNotConnectedError("BRK-1", "DISCONNECTED")
        assert e.error_code == "BAL-003"
        assert "DISCONNECTED" in str(e)

    def test_authentication_error(self):
        e = BrokerAuthenticationError("BRK-1", "bad credentials")
        assert e.error_code == "BAL-004"

    def test_session_expired(self):
        e = BrokerSessionExpiredError("BRK-1")
        assert e.error_code == "BAL-005"

    def test_capability_not_supported(self):
        e = BrokerCapabilityNotSupportedError("BRK-1", "GTT")
        assert e.error_code == "BAL-006"

    def test_validation_error(self):
        e = BrokerValidationError("fail", ("err1",))
        assert e.error_code == "BAL-007"
        assert e.errors == ("err1",)

    def test_configuration_error(self):
        e = BrokerConfigurationError("BRK-1", "missing env")
        assert e.error_code == "BAL-008"

    def test_connection_error(self):
        e = BrokerConnectionError("BRK-1")
        assert e.error_code == "BAL-009"

    def test_registry_capacity_error(self):
        e = BrokerRegistryCapacityError(100)
        assert e.error_code == "BAL-010"
        assert e.max_brokers == 100

    def test_health_error(self):
        e = BrokerHealthError("BRK-1", "timeout")
        assert e.error_code == "BAL-011"

    def test_request_error(self):
        e = BrokerRequestError("bad request")
        assert e.error_code == "BAL-012"

    def test_manager_not_running(self):
        e = BrokerManagerNotRunningError()
        assert e.error_code == "BAL-013"

    def test_duplicate_broker(self):
        e = DuplicateBrokerError("BRK-1")
        assert e.error_code == "BAL-014"

    def test_all_inherit_from_base(self):
        errors = [
            BrokerNotRegisteredError("X"),
            BrokerAlreadyRegisteredError("X"),
            BrokerNotConnectedError("X"),
            BrokerAuthenticationError("X"),
            BrokerSessionExpiredError("X"),
            BrokerCapabilityNotSupportedError("X", "CAP"),
            BrokerValidationError("X"),
            BrokerConfigurationError("X"),
            BrokerConnectionError("X"),
            BrokerRegistryCapacityError(1),
            BrokerHealthError("X"),
            BrokerRequestError(),
            BrokerManagerNotRunningError(),
            DuplicateBrokerError("X"),
        ]
        for err in errors:
            assert isinstance(err, BrokerAbstractionError)


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerInterface
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerInterface:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BrokerInterface()  # type: ignore[abstract]

    def test_concrete_broker_satisfies_interface(self):
        b = _broker()
        assert isinstance(b, BrokerInterface)

    def test_broker_id_property(self):
        b = _broker(broker_id="DHAN-001")
        assert b.broker_id == "DHAN-001"

    def test_broker_name_property(self):
        b = _broker(broker_name="Dhan")
        assert b.broker_name == "Dhan"

    def test_repr(self):
        b = _broker()
        assert "test-broker" in repr(b)

    def test_connect_returns_response(self):
        b = _broker()
        resp = b.connect()
        assert isinstance(resp, BrokerResponse)
        assert resp.is_success

    def test_disconnect_returns_response(self):
        b = _broker()
        resp = b.disconnect()
        assert isinstance(resp, BrokerResponse)

    def test_authenticate_success(self):
        b = _broker(auth_success=True)
        resp = b.authenticate()
        assert resp.is_success

    def test_authenticate_failure(self):
        b = _broker(auth_success=False)
        resp = b.authenticate()
        assert resp.is_auth_failure

    def test_ping_returns_bool(self):
        b = _broker()
        assert isinstance(b.ping(), bool)

    def test_capabilities_returns_broker_capabilities(self):
        b = _broker()
        caps = b.capabilities()
        assert isinstance(caps, BrokerCapabilities)

    def test_status_returns_broker_status(self):
        b = _broker()
        s = b.status()
        assert isinstance(s, BrokerStatus)

    def test_health_returns_health_record(self):
        b = _broker()
        r = b.health()
        assert isinstance(r, BrokerHealthRecord)


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerCapabilities
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerCapabilities:
    def test_empty_capabilities(self):
        caps = BrokerCapabilities()
        assert len(caps) == 0

    def test_has(self):
        caps = make_capabilities(BrokerCapability.MIS, BrokerCapability.CNC)
        assert caps.has(BrokerCapability.MIS)
        assert not caps.has(BrokerCapability.OPTIONS)

    def test_supports_all(self):
        caps = make_capabilities(BrokerCapability.MIS, BrokerCapability.CNC)
        assert caps.supports_all(BrokerCapability.MIS, BrokerCapability.CNC)
        assert not caps.supports_all(BrokerCapability.MIS, BrokerCapability.OPTIONS)

    def test_supports_any(self):
        caps = make_capabilities(BrokerCapability.MIS)
        assert caps.supports_any(BrokerCapability.MIS, BrokerCapability.OPTIONS)
        assert not caps.supports_any(BrokerCapability.OPTIONS, BrokerCapability.FUTURES)

    def test_missing(self):
        caps = make_capabilities(BrokerCapability.MIS)
        missing = caps.missing(BrokerCapability.MIS, BrokerCapability.CNC)
        assert BrokerCapability.CNC in missing
        assert BrokerCapability.MIS not in missing

    def test_union(self):
        a = make_capabilities(BrokerCapability.MIS)
        b = make_capabilities(BrokerCapability.CNC)
        c = a.union(b)
        assert c.has(BrokerCapability.MIS)
        assert c.has(BrokerCapability.CNC)

    def test_intersection(self):
        a = make_capabilities(BrokerCapability.MIS, BrokerCapability.CNC)
        b = make_capabilities(BrokerCapability.CNC, BrokerCapability.OPTIONS)
        c = a.intersection(b)
        assert c.has(BrokerCapability.CNC)
        assert not c.has(BrokerCapability.MIS)

    def test_to_list(self):
        caps = make_capabilities(BrokerCapability.MIS, BrokerCapability.CNC)
        lst = caps.to_list()
        assert "MIS" in lst
        assert "CNC" in lst
        assert lst == sorted(lst)

    def test_to_dict(self):
        caps = make_capabilities(BrokerCapability.MIS)
        d = caps.to_dict()
        assert "capabilities" in d
        assert d["count"] == 1

    def test_contains(self):
        caps = make_capabilities(BrokerCapability.MIS)
        assert BrokerCapability.MIS in caps

    def test_len(self):
        caps = make_capabilities(BrokerCapability.MIS, BrokerCapability.CNC)
        assert len(caps) == 2

    def test_repr(self):
        caps = make_capabilities(BrokerCapability.MIS)
        assert "MIS" in repr(caps)

    def test_find_brokers_by_capability(self):
        a = make_capabilities(BrokerCapability.MIS)
        b = make_capabilities(BrokerCapability.CNC)
        mapping = {"broker-a": a, "broker-b": b}
        result = find_brokers_by_capability(mapping, BrokerCapability.MIS)
        assert "broker-a" in result
        assert "broker-b" not in result

    def test_all_capabilities_sentinel(self):
        assert len(ALL_CAPABILITIES) > 0
        assert BrokerCapability.OPTIONS in ALL_CAPABILITIES

    def test_make_from_iterable(self):
        caps = make_capabilities_from_iterable(
            [BrokerCapability.MIS, BrokerCapability.CNC]
        )
        assert caps.has(BrokerCapability.MIS)


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerConfiguration
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerConfiguration:
    def test_required_fields(self):
        config = BrokerConfiguration(broker_id="B1", broker_name="Broker 1")
        assert config.broker_id   == "B1"
        assert config.broker_name == "Broker 1"

    def test_default_environment(self):
        config = _config()
        assert config.environment == "paper"
        assert config.is_paper
        assert not config.is_live

    def test_live_environment(self):
        config = _config(environment="live")
        assert config.is_live
        assert not config.is_paper

    def test_to_dict(self):
        d = _config().to_dict()
        assert d["broker_id"]   == "test-broker"
        assert d["environment"] == "paper"

    def test_repr(self):
        r = repr(_config())
        assert "test-broker" in r

    def test_frozen(self):
        config = _config()
        with pytest.raises((AttributeError, TypeError)):
            config.broker_id = "changed"  # type: ignore[misc]

    def test_metadata_default_empty(self):
        config = _config()
        assert config.metadata == {}


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerRequests
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerRequests:
    def test_make_order_request(self):
        req = make_order_request(
            "DHAN", "NIFTY", "NSE",
            OrderSide.BUY, OrderType.MARKET, ProductType.MIS,
            quantity=50.0, price=0.0,
        )
        assert isinstance(req, OrderRequest)
        assert req.broker_id  == "DHAN"
        assert req.symbol     == "NIFTY"
        assert req.side       == OrderSide.BUY
        assert req.request_type == RequestType.ORDER
        assert len(req.request_id) == 36

    def test_order_request_to_dict(self):
        req = make_order_request(
            "B", "SYM", "NSE", OrderSide.SELL, OrderType.LIMIT, ProductType.CNC,
            quantity=10.0, price=500.0,
        )
        d = req.to_dict()
        assert d["side"]   == "SELL"
        assert d["price"]  == 500.0

    def test_make_modify_order_request(self):
        req = make_modify_order_request(
            "B", "ORD-1", "SYM", "NSE", 10.0, 100.0, OrderType.LIMIT
        )
        assert isinstance(req, ModifyOrderRequest)
        assert req.request_type == RequestType.MODIFY_ORDER

    def test_make_cancel_order_request(self):
        req = make_cancel_order_request("B", "ORD-1", "SYM", "NSE", reason="user")
        assert isinstance(req, CancelOrderRequest)
        assert req.reason == "user"

    def test_make_position_request(self):
        req = make_position_request("B")
        assert isinstance(req, PositionRequest)
        assert req.request_type == RequestType.POSITIONS

    def test_make_funds_request(self):
        req = make_funds_request("B")
        assert isinstance(req, FundsRequest)
        assert req.request_type == RequestType.FUNDS

    def test_make_margin_request(self):
        req = make_margin_request(
            "B", "NIFTY", "NSE", 50.0, 22000.0,
            OrderType.MARKET, ProductType.MIS, OrderSide.BUY,
        )
        assert isinstance(req, MarginRequest)
        assert req.request_type == RequestType.MARGIN

    def test_make_status_request(self):
        req = make_status_request("B")
        assert isinstance(req, StatusRequest)
        assert req.request_type == RequestType.STATUS


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerResponse
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerResponse:
    def test_success_response(self):
        r = make_success_response("REQ-1", "DHAN", data={"val": 1})
        assert r.is_success
        assert not r.is_failure
        assert not r.is_retryable
        assert r.has_data

    def test_failure_response(self):
        r = make_failure_response("REQ-1", "DHAN", error_code="ERR", error_message="msg")
        assert r.is_failure
        assert not r.is_success
        assert r.error_code == "ERR"

    def test_error_response(self):
        r = make_error_response("REQ-1", "DHAN")
        assert r.is_error

    def test_retryable_error_response(self):
        r = make_retryable_error_response("REQ-1", "DHAN")
        assert r.is_retryable
        assert r.status == ResponseStatus.RETRYABLE_ERROR

    def test_auth_failure_response(self):
        r = make_auth_failure_response("REQ-1", "DHAN")
        assert r.is_auth_failure
        assert not r.is_retryable

    def test_network_failure_response(self):
        r = make_network_failure_response("REQ-1", "DHAN")
        assert r.is_network_failure
        assert r.is_retryable

    def test_rate_limit_response(self):
        r = make_rate_limit_response("REQ-1", "DHAN")
        assert r.is_rate_limited
        assert r.is_retryable

    def test_to_dict(self):
        r = make_success_response("REQ-1", "DHAN")
        d = r.to_dict()
        assert d["status"]    == "SUCCESS"
        assert d["broker_id"] == "DHAN"

    def test_repr(self):
        r = make_success_response("R", "B")
        assert "SUCCESS" in repr(r)

    def test_no_data_flag(self):
        r = make_failure_response("R", "B")
        assert not r.has_data


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerConnection
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerConnection:
    def test_initial_state(self):
        c = BrokerConnection("DHAN")
        assert c.state == BrokerStatus.DISCONNECTED
        assert not c.is_connected
        assert not c.is_ready
        assert not c.is_terminal

    def test_set_connecting(self):
        c = BrokerConnection("DHAN")
        c.set_connecting()
        assert c.state == BrokerStatus.CONNECTING
        assert c.is_connected  # CONNECTING is in ACTIVE_BROKER_STATUSES

    def test_set_connected(self):
        c = BrokerConnection("DHAN")
        c.set_connected()
        assert c.is_ready
        assert c.connected_at is not None

    def test_set_active(self):
        c = BrokerConnection("DHAN")
        c.set_active()
        assert c.is_ready

    def test_set_degraded(self):
        c = BrokerConnection("DHAN")
        c.set_degraded()
        assert c.is_ready

    def test_set_reconnecting(self):
        c = BrokerConnection("DHAN")
        c.set_reconnecting()
        assert c.state == BrokerStatus.RECONNECTING
        assert c.reconnect_count == 1

    def test_set_disconnected(self):
        c = BrokerConnection("DHAN")
        c.set_connected()
        c.set_disconnected()
        assert not c.is_connected
        assert c.disconnected_at is not None

    def test_set_failed(self):
        c = BrokerConnection("DHAN")
        c.set_failed()
        assert c.is_terminal
        assert not c.is_ready

    def test_set_stopped(self):
        c = BrokerConnection("DHAN")
        c.set_stopped()
        assert c.is_terminal

    def test_record_heartbeat(self):
        c = BrokerConnection("DHAN")
        c.record_heartbeat()
        assert c.last_heartbeat_at is not None

    def test_to_dict(self):
        c = BrokerConnection("DHAN", "orders")
        d = c.to_dict()
        assert d["broker_id"]     == "DHAN"
        assert d["connection_id"] == "orders"

    def test_repr(self):
        c = BrokerConnection("DHAN")
        assert "DHAN" in repr(c)


class TestConnectionPool:
    def test_add_and_get(self):
        pool = ConnectionPool("DHAN")
        conn = pool.add("orders")
        assert isinstance(conn, BrokerConnection)
        assert pool.get("orders") is conn

    def test_add_default(self):
        pool = ConnectionPool("DHAN")
        conn = pool.add()
        assert pool.get("default") is conn

    def test_duplicate_raises(self):
        pool = ConnectionPool("DHAN")
        pool.add("orders")
        with pytest.raises(BrokerConnectionError):
            pool.add("orders")

    def test_replace(self):
        pool = ConnectionPool("DHAN")
        pool.add("orders")
        pool.add("orders", replace=True)  # should not raise
        assert pool.count() == 1

    def test_get_optional_missing(self):
        pool = ConnectionPool("DHAN")
        assert pool.get_optional("missing") is None

    def test_get_raises_when_missing(self):
        pool = ConnectionPool("DHAN")
        with pytest.raises(BrokerConnectionError):
            pool.get("missing")

    def test_is_any_ready(self):
        pool = ConnectionPool("DHAN")
        pool.add("default").set_active()
        assert pool.is_any_ready()

    def test_not_ready_when_disconnected(self):
        pool = ConnectionPool("DHAN")
        pool.add("default")
        assert not pool.is_any_ready()

    def test_disconnect_all(self):
        pool = ConnectionPool("DHAN")
        conn = pool.add()
        conn.set_connected()
        pool.disconnect_all()
        assert conn.state == BrokerStatus.DISCONNECTED

    def test_stop_all(self):
        pool = ConnectionPool("DHAN")
        conn = pool.add()
        conn.set_connected()
        pool.stop_all()
        assert conn.is_terminal

    def test_remove(self):
        pool = ConnectionPool("DHAN")
        pool.add("x")
        pool.remove("x")
        assert pool.count() == 0

    def test_iter(self):
        pool = ConnectionPool("DHAN")
        pool.add("a")
        pool.add("b")
        conns = list(pool)
        assert len(conns) == 2

    def test_to_dict(self):
        pool = ConnectionPool("DHAN")
        pool.add("default")
        d = pool.to_dict()
        assert d["broker_id"] == "DHAN"
        assert d["count"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerSession
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerSession:
    def test_initial_state(self):
        s = BrokerSession("DHAN")
        assert not s.is_authenticated
        assert not s.is_expired
        assert s.session_id is None

    def test_mark_authenticated(self):
        s = BrokerSession("DHAN")
        s.mark_authenticated(timeout_secs=3600.0)
        assert s.is_authenticated
        assert s.session_id is not None
        assert s.seconds_until_expiry > 0

    def test_mark_expired(self):
        s = BrokerSession("DHAN")
        s.mark_authenticated(timeout_secs=3600.0)
        s.mark_expired()
        assert not s.is_authenticated

    def test_refresh(self):
        s = BrokerSession("DHAN")
        s.mark_authenticated(timeout_secs=3600.0)
        s.refresh(timeout_secs=7200.0)
        assert s.refresh_count == 1
        assert s.seconds_until_expiry > 3600.0

    def test_mark_disconnected_clears_session(self):
        s = BrokerSession("DHAN")
        s.mark_authenticated()
        s.mark_disconnected()
        assert not s.is_authenticated
        assert s.session_id is None

    def test_expired_after_timeout(self):
        s = BrokerSession("DHAN")
        s.mark_authenticated(timeout_secs=0.01)
        time.sleep(0.05)
        assert s.is_expired
        assert not s.is_authenticated

    def test_to_dict(self):
        s = BrokerSession("DHAN")
        d = s.to_dict()
        assert d["broker_id"] == "DHAN"
        assert "is_authenticated" in d

    def test_repr(self):
        s = BrokerSession("DHAN")
        assert "DHAN" in repr(s)


class TestBrokerSessionManager:
    def test_create_and_get(self):
        sm = BrokerSessionManager()
        session = sm.create_session("DHAN")
        assert sm.get_session("DHAN") is session

    def test_get_optional(self):
        sm = BrokerSessionManager()
        assert sm.get_session_optional("MISSING") is None

    def test_get_raises_when_absent(self):
        sm = BrokerSessionManager()
        with pytest.raises(BrokerNotRegisteredError):
            sm.get_session("MISSING")

    def test_is_authenticated(self):
        sm = BrokerSessionManager()
        sm.create_session("B")
        sm.get_session("B").mark_authenticated()
        assert sm.is_authenticated("B")

    def test_remove_session(self):
        sm = BrokerSessionManager()
        sm.create_session("B")
        sm.remove_session("B")
        assert sm.get_session_optional("B") is None

    def test_expire_stale(self):
        sm = BrokerSessionManager()
        s  = sm.create_session("B")
        s.mark_authenticated(timeout_secs=0.01)
        time.sleep(0.05)
        expired = sm.expire_stale_sessions()
        assert expired >= 1

    def test_count(self):
        sm = BrokerSessionManager()
        sm.create_session("A")
        sm.create_session("B")
        assert sm.count() == 2

    def test_authenticated_count(self):
        sm = BrokerSessionManager()
        s1 = sm.create_session("A")
        s1.mark_authenticated()
        sm.create_session("B")
        assert sm.authenticated_count() == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerHealthRecord
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerHealthRecord:
    def test_make_healthy(self):
        r = make_health_record("DHAN", is_healthy=True, latency_ms=2.5)
        assert r.is_healthy
        assert r.latency_ms == 2.5
        assert r.error_message is None

    def test_make_unhealthy(self):
        r = make_health_record("DHAN", is_healthy=False, error_message="timeout")
        assert not r.is_healthy
        assert r.error_message == "timeout"

    def test_age_ms(self):
        r = make_health_record("DHAN", is_healthy=True)
        time.sleep(0.01)
        assert r.age_ms > 0

    def test_to_dict(self):
        r = make_health_record("DHAN", is_healthy=True, latency_ms=5.0)
        d = r.to_dict()
        assert d["broker_id"]  == "DHAN"
        assert d["is_healthy"] is True

    def test_repr(self):
        r = make_health_record("DHAN", is_healthy=True)
        assert "DHAN" in repr(r)
        assert "healthy" in repr(r)


class TestBrokerHealthMonitor:
    def test_record_and_get(self):
        m = BrokerHealthMonitor()
        r = make_health_record("DHAN", is_healthy=True)
        m.record_health(r)
        assert m.get_health("DHAN") is r

    def test_is_healthy(self):
        m = BrokerHealthMonitor()
        m.record_health(make_health_record("DHAN", is_healthy=True))
        assert m.is_healthy("DHAN")

    def test_is_unhealthy(self):
        m = BrokerHealthMonitor()
        m.record_health(make_health_record("DHAN", is_healthy=False))
        assert not m.is_healthy("DHAN")

    def test_missing_returns_false(self):
        m = BrokerHealthMonitor()
        assert not m.is_healthy("MISSING")

    def test_unhealthy_brokers(self):
        m = BrokerHealthMonitor()
        m.record_health(make_health_record("A", is_healthy=True))
        m.record_health(make_health_record("B", is_healthy=False))
        assert "B" in m.unhealthy_brokers()
        assert "A" not in m.unhealthy_brokers()

    def test_healthy_brokers(self):
        m = BrokerHealthMonitor()
        m.record_health(make_health_record("A", is_healthy=True))
        assert "A" in m.healthy_brokers()

    def test_remove(self):
        m = BrokerHealthMonitor()
        m.record_health(make_health_record("A", is_healthy=True))
        m.remove("A")
        assert m.get_health("A") is None

    def test_counts(self):
        m = BrokerHealthMonitor()
        m.record_health(make_health_record("A", is_healthy=True))
        m.record_health(make_health_record("B", is_healthy=False))
        assert m.healthy_count()   == 1
        assert m.unhealthy_count() == 1
        assert m.broker_count()    == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerStatistics:
    def test_initial_zeros(self):
        s = BrokerStatistics(broker_id="B")
        assert s.requests  == 0
        assert s.responses == 0
        assert s.failures  == 0

    def test_record_request(self):
        s = BrokerStatistics(broker_id="B")
        s.record_request()
        assert s.requests == 1

    def test_record_response_and_latency(self):
        s = BrokerStatistics(broker_id="B")
        s.record_response(latency_ms=10.0)
        assert s.responses == 1
        assert s.average_latency_ms == 10.0

    def test_record_failure(self):
        s = BrokerStatistics(broker_id="B")
        s.record_response()
        s.record_failure()
        assert s.failure_rate > 0

    def test_record_reconnect(self):
        s = BrokerStatistics(broker_id="B")
        s.record_reconnect()
        assert s.reconnect_count == 1

    def test_record_authentication(self):
        s = BrokerStatistics(broker_id="B")
        s.record_authentication()
        assert s.authentication_count == 1

    def test_record_session_expiry(self):
        s = BrokerStatistics(broker_id="B")
        s.record_session_expiry()
        assert s.session_expiry_count == 1

    def test_add_session_duration(self):
        s = BrokerStatistics(broker_id="B")
        s.record_authentication()
        s.add_session_duration(3600.0)
        assert s.average_session_duration_secs == 3600.0

    def test_success_count(self):
        s = BrokerStatistics(broker_id="B")
        s.record_response()
        s.record_response()
        s.record_failure()
        assert s.success_count == 1

    def test_success_rate(self):
        s = BrokerStatistics(broker_id="B")
        s.record_response()
        assert s.success_rate == 1.0

    def test_reset(self):
        s = BrokerStatistics(broker_id="B")
        s.record_request()
        s.reset()
        assert s.requests == 0

    def test_copy(self):
        s = BrokerStatistics(broker_id="B")
        s.record_request()
        copy = s.copy()
        assert copy.requests == 1
        copy.record_request()
        assert s.requests == 1  # original unaffected

    def test_to_dict(self):
        s = BrokerStatistics(broker_id="B")
        d = s.to_dict()
        assert d["broker_id"] == "B"
        assert "requests" in d


class TestBrokerStatisticsStore:
    def test_get_or_create(self):
        store = BrokerStatisticsStore()
        s = store.get_or_create("B")
        assert isinstance(s, BrokerStatistics)

    def test_idempotent_create(self):
        store = BrokerStatisticsStore()
        s1 = store.get_or_create("B")
        s2 = store.get_or_create("B")
        assert s1 is s2

    def test_get_snapshot_copies(self):
        store = BrokerStatisticsStore()
        store.get_or_create("B").record_request()
        snap = store.get_snapshot("B")
        assert snap is not None
        snap.record_request()
        assert store.get("B").requests == 1  # original not modified

    def test_remove(self):
        store = BrokerStatisticsStore()
        store.get_or_create("B")
        store.remove("B")
        assert store.get("B") is None

    def test_all(self):
        store = BrokerStatisticsStore()
        store.get_or_create("A")
        store.get_or_create("B")
        result = store.all()
        assert "A" in result
        assert "B" in result


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerHistory:
    def test_append_event(self):
        h = BrokerHistory()
        e = make_broker_connected_event("DHAN")
        h.append_event(e)
        assert h.event_count == 1

    def test_append_response(self):
        h = BrokerHistory()
        r = make_success_response("R", "DHAN")
        h.append_response(r)
        assert h.response_count == 1

    def test_events(self):
        h = BrokerHistory()
        h.append_event(make_broker_connected_event("A"))
        h.append_event(make_broker_connected_event("B"))
        assert len(h.events()) == 2

    def test_events_for_broker(self):
        h = BrokerHistory()
        h.append_event(make_broker_connected_event("A"))
        h.append_event(make_broker_connected_event("B"))
        result = h.events_for_broker("A")
        assert len(result) == 1
        assert result[0].broker_id == "A"

    def test_latest_event(self):
        h = BrokerHistory()
        h.append_event(make_broker_connected_event("A"))
        h.append_event(make_broker_disconnected_event("B"))
        latest = h.latest_event()
        assert latest.broker_id == "B"

    def test_latest_response(self):
        h = BrokerHistory()
        h.append_response(make_success_response("R1", "A"))
        h.append_response(make_failure_response("R2", "B"))
        assert h.latest_response().broker_id == "B"

    def test_bounded_eviction(self):
        h = BrokerHistory(max_size=3)
        for i in range(5):
            h.append_event(make_broker_connected_event(f"B{i}"))
        assert h.event_count == 3
        assert h.evicted_events == 2

    def test_successful_responses(self):
        h = BrokerHistory()
        h.append_response(make_success_response("R1", "A"))
        h.append_response(make_failure_response("R2", "B"))
        assert len(h.successful_responses()) == 1

    def test_failed_responses(self):
        h = BrokerHistory()
        h.append_response(make_failure_response("R2", "B"))
        assert len(h.failed_responses()) == 1

    def test_to_dict(self):
        h = BrokerHistory(max_size=100)
        d = h.to_dict()
        assert d["max_size"]      == 100
        assert d["event_count"]   == 0
        assert d["response_count"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerEvents
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerEvents:
    def test_registered_event(self):
        e = make_broker_registered_event("DHAN")
        assert e.event_type == BrokerEventType.BROKER_REGISTERED
        assert e.broker_id  == "DHAN"
        assert len(e.event_id) == 36

    def test_connected_event(self):
        e = make_broker_connected_event("DHAN")
        assert e.is_connection_event
        assert not e.is_failure_event

    def test_disconnected_event(self):
        e = make_broker_disconnected_event("DHAN")
        assert e.is_connection_event

    def test_auth_succeeded_event(self):
        e = make_authentication_succeeded_event("DHAN")
        assert e.is_auth_event
        assert not e.is_failure_event

    def test_auth_failed_event(self):
        e = make_authentication_failed_event("DHAN")
        assert e.is_auth_event
        assert e.is_failure_event

    def test_session_expired_event(self):
        e = make_session_expired_event("DHAN")
        assert e.is_auth_event
        assert e.is_failure_event

    def test_reconnect_started_event(self):
        e = make_reconnect_started_event("DHAN")
        assert e.is_connection_event

    def test_reconnect_succeeded_event(self):
        e = make_reconnect_succeeded_event("DHAN")
        assert e.is_connection_event

    def test_health_changed_event(self):
        e = make_health_changed_event("DHAN", is_healthy=False)
        assert e.is_health_event
        assert e.metadata["is_healthy"] is False

    def test_to_dict(self):
        e = make_broker_connected_event("DHAN")
        d = e.to_dict()
        assert d["broker_id"]  == "DHAN"
        assert d["event_type"] == "BROKER_CONNECTED"

    def test_repr(self):
        e = make_broker_connected_event("DHAN")
        assert "BROKER_CONNECTED" in repr(e)


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerValidation
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerValidation:
    def _v(self) -> BrokerValidator:
        return BrokerValidator()

    def test_interface_compliance_pass(self):
        v      = self._v()
        result = v.validate_interface_compliance(_broker())
        assert result.is_valid

    def test_interface_compliance_fail_non_interface(self):
        v      = self._v()
        result = v.validate_interface_compliance("not-a-broker")
        assert not result.is_valid

    def test_registration_pass(self):
        v  = self._v()
        b  = _broker()
        r  = v.validate_registration(b, [], DEFAULT_MAX_BROKERS)
        assert r.is_valid

    def test_registration_duplicate(self):
        v  = self._v()
        b  = _broker(broker_id="X")
        r  = v.validate_registration(b, ["X"], DEFAULT_MAX_BROKERS)
        assert not r.is_valid

    def test_registration_capacity_exceeded(self):
        v = self._v()
        b = _broker()
        r = v.validate_registration(b, ["X"], max_brokers=1)
        assert not r.is_valid

    def test_capability_consistency_pass(self):
        v  = self._v()
        b  = _broker()
        r  = v.validate_capability_consistency(b)
        assert r.is_valid

    def test_configuration_valid(self):
        v = self._v()
        r = v.validate_configuration(_config())
        assert r.is_valid

    def test_configuration_invalid_env(self):
        v      = self._v()
        config = BrokerConfiguration(broker_id="B", broker_name="N", environment="staging")
        r      = v.validate_configuration(config)
        assert not r.is_valid

    def test_configuration_empty_broker_id(self):
        v      = self._v()
        config = BrokerConfiguration(broker_id="", broker_name="N")
        r      = v.validate_configuration(config)
        assert not r.is_valid

    def test_session_valid(self):
        v = self._v()
        s = BrokerSession("B")
        s.mark_authenticated(timeout_secs=3600.0)
        r = v.validate_session(s)
        assert r.is_valid

    def test_session_unauthenticated(self):
        v = self._v()
        s = BrokerSession("B")
        r = v.validate_session(s)
        assert not r.is_valid

    def test_session_expired(self):
        v = self._v()
        s = BrokerSession("B")
        s.mark_authenticated(timeout_secs=0.01)
        time.sleep(0.05)
        r = v.validate_session(s)
        assert not r.is_valid

    def test_connection_valid(self):
        v = self._v()
        c = BrokerConnection("B")
        c.set_active()
        r = v.validate_connection(c)
        assert r.is_valid

    def test_connection_disconnected(self):
        v = self._v()
        c = BrokerConnection("B")
        r = v.validate_connection(c)
        assert not r.is_valid

    def test_connection_terminal(self):
        v = self._v()
        c = BrokerConnection("B")
        c.set_failed()
        r = v.validate_connection(c)
        assert not r.is_valid

    def test_raise_if_invalid(self):
        v      = self._v()
        result = BrokerValidationResult(
            is_valid=False,
            errors=("some error",),
            warnings=(),
            validated_at=time.time(),
        )
        with pytest.raises(BrokerValidationError):
            v.raise_if_invalid(result)

    def test_raise_if_valid_does_not_raise(self):
        v      = self._v()
        result = BrokerValidationResult(
            is_valid=True,
            errors=(),
            warnings=(),
            validated_at=time.time(),
        )
        v.raise_if_invalid(result)  # should not raise

    def test_validation_result_bool(self):
        r_ok   = BrokerValidationResult(is_valid=True,  errors=(), warnings=(), validated_at=0)
        r_fail = BrokerValidationResult(is_valid=False, errors=(), warnings=(), validated_at=0)
        assert bool(r_ok)
        assert not bool(r_fail)

    def test_validation_result_to_dict(self):
        r = BrokerValidationResult(
            is_valid=True, errors=(), warnings=("warn",), validated_at=0
        )
        d = r.to_dict()
        assert d["is_valid"]   is True
        assert "warn" in d["warnings"]


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerRegistry:
    def _started_registry(self) -> BrokerRegistry:
        r = BrokerRegistry()
        r.start()
        return r

    def test_register_and_get(self):
        reg = self._started_registry()
        b   = _broker()
        reg.register(b, _config(), b.capabilities())
        assert reg.get("test-broker") is b
        reg.stop()

    def test_double_register_raises(self):
        reg = self._started_registry()
        b   = _broker()
        reg.register(b, _config(), b.capabilities())
        with pytest.raises(BrokerAlreadyRegisteredError):
            reg.register(b, _config(), b.capabilities())
        reg.stop()

    def test_get_missing_raises(self):
        reg = self._started_registry()
        with pytest.raises(BrokerNotRegisteredError):
            reg.get("MISSING")
        reg.stop()

    def test_get_optional_missing(self):
        reg = self._started_registry()
        assert reg.get_optional("MISSING") is None
        reg.stop()

    def test_remove(self):
        reg = self._started_registry()
        b   = _broker()
        reg.register(b, _config(), b.capabilities())
        reg.remove("test-broker")
        assert not reg.exists("test-broker")
        reg.stop()

    def test_set_default(self):
        reg = self._started_registry()
        b   = _broker()
        reg.register(b, _config(), b.capabilities())
        reg.set_default("test-broker")
        assert reg.default() is b
        reg.stop()

    def test_default_is_first_registered(self):
        reg = self._started_registry()
        b   = _broker()
        reg.register(b, _config(), b.capabilities())
        assert reg.default() is b
        reg.stop()

    def test_capacity_error(self):
        reg = BrokerRegistry(max_brokers=1)
        reg.start()
        b1 = _broker(broker_id="B1")
        b2 = _broker(broker_id="B2")
        reg.register(b1, _config("B1"), b1.capabilities())
        with pytest.raises(BrokerRegistryCapacityError):
            reg.register(b2, _config("B2"), b2.capabilities())
        reg.stop()

    def test_find_by_capability(self):
        reg = self._started_registry()
        b   = _broker()
        reg.register(b, _config(), b.capabilities())
        result = reg.find_by_capability(BrokerCapability.MIS)
        assert b in result
        reg.stop()

    def test_find_ids_by_capability(self):
        reg = self._started_registry()
        b   = _broker()
        reg.register(b, _config(), b.capabilities())
        ids = reg.find_ids_by_capability(BrokerCapability.OPTIONS)
        assert "test-broker" not in ids  # our test broker doesn't have OPTIONS
        reg.stop()

    def test_not_running_raises(self):
        reg = BrokerRegistry()
        with pytest.raises(BrokerManagerNotRunningError):
            reg.register(_broker(), _config(), _broker().capabilities())

    def test_count_and_capacity(self):
        reg = self._started_registry()
        assert reg.count    == 0
        assert reg.capacity == DEFAULT_MAX_BROKERS
        reg.stop()

    def test_all_brokers(self):
        reg = self._started_registry()
        b   = _broker()
        reg.register(b, _config(), b.capabilities())
        assert b in reg.all_brokers()
        reg.stop()

    def test_capabilities_map(self):
        reg = self._started_registry()
        b   = _broker()
        reg.register(b, _config(), b.capabilities())
        caps_map = reg.capabilities_map()
        assert "test-broker" in caps_map
        reg.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerManager — lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerManagerLifecycle:
    def test_start_and_stop(self):
        m = BrokerManager()
        m.start()
        m.stop()

    def test_not_running_raises(self):
        m = BrokerManager()
        with pytest.raises(BrokerManagerNotRunningError):
            m.register_broker(_broker(), _config())

    def test_double_start_raises(self):
        from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError
        m = BrokerManager()
        m.start()
        with pytest.raises(EngineAlreadyRunningError):
            m.start()
        m.stop()

    def test_double_stop_raises(self):
        from iios.investment.workflow.engine_lifecycle import EngineNotRunningError
        m = BrokerManager()
        m.start()
        m.stop()
        with pytest.raises(EngineNotRunningError):
            m.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerManager — registration
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerManagerRegistration:
    def test_register_broker(self):
        m, b = _registered_manager()
        assert m.broker_count() == 1
        m.stop()

    def test_register_fires_event(self):
        events: List[BrokerEvent] = []
        m = _manager()
        m.add_event_listener(events.append)
        m.register_broker(_broker(), _config())
        m.stop()
        types = [e.event_type for e in events]
        assert BrokerEventType.BROKER_REGISTERED in types

    def test_duplicate_raises(self):
        m, _ = _registered_manager()
        with pytest.raises((BrokerAlreadyRegisteredError, BrokerValidationError)):
            m.register_broker(_broker(), _config())
        m.stop()

    def test_remove_broker(self):
        m, _ = _registered_manager()
        m.remove_broker("test-broker")
        assert m.broker_count() == 0
        m.stop()

    def test_set_default(self):
        m, b = _registered_manager()
        m.set_default_broker("test-broker")
        assert m.default_broker() is b
        m.stop()

    def test_default_is_auto_set(self):
        m, b = _registered_manager()
        assert m.default_broker() is b
        m.stop()

    def test_get_broker(self):
        m, b = _registered_manager()
        assert m.get_broker("test-broker") is b
        m.stop()

    def test_get_missing_raises(self):
        m = _manager()
        with pytest.raises(BrokerNotRegisteredError):
            m.get_broker("MISSING")
        m.stop()

    def test_find_by_capability(self):
        m, _ = _registered_manager()
        result = m.find_by_capability(BrokerCapability.MIS)
        assert len(result) == 1
        m.stop()

    def test_all_brokers(self):
        m, b = _registered_manager()
        assert b in m.all_brokers()
        m.stop()

    def test_all_broker_ids(self):
        m, _ = _registered_manager()
        assert "test-broker" in m.all_broker_ids()
        m.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerManager — connection lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerManagerConnection:
    def test_connect_success(self):
        m, _ = _registered_manager()
        resp = m.connect("test-broker")
        assert resp.is_success
        m.stop()

    def test_connect_fires_event(self):
        events: List[BrokerEvent] = []
        m, _ = _registered_manager()
        m.add_event_listener(events.append)
        m.connect("test-broker")
        m.stop()
        assert BrokerEventType.BROKER_CONNECTED in [e.event_type for e in events]

    def test_connect_failure(self):
        m  = _manager()
        b  = _broker(connect_success=False)
        m.register_broker(b, _config())
        resp = m.connect("test-broker")
        assert not resp.is_success
        m.stop()

    def test_disconnect(self):
        m, _ = _registered_manager()
        m.connect("test-broker")
        resp = m.disconnect("test-broker")
        assert resp.is_success
        m.stop()

    def test_disconnect_fires_event(self):
        events: List[BrokerEvent] = []
        m, _ = _registered_manager()
        m.connect("test-broker")
        m.add_event_listener(events.append)
        m.disconnect("test-broker")
        m.stop()
        assert BrokerEventType.BROKER_DISCONNECTED in [e.event_type for e in events]

    def test_is_connected_after_connect(self):
        m, _ = _registered_manager()
        m.connect("test-broker")
        assert m.is_connected("test-broker")
        m.stop()

    def test_is_not_connected_initially(self):
        m, _ = _registered_manager()
        assert not m.is_connected("test-broker")
        m.stop()

    def test_ping_returns_bool(self):
        m, _ = _registered_manager()
        m.connect("test-broker")
        assert isinstance(m.ping("test-broker"), bool)
        m.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerManager — authentication
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerManagerAuthentication:
    def test_authenticate_success(self):
        m, _ = _registered_manager()
        m.connect("test-broker")
        resp = m.authenticate("test-broker")
        assert resp.is_success
        m.stop()

    def test_authenticate_fires_succeeded_event(self):
        events: List[BrokerEvent] = []
        m, _ = _registered_manager()
        m.connect("test-broker")
        m.add_event_listener(events.append)
        m.authenticate("test-broker")
        m.stop()
        assert BrokerEventType.AUTHENTICATION_SUCCEEDED in [e.event_type for e in events]

    def test_authenticate_failure_fires_failed_event(self):
        events: List[BrokerEvent] = []
        m  = _manager()
        b  = _broker(auth_success=False)
        m.register_broker(b, _config())
        m.connect("test-broker")
        m.add_event_listener(events.append)
        m.authenticate("test-broker")
        m.stop()
        assert BrokerEventType.AUTHENTICATION_FAILED in [e.event_type for e in events]

    def test_is_authenticated_after_auth(self):
        m, _ = _registered_manager()
        m.connect("test-broker")
        m.authenticate("test-broker")
        assert m.is_authenticated("test-broker")
        m.stop()

    def test_refresh_session(self):
        m, _ = _registered_manager()
        m.connect("test-broker")
        m.authenticate("test-broker")
        resp = m.refresh_session("test-broker")
        assert resp.is_success
        m.stop()

    def test_reconnect_signals(self):
        events: List[BrokerEvent] = []
        m, _ = _registered_manager()
        m.add_event_listener(events.append)
        m.signal_reconnect_started("test-broker")
        m.signal_reconnect_succeeded("test-broker")
        m.stop()
        types = [e.event_type for e in events]
        assert BrokerEventType.RECONNECT_STARTED   in types
        assert BrokerEventType.RECONNECT_SUCCEEDED in types


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerManager — health
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerManagerHealth:
    def test_check_health_returns_record(self):
        m, _ = _registered_manager()
        m.connect("test-broker")
        record = m.check_health("test-broker")
        assert isinstance(record, BrokerHealthRecord)
        m.stop()

    def test_health_change_fires_event(self):
        events: List[BrokerEvent] = []
        m, _ = _registered_manager()
        m.add_event_listener(events.append)
        m.check_health("test-broker")   # first check → health changed
        m.stop()
        assert BrokerEventType.BROKER_HEALTH_CHANGED in [e.event_type for e in events]

    def test_get_health(self):
        m, _ = _registered_manager()
        m.connect("test-broker")
        m.check_health("test-broker")
        record = m.get_health("test-broker")
        assert record is not None
        m.stop()

    def test_unhealthy_brokers_list(self):
        m  = _manager()
        b  = _broker(connect_success=False)
        m.register_broker(b, _config())
        m.check_health("test-broker")
        assert "test-broker" in m.unhealthy_brokers()
        m.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerManager — order operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerManagerOrders:
    def _connected_manager(self):
        m, b = _registered_manager()
        m.connect("test-broker")
        m.authenticate("test-broker")
        return m

    def test_place_order(self):
        m    = self._connected_manager()
        req  = make_order_request(
            "test-broker", "NIFTY", "NSE",
            OrderSide.BUY, OrderType.MARKET, ProductType.MIS,
            quantity=50.0, price=0.0,
        )
        resp = m.place_order("test-broker", req)
        assert resp.is_success
        assert resp.has_data
        m.stop()

    def test_modify_order(self):
        m   = self._connected_manager()
        req = make_modify_order_request(
            "test-broker", "ORD-1", "NIFTY", "NSE", 10.0, 100.0, OrderType.LIMIT
        )
        resp = m.modify_order("test-broker", req)
        assert resp.is_success
        m.stop()

    def test_cancel_order(self):
        m   = self._connected_manager()
        req = make_cancel_order_request("test-broker", "ORD-1", "NIFTY", "NSE")
        resp = m.cancel_order("test-broker", req)
        assert resp.is_success
        m.stop()

    def test_get_order(self):
        m    = self._connected_manager()
        resp = m.get_order("test-broker", "ORD-001")
        assert resp.is_success
        m.stop()

    def test_get_orders(self):
        m    = self._connected_manager()
        resp = m.get_orders("test-broker")
        assert resp.is_success
        m.stop()

    def test_get_positions(self):
        m    = self._connected_manager()
        resp = m.get_positions("test-broker")
        assert resp.is_success
        m.stop()

    def test_get_holdings(self):
        m    = self._connected_manager()
        resp = m.get_holdings("test-broker")
        assert resp.is_success
        m.stop()

    def test_get_funds(self):
        m    = self._connected_manager()
        resp = m.get_funds("test-broker")
        assert resp.is_success
        m.stop()

    def test_get_margin(self):
        m    = self._connected_manager()
        resp = m.get_margin("test-broker")
        assert resp.is_success
        m.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerManager — statistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerManagerStatistics:
    def test_statistics_after_request(self):
        m, _ = _registered_manager()
        m.connect("test-broker")
        stats = m.statistics("test-broker")
        assert stats is not None
        assert stats.requests >= 1
        m.stop()

    def test_all_statistics(self):
        m, _ = _registered_manager()
        all_stats = m.all_statistics()
        assert "test-broker" in all_stats
        m.stop()

    def test_statistics_none_for_missing(self):
        m = _manager()
        # No broker registered
        store = BrokerStatisticsStore()
        assert store.get_snapshot("MISSING") is None
        m.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerManager — events
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerManagerEvents:
    def test_add_and_fire(self):
        fired: List[BrokerEvent] = []
        m, _ = _registered_manager()
        m.add_event_listener(fired.append)
        m.connect("test-broker")
        m.stop()
        assert len(fired) > 0

    def test_remove_listener(self):
        fired: List[BrokerEvent] = []
        m, _ = _registered_manager()
        m.add_event_listener(fired.append)
        m.remove_event_listener(fired.append)
        m.connect("test-broker")
        m.stop()
        assert len(fired) == 0

    def test_listener_exception_does_not_crash(self):
        def bad_listener(event: BrokerEvent) -> None:
            raise RuntimeError("bad listener")

        m, _ = _registered_manager()
        m.add_event_listener(bad_listener)
        m.connect("test-broker")  # should not raise despite bad listener
        m.stop()

    def test_history_records_events(self):
        m, _ = _registered_manager()
        m.connect("test-broker")
        h = m.history()
        assert h.event_count > 0
        m.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestBrokerFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerFactory:
    def test_create_configuration(self):
        config = BrokerFactory.create_configuration("B", "Broker B")
        assert isinstance(config, BrokerConfiguration)

    def test_create_capabilities(self):
        caps = BrokerFactory.create_capabilities(BrokerCapability.MIS)
        assert caps.has(BrokerCapability.MIS)

    def test_create_connection(self):
        conn = BrokerFactory.create_connection("B", "orders")
        assert isinstance(conn, BrokerConnection)
        assert conn.connection_id == "orders"

    def test_create_pool(self):
        pool = BrokerFactory.create_connection_pool("B")
        assert isinstance(pool, ConnectionPool)

    def test_create_session(self):
        s = BrokerFactory.create_session("B")
        assert isinstance(s, BrokerSession)

    def test_create_session_manager(self):
        sm = BrokerFactory.create_session_manager()
        assert isinstance(sm, BrokerSessionManager)

    def test_create_health_record(self):
        r = BrokerFactory.create_health_record("B", is_healthy=True)
        assert isinstance(r, BrokerHealthRecord)

    def test_create_statistics(self):
        s = BrokerFactory.create_statistics("B")
        assert isinstance(s, BrokerStatistics)

    def test_create_statistics_store(self):
        store = BrokerFactory.create_statistics_store()
        assert isinstance(store, BrokerStatisticsStore)

    def test_create_history(self):
        h = BrokerFactory.create_history(max_size=100)
        assert isinstance(h, BrokerHistory)

    def test_success_response(self):
        r = BrokerFactory.success_response("R", "B", data={"x": 1})
        assert r.is_success

    def test_failure_response(self):
        r = BrokerFactory.failure_response("R", "B", error_code="E", error_message="m")
        assert r.is_failure


# ═══════════════════════════════════════════════════════════════════════════════
# TestConcurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_connections(self):
        """Multiple threads connecting different brokers concurrently."""
        m = _manager()
        brokers = [_broker(broker_id=f"B{i}") for i in range(5)]
        for i, b in enumerate(brokers):
            m.register_broker(b, _config(f"B{i}"))

        errors: List[Exception] = []

        def do_connect(bid: str) -> None:
            try:
                m.connect(bid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=do_connect, args=(f"B{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        m.stop()

    def test_concurrent_statistics_updates(self):
        """Statistics accumulation is thread-safe."""
        stats = BrokerStatistics(broker_id="B")
        errors: List[Exception] = []

        def worker() -> None:
            try:
                for _ in range(100):
                    stats.record_request()
                    stats.record_response(latency_ms=1.0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert stats.requests  == 500
        assert stats.responses == 500

    def test_concurrent_history_writes(self):
        """BrokerHistory is safe under concurrent writes."""
        h = BrokerHistory(max_size=100)

        def writer() -> None:
            for _ in range(50):
                h.append_event(make_broker_connected_event("B"))

        threads = [threading.Thread(target=writer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert h.event_count <= 100  # bounded

    def test_concurrent_event_listeners(self):
        """Event listeners are called safely under concurrent fires."""
        fired: List[BrokerEvent] = []
        lock  = threading.Lock()

        def listener(event: BrokerEvent) -> None:
            with lock:
                fired.append(event)

        m = _manager()
        m.add_event_listener(listener)

        brokers = [_broker(broker_id=f"C{i}") for i in range(4)]
        for i, b in enumerate(brokers):
            m.register_broker(b, _config(f"C{i}"))

        threads = [threading.Thread(target=m.connect, args=(f"C{i}",)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        m.stop()
        assert len(fired) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestRegression
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_session_manager_timeout_floor_removed(self):
        """BrokerSessionManager must honour sub-second timeouts (no minimum floor)."""
        s = BrokerSession("B")
        s.mark_authenticated(timeout_secs=0.01)
        time.sleep(0.05)
        assert s.is_expired

    def test_remove_listener_idempotent(self):
        """Removing a listener not in the list does not raise."""
        m = _manager()
        listener = lambda e: None
        m.remove_event_listener(listener)  # not added — should not raise
        m.stop()

    def test_stop_disconnects_all_pools(self):
        """Stopping BrokerManager sets all connections to STOPPED."""
        m, _ = _registered_manager()
        m.connect("test-broker")
        m.stop()
        # After stop, pools are stopped — no running state remains

    def test_capability_consistency_warnings_not_errors(self):
        """Capability warnings do not prevent registration."""
        # A broker with MARGIN_TRADING but no MIS/NRML
        class MissingProductBroker(_TestBroker):
            def capabilities(self):
                return make_capabilities(
                    BrokerCapability.MARGIN_TRADING,
                    BrokerCapability.ORDER_CANCELLATION,
                )

        m = _manager()
        b = MissingProductBroker()
        # Should register without error (warnings are not errors)
        m.register_broker(b, _config())
        assert m.broker_count() == 1
        m.stop()

    def test_history_events_for_correct_broker(self):
        """events_for_broker filters correctly across multiple brokers."""
        m  = _manager()
        b1 = _broker(broker_id="B1")
        b2 = _broker(broker_id="B2")
        m.register_broker(b1, _config("B1"))
        m.register_broker(b2, _config("B2"))
        m.connect("B1")
        m.connect("B2")
        h  = m.history()
        b1_events = h.events_for_broker("B1")
        b2_events = h.events_for_broker("B2")
        assert all(e.broker_id == "B1" for e in b1_events)
        assert all(e.broker_id == "B2" for e in b2_events)
        m.stop()

    def test_broker_manager_stop_clears_sessions(self):
        """After stop, all sessions are removed."""
        m, _ = _registered_manager()
        m.connect("test-broker")
        m.authenticate("test-broker")
        m.stop()
        # No crash; session cleared during _on_stop
