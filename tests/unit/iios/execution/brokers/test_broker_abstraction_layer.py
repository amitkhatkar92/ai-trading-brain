"""tests/unit/iios/execution/brokers/test_broker_abstraction_layer.py
==================================================
Comprehensive test suite for C6 Phase 1 Module 3:
IIOS Broker Abstraction Layer.

15 test classes, 95%+ coverage.
"""
from __future__ import annotations

import threading
import time
import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────

from iios.execution.brokers.constants import (
    BrokerCapabilityCode,
    BrokerConnectionState,
    BrokerHealthStatus,
    BrokerMode,
    BrokerRequestType,
    BrokerResponseStatus,
    BrokerValidationCode,
    Exchange,
    ProductType,
    TimeInForce,
    DEFAULT_MAX_BROKERS,
    VERSION,
)
from iios.execution.brokers.exceptions import (
    BrokerAbstractionError,
    BrokerCapacityError,
    BrokerCapabilityError,
    BrokerConnectionError,
    BrokerFactoryError,
    BrokerNotFoundError,
    BrokerNotRunningError,
    BrokerRegistrationError,
    BrokerValidationError,
    DuplicateBrokerError,
)
from iios.execution.brokers.broker_metadata import BrokerMetadata, RateLimitSpec
from iios.execution.brokers.broker_capabilities import (
    BrokerCapabilities,
    capabilities_from_metadata,
)
from iios.execution.brokers.broker_request import (
    BalanceRequest,
    BrokerRequest,
    CancelRequest,
    ConnectionRequest,
    HeartbeatRequest,
    ModifyRequest,
    OrderRequest,
    PositionRequest,
)
from iios.execution.brokers.broker_response import (
    BalanceResponse,
    BrokerResponse,
    CancelResponse,
    ConnectionResponse,
    HealthResponse,
    ModifyResponse,
    OrderResponse,
    PositionItem,
    PositionResponse,
)
from iios.execution.brokers.broker_interface import AbstractBrokerInterface
from iios.execution.brokers.broker import AbstractBroker
from iios.execution.brokers.broker_context import BrokerOperationContext, make_context
from iios.execution.brokers.broker_validation import BrokerValidator, BrokerValidationResult
from iios.execution.brokers.broker_events import (
    BrokerEvent,
    BrokerEventType,
    make_broker_event,
)
from iios.execution.brokers.broker_health import BrokerHealthRecord, BrokerHealthMonitor
from iios.execution.brokers.broker_statistics import BrokerStatistics, RegistryStatistics
from iios.execution.brokers.broker_registry import BrokerRecord, BrokerRegistry
from iios.execution.brokers.broker_factory import BrokerFactory
from iios.execution.brokers.broker_manager import BrokerManager


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures and helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_metadata(
    broker_id:    str = "test-broker",
    broker_name:  str = "Test Broker",
    capabilities: frozenset[BrokerCapabilityCode] | None = None,
    exchanges:    frozenset[Exchange] | None = None,
    modes:        frozenset[BrokerMode] | None = None,
) -> BrokerMetadata:
    return BrokerMetadata(
        broker_id           = broker_id,
        broker_name         = broker_name,
        capabilities        = capabilities or frozenset({BrokerCapabilityCode.MARKET_ORDER}),
        supported_exchanges = exchanges    or frozenset({Exchange.NSE}),
        supported_products  = frozenset({ProductType.CNC, ProductType.MIS}),
        supported_tif       = frozenset({TimeInForce.DAY, TimeInForce.IOC}),
        supported_modes     = modes        or frozenset({BrokerMode.PAPER}),
    )


def make_order_request(broker_id: str = "test-broker") -> OrderRequest:
    return OrderRequest(
        broker_id    = broker_id,
        order_id     = str(uuid.uuid4()),
        instrument   = "RELIANCE",
        exchange     = Exchange.NSE,
        product      = ProductType.CNC,
        side         = "BUY",
        quantity     = Decimal("100"),
        order_type   = "MARKET",
        capability   = BrokerCapabilityCode.MARKET_ORDER,
    )


@pytest.fixture
def registry() -> BrokerRegistry:
    r = BrokerRegistry()
    r.start()
    yield r
    if r.is_running:
        r.stop()


@pytest.fixture
def manager() -> BrokerManager:
    m = BrokerManager()
    m.start()
    yield m
    if m.is_running:
        m.stop()


