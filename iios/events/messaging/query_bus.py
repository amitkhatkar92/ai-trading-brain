"""
iios/events/messaging/query_bus.py
=====================================
Query Bus — dispatches Queries to registered QueryHandlers and returns Responses.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .message import Query, Response
from ..event_exceptions import QueryError, QueryTimeoutError

__all__ = ["QueryHandler", "QueryBus", "get_query_bus", "reset_query_bus"]

_LOG = logging.getLogger("iios.events.messaging.query_bus")

QueryHandler = Callable[[Query], Response]

_bus_lock = threading.Lock()
_bus: Optional["QueryBus"] = None


@dataclass
class QueryStats:
    executed: int = 0
    succeeded: int = 0
    failed: int = 0
    avg_duration_ms: float = 0.0
    _total_ms: float = 0.0

    def record(self, ms: float, ok: bool) -> None:
        self.executed += 1
        self._total_ms += ms
        if ok:
            self.succeeded += 1
        else:
            self.failed += 1
        self.avg_duration_ms = self._total_ms / self.executed


class QueryBus:
    """Dispatches Queries to their registered handlers.

    Each query type has exactly one handler (CQRS principle).

    Usage::

        bus = get_query_bus()
        bus.register("portfolio.positions", handle_get_positions)

        query = Query(query_type="portfolio.positions", parameters={"account": "ACC001"})
        response = bus.execute(query)
        print(response.payload)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, QueryHandler] = {}
        self._stats = QueryStats()
        self._lock = threading.RLock()

    def register(self, query_type: str, handler: QueryHandler, allow_override: bool = False) -> None:
        with self._lock:
            if query_type in self._handlers and not allow_override:
                raise QueryError(f"Handler already registered for: {query_type}")
            self._handlers[query_type] = handler

    def unregister(self, query_type: str) -> bool:
        with self._lock:
            return self._handlers.pop(query_type, None) is not None

    def execute(self, query: Query) -> Response:
        with self._lock:
            handler = self._handlers.get(query.query_type)
        if handler is None:
            raise QueryError(f"No handler for query: {query.query_type}")

        t0 = time.monotonic()
        try:
            response = handler(query)
            ms = (time.monotonic() - t0) * 1000

            if query.timeout > 0 and ms / 1000 > query.timeout:
                self._stats.record(ms, ok=False)
                raise QueryTimeoutError(query.query_type, query.timeout)

            self._stats.record(ms, ok=True)
            return response
        except (QueryError, QueryTimeoutError):
            raise
        except Exception as exc:
            ms = (time.monotonic() - t0) * 1000
            self._stats.record(ms, ok=False)
            _LOG.error("Query %s failed: %s", query.query_type, exc)
            return Response.err(query.query_id, str(exc))

    def has_handler(self, query_type: str) -> bool:
        with self._lock:
            return query_type in self._handlers

    def registered_types(self) -> list[str]:
        with self._lock:
            return list(self._handlers.keys())

    def stats(self) -> QueryStats:
        return self._stats


def get_query_bus() -> QueryBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = QueryBus()
        return _bus


def reset_query_bus() -> None:
    global _bus
    with _bus_lock:
        _bus = None
