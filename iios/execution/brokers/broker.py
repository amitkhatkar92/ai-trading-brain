"""iios/execution/brokers/broker.py
==================================================
AbstractBroker — concrete partial base providing default implementations
of boilerplate lifecycle management for broker adapters.

Adapter authors subclass AbstractBroker (which already implements
AbstractBrokerInterface) and override only the abstract methods.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from iios.execution.brokers.broker_interface import AbstractBrokerInterface
from iios.execution.brokers.broker_metadata import BrokerMetadata
from iios.execution.brokers.broker_capabilities import (
    BrokerCapabilities,
    capabilities_from_metadata,
)
from iios.execution.brokers.broker_request import (
    BrokerRequest,
    ConnectionRequest,
    HeartbeatRequest,
)
from iios.execution.brokers.broker_response import (
    BrokerResponse,
    ConnectionResponse,
    HealthResponse,
)
from iios.execution.brokers.constants import (
    BrokerConnectionState,
    BrokerHealthStatus,
    BrokerMode,
    BrokerRequestType,
    BrokerResponseStatus,
)
from iios.execution.brokers.exceptions import BrokerNotConnectedError


class AbstractBroker(AbstractBrokerInterface):
    """
    Partial base class for broker adapters.

    Provides:
      - identity property (broker_id, metadata, capabilities)
      - connection_state management via _set_connection_state()
      - heartbeat default (delegates to health())
      - is_connected / _require_connected() guard

    Subclasses must implement:
      - connect(), disconnect()
      - health()
      - submit_order(), modify_order(), cancel_order(), order_status()
      - positions(), holdings(), balances(), margin()
    """

    def __init__(self, metadata: BrokerMetadata) -> None:
        self._metadata:    BrokerMetadata       = metadata
        self._capabilities: BrokerCapabilities  = capabilities_from_metadata(metadata)
        self._connection_state: BrokerConnectionState = BrokerConnectionState.DISCONNECTED
        self._lock: threading.RLock             = threading.RLock()
        self._connected_at: float | None        = None

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def broker_id(self) -> str:
        return self._metadata.broker_id

    @property
    def metadata(self) -> BrokerMetadata:
        return self._metadata

    @property
    def capabilities(self) -> BrokerCapabilities:
        return self._capabilities

    # ── Connection state ──────────────────────────────────────────────────────

    @property
    def connection_state(self) -> BrokerConnectionState:
        with self._lock:
            return self._connection_state

    def _set_connection_state(self, state: BrokerConnectionState) -> None:
        with self._lock:
            self._connection_state = state
            if state == BrokerConnectionState.CONNECTED:
                self._connected_at = time.time()
            elif state == BrokerConnectionState.DISCONNECTED:
                self._connected_at = None

    def _require_connected(self) -> None:
        """Raise if the adapter is not connected."""
        if not self.is_connected:
            raise BrokerNotConnectedError(self.broker_id)

    # ── Heartbeat default ─────────────────────────────────────────────────────

    def heartbeat(self, request: HeartbeatRequest) -> BrokerResponse:
        """Default heartbeat: delegates to health()."""
        t0 = time.time()
        health_resp = self.health(request)
        duration_ms = (time.time() - t0) * 1_000
        return BrokerResponse(
            response_id    = str(uuid.uuid4()),
            request_id     = request.request_id,
            broker_id      = self.broker_id,
            request_type   = BrokerRequestType.HEARTBEAT,
            status         = (
                BrokerResponseStatus.SUCCESS
                if health_resp.succeeded
                else BrokerResponseStatus.FAILURE
            ),
            responded_at   = time.time(),
            duration_ms    = duration_ms,
            correlation_id = request.correlation_id,
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["connected_at"] = self._connected_at
        return d

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id={self.broker_id!r}, state={self.connection_state.value})"
        )
