"""
iios/events/messaging/response_bus.py
=======================================
Response Bus — collects and routes Response messages back to their callers.
Implements request/reply pattern for synchronous-over-async messaging.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from .message import Response
from ..event_exceptions import QueryTimeoutError

__all__ = ["ResponseBus", "get_response_bus", "reset_response_bus"]

_LOG = logging.getLogger("iios.events.messaging.response_bus")

_bus_lock = threading.Lock()
_bus: Optional["ResponseBus"] = None


class ResponseBus:
    """Routes Response messages to awaiting callers by correlation_id.

    Usage::

        bus = get_response_bus()

        # Publisher side — register a correlation_id to wait for
        correlation_id = "abc-123"
        future = bus.register(correlation_id)

        # Subscriber side — when response arrives, route it
        bus.route(response)   # response.correlation_id == "abc-123"

        # Caller side — block until response or timeout
        response = bus.wait(correlation_id, timeout=10.0)
    """

    def __init__(self) -> None:
        self._pending: dict[str, threading.Event] = {}
        self._responses: dict[str, Response] = {}
        self._lock = threading.RLock()

    def register(self, correlation_id: str) -> threading.Event:
        """Register a correlation_id and return an Event to wait on."""
        evt = threading.Event()
        with self._lock:
            self._pending[correlation_id] = evt
        return evt

    def route(self, response: Response) -> bool:
        """Deliver a response to its waiting caller. Returns True if caller was found."""
        with self._lock:
            evt = self._pending.get(response.correlation_id)
            if evt is None:
                return False
            self._responses[response.correlation_id] = response
        evt.set()
        return True

    def wait(self, correlation_id: str, timeout: float = 30.0) -> Response:
        """Block until a response arrives for *correlation_id* or timeout."""
        with self._lock:
            evt = self._pending.get(correlation_id)
        if evt is None:
            raise QueryTimeoutError(correlation_id, 0)

        if not evt.wait(timeout=timeout):
            with self._lock:
                self._pending.pop(correlation_id, None)
                self._responses.pop(correlation_id, None)
            raise QueryTimeoutError(correlation_id, timeout)

        with self._lock:
            response = self._responses.pop(correlation_id, None)
            self._pending.pop(correlation_id, None)

        if response is None:
            raise QueryTimeoutError(correlation_id, timeout)
        return response

    def cancel(self, correlation_id: str) -> bool:
        with self._lock:
            evt = self._pending.pop(correlation_id, None)
            self._responses.pop(correlation_id, None)
        return evt is not None

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def clear(self) -> None:
        with self._lock:
            # Unblock all waiting callers with a sentinel
            for evt in self._pending.values():
                evt.set()
            self._pending.clear()
            self._responses.clear()


def get_response_bus() -> ResponseBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = ResponseBus()
        return _bus


def reset_response_bus() -> None:
    global _bus
    with _bus_lock:
        if _bus is not None:
            _bus.clear()
        _bus = None