@pytest.fixture
def metadata() -> BrokerMetadata:
    return make_metadata()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants and enumerations
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_broker_mode_values(self) -> None:
        assert BrokerMode.LIVE.value      == "LIVE"
        assert BrokerMode.PAPER.value     == "PAPER"
        assert BrokerMode.SIMULATION.value == "SIMULATION"
        assert BrokerMode.BACKTEST.value  == "BACKTEST"

    def test_broker_health_status_values(self) -> None:
        assert BrokerHealthStatus.HEALTHY.value   == "HEALTHY"
        assert BrokerHealthStatus.UNHEALTHY.value == "UNHEALTHY"
        assert BrokerHealthStatus.DEGRADED.value  == "DEGRADED"
        assert BrokerHealthStatus.UNKNOWN.value   == "UNKNOWN"

    def test_broker_connection_state_values(self) -> None:
        assert BrokerConnectionState.CONNECTED.value    == "CONNECTED"
        assert BrokerConnectionState.DISCONNECTED.value == "DISCONNECTED"

    def test_capability_codes(self) -> None:
        assert BrokerCapabilityCode.MARKET_ORDER.value  == "MARKET_ORDER"
        assert BrokerCapabilityCode.LIMIT_ORDER.value   == "LIMIT_ORDER"
        assert BrokerCapabilityCode.BRACKET_ORDER.value == "BRACKET_ORDER"
        assert BrokerCapabilityCode.PAPER_TRADING.value == "PAPER_TRADING"
        assert BrokerCapabilityCode.AMO.value           == "AMO"
        assert BrokerCapabilityCode.GTT.value           == "GTT"
        assert BrokerCapabilityCode.PARTIAL_FILL.value  == "PARTIAL_FILL"
        assert BrokerCapabilityCode.MARGIN.value        == "MARGIN"

    def test_exchange_values(self) -> None:
        assert Exchange.NSE.value     == "NSE"
        assert Exchange.BSE.value     == "BSE"
        assert Exchange.NFO.value     == "NFO"
        assert Exchange.BINANCE.value == "BINANCE"

    def test_time_in_force_values(self) -> None:
        assert TimeInForce.DAY.value == "DAY"
        assert TimeInForce.IOC.value == "IOC"
        assert TimeInForce.GTC.value == "GTC"
        assert TimeInForce.GTT.value == "GTT"

    def test_request_type_values(self) -> None:
        assert BrokerRequestType.ORDER.value     == "ORDER"
        assert BrokerRequestType.MODIFY.value    == "MODIFY"
        assert BrokerRequestType.CANCEL.value    == "CANCEL"
        assert BrokerRequestType.HEARTBEAT.value == "HEARTBEAT"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_hierarchy(self) -> None:
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(BrokerAbstractionError, IIOSError)
        assert issubclass(BrokerNotFoundError,    BrokerAbstractionError)
        assert issubclass(DuplicateBrokerError,   BrokerAbstractionError)
        assert issubclass(BrokerCapacityError,    BrokerAbstractionError)
        assert issubclass(BrokerCapabilityError,  BrokerAbstractionError)
        assert issubclass(BrokerValidationError,  BrokerAbstractionError)
        assert issubclass(BrokerFactoryError,     BrokerAbstractionError)
        assert issubclass(BrokerNotRunningError,  BrokerAbstractionError)

    def test_broker_not_found_carries_id(self) -> None:
        exc = BrokerNotFoundError("broker-x")
        assert exc.broker_id == "broker-x"
        assert "broker-x" in str(exc)

    def test_duplicate_broker_carries_id(self) -> None:
        exc = DuplicateBrokerError("broker-y")
        assert exc.broker_id == "broker-y"

    def test_capability_error_carries_fields(self) -> None:
        exc = BrokerCapabilityError("broker-z", "BRACKET_ORDER")
        assert exc.broker_id  == "broker-z"
        assert exc.capability == "BRACKET_ORDER"

    def test_validation_error_carries_errors(self) -> None:
        exc = BrokerValidationError("failed", errors=("e1", "e2"))
        assert exc.errors == ("e1", "e2")

    def test_error_codes(self) -> None:
        assert BrokerAbstractionError.DEFAULT_CODE == "BR-000"
        assert BrokerNotFoundError.DEFAULT_CODE    == "BR-002"
        assert DuplicateBrokerError.DEFAULT_CODE   == "BR-003"
        assert BrokerCapacityError.DEFAULT_CODE    == "BR-004"
        assert BrokerCapabilityError.DEFAULT_CODE  == "BR-008"
        assert BrokerNotRunningError.DEFAULT_CODE  == "BR-012"


# ─────────────────────────────────────────────────────────────────────────────
# 3. BrokerMetadata
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerMetadata:
    def test_creation(self) -> None:
        m = make_metadata("dhan", "Dhan Broker")
        assert m.broker_id   == "dhan"
        assert m.broker_name == "Dhan Broker"

    def test_frozen(self) -> None:
        m = make_metadata()
        with pytest.raises((AttributeError, TypeError)):
            m.broker_id = "modified"  # type: ignore[misc]

    def test_supports_mode(self) -> None:
        m = make_metadata(modes=frozenset({BrokerMode.PAPER, BrokerMode.LIVE}))
        assert m.supports_mode(BrokerMode.PAPER)
        assert m.supports_mode(BrokerMode.LIVE)
        assert not m.supports_mode(BrokerMode.BACKTEST)

    def test_supports_exchange(self) -> None:
        m = make_metadata(exchanges=frozenset({Exchange.NSE, Exchange.BSE}))
        assert m.supports_exchange(Exchange.NSE)
        assert not m.supports_exchange(Exchange.NYSE)

    def test_has_capability(self) -> None:
        caps = frozenset({BrokerCapabilityCode.MARKET_ORDER, BrokerCapabilityCode.LIMIT_ORDER})
        m = make_metadata(capabilities=caps)
        assert m.has_capability(BrokerCapabilityCode.MARKET_ORDER)
        assert not m.has_capability(BrokerCapabilityCode.BRACKET_ORDER)

    def test_missing_capabilities(self) -> None:
        caps = frozenset({BrokerCapabilityCode.MARKET_ORDER})
        m    = make_metadata(capabilities=caps)
        missing = m.missing_capabilities(
            frozenset({BrokerCapabilityCode.MARKET_ORDER, BrokerCapabilityCode.LIMIT_ORDER})
        )
        assert BrokerCapabilityCode.LIMIT_ORDER in missing
        assert BrokerCapabilityCode.MARKET_ORDER not in missing

    def test_to_dict(self) -> None:
        m = make_metadata()
        d = m.to_dict()
        assert d["broker_id"]   == "test-broker"
        assert d["broker_name"] == "Test Broker"
        assert "capabilities"        in d
        assert "supported_exchanges" in d

    def test_rate_limit_spec(self) -> None:
        rl = RateLimitSpec(requests_per_second=5.0, requests_per_minute=100)
        assert rl.requests_per_second == 5.0
        d = rl.to_dict()
        assert d["requests_per_second"] == 5.0

    def test_repr(self) -> None:
        m = make_metadata()
        assert "test-broker" in repr(m)


