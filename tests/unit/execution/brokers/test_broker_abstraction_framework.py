"""tests/unit/execution/brokers/test_broker_abstraction_framework.py

Comprehensive unit tests for the Broker Abstraction & Adapter Framework.
Target: ≥150 tests, ≥90% coverage.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid
from typing import Any, AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

def run_async(coro):
    """Run a coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 1: Constants & Enums
# ════════════════════════════════════════════════════════════════════════════════

class TestBrokerConstants:
    def test_broker_status_values(self):
        from iios.execution.brokers.broker_constants import BrokerStatus
        assert BrokerStatus.ACTIVE.value   == "active"
        assert BrokerStatus.CONNECTED.value == "connected"
        assert BrokerStatus.ERROR.value    == "error"

    def test_auth_method_values(self):
        from iios.execution.brokers.broker_constants import AuthMethod
        assert AuthMethod.API_KEY.value == "api_key"
        assert AuthMethod.OAUTH.value   == "oauth"
        assert AuthMethod.JWT.value     == "jwt"
        assert AuthMethod.NONE.value    == "none"

    def test_capability_types_exist(self):
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        assert BrokerCapabilityType.CASH_EQUITY.value == "cash_equity"
        assert BrokerCapabilityType.CRYPTO.value      == "crypto"
        assert BrokerCapabilityType.GTT.value         == "gtt"
        assert BrokerCapabilityType.PAPER_TRADING.value == "paper_trading"
        assert BrokerCapabilityType.STREAMING.value   == "streaming"

    def test_connection_status_values(self):
        from iios.execution.brokers.broker_constants import ConnectionStatus
        assert ConnectionStatus.CONNECTED.value    == "connected"
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.FAILED.value       == "failed"

    def test_retry_policy_values(self):
        from iios.execution.brokers.broker_constants import RetryPolicy
        assert RetryPolicy.EXPONENTIAL.value == "exponential"
        assert RetryPolicy.LINEAR.value      == "linear"

    def test_broker_environment_values(self):
        from iios.execution.brokers.broker_constants import BrokerEnvironment
        assert BrokerEnvironment.LIVE.value   == "live"
        assert BrokerEnvironment.PAPER.value  == "paper"

    def test_framework_constants(self):
        from iios.execution.brokers.broker_constants import (
            BROKER_FRAMEWORK_VERSION,
            DEFAULT_CONNECT_TIMEOUT_SEC,
            DEFAULT_MAX_BROKERS,
            DEFAULT_HEARTBEAT_INTERVAL_SEC,
        )
        assert BROKER_FRAMEWORK_VERSION.startswith("1.")
        assert DEFAULT_CONNECT_TIMEOUT_SEC > 0
        assert DEFAULT_MAX_BROKERS > 0
        assert DEFAULT_HEARTBEAT_INTERVAL_SEC > 0

    def test_capability_type_is_str(self):
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        cap = BrokerCapabilityType.CASH_EQUITY
        assert isinstance(cap, str)
        assert cap == "cash_equity"


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 2: Exceptions
# ════════════════════════════════════════════════════════════════════════════════

class TestBrokerExceptions:
    def test_base_exception_hierarchy(self):
        from iios.execution.brokers.broker_exceptions import (
            BrokerFrameworkError,
            BrokerError,
            BrokerNotFoundError,
        )
        assert issubclass(BrokerError, BrokerFrameworkError)
        assert issubclass(BrokerNotFoundError, BrokerError)

    def test_exception_codes(self):
        from iios.execution.brokers.broker_exceptions import (
            BrokerFrameworkError,
            BrokerNotFoundError,
            AuthenticationFailedError,
            CapabilityNotSupportedError,
            CircuitOpenError,
            BrokerRegistryOverflowError,
        )
        assert BrokerFrameworkError.error_code == "BAF-000"
        assert BrokerNotFoundError.error_code  == "BAF-011"
        assert AuthenticationFailedError.error_code == "BAF-031"
        assert CapabilityNotSupportedError.error_code == "BAF-041"
        assert CircuitOpenError.error_code == "BAF-073"
        assert BrokerRegistryOverflowError.error_code == "BAF-081"

    def test_exception_message_stored(self):
        from iios.execution.brokers.broker_exceptions import BrokerNotFoundError
        e = BrokerNotFoundError("broker X not found", "BAF-011")
        assert "broker X not found" in str(e)
        assert e.code == "BAF-011"

    def test_auth_exception_hierarchy(self):
        from iios.execution.brokers.broker_exceptions import (
            BrokerAuthenticationError,
            AuthenticationExpiredError,
            BrokerFrameworkError,
        )
        assert issubclass(AuthenticationExpiredError, BrokerAuthenticationError)
        assert issubclass(BrokerAuthenticationError, BrokerFrameworkError)

    def test_connection_exception_hierarchy(self):
        from iios.execution.brokers.broker_exceptions import (
            BrokerConnectionError,
            CircuitOpenError,
        )
        assert issubclass(CircuitOpenError, BrokerConnectionError)

    def test_adapter_exception_hierarchy(self):
        from iios.execution.brokers.broker_exceptions import (
            AdapterError,
            InvalidAdapterError,
        )
        assert issubclass(InvalidAdapterError, AdapterError)


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 3: Core Models
# ════════════════════════════════════════════════════════════════════════════════

