"""market/market_event_generator.py — Synthetic market events for the simulation loop."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import PTEventType
from iios.integration.research.paper_trading.market.market_simulator import PriceBar


@dataclass
class MarketEvent:
    """A single market event produced during simulation."""
    event_id:   str
    event_type: PTEventType
    timestamp:  float
    symbol:     Optional[str]
    data:       dict[str, Any]

    @classmethod
    def _make(
        cls,
        event_type: PTEventType,
        timestamp:  float,
        symbol:     Optional[str]    = None,
        data:       Optional[dict]   = None,
    ) -> "MarketEvent":
        return cls(
            event_id   = f"evt_{uuid.uuid4().hex[:8]}",
            event_type = event_type,
            timestamp  = timestamp,
            symbol     = symbol,
            data       = data or {},
        )


class MarketEventGenerator:
    """
    Accumulates market events in an internal queue.

    The simulation loop calls ``drain()`` at the end of each bar to consume
    all pending events in chronological order.
    """

    def __init__(self) -> None:
        self._pending: list[MarketEvent] = []

    # ── Generators ────────────────────────────────────────────────────────────

    def generate_bar_event(self, bar: PriceBar) -> MarketEvent:
        evt = MarketEvent._make(
            PTEventType.BAR,
            bar.timestamp,
            bar.symbol,
            {
                "open":      bar.open,
                "high":      bar.high,
                "low":       bar.low,
                "close":     bar.close,
                "volume":    bar.volume,
                "bar_index": bar.bar_index,
                "is_last":   bar.is_last,
            },
        )
        self._pending.append(evt)
        return evt

    def generate_session_start(self, timestamp: float, exchange_id: str) -> MarketEvent:
        evt = MarketEvent._make(
            PTEventType.SESSION_START, timestamp, data={"exchange_id": exchange_id}
        )
        self._pending.append(evt)
        return evt

    def generate_session_end(self, timestamp: float, exchange_id: str) -> MarketEvent:
        evt = MarketEvent._make(
            PTEventType.SESSION_END, timestamp, data={"exchange_id": exchange_id}
        )
        self._pending.append(evt)
        return evt

    def generate_halt(
        self, symbol: str, reason: str, timestamp: float
    ) -> MarketEvent:
        evt = MarketEvent._make(
            PTEventType.HALT, timestamp, symbol, {"reason": reason}
        )
        self._pending.append(evt)
        return evt

    def generate_resume(self, symbol: str, timestamp: float) -> MarketEvent:
        evt = MarketEvent._make(PTEventType.RESUME, timestamp, symbol)
        self._pending.append(evt)
        return evt

    def generate_dividend(
        self, symbol: str, amount: float, ex_ts: float
    ) -> MarketEvent:
        evt = MarketEvent._make(
            PTEventType.CORPORATE_ACTION,
            ex_ts,
            symbol,
            {"action": "dividend", "amount": amount},
        )
        self._pending.append(evt)
        return evt

    def generate_split(
        self, symbol: str, ratio: float, timestamp: float
    ) -> MarketEvent:
        evt = MarketEvent._make(
            PTEventType.CORPORATE_ACTION,
            timestamp,
            symbol,
            {"action": "split", "ratio": ratio},
        )
        self._pending.append(evt)
        return evt

    # ── Queue management ──────────────────────────────────────────────────────

    def drain(self) -> list[MarketEvent]:
        """Return all pending events sorted by timestamp and clear the queue."""
        events        = sorted(self._pending, key=lambda e: e.timestamp)
        self._pending = []
        return events

    def pending_count(self) -> int:
        return len(self._pending)

    def clear(self) -> None:
        self._pending.clear()
