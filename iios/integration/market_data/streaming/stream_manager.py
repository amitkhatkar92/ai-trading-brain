"""iios/integration/market_data/streaming/stream_manager.py

Orchestrates all streaming components:
SubscriptionManager ← StreamRouter ← StreamDispatcher
                                    ↑
                              Heartbeat monitor
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from typing import Any, Callable

from iios.integration.market_data.core.market_event       import MarketEvent
from iios.integration.market_data.market_data_constants   import (
    DEFAULT_HEARTBEAT_INTERVAL_SEC,
    DEFAULT_STREAM_BUFFER_SIZE,
    MarketDataType,
    MarketEventType,
    Exchange,
)
from iios.integration.market_data.streaming.stream_buffer      import StreamBuffer
from iios.integration.market_data.streaming.stream_dispatcher  import StreamDispatcher, DispatcherSubscriber
from iios.integration.market_data.streaming.stream_router      import StreamRouter
from iios.integration.market_data.streaming.subscription_manager import SubscriptionManager, SubscriptionRecord

logger = logging.getLogger(__name__)


class StreamManager:
    """
    Central streaming coordinator.

    Usage::

        mgr = StreamManager()
        sub = mgr.create_subscription("paper_market", ["AAPL"], [MarketDataType.QUOTE])
        listener = mgr.subscribe_symbol("AAPL", my_callback)

        # Ingest events from your provider:
        mgr.ingest(market_event)

        # Or consume from a dispatcher buffer:
        consumer = mgr.register_consumer(symbols_filter=["AAPL"])
        event = await consumer.buffer.get()
    """

    def __init__(
        self,
        heartbeat_interval_sec: float = DEFAULT_HEARTBEAT_INTERVAL_SEC,
    ) -> None:
        self._sub_mgr      = SubscriptionManager()
        self._router       = StreamRouter()
        self._dispatcher   = StreamDispatcher()
        self._hb_interval  = heartbeat_interval_sec
        self._lock         = threading.RLock()
        self._stats: dict[str, int] = {
            "events_ingested":  0,
            "heartbeats_sent":  0,
            "routing_errors":   0,
        }
        self._last_heartbeat: float = 0.0
        self._running       = False

    # ── Subscriptions ──────────────────────────────────────────────────────────

    def create_subscription(
        self,
        provider_id: str,
        symbols:     list[str],
        data_types:  list[MarketDataType],
        sub_id:      str | None = None,
    ) -> SubscriptionRecord:
        sub_id = sub_id or str(uuid.uuid4())
        return self._sub_mgr.register(sub_id, provider_id, symbols, data_types)

    def remove_subscription(self, sub_id: str) -> None:
        self._sub_mgr.unregister(sub_id)

    # ── Consumer registration ──────────────────────────────────────────────────

    def subscribe_topic(
        self, topic: str, listener_id: str, callback: Callable[[MarketEvent], None]
    ) -> None:
        self._router.subscribe_topic(topic, listener_id, callback)

    def subscribe_symbol(
        self, symbol: str, listener_id: str, callback: Callable[[MarketEvent], None]
    ) -> None:
        self._router.subscribe_symbol(symbol, listener_id, callback)

    def subscribe_all(
        self, listener_id: str, callback: Callable[[MarketEvent], None]
    ) -> None:
        self._router.subscribe_all(listener_id, callback)

    def unsubscribe_listener(self, listener_id: str) -> None:
        self._router.unsubscribe(listener_id)

    def register_consumer(
        self,
        name:           str = "",
        symbols_filter: list[str] | None = None,
        buffer_size:    int = DEFAULT_STREAM_BUFFER_SIZE,
    ) -> DispatcherSubscriber:
        """Register a consumer that receives events via a StreamBuffer."""
        return self._dispatcher.register(name=name, symbols_filter=symbols_filter, buffer_size=buffer_size)

    def unregister_consumer(self, sub_id: str) -> None:
        self._dispatcher.unregister(sub_id)

    # ── Ingestion ──────────────────────────────────────────────────────────────

    def ingest(self, event: MarketEvent) -> None:
        """
        Ingest one MarketEvent from a provider.
        Routes it through the router → dispatcher pipeline.
        """
        try:
            self._router.route(event)
            self._dispatcher.dispatch(event)
            self._stats["events_ingested"] += 1

            # Record against subscription
            for rec in self._sub_mgr.find_by_symbol(event.symbol):
                self._sub_mgr.record_event(rec.sub_id)

            # Periodic heartbeat check
            now = time.time()
            if now - self._last_heartbeat >= self._hb_interval:
                self._emit_heartbeat(event.source)
                self._last_heartbeat = now

        except Exception as exc:
            self._stats["routing_errors"] += 1
            logger.error("[StreamManager] Ingest error: %s", exc)

    # ── Heartbeat ──────────────────────────────────────────────────────────────

    def _emit_heartbeat(self, provider_id: str) -> None:
        hb = MarketEvent(
            event_type   = MarketEventType.PROVIDER_CONNECTED,
            source       = provider_id,
            timestamp    = time.time(),
            metadata     = {"heartbeat": True},
        )
        self._dispatcher.dispatch(hb)
        self._stats["heartbeats_sent"] += 1

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "subscriptions":     self._sub_mgr.stats(),
            "router":            self._router.stats(),
            "dispatcher":        self._dispatcher.stats(),
            "listener_count":    self._router.listener_count(),
            "consumer_count":    self._dispatcher.subscriber_count(),
        }

    def subscription_manager(self) -> SubscriptionManager:
        return self._sub_mgr

    def router(self) -> StreamRouter:
        return self._router

    def dispatcher(self) -> StreamDispatcher:
        return self._dispatcher
