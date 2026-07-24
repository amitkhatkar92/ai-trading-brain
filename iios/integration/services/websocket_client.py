"""
websocket_client.py — iios.integration.services
-------------------------------------------------
Provider-independent WebSocket client adapter.

MUST NOT import: websockets, websocket-client, aiohttp, or any WS library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse


# ════════════════════════════════════════════════════════════════════════
# Abstract Interface
# ════════════════════════════════════════════════════════════════════════


class BaseWebSocketClient(ABC):
    """Abstract WebSocket client — implementors inject the WS library."""

    @abstractmethod
    def connect(self, url: str, headers: Optional[Dict[str, str]] = None) -> None:
        """Open a WebSocket connection."""

    @abstractmethod
    def send(self, message: str) -> None:
        """Send a text frame."""

    @abstractmethod
    def receive(self, timeout_ms: int = 30_000) -> str:
        """Receive the next frame and return it as a string."""

    @abstractmethod
    def close(self) -> None:
        """Close the WebSocket connection."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the connection is alive."""

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        try:
            import json
            self.connect(request.endpoint, headers=request.headers)
            self.send(json.dumps(request.payload))
            raw = self.receive(timeout_ms=request.timeout_ms)
            self.close()
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            try:
                data = json.loads(raw)
            except Exception:
                data = {"raw": raw}
            return ConnectorResponse.success(
                request.request_id, data=data, latency_ms=latency_ms,
                adapter_id="websocket-client", transport="websocket",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="websocket-client", transport="websocket",
            )


# ════════════════════════════════════════════════════════════════════════
# Simulated Implementation
# ════════════════════════════════════════════════════════════════════════


class SimulatedWebSocketClient(BaseWebSocketClient):
    """In-process WebSocket simulation — no network I/O."""

    def __init__(self) -> None:
        self._connected = False
        self._url       = ""

    def connect(self, url: str, headers: Optional[Dict[str, str]] = None) -> None:
        self._url       = url
        self._connected = True

    def send(self, message: str) -> None:
        if not self._connected:
            raise RuntimeError("Not connected")

    def receive(self, timeout_ms: int = 30_000) -> str:
        import json
        return json.dumps({"simulated": True, "url": self._url, "echo": True})

    def close(self) -> None:
        self._connected = False

    def health_check(self) -> bool:
        return True
