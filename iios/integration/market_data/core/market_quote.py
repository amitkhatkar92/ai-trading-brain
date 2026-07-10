"""iios/integration/market_data/core/market_quote.py

Bid/ask spread snapshot.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.market_data.market_data_constants import (
    DataQuality,
    Exchange,
    InstrumentType,
    TradingSession,
)


@dataclass
class MarketQuote:
    """Best bid/ask for an instrument at a point in time."""

    symbol:          str               = ""
    exchange:        Exchange          = Exchange.UNKNOWN
    instrument_type: InstrumentType    = InstrumentType.EQUITY
    bid:             float             = 0.0
    bid_size:        float             = 0.0
    ask:             float             = 0.0
    ask_size:        float             = 0.0
    last:            float             = 0.0
    last_size:       float             = 0.0
    mid:             float             = 0.0        # (bid+ask)/2 — computed
    timestamp:       float             = 0.0
    received_at:     float             = field(default_factory=time.time)
    session:         TradingSession    = TradingSession.REGULAR
    provider_id:     str               = ""
    quality:         DataQuality       = DataQuality.UNKNOWN
    sequence_no:     int               = 0
    quote_id:        str               = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:        dict[str, Any]    = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mid == 0.0 and self.bid > 0 and self.ask > 0:
            self.mid = (self.bid + self.ask) / 2.0

    def spread(self) -> float:
        return self.ask - self.bid if self.ask >= self.bid else 0.0

    def spread_pct(self) -> float:
        if self.mid > 0:
            return self.spread() / self.mid * 100.0
        return 0.0

    def is_inverted(self) -> bool:
        return self.bid > self.ask and self.ask > 0

    def is_stale(self, max_age_sec: float = 60.0, now: float | None = None) -> bool:
        if now is None:
            now = time.time()
        return (now - self.received_at) > max_age_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "quote_id":    self.quote_id,
            "symbol":      self.symbol,
            "exchange":    self.exchange.value,
            "bid":         self.bid,
            "bid_size":    self.bid_size,
            "ask":         self.ask,
            "ask_size":    self.ask_size,
            "last":        self.last,
            "last_size":   self.last_size,
            "mid":         round(self.mid, 4),
            "spread":      round(self.spread(), 4),
            "spread_pct":  round(self.spread_pct(), 4),
            "timestamp":   self.timestamp,
            "received_at": self.received_at,
            "session":     self.session.value,
            "provider_id": self.provider_id,
            "quality":     self.quality.value,
            "sequence_no": self.sequence_no,
        }