class TestBrokerCapability:
    def test_capability_creation(self):
        from iios.execution.brokers.core.broker_capability import BrokerCapability
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        cap = BrokerCapability(BrokerCapabilityType.CASH_EQUITY, description="NSE equities")
        assert cap.capability_type == BrokerCapabilityType.CASH_EQUITY
        assert cap.is_supported is True
        assert cap.description == "NSE equities"

    def test_capability_to_dict(self):
        from iios.execution.brokers.core.broker_capability import BrokerCapability
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        cap = BrokerCapability(BrokerCapabilityType.GTT)
        d = cap.to_dict()
        assert d["capability_type"] == "gtt"
        assert d["is_supported"] is True

    def test_capability_set_supports(self):
        from iios.execution.brokers.core.broker_capability import BrokerCapability, BrokerCapabilitySet
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        caps = BrokerCapabilitySet([
            BrokerCapability(BrokerCapabilityType.CASH_EQUITY),
            BrokerCapability(BrokerCapabilityType.STREAMING),
        ])
        assert caps.supports(BrokerCapabilityType.CASH_EQUITY) is True
        assert caps.supports(BrokerCapabilityType.CRYPTO) is False

    def test_capability_set_add_remove(self):
        from iios.execution.brokers.core.broker_capability import BrokerCapability, BrokerCapabilitySet
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        caps = BrokerCapabilitySet()
        caps.add(BrokerCapability(BrokerCapabilityType.CRYPTO))
        assert caps.supports(BrokerCapabilityType.CRYPTO)
        caps.remove(BrokerCapabilityType.CRYPTO)
        assert not caps.supports(BrokerCapabilityType.CRYPTO)

    def test_capability_set_all_supported(self):
        from iios.execution.brokers.core.broker_capability import BrokerCapability, BrokerCapabilitySet
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        caps = BrokerCapabilitySet([
            BrokerCapability(BrokerCapabilityType.LIMIT_ORDER, is_supported=True),
            BrokerCapability(BrokerCapabilityType.BRACKET_ORDER, is_supported=False),
        ])
        supported = caps.all_supported()
        assert BrokerCapabilityType.LIMIT_ORDER in supported
        assert BrokerCapabilityType.BRACKET_ORDER not in supported

    def test_capability_set_len(self):
        from iios.execution.brokers.core.broker_capability import BrokerCapability, BrokerCapabilitySet
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        caps = BrokerCapabilitySet([
            BrokerCapability(BrokerCapabilityType.CASH_EQUITY),
            BrokerCapability(BrokerCapabilityType.STREAMING),
        ])
        assert len(caps) == 2

    def test_capability_set_contains(self):
        from iios.execution.brokers.core.broker_capability import BrokerCapability, BrokerCapabilitySet
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        caps = BrokerCapabilitySet([BrokerCapability(BrokerCapabilityType.MARGIN)])
        assert BrokerCapabilityType.MARGIN in caps
        assert BrokerCapabilityType.CRYPTO not in caps

    def test_capability_set_to_dict(self):
        from iios.execution.brokers.core.broker_capability import BrokerCapability, BrokerCapabilitySet
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        caps = BrokerCapabilitySet([BrokerCapability(BrokerCapabilityType.FUTURES)])
        d = caps.to_dict()
        assert "capabilities" in d
        assert d["supported_count"] >= 1