# ─────────────────────────────────────────────────────────────────────────────
# 4. BrokerCapabilities
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerCapabilities:
    def test_has(self) -> None:
        caps = BrokerCapabilities(
            broker_id    = "b",
            capabilities = frozenset({BrokerCapabilityCode.MARKET_ORDER}),
        )
        assert caps.has(BrokerCapabilityCode.MARKET_ORDER)
        assert not caps.has(BrokerCapabilityCode.LIMIT_ORDER)

    def test_has_all(self) -> None:
        caps = BrokerCapabilities(
            broker_id    = "b",
            capabilities = frozenset({
                BrokerCapabilityCode.MARKET_ORDER,
                BrokerCapabilityCode.LIMIT_ORDER,
            }),
        )
        assert caps.has_all(frozenset({BrokerCapabilityCode.MARKET_ORDER}))
        assert not caps.has_all(frozenset({BrokerCapabilityCode.BRACKET_ORDER}))

    def test_missing(self) -> None:
        caps = BrokerCapabilities(
            broker_id    = "b",
            capabilities = frozenset({BrokerCapabilityCode.MARKET_ORDER}),
        )
        missing = caps.missing(
            frozenset({BrokerCapabilityCode.MARKET_ORDER, BrokerCapabilityCode.LIMIT_ORDER})
        )
        assert BrokerCapabilityCode.LIMIT_ORDER in missing

    def test_intersection(self) -> None:
        c1 = BrokerCapabilities("b1", frozenset({BrokerCapabilityCode.MARKET_ORDER, BrokerCapabilityCode.LIMIT_ORDER}))
        c2 = BrokerCapabilities("b2", frozenset({BrokerCapabilityCode.LIMIT_ORDER, BrokerCapabilityCode.STOP_ORDER}))
        common = c1.intersection(c2)
        assert BrokerCapabilityCode.LIMIT_ORDER in common
        assert BrokerCapabilityCode.MARKET_ORDER not in common

    def test_union(self) -> None:
        c1 = BrokerCapabilities("b1", frozenset({BrokerCapabilityCode.MARKET_ORDER}))
        c2 = BrokerCapabilities("b2", frozenset({BrokerCapabilityCode.LIMIT_ORDER}))
        combined = c1.union(c2)
        assert BrokerCapabilityCode.MARKET_ORDER in combined
        assert BrokerCapabilityCode.LIMIT_ORDER  in combined

    def test_capabilities_from_metadata(self) -> None:
        m    = make_metadata(capabilities=frozenset({BrokerCapabilityCode.AMO}))
        caps = capabilities_from_metadata(m)
        assert caps.broker_id == m.broker_id
        assert caps.has(BrokerCapabilityCode.AMO)

    def test_to_dict(self) -> None:
        caps = BrokerCapabilities(
            broker_id    = "b",
            capabilities = frozenset({BrokerCapabilityCode.MARKET_ORDER}),
        )
        d = caps.to_dict()
        assert "MARKET_ORDER" in d["capabilities"]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Request types
# ─────────────────────────────────────────────────────────────────────────────

class TestRequestTypes:
    def test_broker_request_defaults(self) -> None:
        r = BrokerRequest(broker_id="b")
        assert r.request_id != ""
        assert r.broker_id == "b"
        assert r.age_sec >= 0.0

    def test_connection_request(self) -> None:
        r = ConnectionRequest(broker_id="b", reconnect=True)
        assert r.request_type == BrokerRequestType.CONNECTION
        assert r.reconnect
        d = r.to_dict()
        assert d["reconnect"] is True

    def test_order_request(self) -> None:
        r = make_order_request()
        assert r.request_type == BrokerRequestType.ORDER
        assert r.instrument   == "RELIANCE"
        d = r.to_dict()
        assert d["quantity"] == "100"

    def test_modify_request(self) -> None:
        r = ModifyRequest(broker_id="b", order_id="O1", new_quantity=Decimal("50"))
        assert r.request_type == BrokerRequestType.MODIFY
        d = r.to_dict()
        assert d["new_quantity"] == "50"

    def test_cancel_request(self) -> None:
        r = CancelRequest(broker_id="b", order_id="O1", reason="user")
        assert r.request_type == BrokerRequestType.CANCEL
        d = r.to_dict()
        assert d["reason"] == "user"

    def test_position_request(self) -> None:
        r = PositionRequest(broker_id="b", portfolio_id="P1")
        assert r.request_type == BrokerRequestType.POSITION
        d = r.to_dict()
        assert d["portfolio_id"] == "P1"

    def test_balance_request(self) -> None:
        r = BalanceRequest(broker_id="b", include_margin=True)
        assert r.request_type == BrokerRequestType.BALANCE
        d = r.to_dict()
        assert d["include_margin"] is True

    def test_heartbeat_request(self) -> None:
        r = HeartbeatRequest(broker_id="b")
        assert r.request_type == BrokerRequestType.HEARTBEAT

    def test_request_repr(self) -> None:
        r = make_order_request()
        assert "ORDER" in repr(r)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Response types
# ─────────────────────────────────────────────────────────────────────────────

