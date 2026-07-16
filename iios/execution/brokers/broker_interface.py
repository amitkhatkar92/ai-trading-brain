"""iios/execution/brokers/broker_interface.py
==================================================
AbstractBrokerInterface — the canonical protocol every broker adapter
MUST satisfy.

This file defines WHAT a broker must be able to do.
No implementation belongs here.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

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
    PositionResponse,
)
from iios.execution.brokers.broker_metadata import BrokerMetadata
from iios.execution.brokers.broker_capabilities import BrokerCapabilities
from iios.execution.brokers.constants import BrokerConnectionState, BrokerHealthStatus


class AbstractBrokerInterface(ABC):
    """
    Abstract base class that all broker adapters must implement.

    Rules
    -----
    - Implementations must be concrete classes (no partial implementation).
    - All methods are synchronous at this abstraction level.
    - No authentication, credentials, or API keys at this level.
    - Return types are always the matching response dataclass.
    - Raise BrokerAbstractionError (or a subclass) on failures.
    """

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def broker_id(self) -> str:
        """Unique, immutable identifier for this broker adapter."""

    @property
    @abstractmethod
    def metadata(self) -> BrokerMetadata:
        """Static description of this broker's capabilities and identity."""

    @property
    @abstractmethod
    def capabilities(self) -> BrokerCapabilities:
        """Live capability set (may depend on current connection state)."""

    # ── Connection lifecycle ───────────────────────────────────────────────────

    @abstractmethod
    def connect(self, request: ConnectionRequest) -> ConnectionResponse:
        """
        Establish a connection to the broker.

        Must transition connection_state to CONNECTED on success.
        """

    @abstractmethod
    def disconnect(self, request: ConnectionRequest) -> ConnectionResponse:
        """
        Gracefully terminate the broker connection.

        Must transition connection_state to DISCONNECTED on success.
        """

    @property
    @abstractmethod
    def connection_state(self) -> BrokerConnectionState:
        """Current connection state of this adapter."""

    @property
    def is_connected(self) -> bool:
        """Convenience: True when connection_state is CONNECTED."""
        return self.connection_state == BrokerConnectionState.CONNECTED

    # ── Health ─────────────────────────────────────────────────────────────────

    @abstractmethod
    def health(self, request: BrokerRequest) -> HealthResponse:
        """Return the current health status of this adapter."""

    @abstractmethod
    def heartbeat(self, request: HeartbeatRequest) -> BrokerResponse:
        """Send a lightweight liveness probe to the broker."""

    # ── Order operations ───────────────────────────────────────────────────────

    @abstractmethod
    def submit_order(self, request: OrderRequest) -> OrderResponse:
        """Submit a new order to the broker."""

    @abstractmethod
    def modify_order(self, request: ModifyRequest) -> ModifyResponse:
        """Modify an existing order's quantity, price, or trigger."""

    @abstractmethod
    def cancel_order(self, request: CancelRequest) -> CancelResponse:
        """Cancel an existing order."""

    @abstractmethod
    def order_status(self, request: OrderRequest) -> OrderResponse:
        """Fetch the current status of an order."""

    # ── Account queries ────────────────────────────────────────────────────────

    @abstractmethod
    def positions(self, request: PositionRequest) -> PositionResponse:
        """Fetch currently open positions."""

    @abstractmethod
    def holdings(self, request: PositionRequest) -> PositionResponse:
        """Fetch long-term holdings (e.g. CNC delivery positions)."""

    @abstractmethod
    def balances(self, request: BalanceRequest) -> BalanceResponse:
        """Fetch account cash and margin balances."""

    @abstractmethod
    def margin(self, request: BalanceRequest) -> BalanceResponse:
        """Fetch margin-specific balance details."""

    # ── Serialisation ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "broker_id":       self.broker_id,
            "connection_state": self.connection_state.value,
            "is_connected":    self.is_connected,
            "metadata":        self.metadata.to_dict(),
        }
