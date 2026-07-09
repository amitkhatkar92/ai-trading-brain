"""iios/execution/brokers/core/base_broker_adapter.py

Abstract base that every broker adapter must subclass.  No broker-specific
logic lives here — only the uniform interface contract.
"""
from __future__ import annotations

import abc
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from iios.execution.brokers.broker_constants import (
    AuthMethod,
    BrokerCapabilityType,
    BrokerEnvironment,
    BrokerStatus,
    ConnectionStatus,
    DEFAULT_REQUEST_TIMEOUT_SEC,
)
from iios.execution.brokers.core.broker_capability import (
    BrokerCapability,
    BrokerCapabilitySet,
)
from iios.execution.brokers.core.broker_connection import BrokerConnection
from iios.execution.brokers.core.broker_request import BrokerRequest
from iios.execution.brokers.core.broker_response import BrokerResponse
from iios.execution.brokers.core.broker_session import BrokerSession

logger = logging.getLogger(__name__)


# ── Adapter configuration ─────────────────────────────────────────────────────

@dataclass
class BrokerAdapterConfig:
    """Immutable configuration injected at adapter construction time."""

    broker_id:           str                          = ""
    broker_name:         str                          = ""
    vendor:              str                          = ""
    version:             str                          = "1.0.0"
    environment:         BrokerEnvironment            = BrokerEnvironment.PAPER
    auth_method:         AuthMethod                   = AuthMethod.API_KEY
    base_url:            str                          = ""
    ws_url:              str                          = ""
    supported_capabilities: list[BrokerCapabilityType] = field(default_factory=list)
    request_timeout_sec: float                        = DEFAULT_REQUEST_TIMEOUT_SEC
    max_retries:         int                          = 3
    metadata:            dict[str, Any]               = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":    self.broker_id,
            "broker_name":  self.broker_name,
            "vendor":       self.vendor,
            "version":      self.version,
            "environment":  self.environment.value,
            "auth_method":  self.auth_method.value,
            "base_url":     self.base_url,
            "ws_url":       self.ws_url,
            "supported_capabilities": [c.value for c in self.supported_capabilities],
            "request_timeout_sec":    self.request_timeout_sec,
            "max_retries":  self.max_retries,
            "metadata":     self.metadata,
        }


# ── Abstract base ─────────────────────────────────────────────────────────────

