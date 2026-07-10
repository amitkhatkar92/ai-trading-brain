"""iios/integration/market_data/streaming/stream_router.py

Routes incoming MarketEvent objects to the correct subscriber buffers.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from iios.integration.market_data.core.market_event     import MarketEvent
from iios.integration.market_data.market_data_constants import MarketDataType, MarketEventType
from iios.integration.market_data.streaming.stream_buffer import StreamBuffer

logger = logging.getLogger(__name__)

# Callback type: accepts MarketEvent, returns nothing
EventCallback = Callable[[MarketEvent], None]


class StreamRouter:
    """
    Routes MarketEvent objects to registered symbol/topic/wildcard listeners.

    Routing priority:
    1. Exact topic match  (exchange.symbol.event_type)
    2. Symbol wildcard    (*.symbol.*)
    3. Global wildcard    (*) — receives every event
    """

    def __init__(self) -> None:
        self._lock           = threading.RLock()
        # topic → list[(listener_id, callback)]
        self._topic_routes:  dict[str, list[tuple[str, EventCallback]]] = {}
        # symbol → list[(listener_id, callback)]
        self._symbol_routes: dict[str, list[tuple[str, EventCallback]]] = {}
        # global listeners: list[(listener_id, callback)]
        self._global:        list[tuple[str, EventCallback]] = []
        self._stats          = {"routed": 0, "no_route": 0}

    # ── Registration ───────────────────────────────────────────────────────────

    def subscribe_topic(
        self,
        topic:       str,
        listener_id: str,
        callback:    EventCallback,
    ) -> None:
        with self._lock:
            self._topic_routes.setdefault(topic, []).append((listener_id, callback))
            logger.debug("[StreamRouter] topic subscription: %s → %s", topic, listener_id)

    def subscribe_symbol(
        self,
        symbol:      str,
        listener_id: str,
        callback:    EventCallback,
    ) -> None:
        with self._lock:
            self._symbol_routes.setdefault(symbol, []).append((listener_id, callback))

    def subscribe_all(self, listener_id: str, callback: EventCallback) -> None:
        with self._lock:
            self._global.append((listener_id, callback))

    def unsubscribe(self, listener_id: str) -> None:
        with self._lock:
            for routes in self._topic_routes.values():
                routes[:] = [(lid, cb) for lid, cb in routes if lid != listener_id]
            for routes in self._symbol_routes.values():
                routes[:] = [(lid, cb) for lid, cb in routes if lid != listener_id]
            self._global[:] = [(lid, cb) for lid, cb in self._global if lid != listener_id]

    # ── Routing ────────────────────────────────────────────────────────────────

    def route(self, event: MarketEvent) -> int:
        """
        Dispatch event to all matching listeners.
        Returns number of listeners notified.
        """
        listeners_called = 0
        with self._lock:
            targets: list[tuple[str, EventCallback]] = []

            # Exact topic
            if event.topic in self._topic_routes:
                targets.extend(self._topic_routes[event.topic])

            # Symbol wildcard
            if event.symbol in self._symbol_routes:
                targets.extend(self._symbol_routes[event.symbol])

            # Global
            targets.extend(self._global)

        # Call outside lock so callbacks don't deadlock
        seen: set[str] = set()
        for lid, cb in targets:
            if lid not in seen:
                seen.add(lid)
                try:
                    cb(event)
                    listeners_called += 1
                except Exception as exc:
                    logger.warning("[StreamRouter] Listener %s raised: %s", lid, exc)

        self._stats["routed"] += 1
        if listeners_called == 0:
            self._stats["no_route"] += 1

        return listeners_called

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)

    def listener_count(self) -> int:
        with self._lock:
            total = sum(len(v) for v in self._topic_routes.values())
            total += sum(len(v) for v in self._symbol_routes.values())
            total += len(self._global)
            return total
