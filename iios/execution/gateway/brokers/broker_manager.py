"""iios/execution/gateway/brokers/broker_manager.py
==================================================
BrokerManager — LifecycleAwareMixin orchestrator for the IIOS
Broker Abstraction Layer.

Coordinates:
  BrokerRegistry          — broker storage and lookup
  ConnectionPool (per broker)  — connection state tracking
  BrokerSessionManager    — authentication session tracking
  BrokerHealthMonitor     — health record storage
  BrokerStatisticsStore   — per-broker statistics
  BrokerHistory           — event and response history
  BrokerValidator         — validation
  BrokerFactory           — object construction

Non-responsibilities
  No broker SDK.
  No REST implementation.
  No WebSocket implementation.
  No routing algorithms.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .broker_capabilities import BrokerCapabilities
from .broker_configuration import BrokerConfiguration
from .broker_connection import BrokerConnection, ConnectionPool
from .broker_events import (
    BrokerEvent,
    make_authentication_failed_event,
    make_authentication_succeeded_event,
    make_broker_connected_event,
    make_broker_disconnected_event,
    make_broker_registered_event,
    make_health_changed_event,
    make_reconnect_started_event,
    make_reconnect_succeeded_event,
    make_session_expired_event,
)
from .broker_factory import BrokerFactory
from .broker_health import BrokerHealthMonitor, BrokerHealthRecord
from .broker_history import BrokerHistory
from .broker_interface import BrokerInterface
from .broker_registry import BrokerRegistry
from .broker_request import (
    CancelOrderRequest,
    FundsRequest,
    MarginRequest,
    ModifyOrderRequest,
    OrderRequest,
    PositionRequest,
    StatusRequest,
)
from .broker_response import BrokerResponse
from .broker_session import BrokerSessionManager
from .broker_statistics import BrokerStatistics, BrokerStatisticsStore
from .broker_validation import BrokerValidator
from .constants import (
    ACTOR_BROKER_MANAGER,
    BROKER_MANAGER_SYSTEM_ID,
    DEFAULT_MAX_BROKERS,
    DEFAULT_MAX_HISTORY,
    BrokerCapability,
    BrokerStatus,
    VERSION,
)
from .exceptions import (
    BrokerAuthenticationError,
    BrokerManagerNotRunningError,
    BrokerNotConnectedError,
    BrokerNotRegisteredError,
    BrokerValidationError,
)

_log   = get_logger(__name__, engine_id=BROKER_MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=BROKER_MANAGER_SYSTEM_ID)


class BrokerManager(LifecycleAwareMixin):
    """
    LifecycleAwareMixin orchestrator for the Broker Abstraction Layer.

    Usage
    -----
    manager = BrokerManager()
    manager.start()

    manager.register_broker(my_broker, config, caps)
    resp = manager.connect("my-broker-id")
    resp = manager.authenticate("my-broker-id")
    resp = manager.place_order("my-broker-id", order_request)

    manager.stop()
    """

    def __init__(
        self,
        max_brokers: int = DEFAULT_MAX_BROKERS,
        max_history: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._max_brokers = max(1, max_brokers)

        # ── Sub-components ────────────────────────────────────────────────────
        self._registry   = BrokerRegistry(max_brokers=max_brokers)
        self._sessions   = BrokerSessionManager()
        self._health     = BrokerHealthMonitor()
        self._stats      = BrokerStatisticsStore()
        self._history    = BrokerFactory.create_history(max_size=max_history)
        self._validator  = BrokerValidator()
        self._pools:     Dict[str, ConnectionPool] = {}

        # ── Event listeners ───────────────────────────────────────────────────
        self._listeners: List[Callable[[BrokerEvent], None]] = []
        self._listener_lock = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise BrokerManagerNotRunningError()

    def _on_start(self) -> None:
        self._registry.start()
        _audit.log_lifecycle_event(
            BROKER_MANAGER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("BrokerManager started.", version=VERSION)

    def _on_stop(self) -> None:
        # Gracefully disconnect all brokers
        for broker_id in list(self._pools.keys()):
            try:
                self._pools[broker_id].stop_all()
            except Exception:
                pass

        self._sessions.clear()
        self._registry.stop()
        _audit.log_lifecycle_event(
            BROKER_MANAGER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info(
            "BrokerManager stopped.",
            registered_brokers=self._registry.count,
        )

    # ── Registration ─────────────────────────────────────────────────────────

    def register_broker(
        self,
        broker: BrokerInterface,
        config: BrokerConfiguration,
        *,
        capabilities: Optional[BrokerCapabilities] = None,
    ) -> None:
        """
        Register a broker with the manager.

        Validates the broker against BrokerInterface before registration.
        Creates a ConnectionPool and BrokerSession for the broker.

        Parameters
        ----------
        broker:
            Fully implemented BrokerInterface instance.
        config:
            BrokerConfiguration for this broker.
        capabilities:
            Optional explicit capability set.  When None, calls
            ``broker.capabilities()`` to discover them.
        """
        self._assert_running()

        # Validate
        existing_ids = self._registry.all_broker_ids()
        validation   = self._validator.validate_registration(
            broker, existing_ids, self._max_brokers
        )
        self._validator.raise_if_invalid(validation, context="register_broker")

        cfg_validation = self._validator.validate_configuration(config)
        self._validator.raise_if_invalid(cfg_validation, context="validate_configuration")

        # Resolve capabilities
        caps = capabilities or broker.capabilities()

        # Register
        self._registry.register(broker, config, caps)

        # Create connection pool
        pool = BrokerFactory.create_connection_pool(broker.broker_id)
        pool.add("default")
        self._pools[broker.broker_id] = pool

        # Create session
        self._sessions.create_session(broker.broker_id)

        # Initialise statistics
        self._stats.get_or_create(broker.broker_id)

        # Fire event
        event = make_broker_registered_event(broker.broker_id)
        self._history.append_event(event)
        self._fire_event(event)

        _log.info(
            "Broker registered.",
            broker_id=broker.broker_id,
            broker_name=broker.broker_name,
            environment=config.environment,
        )

    def remove_broker(self, broker_id: str) -> None:
        """
        Remove a registered broker.

        Marks all connections as stopped and removes session state.
        """
        self._assert_running()

        pool = self._pools.get(broker_id)
        if pool:
            pool.stop_all()
            del self._pools[broker_id]

        self._sessions.remove_session(broker_id)
        self._health.remove(broker_id)
        self._registry.remove(broker_id)

        _log.info("Broker removed.", broker_id=broker_id)

    # ── Connection lifecycle ──────────────────────────────────────────────────

    def connect(self, broker_id: str) -> BrokerResponse:
        """
        Connect a registered broker.

        Calls broker.connect(), updates connection state, fires
        BROKER_CONNECTED event, and records statistics.
        """
        self._assert_running()
        broker = self._registry.get(broker_id)
        pool   = self._get_pool(broker_id)
        conn   = pool.get("default")
        stats  = self._stats.get_or_create(broker_id)

        conn.set_connecting()
        start_ms = time.time()
        stats.record_request()

        try:
            response = broker.connect()
        except Exception as exc:
            conn.set_failed()
            response = BrokerFactory.failure_response(
                request_id="connect",
                broker_id=broker_id,
                error_code="CONNECTION_EXCEPTION",
                error_message=str(exc),
            )

        elapsed_ms = (time.time() - start_ms) * 1_000.0
        stats.record_response(elapsed_ms)

        if response.is_success:
            conn.set_connected()
            event = make_broker_connected_event(broker_id)
            self._history.append_event(event)
            self._fire_event(event)
            _log.info("Broker connected.", broker_id=broker_id, elapsed_ms=elapsed_ms)
        else:
            conn.set_disconnected()
            stats.record_failure()
            _log.warning(
                "Broker connect failed.",
                broker_id=broker_id,
                error=response.error_message,
            )

        self._history.append_response(response)
        return response

    def disconnect(self, broker_id: str) -> BrokerResponse:
        """
        Disconnect a registered broker.

        Calls broker.disconnect(), marks connection DISCONNECTED,
        clears session, fires BROKER_DISCONNECTED event.
        """
        self._assert_running()
        broker = self._registry.get(broker_id)
        pool   = self._get_pool(broker_id)
        conn   = pool.get("default")
        stats  = self._stats.get_or_create(broker_id)

        stats.record_request()
        start_ms = time.time()

        try:
            response = broker.disconnect()
        except Exception as exc:
            response = BrokerFactory.failure_response(
                request_id="disconnect",
                broker_id=broker_id,
                error_code="DISCONNECT_EXCEPTION",
                error_message=str(exc),
            )

        elapsed_ms = (time.time() - start_ms) * 1_000.0
        stats.record_response(elapsed_ms)
        conn.set_disconnected()

        session = self._sessions.get_session_optional(broker_id)
        if session:
            session.mark_disconnected()

        event = make_broker_disconnected_event(broker_id)
        self._history.append_event(event)
        self._fire_event(event)
        self._history.append_response(response)

        _log.info("Broker disconnected.", broker_id=broker_id)
        return response

    def authenticate(self, broker_id: str) -> BrokerResponse:
        """
        Authenticate a connected broker.

        Calls broker.authenticate(), updates session state, fires
        AUTHENTICATION_SUCCEEDED or AUTHENTICATION_FAILED event.
        """
        self._assert_running()
        broker  = self._registry.get(broker_id)
        config  = self._registry.get_config(broker_id)
        stats   = self._stats.get_or_create(broker_id)
        session = self._sessions.get_session(broker_id)

        stats.record_request()
        stats.record_authentication()
        start_ms = time.time()

        try:
            response = broker.authenticate()
        except Exception as exc:
            response = BrokerFactory.failure_response(
                request_id="authenticate",
                broker_id=broker_id,
                error_code="AUTH_EXCEPTION",
                error_message=str(exc),
            )

        elapsed_ms = (time.time() - start_ms) * 1_000.0
        stats.record_response(elapsed_ms)

        if response.is_success:
            session.mark_authenticated(timeout_secs=config.session_timeout_secs)
            event = make_authentication_succeeded_event(broker_id)
            self._history.append_event(event)
            self._fire_event(event)
            _log.info("Broker authenticated.", broker_id=broker_id)
        else:
            stats.record_failure()
            event = make_authentication_failed_event(
                broker_id,
                metadata={"error": response.error_message},
            )
            self._history.append_event(event)
            self._fire_event(event)
            _log.warning(
                "Broker authentication failed.",
                broker_id=broker_id,
                error=response.error_message,
            )

        self._history.append_response(response)
        return response

    def refresh_session(self, broker_id: str) -> BrokerResponse:
        """
        Refresh an expiring session.

        Calls broker.refresh_session() and extends session expiry on success.
        """
        self._assert_running()
        broker  = self._registry.get(broker_id)
        config  = self._registry.get_config(broker_id)
        session = self._sessions.get_session(broker_id)
        stats   = self._stats.get_or_create(broker_id)

        stats.record_request()
        start_ms = time.time()

        try:
            response = broker.refresh_session()
        except Exception as exc:
            response = BrokerFactory.failure_response(
                request_id="refresh_session",
                broker_id=broker_id,
                error_code="REFRESH_EXCEPTION",
                error_message=str(exc),
            )

        elapsed_ms = (time.time() - start_ms) * 1_000.0
        stats.record_response(elapsed_ms)

        if response.is_success:
            session.refresh(timeout_secs=config.session_timeout_secs)
            _log.info("Session refreshed.", broker_id=broker_id)
        else:
            stats.record_failure()
            _log.warning(
                "Session refresh failed.",
                broker_id=broker_id,
                error=response.error_message,
            )

        self._history.append_response(response)
        return response

    def signal_reconnect_started(self, broker_id: str) -> None:
        """Signal that a reconnection attempt has started."""
        self._assert_running()
        pool = self._get_pool(broker_id)
        conn = pool.get("default")
        conn.set_reconnecting()
        stats = self._stats.get_or_create(broker_id)
        stats.record_reconnect()
        event = make_reconnect_started_event(broker_id)
        self._history.append_event(event)
        self._fire_event(event)

    def signal_reconnect_succeeded(self, broker_id: str) -> None:
        """Signal that a reconnection attempt succeeded."""
        self._assert_running()
        pool = self._get_pool(broker_id)
        conn = pool.get("default")
        conn.set_connected()
        event = make_reconnect_succeeded_event(broker_id)
        self._history.append_event(event)
        self._fire_event(event)

    # ── Health ────────────────────────────────────────────────────────────────

    def check_health(self, broker_id: str) -> BrokerHealthRecord:
        """
        Perform a health check on a registered broker.

        Calls broker.health(), stores the result, fires
        BROKER_HEALTH_CHANGED if the health status changed.
        """
        self._assert_running()
        broker  = self._registry.get(broker_id)
        stats   = self._stats.get_or_create(broker_id)

        prev_record = self._health.get_health(broker_id)
        prev_healthy = prev_record.is_healthy if prev_record else None

        start_ms = time.time()
        try:
            record = broker.health()
        except Exception as exc:
            from .broker_health import make_health_record
            record = make_health_record(
                broker_id=broker_id,
                is_healthy=False,
                error_message=str(exc),
            )

        elapsed_ms = (time.time() - start_ms) * 1_000.0
        self._health.record_health(record)

        if prev_healthy is None or record.is_healthy != prev_healthy:
            event = make_health_changed_event(broker_id, is_healthy=record.is_healthy)
            self._history.append_event(event)
            self._fire_event(event)

        if not record.is_healthy:
            stats.record_failure()

        return record

    # ── Order management ──────────────────────────────────────────────────────

    def place_order(
        self, broker_id: str, request: OrderRequest
    ) -> BrokerResponse:
        """Submit an order to the broker."""
        return self._delegate(broker_id, lambda b: b.place_order(request))

    def modify_order(
        self, broker_id: str, request: ModifyOrderRequest
    ) -> BrokerResponse:
        """Modify a pending order."""
        return self._delegate(broker_id, lambda b: b.modify_order(request))

    def cancel_order(
        self, broker_id: str, request: CancelOrderRequest
    ) -> BrokerResponse:
        """Cancel a pending order."""
        return self._delegate(broker_id, lambda b: b.cancel_order(request))

    def get_order(self, broker_id: str, order_id: str) -> BrokerResponse:
        """Retrieve a single order."""
        return self._delegate(broker_id, lambda b: b.get_order(order_id))

    def get_orders(self, broker_id: str) -> BrokerResponse:
        """Retrieve all orders for the session."""
        return self._delegate(broker_id, lambda b: b.get_orders())

    def get_positions(self, broker_id: str) -> BrokerResponse:
        """Retrieve open positions."""
        return self._delegate(broker_id, lambda b: b.get_positions())

    def get_holdings(self, broker_id: str) -> BrokerResponse:
        """Retrieve long-term holdings."""
        return self._delegate(broker_id, lambda b: b.get_holdings())

    def get_funds(self, broker_id: str) -> BrokerResponse:
        """Retrieve available funds."""
        return self._delegate(broker_id, lambda b: b.get_funds())

    def get_margin(self, broker_id: str) -> BrokerResponse:
        """Retrieve margin information."""
        return self._delegate(broker_id, lambda b: b.get_margin())

    def ping(self, broker_id: str) -> bool:
        """Ping the broker.  Returns True on success."""
        self._assert_running()
        broker = self._registry.get(broker_id)
        try:
            return broker.ping()
        except Exception:
            return False

    # ── Lookup / enumeration ──────────────────────────────────────────────────

    def get_broker(self, broker_id: str) -> BrokerInterface:
        """Return the registered broker.  Raises BrokerNotRegisteredError if absent."""
        return self._registry.get(broker_id)

    def default_broker(self) -> Optional[BrokerInterface]:
        """Return the default broker, or None if no brokers are registered."""
        return self._registry.default()

    def default_broker_id(self) -> Optional[str]:
        return self._registry.default_id()

    def set_default_broker(self, broker_id: str) -> None:
        self._assert_running()
        self._registry.set_default(broker_id)

    def all_brokers(self) -> List[BrokerInterface]:
        return self._registry.all_brokers()

    def all_broker_ids(self) -> List[str]:
        return self._registry.all_broker_ids()

    def find_by_capability(self, capability: BrokerCapability) -> List[BrokerInterface]:
        return self._registry.find_by_capability(capability)

    def broker_count(self) -> int:
        return self._registry.count

    # ── Session / health / stats / events ─────────────────────────────────────

    def expire_stale_sessions(self) -> int:
        """Expire stale sessions.  Returns the count of sessions expired."""
        count = self._sessions.expire_stale_sessions()
        for session in self._sessions.all_sessions():
            if session.is_expired:
                stats = self._stats.get_or_create(session.broker_id)
                stats.record_session_expiry()
                event = make_session_expired_event(session.broker_id)
                self._history.append_event(event)
                self._fire_event(event)
        return count

    def is_connected(self, broker_id: str) -> bool:
        pool = self._pools.get(broker_id)
        return pool is not None and pool.is_any_ready()

    def is_authenticated(self, broker_id: str) -> bool:
        return self._sessions.is_authenticated(broker_id)

    def get_health(self, broker_id: str) -> Optional[BrokerHealthRecord]:
        return self._health.get_health(broker_id)

    def unhealthy_brokers(self) -> List[str]:
        return self._health.unhealthy_brokers()

    def statistics(self, broker_id: str) -> Optional[BrokerStatistics]:
        return self._stats.get_snapshot(broker_id)

    def all_statistics(self) -> Dict[str, BrokerStatistics]:
        return self._stats.all()

    def history(self) -> BrokerHistory:
        """Return the shared history store (read-only use expected)."""
        return self._history

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[BrokerEvent], None]
    ) -> None:
        with self._listener_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[BrokerEvent], None]
    ) -> None:
        with self._listener_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    def _fire_event(self, event: BrokerEvent) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(
                    "Event listener raised an exception.",
                    listener=repr(listener),
                    error=str(exc),
                )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_pool(self, broker_id: str) -> ConnectionPool:
        pool = self._pools.get(broker_id)
        if pool is None:
            raise BrokerNotRegisteredError(broker_id)
        return pool

    def _delegate(
        self,
        broker_id: str,
        fn: Callable[[BrokerInterface], BrokerResponse],
    ) -> BrokerResponse:
        """
        Execute a broker operation, recording request and response statistics.
        """
        self._assert_running()
        broker = self._registry.get(broker_id)
        stats  = self._stats.get_or_create(broker_id)

        stats.record_request()
        start_ms = time.time()

        try:
            response = fn(broker)
        except Exception as exc:
            elapsed_ms = (time.time() - start_ms) * 1_000.0
            response = BrokerFactory.failure_response(
                request_id="unknown",
                broker_id=broker_id,
                error_code="DELEGATE_EXCEPTION",
                error_message=str(exc),
                elapsed_ms=elapsed_ms,
            )

        elapsed_ms = (time.time() - start_ms) * 1_000.0
        stats.record_response(elapsed_ms)

        if not response.is_success:
            stats.record_failure()

        self._history.append_response(response)
        return response