class BaseBrokerAdapter(abc.ABC):
    """
    Contract that every broker adapter must honour.

    Concrete subclasses implement all abstract methods.
    The framework only ever calls methods on this interface — never on
    broker-specific subclasses directly.
    """

    def __init__(self, config: BrokerAdapterConfig) -> None:
        self._config     = config
        self._broker_id  = config.broker_id
        self._status     = BrokerStatus.INACTIVE
        self._session:    BrokerSession  | None = None
        self._connection: BrokerConnection | None = None
        self._capabilities = BrokerCapabilitySet(
            [BrokerCapability(ct) for ct in config.supported_capabilities]
        )
        self._lock            = threading.RLock()
        self._request_count   = 0
        self._success_count   = 0
        self._failure_count   = 0
        self._total_latency   = 0.0
        self._initialized_at  = time.time()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def broker_id(self) -> str:
        return self._broker_id

    @property
    def config(self) -> BrokerAdapterConfig:
        return self._config

    @property
    def status(self) -> BrokerStatus:
        with self._lock:
            return self._status

    @property
    def capabilities(self) -> BrokerCapabilitySet:
        return self._capabilities

    @property
    def session(self) -> BrokerSession | None:
        with self._lock:
            return self._session

    @property
    def connection(self) -> BrokerConnection | None:
        with self._lock:
            return self._connection

    def supports(self, capability_type: BrokerCapabilityType) -> bool:
        return self._capabilities.supports(capability_type)

    def is_connected(self) -> bool:
        conn = self._connection
        return conn is not None and conn.is_connected()

    def is_authenticated(self) -> bool:
        sess = self._session
        return sess is not None and sess.is_valid()

    # ── Abstract interface — connection ───────────────────────────────────────

    @abc.abstractmethod
    async def connect(self) -> BrokerResponse:
        """Establish the transport-layer connection."""

    @abc.abstractmethod
    async def disconnect(self) -> BrokerResponse:
        """Gracefully close the transport-layer connection."""

    @abc.abstractmethod
    async def authenticate(self, credentials: dict[str, Any]) -> BrokerResponse:
        """Authenticate with the broker using the supplied credentials."""

    # ── Abstract interface — order management ─────────────────────────────────

    @abc.abstractmethod
    async def place_order(self, request: BrokerRequest) -> BrokerResponse:
        """Submit a new order."""

    @abc.abstractmethod
    async def modify_order(self, request: BrokerRequest) -> BrokerResponse:
        """Modify an open order."""

    @abc.abstractmethod
    async def cancel_order(self, request: BrokerRequest) -> BrokerResponse:
        """Cancel an open order."""

    @abc.abstractmethod
    async def fetch_order(self, request: BrokerRequest) -> BrokerResponse:
        """Fetch details for a single order by order_id."""

    @abc.abstractmethod
    async def fetch_orders(self, request: BrokerRequest) -> BrokerResponse:
        """Fetch all orders (optionally filtered)."""

    # ── Abstract interface — portfolio ────────────────────────────────────────

    @abc.abstractmethod
    async def fetch_positions(self, request: BrokerRequest) -> BrokerResponse:
        """Fetch current intraday positions."""

    @abc.abstractmethod
    async def fetch_holdings(self, request: BrokerRequest) -> BrokerResponse:
        """Fetch long-term holdings."""

    @abc.abstractmethod
    async def fetch_balance(self, request: BrokerRequest) -> BrokerResponse:
        """Fetch available cash balance."""

    @abc.abstractmethod
    async def fetch_margin(self, request: BrokerRequest) -> BrokerResponse:
        """Fetch margin / buying-power details."""

    @abc.abstractmethod
    async def fetch_trades(self, request: BrokerRequest) -> BrokerResponse:
        """Fetch executed trade history."""

    # ── Abstract interface — streaming ────────────────────────────────────────

    @abc.abstractmethod
    async def stream_market_data(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        """Yield real-time market-data ticks."""

    @abc.abstractmethod
    async def stream_order_updates(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        """Yield real-time order-status updates."""

    @abc.abstractmethod
    async def stream_positions(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        """Yield real-time position updates."""

    # ── Abstract interface — diagnostics ──────────────────────────────────────

    @abc.abstractmethod
    async def health_check(self) -> BrokerResponse:
        """Return a health snapshot for the broker connection."""

    # ── Concrete helpers ──────────────────────────────────────────────────────

    def _record_request(self, success: bool, latency_ms: float = 0.0) -> None:
        with self._lock:
            self._request_count += 1
            self._total_latency += latency_ms
            if success:
                self._success_count += 1
            else:
                self._failure_count += 1

    def _set_status(self, new_status: BrokerStatus) -> None:
        with self._lock:
            old = self._status
            self._status = new_status
            logger.debug(
                "Broker %s status: %s → %s",
                self._broker_id, old.value, new_status.value,
            )

    def _new_connection(self) -> BrokerConnection:
        return BrokerConnection(
            broker_id = self._broker_id,
            host      = self._config.base_url,
            is_ssl    = self._config.base_url.startswith("https"),
        )

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            avg_lat = (
                self._total_latency / self._request_count
                if self._request_count else 0.0
            )
            return {
                "broker_id":      self._broker_id,
                "request_count":  self._request_count,
                "success_count":  self._success_count,
                "failure_count":  self._failure_count,
                "avg_latency_ms": round(avg_lat, 3),
                "uptime_sec":     round(time.time() - self._initialized_at, 1),
            }

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":    self._broker_id,
            "status":       self._status.value,
            "environment":  self._config.environment.value,
            "version":      self._config.version,
            "vendor":       self._config.vendor,
            "capabilities": self._capabilities.to_dict(),
            "statistics":   self.statistics(),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"broker_id={self._broker_id!r}, "
            f"status={self._status.value!r})"
        )