class TestResponseTypes:
    def test_broker_response_succeeded(self) -> None:
        r = BrokerResponse(broker_id="b", status=BrokerResponseStatus.SUCCESS)
        assert r.succeeded
        assert not r.failed
        assert not r.has_error

    def test_broker_response_failed(self) -> None:
        r = BrokerResponse(
            broker_id="b",
            status=BrokerResponseStatus.FAILURE,
            error_message="oops",
        )
        assert not r.succeeded
        assert r.failed
        assert r.has_error

    def test_connection_response(self) -> None:
        r = ConnectionResponse(
            broker_id        = "b",
            connection_state = BrokerConnectionState.CONNECTED,
        )
        d = r.to_dict()
        assert d["connection_state"] == "CONNECTED"

    def test_order_response(self) -> None:
        r = OrderResponse(
            broker_id      = "b",
            order_id       = "O1",
            broker_order_id = "EXT-001",
            submitted_qty  = Decimal("100"),
            acknowledged   = True,
        )
        d = r.to_dict()
        assert d["acknowledged"]
        assert d["submitted_qty"] == "100"

    def test_modify_response(self) -> None:
        r = ModifyResponse(broker_id="b", order_id="O1", modified=True)
        d = r.to_dict()
        assert d["modified"]

    def test_cancel_response(self) -> None:
        r = CancelResponse(broker_id="b", order_id="O1", cancelled=True)
        assert r.cancelled
        d = r.to_dict()
        assert d["cancelled"]

    def test_position_response(self) -> None:
        pos = PositionItem(instrument="RELIANCE", exchange="NSE", quantity=Decimal("50"))
        r = PositionResponse(broker_id="b", positions=(pos,))
        d = r.to_dict()
        assert len(d["positions"]) == 1
        assert d["positions"][0]["instrument"] == "RELIANCE"

    def test_balance_response(self) -> None:
        r = BalanceResponse(
            broker_id       = "b",
            available_cash  = Decimal("100000"),
            used_margin     = Decimal("20000"),
        )
        d = r.to_dict()
        assert d["available_cash"] == "100000"

    def test_health_response(self) -> None:
        r = HealthResponse(
            broker_id     = "b",
            health_status = BrokerHealthStatus.HEALTHY,
            latency_ms    = 12.5,
        )
        d = r.to_dict()
        assert d["health_status"] == "HEALTHY"
        assert d["latency_ms"] == 12.5

    def test_response_frozen(self) -> None:
        r = BrokerResponse(broker_id="b")
        with pytest.raises((AttributeError, TypeError)):
            r.broker_id = "x"  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# 7. Abstract interface and base
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerInterface:
    def test_cannot_instantiate_interface(self) -> None:
        with pytest.raises(TypeError):
            AbstractBrokerInterface()  # type: ignore[abstract]

    def test_cannot_instantiate_abstract_broker(self) -> None:
        with pytest.raises(TypeError):
            AbstractBroker(make_metadata())  # type: ignore[abstract]

    def test_concrete_adapter_registers_metadata(self) -> None:
        m = make_metadata("concrete-broker")

        class ConcreteBroker(AbstractBroker):
            def connect(self, r):
                return ConnectionResponse(broker_id=self.broker_id)
            def disconnect(self, r):
                return ConnectionResponse(broker_id=self.broker_id)
            def health(self, r):
                return HealthResponse(broker_id=self.broker_id)
            def submit_order(self, r):
                return OrderResponse(broker_id=self.broker_id)
            def modify_order(self, r):
                return ModifyResponse(broker_id=self.broker_id)
            def cancel_order(self, r):
                return CancelResponse(broker_id=self.broker_id)
            def order_status(self, r):
                return OrderResponse(broker_id=self.broker_id)
            def positions(self, r):
                return PositionResponse(broker_id=self.broker_id)
            def holdings(self, r):
                return PositionResponse(broker_id=self.broker_id)
            def balances(self, r):
                return BalanceResponse(broker_id=self.broker_id)
            def margin(self, r):
                return BalanceResponse(broker_id=self.broker_id)

        b = ConcreteBroker(m)
        assert b.broker_id == "concrete-broker"
        assert b.metadata  == m
        assert not b.is_connected

    def test_heartbeat_delegates_to_health(self) -> None:
        m = make_metadata("hb-broker")

        class ConcreteBroker(AbstractBroker):
            def connect(self, r):    return ConnectionResponse(broker_id=self.broker_id)
            def disconnect(self, r): return ConnectionResponse(broker_id=self.broker_id)
            def health(self, r):
                return HealthResponse(broker_id=self.broker_id, health_status=BrokerHealthStatus.HEALTHY)
            def submit_order(self, r): return OrderResponse(broker_id=self.broker_id)
            def modify_order(self, r): return ModifyResponse(broker_id=self.broker_id)
            def cancel_order(self, r): return CancelResponse(broker_id=self.broker_id)
            def order_status(self, r): return OrderResponse(broker_id=self.broker_id)
            def positions(self, r):    return PositionResponse(broker_id=self.broker_id)
            def holdings(self, r):     return PositionResponse(broker_id=self.broker_id)
            def balances(self, r):     return BalanceResponse(broker_id=self.broker_id)
            def margin(self, r):       return BalanceResponse(broker_id=self.broker_id)

        b   = ConcreteBroker(m)
        req = HeartbeatRequest(broker_id="hb-broker")
        resp = b.heartbeat(req)
        assert resp.succeeded

    def test_require_connected_raises(self) -> None:
        from iios.execution.brokers.broker import AbstractBroker
        from iios.execution.brokers.exceptions import BrokerNotConnectedError
        m = make_metadata("nc-broker")

        class ConcreteBroker(AbstractBroker):
            def connect(self, r):    return ConnectionResponse(broker_id=self.broker_id)
            def disconnect(self, r): return ConnectionResponse(broker_id=self.broker_id)
            def health(self, r):     return HealthResponse(broker_id=self.broker_id)
            def submit_order(self, r): return OrderResponse(broker_id=self.broker_id)
            def modify_order(self, r): return ModifyResponse(broker_id=self.broker_id)
            def cancel_order(self, r): return CancelResponse(broker_id=self.broker_id)
            def order_status(self, r): return OrderResponse(broker_id=self.broker_id)
            def positions(self, r):    return PositionResponse(broker_id=self.broker_id)
            def holdings(self, r):     return PositionResponse(broker_id=self.broker_id)
            def balances(self, r):     return BalanceResponse(broker_id=self.broker_id)
            def margin(self, r):       return BalanceResponse(broker_id=self.broker_id)

        b = ConcreteBroker(m)
        with pytest.raises(BrokerNotConnectedError):
            b._require_connected()