class TestBrokerRequest:
    def test_request_defaults(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        req = BrokerRequest(operation="place_order")
        assert req.operation == "place_order"
        assert req.request_id != ""
        assert req.created_at > 0

    def test_request_to_dict(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        req = BrokerRequest(operation="fetch_balance", broker_id="dhan")
        d = req.to_dict()
        assert d["operation"] == "fetch_balance"
        assert d["broker_id"] == "dhan"
        assert "request_id" in d


class TestBrokerResponse:
    def test_ok_factory(self):
        from iios.execution.brokers.core.broker_response import BrokerResponse
        r = BrokerResponse.ok({"balance": 100}, broker_id="paper")
        assert r.success is True
        assert r.data["balance"] == 100
        assert r.broker_id == "paper"
        assert r.is_success()
        assert not r.is_error()

    def test_fail_factory(self):
        from iios.execution.brokers.core.broker_response import BrokerResponse
        r = BrokerResponse.fail("BAF-011", "not found", broker_id="x")
        assert r.success is False
        assert r.error_code == "BAF-011"
        assert r.error_message == "not found"
        assert r.is_error()

    def test_response_to_dict(self):
        from iios.execution.brokers.core.broker_response import BrokerResponse
        r = BrokerResponse.ok({"k": "v"}, operation="health_check")
        d = r.to_dict()
        assert d["success"] is True
        assert d["operation"] == "health_check"
        assert "response_id" in d


class TestBrokerSession:
    def test_session_creation(self):
        from iios.execution.brokers.core.broker_session import BrokerSession
        from iios.execution.brokers.broker_constants import AuthMethod
        s = BrokerSession(
            broker_id="paper",
            auth_method=AuthMethod.NONE,
            access_token="tok123",
            expires_at=time.time() + 3600,
        )
        assert s.is_active
        assert not s.is_expired()
        assert s.is_valid()

    def test_session_expiry(self):
        from iios.execution.brokers.core.broker_session import BrokerSession
        s = BrokerSession(expires_at=time.time() - 1)
        assert s.is_expired()
        assert not s.is_valid()

    def test_session_refresh(self):
        from iios.execution.brokers.core.broker_session import BrokerSession
        s = BrokerSession(access_token="old", expires_at=time.time() + 100)
        s.refresh("new_token", time.time() + 7200)
        assert s.access_token == "new_token"

    def test_session_invalidate(self):
        from iios.execution.brokers.core.broker_session import BrokerSession
        s = BrokerSession(access_token="tok", is_active=True)
        s.invalidate()
        assert not s.is_active
        assert s.access_token == ""

    def test_session_to_dict(self):
        from iios.execution.brokers.core.broker_session import BrokerSession
        s = BrokerSession(broker_id="zerodha")
        d = s.to_dict()
        assert d["broker_id"] == "zerodha"
        assert "session_id" in d


class TestBrokerConnection:
    def test_mark_connected(self):
        from iios.execution.brokers.core.broker_connection import BrokerConnection
        from iios.execution.brokers.broker_constants import ConnectionStatus
        conn = BrokerConnection(broker_id="dhan")
        conn.mark_connected()
        assert conn.status == ConnectionStatus.CONNECTED
        assert conn.is_connected()
        assert conn.connected_at is not None

    def test_mark_disconnected(self):
        from iios.execution.brokers.core.broker_connection import BrokerConnection
        conn = BrokerConnection(broker_id="dhan")
        conn.mark_connected()
        conn.mark_disconnected("user request")
        assert not conn.is_connected()
        assert conn.error_message == "user request"

    def test_mark_failed(self):
        from iios.execution.brokers.core.broker_connection import BrokerConnection
        from iios.execution.brokers.broker_constants import ConnectionStatus
        conn = BrokerConnection(broker_id="dhan")
        conn.mark_failed("timeout")
        assert conn.status == ConnectionStatus.FAILED
        assert conn.failure_count == 1

    def test_heartbeat(self):
        from iios.execution.brokers.core.broker_connection import BrokerConnection
        conn = BrokerConnection()
        conn.update_heartbeat()
        age = conn.heartbeat_age_sec()
        assert age is not None
        assert age < 1.0

    def test_connection_to_dict(self):
        from iios.execution.brokers.core.broker_connection import BrokerConnection
        conn = BrokerConnection(broker_id="paper", host="localhost")
        conn.mark_connected()
        d = conn.to_dict()
        assert d["broker_id"] == "paper"
        assert d["host"] == "localhost"
        assert "connection_id" in d


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 4: Authentication
# ════════════════════════════════════════════════════════════════════════════════

class TestCredentialProvider:
    def test_in_memory_provider(self):
        from iios.execution.brokers.authentication.credential_provider import (
            Credentials, InMemoryCredentialProvider,
        )
        provider = InMemoryCredentialProvider()
        creds = Credentials(broker_id="paper", api_key="key123")
        provider.register(creds)
        assert provider.has_credentials("paper")
        retrieved = provider.get_credentials("paper")
        assert retrieved.api_key == "key123"

    def test_no_credentials_returns_empty(self):
        from iios.execution.brokers.authentication.credential_provider import (
            InMemoryCredentialProvider,
        )
        provider = InMemoryCredentialProvider()
        creds = provider.get_credentials("missing")
        assert creds.api_key == ""
        assert not provider.has_credentials("missing")

    def test_rotate_credentials(self):
        from iios.execution.brokers.authentication.credential_provider import (
            Credentials, InMemoryCredentialProvider,
        )
        provider = InMemoryCredentialProvider()
        provider.register(Credentials(broker_id="dhan", api_key="old"))
        provider.rotate_credentials("dhan", Credentials(broker_id="dhan", api_key="new"))
        assert provider.get_credentials("dhan").api_key == "new"

    def test_credentials_to_dict_omits_secrets(self):
        from iios.execution.brokers.authentication.credential_provider import Credentials
        creds = Credentials(broker_id="x", api_key="secret")
        d = creds.to_dict()
        assert "api_key" not in d
        assert d["has_api_key"] is True


class TestTokenManager:
    def test_store_and_get(self):
        from iios.execution.brokers.authentication.token_manager import TokenInfo, TokenManager
        mgr  = TokenManager()
        info = TokenInfo(broker_id="paper", access_token="tok", expires_at=time.time() + 3600)
        mgr.store(info)
        retrieved = mgr.get("paper")
        assert retrieved.access_token == "tok"

    def test_expired_token_raises(self):
        from iios.execution.brokers.authentication.token_manager import TokenInfo, TokenManager
        from iios.execution.brokers.broker_exceptions import AuthenticationExpiredError
        mgr  = TokenManager()
        info = TokenInfo(broker_id="x", access_token="tok", expires_at=time.time() - 1)
        mgr.store(info)
        with pytest.raises(AuthenticationExpiredError):
            mgr.get("x", auto_refresh=False)

    def test_missing_token_raises(self):
        from iios.execution.brokers.authentication.token_manager import TokenManager
        from iios.execution.brokers.broker_exceptions import AuthenticationExpiredError
        mgr = TokenManager()
        with pytest.raises(AuthenticationExpiredError):
            mgr.get("nonexistent")

    def test_invalidate(self):
        from iios.execution.brokers.authentication.token_manager import TokenInfo, TokenManager
        mgr = TokenManager()
        mgr.store(TokenInfo(broker_id="x", access_token="t", expires_at=time.time() + 3600))
        mgr.invalidate("x")
        assert not mgr.has("x")

    def test_token_expiry_soon(self):
        from iios.execution.brokers.authentication.token_manager import TokenInfo
        info = TokenInfo(broker_id="x", access_token="t", expires_at=time.time() + 60)
        assert info.is_expiring_soon(threshold_sec=300)

    def test_token_to_dict(self):
        from iios.execution.brokers.authentication.token_manager import TokenInfo
        info = TokenInfo(broker_id="b", access_token="t", expires_at=time.time() + 3600)
        d = info.to_dict()
        assert d["broker_id"] == "b"
        assert "token_id" in d


class TestSessionManager:
    def test_create_and_get(self):
        from iios.execution.brokers.authentication.session_manager import SessionManager
        from iios.execution.brokers.broker_constants import AuthMethod
        mgr = SessionManager()
        sess = mgr.create("paper", auth_method=AuthMethod.NONE, access_token="t",
                          expires_at=time.time() + 3600)
        assert mgr.has("paper")
        retrieved = mgr.get("paper")
        assert retrieved.session_id == sess.session_id

    def test_get_missing_raises(self):
        from iios.execution.brokers.authentication.session_manager import SessionManager
        from iios.execution.brokers.broker_exceptions import AuthenticationFailedError
        mgr = SessionManager()
        with pytest.raises(AuthenticationFailedError):
            mgr.get("missing")

    def test_invalidate(self):
        from iios.execution.brokers.authentication.session_manager import SessionManager
        mgr = SessionManager()
        mgr.create("paper", expires_at=time.time() + 3600)
        mgr.invalidate("paper")
        assert not mgr.has("paper")

    def test_purge_expired(self):
        from iios.execution.brokers.authentication.session_manager import SessionManager
        mgr = SessionManager()
        mgr.create("expired", expires_at=time.time() - 1)
        mgr.create("valid",   expires_at=time.time() + 3600)
        count = mgr.purge_expired()
        assert count == 1
        assert not mgr.has("expired")
        assert mgr.has("valid")

    def test_renew(self):
        from iios.execution.brokers.authentication.session_manager import SessionManager
        mgr = SessionManager()
        mgr.create("b", expires_at=time.time() + 3600)
        mgr.renew("b", "new_token", time.time() + 7200)
        assert mgr.get("b").access_token == "new_token"


class TestAuthenticationManager:
    def test_authenticate_creates_session(self):
        from iios.execution.brokers.authentication.authentication_manager import AuthenticationManager
        from iios.execution.brokers.broker_constants import AuthMethod
        mgr = AuthenticationManager()
        sess = mgr.authenticate(
            "paper", AuthMethod.NONE,
            {"access_token": "tok", "expires_in": 3600},
        )
        assert mgr.has_session("paper")
        assert sess.access_token == "tok"

    def test_invalidate_removes_session_and_token(self):
        from iios.execution.brokers.authentication.authentication_manager import AuthenticationManager
        from iios.execution.brokers.broker_constants import AuthMethod
        mgr = AuthenticationManager()
        mgr.authenticate("x", AuthMethod.API_KEY, {"access_token": "t", "expires_in": 3600})
        mgr.invalidate("x")
        assert not mgr.has_session("x")
        assert not mgr.token_manager.has("x")

    def test_statistics(self):
        from iios.execution.brokers.authentication.authentication_manager import AuthenticationManager
        from iios.execution.brokers.broker_constants import AuthMethod
        mgr = AuthenticationManager()
        mgr.authenticate("x", AuthMethod.API_KEY, {"access_token": "t", "expires_in": 3600})
        stats = mgr.statistics()
        assert stats["active_sessions"] == 1
        assert stats["stored_tokens"]   == 1


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 5: Connection
# ════════════════════════════════════════════════════════════════════════════════

class TestCircuitBreaker:
    def test_initially_closed(self):
        from iios.execution.brokers.connection.connection_retry import CircuitBreaker, CircuitState
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        from iios.execution.brokers.connection.connection_retry import CircuitBreaker, CircuitState
        from iios.execution.brokers.broker_exceptions import CircuitOpenError
        cb = CircuitBreaker(failure_threshold=2, recovery_sec=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitOpenError):
            cb.allow_request()

    def test_resets_on_success(self):
        from iios.execution.brokers.connection.connection_retry import CircuitBreaker, CircuitState
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_to_dict(self):
        from iios.execution.brokers.connection.connection_retry import CircuitBreaker
        cb = CircuitBreaker()
        d = cb.to_dict()
        assert "state" in d
        assert "failure_count" in d


class TestRetryConfig:
    def test_exponential_delay(self):
        from iios.execution.brokers.connection.connection_retry import RetryConfig
        from iios.execution.brokers.broker_constants import RetryPolicy
        cfg = RetryConfig(policy=RetryPolicy.EXPONENTIAL, base_delay_sec=1.0,
                          backoff_factor=2.0, jitter=False)
        assert cfg.delay_for_attempt(1) == pytest.approx(1.0)
        assert cfg.delay_for_attempt(2) == pytest.approx(2.0)
        assert cfg.delay_for_attempt(3) == pytest.approx(4.0)

    def test_linear_delay(self):
        from iios.execution.brokers.connection.connection_retry import RetryConfig
        from iios.execution.brokers.broker_constants import RetryPolicy
        cfg = RetryConfig(policy=RetryPolicy.LINEAR, base_delay_sec=1.0, jitter=False)
        assert cfg.delay_for_attempt(1) == pytest.approx(1.0)
        assert cfg.delay_for_attempt(3) == pytest.approx(3.0)

    def test_none_delay(self):
        from iios.execution.brokers.connection.connection_retry import RetryConfig
        from iios.execution.brokers.broker_constants import RetryPolicy
        cfg = RetryConfig(policy=RetryPolicy.NONE)
        assert cfg.delay_for_attempt(5) == 0.0


class TestRetryManager:
    def test_should_retry(self):
        from iios.execution.brokers.connection.connection_retry import RetryManager
        mgr = RetryManager()
        assert mgr.should_retry(1) is True
        assert mgr.should_retry(3) is True
        assert mgr.should_retry(4) is False    # max_retries=3

    def test_success_resets_circuit(self):
        from iios.execution.brokers.connection.connection_retry import (
            CircuitBreaker, RetryManager,
        )
        from iios.execution.brokers.connection.connection_retry import CircuitState
        cb  = CircuitBreaker(failure_threshold=1)
        mgr = RetryManager(circuit_breaker=cb)
        mgr.record_failure()
        mgr.record_success()
        assert cb.state == CircuitState.CLOSED


class TestConnectionPool:
    def test_acquire_creates_slot(self):
        from iios.execution.brokers.connection.connection_pool import ConnectionPool
        pool = ConnectionPool()
        conn = pool.acquire("dhan")
        assert conn.broker_id == "dhan"
        assert pool.has("dhan")

    def test_acquire_same_returns_same(self):
        from iios.execution.brokers.connection.connection_pool import ConnectionPool
        pool = ConnectionPool()
        c1 = pool.acquire("zerodha")
        c2 = pool.acquire("zerodha")
        assert c1.connection_id == c2.connection_id

    def test_remove(self):
        from iios.execution.brokers.connection.connection_pool import ConnectionPool
        pool = ConnectionPool()
        pool.acquire("x")
        pool.remove("x")
        assert not pool.has("x")

    def test_overflow_raises(self):
        from iios.execution.brokers.connection.connection_pool import ConnectionPool
        from iios.execution.brokers.broker_exceptions import BrokerRegistryOverflowError
        pool = ConnectionPool(max_connections=1)
        conn = pool.acquire("a")
        conn.mark_connected()   # prevent eviction — slot is live
        with pytest.raises(BrokerRegistryOverflowError):
            pool.acquire("b")

    def test_statistics(self):
        from iios.execution.brokers.connection.connection_pool import ConnectionPool
        pool = ConnectionPool()
        pool.acquire("a")
        pool.acquire("b")
        stats = pool.statistics()
        assert stats["total_slots"] == 2


class TestConnectionHealth:
    def test_healthy_factory(self):
        from iios.execution.brokers.connection.connection_health import ConnectionHealth
        h = ConnectionHealth.healthy("dhan", response_time_ms=5.0)
        assert h.is_healthy is True
        assert h.response_time_ms == 5.0

    def test_unhealthy_factory(self):
        from iios.execution.brokers.connection.connection_health import ConnectionHealth
        h = ConnectionHealth.unhealthy("x", "timeout")
        assert h.is_healthy is False
        assert "timeout" in h.error_message

    def test_to_dict(self):
        from iios.execution.brokers.connection.connection_health import ConnectionHealth
        h = ConnectionHealth.healthy("paper")
        d = h.to_dict()
        assert d["broker_id"] == "paper"
        assert d["is_healthy"] is True


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 6: Registry & Factory
# ════════════════════════════════════════════════════════════════════════════════

class TestAdapterRegistry:
    def test_register_and_get(self):
        from iios.execution.brokers.registry.adapter_registry import AdapterRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        reg = AdapterRegistry()
        reg.register("paper", PaperBrokerAdapter)
        assert reg.has("paper")
        entry = reg.get("paper")
        assert entry.adapter_class is PaperBrokerAdapter

    def test_register_invalid_class_raises(self):
        from iios.execution.brokers.registry.adapter_registry import AdapterRegistry
        from iios.execution.brokers.broker_exceptions import InvalidAdapterError
        reg = AdapterRegistry()
        with pytest.raises(InvalidAdapterError):
            reg.register("bad", str)    # str is not a BaseBrokerAdapter

    def test_duplicate_raises_without_overwrite(self):
        from iios.execution.brokers.registry.adapter_registry import AdapterRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        from iios.execution.brokers.broker_exceptions import BrokerAlreadyExistsError
        reg = AdapterRegistry()
        reg.register("paper", PaperBrokerAdapter)
        with pytest.raises(BrokerAlreadyExistsError):
            reg.register("paper", PaperBrokerAdapter)

    def test_overwrite_succeeds(self):
        from iios.execution.brokers.registry.adapter_registry import AdapterRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        reg = AdapterRegistry()
        reg.register("paper", PaperBrokerAdapter)
        reg.register("paper", PaperBrokerAdapter, overwrite=True)
        assert reg.has("paper")

    def test_overflow_raises(self):
        from iios.execution.brokers.registry.adapter_registry import AdapterRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        from iios.execution.brokers.broker_exceptions import BrokerRegistryOverflowError
        reg = AdapterRegistry(max_adapters=1)
        reg.register("a", PaperBrokerAdapter)
        with pytest.raises(BrokerRegistryOverflowError):
            reg.register("b", PaperBrokerAdapter)

    def test_unregister(self):
        from iios.execution.brokers.registry.adapter_registry import AdapterRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        reg = AdapterRegistry()
        reg.register("paper", PaperBrokerAdapter)
        reg.unregister("paper")
        assert not reg.has("paper")

    def test_get_missing_raises(self):
        from iios.execution.brokers.registry.adapter_registry import AdapterRegistry
        from iios.execution.brokers.broker_exceptions import BrokerNotFoundError
        reg = AdapterRegistry()
        with pytest.raises(BrokerNotFoundError):
            reg.get("missing")


class TestAdapterFactory:
    def test_create_adapter(self):
        from iios.execution.brokers.registry.adapter_registry import AdapterRegistry
        from iios.execution.brokers.factory.adapter_factory import AdapterFactory
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        reg = AdapterRegistry()
        reg.register("paper", PaperBrokerAdapter)
        factory = AdapterFactory(reg)
        adapter = factory.create("paper")
        assert isinstance(adapter, PaperBrokerAdapter)
        assert adapter.broker_id == "paper"

    def test_create_missing_raises(self):
        from iios.execution.brokers.registry.adapter_registry import AdapterRegistry
        from iios.execution.brokers.factory.adapter_factory import AdapterFactory
        from iios.execution.brokers.broker_exceptions import BrokerNotFoundError
        reg = AdapterRegistry()
        factory = AdapterFactory(reg)
        with pytest.raises(BrokerNotFoundError):
            factory.create("missing")


class TestBrokerRegistry:
    def test_register_and_get(self):
        from iios.execution.brokers.broker_registry import BrokerRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        reg     = BrokerRegistry()
        adapter = PaperBrokerAdapter()
        reg.register(adapter)
        assert reg.has("paper")
        assert reg.get("paper") is adapter

    def test_unregister(self):
        from iios.execution.brokers.broker_registry import BrokerRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        reg = BrokerRegistry()
        reg.register(PaperBrokerAdapter())
        reg.unregister("paper")
        assert not reg.has("paper")

    def test_get_missing_raises(self):
        from iios.execution.brokers.broker_registry import BrokerRegistry
        from iios.execution.brokers.broker_exceptions import BrokerNotFoundError
        reg = BrokerRegistry()
        with pytest.raises(BrokerNotFoundError):
            reg.get("ghost")

    def test_duplicate_raises(self):
        from iios.execution.brokers.broker_registry import BrokerRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        from iios.execution.brokers.broker_exceptions import BrokerAlreadyExistsError
        reg = BrokerRegistry()
        reg.register(PaperBrokerAdapter())
        with pytest.raises(BrokerAlreadyExistsError):
            reg.register(PaperBrokerAdapter())

    def test_overwrite(self):
        from iios.execution.brokers.broker_registry import BrokerRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        reg = BrokerRegistry()
        reg.register(PaperBrokerAdapter())
        reg.register(PaperBrokerAdapter(), overwrite=True)

    def test_singleton(self):
        from iios.execution.brokers.broker_registry import get_broker_registry, reset_broker_registry
        reset_broker_registry()
        r1 = get_broker_registry()
        r2 = get_broker_registry()
        assert r1 is r2

    def test_reset_singleton(self):
        from iios.execution.brokers.broker_registry import get_broker_registry, reset_broker_registry
        reset_broker_registry()
        r1 = get_broker_registry()
        reset_broker_registry()
        r2 = get_broker_registry()
        assert r1 is not r2


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 7: PaperBrokerAdapter (functional)
# ════════════════════════════════════════════════════════════════════════════════

class TestPaperBrokerAdapter:
    def _adapter(self):
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        return PaperBrokerAdapter()

    def test_connect(self):
        adapter = self._adapter()
        resp = run_async(adapter.connect())
        assert resp.success
        assert adapter.is_connected()

    def test_disconnect(self):
        adapter = self._adapter()
        run_async(adapter.connect())
        resp = run_async(adapter.disconnect())
        assert resp.success
        assert not adapter.is_connected()

    def test_authenticate(self):
        adapter = self._adapter()
        run_async(adapter.connect())
        resp = run_async(adapter.authenticate({"user_id": "test_user"}))
        assert resp.success
        assert adapter.is_authenticated()

    def test_place_order(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        req  = BrokerRequest(
            operation="place_order",
            payload={"symbol": "NIFTY", "side": "BUY", "quantity": 50, "price": 22000.0},
        )
        resp = run_async(adapter.place_order(req))
        assert resp.success
        assert "order_id" in resp.data

    def test_cancel_order(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        req   = BrokerRequest(
            operation="place_order",
            payload={"symbol": "NIFTY", "side": "BUY", "quantity": 50},
        )
        p_resp = run_async(adapter.place_order(req))
        order_id = p_resp.data["order_id"]
        c_resp = run_async(adapter.cancel_order(
            BrokerRequest(operation="cancel_order", payload={"order_id": order_id})
        ))
        assert c_resp.success

    def test_cancel_missing_order_fails(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        resp = run_async(adapter.cancel_order(
            BrokerRequest(operation="cancel_order", payload={"order_id": "GHOST"})
        ))
        assert not resp.success

    def test_fetch_orders(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        run_async(adapter.place_order(
            BrokerRequest(operation="place_order", payload={"symbol": "X", "quantity": 1})
        ))
        resp = run_async(adapter.fetch_orders(BrokerRequest()))
        assert resp.success
        assert resp.data["count"] >= 1

    def test_fetch_balance(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        resp = run_async(adapter.fetch_balance(BrokerRequest()))
        assert resp.success
        assert resp.data["available_cash"] == 1_000_000.0

    def test_set_cash_balance(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        adapter.set_cash_balance(500_000.0)
        run_async(adapter.connect())
        resp = run_async(adapter.fetch_balance(BrokerRequest()))
        assert resp.data["available_cash"] == 500_000.0

    def test_fetch_margin(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        resp = run_async(adapter.fetch_margin(BrokerRequest()))
        assert resp.success
        assert "available_margin" in resp.data

    def test_fetch_positions(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        run_async(adapter.place_order(
            BrokerRequest(payload={"symbol": "BANKNIFTY", "side": "BUY", "quantity": 25})
        ))
        resp = run_async(adapter.fetch_positions(BrokerRequest()))
        assert resp.success
        assert resp.data["count"] >= 1

    def test_fetch_holdings(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        resp = run_async(adapter.fetch_holdings(BrokerRequest()))
        assert resp.success

    def test_fetch_trades(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        run_async(adapter.place_order(BrokerRequest(payload={"symbol": "X", "quantity": 1})))
        resp = run_async(adapter.fetch_trades(BrokerRequest()))
        assert resp.success
        assert resp.data["count"] >= 1

    def test_stream_market_data(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())

        async def collect():
            results = []
            async for tick in adapter.stream_market_data(
                BrokerRequest(payload={"symbols": ["NIFTY"]})
            ):
                results.append(tick)
            return results

        ticks = run_async(collect())
        assert len(ticks) > 0
        assert all(t.success for t in ticks)

    def test_health_check(self):
        adapter = self._adapter()
        run_async(adapter.connect())
        resp = run_async(adapter.health_check())
        assert resp.success
        assert resp.data["healthy"] is True

    def test_reset(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        run_async(adapter.place_order(BrokerRequest(payload={"symbol": "X", "quantity": 1})))
        adapter.reset()
        assert adapter._orders == {}
        assert adapter._cash_balance == 1_000_000.0

    def test_modify_order(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        adapter = self._adapter()
        run_async(adapter.connect())
        p = run_async(adapter.place_order(BrokerRequest(payload={"symbol": "Y", "quantity": 5})))
        oid = p.data["order_id"]
        m = run_async(adapter.modify_order(
            BrokerRequest(payload={"order_id": oid, "quantity": 10})
        ))
        assert m.success

    def test_capabilities(self):
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        adapter = self._adapter()
        assert adapter.supports(BrokerCapabilityType.PAPER_TRADING)
        assert adapter.supports(BrokerCapabilityType.CASH_EQUITY)
        assert not adapter.supports(BrokerCapabilityType.CO)

    def test_statistics(self):
        adapter = self._adapter()
        stats = adapter.statistics()
        assert "broker_id" in stats
        assert stats["broker_id"] == "paper"

    def test_to_dict(self):
        adapter = self._adapter()
        d = adapter.to_dict()
        assert d["broker_id"] == "paper"
        assert "capabilities" in d


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 8: Skeleton Adapters
# ════════════════════════════════════════════════════════════════════════════════

class TestSkeletonAdapters:
    def _check_skeleton(self, adapter):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        from iios.execution.brokers.core.base_broker_adapter import BaseBrokerAdapter
        assert isinstance(adapter, BaseBrokerAdapter)
        with pytest.raises(NotImplementedError):
            run_async(adapter.connect())
        with pytest.raises(NotImplementedError):
            run_async(adapter.health_check())

    def test_dhan_adapter_is_skeleton(self):
        from iios.execution.brokers.adapters.dhan_adapter import DhanAdapter
        self._check_skeleton(DhanAdapter())

    def test_zerodha_adapter_is_skeleton(self):
        from iios.execution.brokers.adapters.zerodha_adapter import ZerodhaAdapter
        self._check_skeleton(ZerodhaAdapter())

    def test_angelone_adapter_is_skeleton(self):
        from iios.execution.brokers.adapters.angelone_adapter import AngelOneAdapter
        self._check_skeleton(AngelOneAdapter())

    def test_ibkr_adapter_is_skeleton(self):
        from iios.execution.brokers.adapters.interactive_brokers_adapter import (
            InteractiveBrokersAdapter,
        )
        self._check_skeleton(InteractiveBrokersAdapter())

    def test_alpaca_adapter_is_skeleton(self):
        from iios.execution.brokers.adapters.alpaca_adapter import AlpacaAdapter
        self._check_skeleton(AlpacaAdapter())

    def test_binance_adapter_is_skeleton(self):
        from iios.execution.brokers.adapters.binance_adapter import BinanceAdapter
        self._check_skeleton(BinanceAdapter())

    def test_dhan_capabilities(self):
        from iios.execution.brokers.adapters.dhan_adapter import DhanAdapter
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        a = DhanAdapter()
        assert a.supports(BrokerCapabilityType.GTT)
        assert a.supports(BrokerCapabilityType.STREAMING)

    def test_alpaca_paper_environment(self):
        from iios.execution.brokers.adapters.alpaca_adapter import AlpacaAdapter
        from iios.execution.brokers.broker_constants import BrokerEnvironment
        a = AlpacaAdapter()
        assert a.config.environment == BrokerEnvironment.PAPER

    def test_binance_crypto_capability(self):
        from iios.execution.brokers.adapters.binance_adapter import BinanceAdapter
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        a = BinanceAdapter()
        assert a.supports(BrokerCapabilityType.CRYPTO)


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 9: Capabilities Framework
# ════════════════════════════════════════════════════════════════════════════════

class TestCapabilityRegistry:
    def test_register_and_discover(self):
        from iios.execution.brokers.capabilities.capability_registry import CapabilityRegistry
        from iios.execution.brokers.core.broker_capability import BrokerCapability, BrokerCapabilitySet
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        reg  = CapabilityRegistry()
        caps = BrokerCapabilitySet([BrokerCapability(BrokerCapabilityType.CASH_EQUITY)])
        reg.register("paper", caps)
        discovered = reg.discover("paper")
        assert BrokerCapabilityType.CASH_EQUITY in discovered

    def test_brokers_with_capability(self):
        from iios.execution.brokers.capabilities.capability_registry import CapabilityRegistry
        from iios.execution.brokers.core.broker_capability import BrokerCapability, BrokerCapabilitySet
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        reg  = CapabilityRegistry()
        caps = BrokerCapabilitySet([BrokerCapability(BrokerCapabilityType.CRYPTO)])
        reg.register("binance", caps)
        reg.register("dhan", BrokerCapabilitySet())
        brokers = reg.brokers_with_capability(BrokerCapabilityType.CRYPTO)
        assert "binance" in brokers
        assert "dhan" not in brokers


class TestCapabilityChecker:
    def test_check_passes(self):
        from iios.execution.brokers.capabilities.capability_checker import CapabilityChecker
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        adapter = PaperBrokerAdapter()
        assert CapabilityChecker.check(adapter, BrokerCapabilityType.CASH_EQUITY)

    def test_check_fails_returns_false(self):
        from iios.execution.brokers.capabilities.capability_checker import CapabilityChecker
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        adapter = PaperBrokerAdapter()
        assert not CapabilityChecker.check(adapter, BrokerCapabilityType.CO)

    def test_assert_capability_raises(self):
        from iios.execution.brokers.capabilities.capability_checker import CapabilityChecker
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        from iios.execution.brokers.broker_exceptions import CapabilityNotSupportedError
        adapter = PaperBrokerAdapter()
        with pytest.raises(CapabilityNotSupportedError):
            CapabilityChecker.assert_capability(adapter, BrokerCapabilityType.CO)

    def test_assert_all_passes(self):
        from iios.execution.brokers.capabilities.capability_checker import CapabilityChecker
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        from iios.execution.brokers.broker_constants import BrokerCapabilityType
        adapter = PaperBrokerAdapter()
        CapabilityChecker.assert_all(
            adapter,
            [BrokerCapabilityType.CASH_EQUITY, BrokerCapabilityType.PAPER_TRADING],
        )


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 10: BrokerManager
# ════════════════════════════════════════════════════════════════════════════════

class TestBrokerManager:
    def _manager_with_paper(self):
        from iios.execution.brokers.broker_manager import BrokerManager
        from iios.execution.brokers.broker_factory import BrokerFactory
        from iios.execution.brokers.broker_registry import BrokerRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        factory  = BrokerFactory()
        factory.register_class("paper", PaperBrokerAdapter)
        registry = BrokerRegistry()
        mgr      = BrokerManager(broker_registry=registry, broker_factory=factory)
        mgr.load_adapter("paper")
        return mgr

    def test_load_adapter(self):
        mgr = self._manager_with_paper()
        assert mgr.has_adapter("paper")

    def test_connect(self):
        mgr  = self._manager_with_paper()
        resp = run_async(mgr.connect("paper"))
        assert resp.success

    def test_place_order_via_manager(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        mgr = self._manager_with_paper()
        run_async(mgr.connect("paper"))
        req  = BrokerRequest(payload={"symbol": "NIFTY", "quantity": 50})
        resp = run_async(mgr.place_order("paper", req))
        assert resp.success

    def test_fetch_balance_via_manager(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        mgr = self._manager_with_paper()
        run_async(mgr.connect("paper"))
        resp = run_async(mgr.fetch_balance("paper", BrokerRequest()))
        assert resp.success

    def test_unload_adapter(self):
        mgr = self._manager_with_paper()
        mgr.unload_adapter("paper")
        assert not mgr.has_adapter("paper")

    def test_get_missing_raises(self):
        from iios.execution.brokers.broker_manager import BrokerManager
        from iios.execution.brokers.broker_exceptions import BrokerNotFoundError
        mgr = BrokerManager()
        with pytest.raises(BrokerNotFoundError):
            mgr.get_adapter("ghost")

    def test_statistics_recorded(self):
        from iios.execution.brokers.core.broker_request import BrokerRequest
        mgr = self._manager_with_paper()
        run_async(mgr.connect("paper"))
        run_async(mgr.fetch_balance("paper", BrokerRequest()))
        stats = mgr.get_statistics("paper")
        assert stats is not None
        assert stats.requests_total >= 1

    def test_list_broker_ids(self):
        mgr = self._manager_with_paper()
        ids = mgr.list_broker_ids()
        assert "paper" in ids

    def test_singleton(self):
        from iios.execution.brokers.broker_manager import get_broker_manager, reset_broker_manager
        reset_broker_manager()
        m1 = get_broker_manager()
        m2 = get_broker_manager()
        assert m1 is m2

    def test_summary(self):
        mgr = self._manager_with_paper()
        s   = mgr.summary()
        assert s["broker_count"] == 1


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 11: BrokerContext
# ════════════════════════════════════════════════════════════════════════════════

class TestBrokerContext:
    def test_set_and_get(self):
        from iios.execution.brokers.broker_context import BrokerContextState
        BrokerContextState.set("dhan", "place_order")
        assert BrokerContextState.get_broker_id() == "dhan"
        assert BrokerContextState.get_operation() == "place_order"
        BrokerContextState.clear()

    def test_context_manager(self):
        from iios.execution.brokers.broker_context import broker_operation_context, BrokerContextState
        with broker_operation_context("paper", "health_check"):
            assert BrokerContextState.get_broker_id() == "paper"
        assert BrokerContextState.get_broker_id() == ""

    def test_elapsed_ms(self):
        from iios.execution.brokers.broker_context import BrokerContextState
        BrokerContextState.set("x", "op")
        time.sleep(0.01)
        assert BrokerContextState.get_elapsed_ms() > 0
        BrokerContextState.clear()

    def test_snapshot(self):
        from iios.execution.brokers.broker_context import BrokerContextState
        BrokerContextState.set("z", "test_op")
        snap = BrokerContextState.snapshot()
        assert snap["broker_id"] == "z"
        assert snap["operation"] == "test_op"
        BrokerContextState.clear()


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 12: Models
# ════════════════════════════════════════════════════════════════════════════════

class TestBrokerMetadata:
    def test_creation(self):
        from iios.execution.brokers.models.broker_metadata import BrokerMetadata
        from iios.execution.brokers.broker_constants import BrokerEnvironment, BrokerCapabilityType
        m = BrokerMetadata(
            broker_id="dhan",
            name="Dhan",
            vendor="Dhan HQ",
            environment=BrokerEnvironment.LIVE,
            capabilities=[BrokerCapabilityType.CASH_EQUITY],
        )
        assert m.broker_id == "dhan"
        assert m.is_active is True

    def test_to_dict(self):
        from iios.execution.brokers.models.broker_metadata import BrokerMetadata
        m = BrokerMetadata(broker_id="x")
        d = m.to_dict()
        assert d["broker_id"] == "x"
        assert "metadata_id" in d


class TestBrokerStatistics:
    def test_record_request(self):
        from iios.execution.brokers.models.broker_statistics import BrokerStatistics
        s = BrokerStatistics(broker_id="paper")
        s.record_request(True, 5.0)
        s.record_request(False, 10.0)
        assert s.requests_total   == 2
        assert s.requests_ok      == 1
        assert s.requests_failed  == 1
        assert s.success_rate()   == 0.5
        assert s.avg_latency_ms() == 7.5

    def test_to_dict(self):
        from iios.execution.brokers.models.broker_statistics import BrokerStatistics
        s = BrokerStatistics(broker_id="dhan")
        s.record_connect()
        d = s.to_dict()
        assert d["connect_count"] == 1


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 13: Package imports
# ════════════════════════════════════════════════════════════════════════════════

class TestPackageImports:
    def test_top_level_import(self):
        import iios.execution.brokers as brokers
        assert hasattr(brokers, "BaseBrokerAdapter")
        assert hasattr(brokers, "BrokerManager")
        assert hasattr(brokers, "BrokerRequest")
        assert hasattr(brokers, "BrokerResponse")

    def test_adapters_import(self):
        from iios.execution.brokers.adapters import (
            PaperBrokerAdapter,
            DhanAdapter,
            ZerodhaAdapter,
            AlpacaAdapter,
            BinanceAdapter,
        )
        assert PaperBrokerAdapter is not None

    def test_core_import(self):
        from iios.execution.brokers.core import (
            BaseBrokerAdapter,
            BrokerCapabilitySet,
            BrokerConnection,
            BrokerRequest,
            BrokerResponse,
            BrokerSession,
        )

    def test_auth_import(self):
        from iios.execution.brokers.authentication import (
            AuthenticationManager,
            CredentialProvider,
            TokenManager,
        )

    def test_connection_import(self):
        from iios.execution.brokers.connection import (
            CircuitBreaker,
            ConnectionHealth,
            ConnectionPool,
            RetryManager,
        )


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 14: Concurrency
# ════════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_registry_thread_safety(self):
        from iios.execution.brokers.broker_registry import BrokerRegistry
        from iios.execution.brokers.adapters.paper_broker_adapter import (
            PaperBrokerAdapter,
            BrokerAdapterConfig,
            BrokerEnvironment,
            AuthMethod,
        )
        reg    = BrokerRegistry(max_brokers=500)
        errors = []

        def _register(i):
            try:
                from iios.execution.brokers.core.base_broker_adapter import BrokerAdapterConfig
                cfg = BrokerAdapterConfig(
                    broker_id=f"paper_{i}",
                    environment=BrokerEnvironment.PAPER,
                    auth_method=AuthMethod.NONE,
                )
                adapter = PaperBrokerAdapter(cfg)
                adapter._broker_id = f"paper_{i}"
                reg.register(adapter, overwrite=True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_register, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_connection_pool_thread_safety(self):
        from iios.execution.brokers.connection.connection_pool import ConnectionPool
        pool   = ConnectionPool(max_connections=500)
        errors = []

        def _acquire(i):
            try:
                pool.acquire(f"broker_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_acquire, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_token_manager_concurrent_access(self):
        from iios.execution.brokers.authentication.token_manager import TokenInfo, TokenManager
        mgr    = TokenManager()
        errors = []

        def _store(i):
            try:
                mgr.store(TokenInfo(
                    broker_id=f"b{i}",
                    access_token="t",
                    expires_at=time.time() + 3600,
                ))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_store, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 15: BrokerFactory top-level
# ════════════════════════════════════════════════════════════════════════════════

class TestBrokerFactory:
    def test_register_and_create(self):
        from iios.execution.brokers.broker_factory import BrokerFactory
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        factory = BrokerFactory()
        factory.register_class("paper", PaperBrokerAdapter)
        adapter = factory.create("paper")
        assert isinstance(adapter, PaperBrokerAdapter)

    def test_create_missing_raises(self):
        from iios.execution.brokers.broker_factory import BrokerFactory
        from iios.execution.brokers.broker_exceptions import AdapterLoadFailedError
        factory = BrokerFactory()
        with pytest.raises(AdapterLoadFailedError):
            factory.create("ghost")

    def test_has(self):
        from iios.execution.brokers.broker_factory import BrokerFactory
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        factory = BrokerFactory()
        assert not factory.has("paper")
        factory.register_class("paper", PaperBrokerAdapter)
        assert factory.has("paper")

    def test_registered_ids(self):
        from iios.execution.brokers.broker_factory import BrokerFactory
        from iios.execution.brokers.adapters.paper_broker_adapter import PaperBrokerAdapter
        factory = BrokerFactory()
        factory.register_class("p1", PaperBrokerAdapter)
        factory.register_class("p2", PaperBrokerAdapter)
        ids = factory.registered_broker_ids()
        assert "p1" in ids
        assert "p2" in ids
