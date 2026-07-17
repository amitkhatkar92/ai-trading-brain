"""iios/execution/gateway/brokers/broker_interface.py
==================================================
BrokerInterface — abstract base class every broker implementation
must satisfy.

No broker SDK, REST client, or WebSocket implementation lives here.
This file defines the contract only.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .constants import BrokerStatus

if TYPE_CHECKING:
    from .broker_capabilities import BrokerCapabilities
    from .broker_health import BrokerHealthRecord
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


class BrokerInterface(ABC):
    """
    Abstract interface for every broker plugin.

    Rules
    -----
    * Every broker implementation MUST subclass BrokerInterface.
    * No IIOS module may bypass this interface and call broker APIs
      directly.
    * Implementations may not be instantiated unless all abstract
      methods are implemented (enforced by Python's ABC mechanism).

    Lifecycle contract
    ------------------
    A broker transitions through the following states:

        connect() → authenticate() → place_order() / get_positions() / …
                                   → disconnect()

    The manager drives these transitions; the broker implementation
    only executes the underlying I/O.
    """

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def broker_id(self) -> str:
        """Unique identifier for this broker instance."""

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Human-readable name, e.g. ``"Dhan"``, ``"Zerodha"``."""

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """True when the broker is in a ready state (CONNECTED, ACTIVE, or DEGRADED)."""

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """True when a valid authentication session exists."""

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @abstractmethod
    def connect(self) -> BrokerResponse:
        """
        Initiate a connection to the broker.

        Returns a BrokerResponse with status SUCCESS when the
        connection is established, NETWORK_FAILURE on timeout, or
        ERROR on unexpected failure.
        """

    @abstractmethod
    def disconnect(self) -> BrokerResponse:
        """
        Gracefully close the broker connection.

        Should flush any pending state and release all resources.
        Returns a BrokerResponse with status SUCCESS on clean shutdown.
        """

    @abstractmethod
    def authenticate(self) -> BrokerResponse:
        """
        Authenticate with the broker using configured credentials.

        Returns SUCCESS on acceptance, AUTH_FAILURE if credentials
        are rejected, or RETRYABLE_ERROR on transient failure.
        The implementation must NOT expose credentials in the response.
        """

    @abstractmethod
    def refresh_session(self) -> BrokerResponse:
        """
        Refresh an expiring or expired authentication session.

        Returns SUCCESS with an updated session, AUTH_FAILURE if
        re-authentication is required, or RETRYABLE_ERROR on
        transient failure.
        """

    # ── Observability ─────────────────────────────────────────────────────────

    @abstractmethod
    def health(self) -> BrokerHealthRecord:
        """
        Perform a lightweight health check and return a BrokerHealthRecord.

        Must complete within a short deadline (typically 5 s).
        """

    @abstractmethod
    def status(self) -> BrokerStatus:
        """
        Return the current BrokerStatus without making a network call.

        This is a local state query; it must not block.
        """

    @abstractmethod
    def capabilities(self) -> BrokerCapabilities:
        """
        Return the static capability set declared by this broker.

        Must not make a network call; capabilities are declared at
        class / instance construction time.
        """

    # ── Order management ──────────────────────────────────────────────────────

    @abstractmethod
    def place_order(self, request: OrderRequest) -> BrokerResponse:
        """
        Submit a new order to the broker.

        Returns SUCCESS with order details in ``response.data``,
        FAILURE on order rejection, or RETRYABLE_ERROR on transient failure.
        """

    @abstractmethod
    def modify_order(self, request: ModifyOrderRequest) -> BrokerResponse:
        """
        Modify a pending order.

        Returns SUCCESS on acceptance, FAILURE if the order cannot be
        modified (e.g., already filled), or RETRYABLE_ERROR on transient failure.
        """

    @abstractmethod
    def cancel_order(self, request: CancelOrderRequest) -> BrokerResponse:
        """
        Cancel a pending order.

        Returns SUCCESS on acceptance, FAILURE if the order is not
        cancellable, or RETRYABLE_ERROR on transient failure.
        """

    @abstractmethod
    def get_order(self, order_id: str) -> BrokerResponse:
        """
        Retrieve the current state of a single order.

        Returns SUCCESS with order details in ``response.data``,
        FAILURE if the order_id is unknown.
        """

    @abstractmethod
    def get_orders(self) -> BrokerResponse:
        """
        Retrieve all orders for the current trading day.

        Returns SUCCESS with a list of orders in ``response.data``.
        """

    # ── Portfolio queries ─────────────────────────────────────────────────────

    @abstractmethod
    def get_positions(self) -> BrokerResponse:
        """
        Retrieve current open positions.

        Returns SUCCESS with a list of positions in ``response.data``.
        """

    @abstractmethod
    def get_holdings(self) -> BrokerResponse:
        """
        Retrieve long-term holdings (CNC / delivery positions).

        Returns SUCCESS with a list of holdings in ``response.data``.
        """

    @abstractmethod
    def get_funds(self) -> BrokerResponse:
        """
        Retrieve available funds and cash balance.

        Returns SUCCESS with fund details in ``response.data``.
        """

    @abstractmethod
    def get_margin(self) -> BrokerResponse:
        """
        Retrieve margin utilisation and available margin.

        Returns SUCCESS with margin details in ``response.data``.
        """

    # ── Connectivity ──────────────────────────────────────────────────────────

    @abstractmethod
    def ping(self) -> bool:
        """
        Send a lightweight ping to verify the connection is alive.

        Returns True on success, False on failure.
        Must complete within a short deadline (typically 2 s).
        """

    # ── Dunder ────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"broker_id={self.broker_id!r}, "
            f"broker_name={self.broker_name!r}"
            f")"
        )