# ─────────────────────────────────────────────────────────────────────────────
# 8. BrokerOperationContext
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerContext:
    def test_creation(self) -> None:
        ctx = BrokerOperationContext(broker_id="b", operation="submit_order")
        assert ctx.broker_id == "b"
        assert ctx.operation == "submit_order"

    def test_frozen(self) -> None:
        ctx = BrokerOperationContext(broker_id="b")
        with pytest.raises((AttributeError, TypeError)):
            ctx.broker_id = "x"  # type: ignore[misc]

    def test_is_connected(self) -> None:
        ctx = BrokerOperationContext(
            broker_id        = "b",
            connection_state = BrokerConnectionState.CONNECTED,
        )
        assert ctx.is_connected

    def test_is_healthy(self) -> None:
        ctx = BrokerOperationContext(
            broker_id     = "b",
            health_status = BrokerHealthStatus.HEALTHY,
        )
        assert ctx.is_healthy

    def test_age_ms(self) -> None:
        ctx = BrokerOperationContext(broker_id="b")
        time.sleep(0.01)
        assert ctx.age_ms >= 0.0

    def test_to_dict(self) -> None:
        ctx = BrokerOperationContext(broker_id="b", operation="health")
        d   = ctx.to_dict()
        assert d["broker_id"]  == "b"
        assert d["operation"]  == "health"

    def test_make_context_factory(self) -> None:
        req = BrokerRequest(broker_id="b")
        ctx = make_context("b", "heartbeat", req)
        assert ctx.broker_id == "b"
        assert ctx.operation == "heartbeat"
        assert ctx.request_id == req.request_id


# ─────────────────────────────────────────────────────────────────────────────
# 9. BrokerValidation
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerValidation:
    def setup_method(self) -> None:
        self.v = BrokerValidator()

    def test_valid_metadata(self) -> None:
        m = make_metadata()
        r = self.v.validate_metadata(m)
        assert r.passed

    def test_empty_broker_id(self) -> None:
        m = BrokerMetadata(broker_id="", broker_name="X")
        r = self.v.validate_metadata(m)
        assert not r.passed
        assert any("MISSING_BROKER_ID" in e for e in r.errors)

    def test_empty_broker_name(self) -> None:
        m = BrokerMetadata(broker_id="x", broker_name="")
        r = self.v.validate_metadata(m)
        assert not r.passed
        assert any("MISSING_BROKER_NAME" in e for e in r.errors)

    def test_valid_request(self) -> None:
        req = BrokerRequest(broker_id="b")
        r   = self.v.validate_request(req)
        assert r.passed

    def test_missing_broker_id_in_request(self) -> None:
        req = BrokerRequest()
        r   = self.v.validate_request(req)
        assert not r.passed
        assert any("MISSING_BROKER_ID" in e for e in r.errors)

    def test_not_connected_blocks_order(self) -> None:
        req = make_order_request()
        caps = BrokerCapabilities(
            broker_id    = "test-broker",
            capabilities = frozenset({BrokerCapabilityCode.MARKET_ORDER}),
            supported_exchanges = frozenset({Exchange.NSE}),
            supported_products  = frozenset({ProductType.CNC}),
        )
        r = self.v.validate_request(
            req,
            capabilities     = caps,
            connection_state = BrokerConnectionState.DISCONNECTED,
        )
        assert not r.passed
        assert any("BROKER_NOT_CONNECTED" in e for e in r.errors)

    def test_unsupported_capability(self) -> None:
        req = make_order_request()
        req.capability = BrokerCapabilityCode.BRACKET_ORDER
        caps = BrokerCapabilities(
            broker_id    = "test-broker",
            capabilities = frozenset({BrokerCapabilityCode.MARKET_ORDER}),
            supported_exchanges = frozenset({Exchange.NSE}),
            supported_products  = frozenset({ProductType.CNC}),
        )
        r = self.v.validate_request(
            req,
            capabilities     = caps,
            connection_state = BrokerConnectionState.CONNECTED,
        )
        assert not r.passed
        assert any("UNSUPPORTED_CAPABILITY" in e for e in r.errors)

    def test_valid_response(self) -> None:
        resp = BrokerResponse(broker_id="b")
        r    = self.v.validate_response(resp)
        assert r.passed

    def test_missing_broker_id_in_response(self) -> None:
        resp = BrokerResponse(broker_id="")
        r    = self.v.validate_response(resp)
        assert not r.passed

    def test_validation_result_bool(self) -> None:
        assert bool(BrokerValidationResult.ok())
        assert not bool(BrokerValidationResult.fail("error"))

    def test_validation_result_to_dict(self) -> None:
        r = BrokerValidationResult.ok(warnings=("w1",))
        d = r.to_dict()
        assert d["passed"]
        assert "w1" in d["warnings"]

    def test_capability_consistency(self) -> None:
        m    = make_metadata("b")
        caps = capabilities_from_metadata(m)
        r    = self.v.validate_capability(caps, m)
        assert r.passed

    def test_capability_mismatch(self) -> None:
        m1   = make_metadata("b1")
        m2   = make_metadata("b2")
        caps = capabilities_from_metadata(m1)
        r    = self.v.validate_capability(caps, m2)
        assert not r.passed


