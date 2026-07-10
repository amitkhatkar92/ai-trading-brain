"""iios/integration/market_data/distribution/market_event_publisher.py

Publishes normalized MarketEvent objects to all registered consumers.

Supports:
- Topic-based fan-out
- Symbol-based fan-out
- Market-wide broadcasts
- Replay-ready publishing (sets is_replay=True)
- Sequence numbering
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from iios.integration.market_data.core.market_event     import MarketEvent
from iios.integration.market_data.market_data_constants import MarketEventType
from iios.integration.market_data.streaming.stream_manager import StreamManager

logger = logging.getLogger(__name__)


class MarketEventPublisher:
    """
    Central event publisher.

    Wraps any market data object in a ``MarketEvent`` envelope and routes
    it through the ``StreamManager``.
    """

    def __init__(self, stream_manager: StreamManager) -> None:
        self._mgr       = stream_manager
        self._lock      = threading.Lock()
        self._seq_no    = 0
        self._stats: dict[str, int] = {
            "published":    0,
            "replayed":     0,
            "errors":       0,
        }

    # ── Publish helpers ───────────────────────────────────────────────────────

    def publish(self, event: MarketEvent) -> bool:
        """Publish a fully-formed MarketEvent. Returns True on success."""
        try:
            with self._lock:
                self._seq_no += 1
                event.sequence_no = self._seq_no
            if not event.published_at:
                event.published_at = time.time()
            self._mgr.ingest(event)
            if event.is_replay:
                self._stats["replayed"] += 1
            else:
                self._stats["published"] += 1
            return True
        except Exception as exc:
            self._stats["errors"] += 1
            logger.error("[MarketEventPublisher] Failed to publish %s: %s", event.event_id, exc)
            return False

    def publish_payload(
        self,
        payload:     Any,
        event_type:  MarketEventType,
        symbol:      str,
        source:      str,
        is_replay:   bool = False,
    ) -> bool:
        """Convenience: wraps payload in a MarketEvent and publishes it."""
        event = MarketEvent(
            event_type  = event_type,
            symbol      = symbol,
            source      = source,
            timestamp   = time.time(),
            payload     = payload,
            is_replay   = is_replay,
        )
        return self.publish(event)

    def broadcast(self, event: MarketEvent) -> bool:
        """
        Broadcast to all consumers regardless of symbol filter.
        Publishes via the global listener route.
        """
        event.symbol = ""   # empty symbol = global broadcast
        return self.publish(event)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {**self._stats, "sequence_no": self._seq_no}

    def current_sequence(self) -> int:
        with self._lock:
            return self._seq_no