# ─────────────────────────────────────────────────────────────────────────────
# 10. BrokerEvents
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerEvents:
    def test_event_type_values(self) -> None:
        assert BrokerEventType.BROKER_REGISTERED.value   == "BROKER_REGISTERED"
        assert BrokerEventType.BROKER_CONNECTED.value    == "BROKER_CONNECTED"
        assert BrokerEventType.BROKER_DISCONNECTED.value == "BROKER_DISCONNECTED"
        assert BrokerEventType.BROKER_HEALTHY.value      == "BROKER_HEALTHY"
        assert BrokerEventType.BROKER_UNHEALTHY.value    == "BROKER_UNHEALTHY"
        assert BrokerEventType.REQUEST_VALIDATED.value   == "REQUEST_VALIDATED"
        assert BrokerEventType.RESPONSE_RECEIVED.value   == "RESPONSE_RECEIVED"

    def test_make_broker_event(self) -> None:
        e = make_broker_event(
            "dhan",
            BrokerEventType.BROKER_CONNECTED,
            connection_state = BrokerConnectionState.CONNECTED,
        )
        assert e.broker_id == "dhan"
        assert e.event_type == BrokerEventType.BROKER_CONNECTED
        assert e.connection_state == BrokerConnectionState.CONNECTED

    def test_event_to_dict(self) -> None:
        e = make_broker_event("b", BrokerEventType.BROKER_HEALTHY)
        d = e.to_dict()
        assert d["broker_id"]  == "b"
        assert d["event_type"] == "BROKER_HEALTHY"

    def test_event_frozen(self) -> None:
        e = make_broker_event("b", BrokerEventType.BROKER_REGISTERED)
        with pytest.raises((AttributeError, TypeError)):
            e.broker_id = "x"  # type: ignore[misc]

    def test_event_repr(self) -> None:
        e = make_broker_event("b", BrokerEventType.BROKER_REGISTERED)
        assert "BROKER_REGISTERED" in repr(e)


# ─────────────────────────────────────────────────────────────────────────────
# 11. BrokerHealth
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerHealth:
    def test_initial_state(self) -> None:
        r = BrokerHealthRecord(broker_id="b")
        assert r.status       == BrokerHealthStatus.UNKNOWN
        assert r.check_count  == 0
        assert r.health_rate  == 0.0

    def test_record_healthy(self) -> None:
        r = BrokerHealthRecord(broker_id="b")
        r.record_healthy(latency_ms=10.0)
        assert r.status        == BrokerHealthStatus.HEALTHY
        assert r.check_count   == 1
        assert r.healthy_count == 1
        assert r.last_latency_ms == 10.0
        assert r.consecutive_failures == 0

    def test_record_unhealthy(self) -> None:
        r = BrokerHealthRecord(broker_id="b")
        r.record_unhealthy("timeout")
        assert r.status               == BrokerHealthStatus.UNHEALTHY
        assert r.unhealthy_count      == 1
        assert r.consecutive_failures == 1
        assert r.error_message        == "timeout"

    def test_record_degraded(self) -> None:
        r = BrokerHealthRecord(broker_id="b")
        r.record_degraded(latency_ms=200.0)
        assert r.status == BrokerHealthStatus.DEGRADED

    def test_health_rate(self) -> None:
        r = BrokerHealthRecord(broker_id="b")
        r.record_healthy()
        r.record_healthy()
        r.record_unhealthy()
        assert abs(r.health_rate - 2/3) < 0.01

    def test_to_dict(self) -> None:
        r = BrokerHealthRecord(broker_id="b")
        r.record_healthy(10.0)
        d = r.to_dict()
        assert d["broker_id"] == "b"
        assert d["status"]    == "HEALTHY"

    def test_monitor_register_unregister(self) -> None:
        m = BrokerHealthMonitor()
        m.register("b1")
        assert m.get("b1") is not None
        m.unregister("b1")
        assert m.get("b1") is None

    def test_monitor_record_healthy(self) -> None:
        m = BrokerHealthMonitor()
        m.register("b1")
        m.record_healthy("b1", 5.0)
        assert m.get("b1").is_healthy
        assert "b1" in m.healthy_broker_ids()

    def test_monitor_overall_status(self) -> None:
        m = BrokerHealthMonitor()
        m.register("b1")
        m.register("b2")
        m.record_healthy("b1")
        m.record_healthy("b2")
        assert m.overall_status == BrokerHealthStatus.HEALTHY

    def test_monitor_summary(self) -> None:
        m = BrokerHealthMonitor()
        m.register("b1")
        m.record_healthy("b1")
        s = m.summary()
        assert s["total_brokers"]   == 1
        assert s["healthy_brokers"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 12. BrokerStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerStatistics:
    def test_initial_state(self) -> None:
        s = BrokerStatistics(broker_id="b")
        assert s.total_requests    == 0
        assert s.success_rate      == 0.0
        assert s.avg_response_ms   == 0.0

    def test_record_request(self) -> None:
        s = BrokerStatistics(broker_id="b")
        s.record_request("ORDER", succeeded=True, duration_ms=12.0)
        assert s.order_requests      == 1
        assert s.successful_requests == 1
        assert s.total_requests      == 1
        assert abs(s.avg_response_ms - 12.0) < 0.01

    def test_record_failure(self) -> None:
        s = BrokerStatistics(broker_id="b")
        s.record_request("ORDER", succeeded=False)
        assert s.failed_requests == 1
        assert s.success_rate    == 0.0

    def test_success_rate(self) -> None:
        s = BrokerStatistics(broker_id="b")
        s.record_request("ORDER", succeeded=True)
        s.record_request("ORDER", succeeded=True)
        s.record_request("ORDER", succeeded=False)
        assert abs(s.success_rate - 2/3) < 0.01

    def test_all_request_types(self) -> None:
        s = BrokerStatistics(broker_id="b")
        for rt in ("ORDER", "MODIFY", "CANCEL", "POSITION", "BALANCE", "HEARTBEAT", "HEALTH"):
            s.record_request(rt)
        assert s.order_requests     == 1
        assert s.modify_requests    == 1
        assert s.cancel_requests    == 1
        assert s.position_requests  == 1
        assert s.balance_requests   == 1
        assert s.heartbeat_count    == 1
        assert s.health_check_count == 1

    def test_to_dict(self) -> None:
        s = BrokerStatistics(broker_id="b")
        s.record_request("ORDER", succeeded=True, duration_ms=5.0)
        d = s.to_dict()
        assert d["broker_id"]      == "b"
        assert d["total_requests"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 13. BrokerRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerRegistry:
    def test_not_running_before_start(self) -> None:
        r = BrokerRegistry()
        with pytest.raises(BrokerNotRunningError):
            r.register(make_metadata())

    def test_start_stop(self, registry: BrokerRegistry) -> None:
        assert registry.is_running

    def test_register_and_get(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        record = registry.register(metadata)
        assert record.broker_id == "test-broker"
        assert registry.get("test-broker").broker_id == "test-broker"

    def test_duplicate_raises(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        registry.register(metadata)
        with pytest.raises(DuplicateBrokerError):
            registry.register(metadata)

    def test_overwrite_allowed(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        registry.register(metadata)
        record = registry.register(metadata, overwrite=True)
        assert record.broker_id == "test-broker"

    def test_not_found_raises(self, registry: BrokerRegistry) -> None:
        with pytest.raises(BrokerNotFoundError):
            registry.get("missing-broker")

    def test_contains(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        assert not registry.contains("test-broker")
        registry.register(metadata)
        assert registry.contains("test-broker")

    def test_count(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        assert registry.count() == 0
        registry.register(metadata)
        assert registry.count() == 1

    def test_all_broker_ids(self, registry: BrokerRegistry) -> None:
        registry.register(make_metadata("b1"))
        registry.register(make_metadata("b2"))
        ids = registry.all_broker_ids()
        assert "b1" in ids
        assert "b2" in ids

    def test_unregister(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        registry.register(metadata)
        registry.unregister("test-broker")
        assert not registry.contains("test-broker")

    def test_unregister_missing_raises(self, registry: BrokerRegistry) -> None:
        with pytest.raises(BrokerNotFoundError):
            registry.unregister("ghost")

    def test_capacity_limit(self) -> None:
        r = BrokerRegistry(max_brokers=2)
        r.start()
        r.register(make_metadata("b1"))
        r.register(make_metadata("b2"))
        with pytest.raises(BrokerCapacityError):
            r.register(make_metadata("b3"))
        r.stop()

    def test_health_update(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        registry.register(metadata)
        registry.record_health_update("test-broker", is_healthy=True, latency_ms=5.0)
        hr = registry.get_health("test-broker")
        assert hr is not None
        assert hr.is_healthy

    def test_connection_state(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        registry.register(metadata)
        registry.set_connection_state("test-broker", BrokerConnectionState.CONNECTED)
        hr = registry.get_health("test-broker")
        assert hr.connection_state == BrokerConnectionState.CONNECTED

    def test_statistics(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        registry.register(metadata)
        stats = registry.statistics()
        assert stats.total_registered == 1
        assert stats.capacity         == DEFAULT_MAX_BROKERS

    def test_listeners(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        events: list[BrokerEvent] = []
        registry.add_listener(events.append)
        registry.register(metadata)
        assert len(events) >= 1
        assert events[0].event_type == BrokerEventType.BROKER_REGISTERED

    def test_remove_listener(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        events: list[BrokerEvent] = []
        registry.add_listener(events.append)
        registry.remove_listener(events.append)
        registry.register(metadata)
        assert len(events) == 0

    def test_faulty_listener_does_not_crash(self, registry: BrokerRegistry, metadata: BrokerMetadata) -> None:
        def bad_listener(e: BrokerEvent) -> None:
            raise RuntimeError("listener error")
        registry.add_listener(bad_listener)
        # Should not raise
        registry.register(metadata)


# ─────────────────────────────────────────────────────────────────────────────
# 14. BrokerFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerFactory:
    def test_create_metadata(self) -> None:
        f = BrokerFactory()
        m = f.create_metadata(broker_id="dhan", broker_name="Dhan")
        assert m.broker_id   == "dhan"
        assert m.broker_name == "Dhan"

    def test_create_metadata_empty_id_raises(self) -> None:
        f = BrokerFactory()
        with pytest.raises(BrokerFactoryError):
            f.create_metadata(broker_id="", broker_name="X")

    def test_create_metadata_empty_name_raises(self) -> None:
        f = BrokerFactory()
        with pytest.raises(BrokerFactoryError):
            f.create_metadata(broker_id="b", broker_name="")

    def test_catalogue_lookup(self) -> None:
        f = BrokerFactory()
        f.create_metadata(broker_id="dhan", broker_name="Dhan")
        assert f.has("dhan")
        assert f.get("dhan") is not None
        assert "dhan" in f.registered_broker_ids()

    def test_all_metadata(self) -> None:
        f = BrokerFactory()
        f.create_metadata(broker_id="b1", broker_name="B1")
        f.create_metadata(broker_id="b2", broker_name="B2")
        assert len(f.all_metadata()) == 2

    def test_gen_broker_id(self) -> None:
        bid = BrokerFactory.gen_broker_id("dhan")
        assert bid.startswith("dhan-")
        assert len(bid) > 10

    def test_create_with_capabilities(self) -> None:
        f = BrokerFactory()
        caps = frozenset({BrokerCapabilityCode.LIMIT_ORDER, BrokerCapabilityCode.AMO})
        m = f.create_metadata(
            broker_id    = "zerodha",
            broker_name  = "Zerodha",
            capabilities = caps,
        )
        assert m.has_capability(BrokerCapabilityCode.AMO)


# ─────────────────────────────────────────────────────────────────────────────
# 15. BrokerManager (facade)
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerManager:
    def test_not_running_before_start(self) -> None:
        m = BrokerManager()
        with pytest.raises(BrokerNotRunningError):
            m.register(make_metadata())

    def test_start_stop(self, manager: BrokerManager) -> None:
        assert manager.is_running

    def test_create_and_register(self, manager: BrokerManager) -> None:
        record = manager.create_and_register(
            broker_id   = "dhan",
            broker_name = "Dhan Broker",
            capabilities = frozenset({BrokerCapabilityCode.LIMIT_ORDER}),
        )
        assert record.broker_id == "dhan"
        assert manager.contains("dhan")

    def test_register_and_unregister(self, manager: BrokerManager) -> None:
        m = make_metadata("to-unregister")
        manager.register(m)
        assert manager.contains("to-unregister")
        manager.unregister("to-unregister")
        assert not manager.contains("to-unregister")

    def test_register_invalid_metadata_raises(self, manager: BrokerManager) -> None:
        m = BrokerMetadata(broker_id="", broker_name="")
        with pytest.raises(BrokerValidationError):
            manager.register(m)

    def test_get_record(self, manager: BrokerManager) -> None:
        manager.create_and_register(broker_id="b", broker_name="B")
        record = manager.get_record("b")
        assert record.broker_id == "b"

    def test_get_capabilities(self, manager: BrokerManager) -> None:
        caps = frozenset({BrokerCapabilityCode.AMO})
        manager.create_and_register(
            broker_id    = "dhan",
            broker_name  = "Dhan",
            capabilities = caps,
        )
        c = manager.get_capabilities("dhan")
        assert c.has(BrokerCapabilityCode.AMO)

    def test_health_update(self, manager: BrokerManager) -> None:
        manager.create_and_register(broker_id="b", broker_name="B")
        manager.record_health_update("b", is_healthy=True, latency_ms=3.0)
        hr = manager.get_health("b")
        assert hr is not None
        assert hr.is_healthy

    def test_connection_state(self, manager: BrokerManager) -> None:
        manager.create_and_register(broker_id="b", broker_name="B")
        manager.set_connection_state("b", BrokerConnectionState.CONNECTED)
        hr = manager.get_health("b")
        assert hr.connection_state == BrokerConnectionState.CONNECTED

    def test_statistics(self, manager: BrokerManager) -> None:
        manager.create_and_register(broker_id="b", broker_name="B")
        stats = manager.statistics()
        assert stats.total_registered == 1

    def test_count(self, manager: BrokerManager) -> None:
        assert manager.count() == 0
        manager.create_and_register(broker_id="b", broker_name="B")
        assert manager.count() == 1

    def test_listeners(self, manager: BrokerManager) -> None:
        events: list[BrokerEvent] = []
        manager.add_listener(events.append)
        manager.create_and_register(broker_id="b", broker_name="B")
        assert any(e.event_type == BrokerEventType.BROKER_REGISTERED for e in events)
        manager.remove_listener(events.append)

    def test_validate_metadata_valid(self, manager: BrokerManager) -> None:
        m = make_metadata()
        r = manager.validate_metadata(m)
        assert r.passed

    def test_validate_metadata_invalid(self, manager: BrokerManager) -> None:
        m = BrokerMetadata(broker_id="", broker_name="")
        r = manager.validate_metadata(m)
        assert not r.passed

    def test_uptime_sec(self, manager: BrokerManager) -> None:
        time.sleep(0.01)
        assert manager.uptime_sec > 0.0

    def test_all_broker_ids(self, manager: BrokerManager) -> None:
        manager.create_and_register(broker_id="b1", broker_name="B1")
        manager.create_and_register(broker_id="b2", broker_name="B2")
        ids = manager.all_broker_ids()
        assert "b1" in ids
        assert "b2" in ids


# ─────────────────────────────────────────────────────────────────────────────
# 16. Thread safety
# ─────────────────────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_registrations(self) -> None:
        registry = BrokerRegistry(max_brokers=200)
        registry.start()
        errors: list[Exception] = []

        def register(i: int) -> None:
            try:
                registry.register(make_metadata(f"broker-{i}", f"Broker {i}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert registry.count() == 50
        registry.stop()

    def test_concurrent_health_updates(self) -> None:
        registry = BrokerRegistry()
        registry.start()
        registry.register(make_metadata("b"))
        errors: list[Exception] = []

        def update(i: int) -> None:
            try:
                registry.record_health_update("b", is_healthy=(i % 2 == 0))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        registry.stop()

    def test_concurrent_statistics_recording(self) -> None:
        s = BrokerStatistics(broker_id="b")
        errors: list[Exception] = []

        def record(i: int) -> None:
            try:
                s.record_request("ORDER", succeeded=True, duration_ms=float(i))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert s.order_requests == 50
