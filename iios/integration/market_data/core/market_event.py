"""iios/integration/market_data/core/market_event.py

Generic envelope for any market data event.
Used by the distribution layer.
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
    MarketEventType,
)


@dataclass
class MarketEvent:
    """
    Envelope wrapping any market data payload.

    The distribution layer routes `MarketEvent` objects to subscribers.
    `payload` holds the typed market data object (MarketTick, MarketQuote, …).
    """

    event_type:      MarketEventType    = MarketEventType.TICK_RECEIVED
    symbol:          str                = ""
    exchange:        Exchange           = Exchange.UNKNOWN
    instrument_type: InstrumentType     = InstrumentType.EQUITY
    source:          str                = ""       # provider_id
    timestamp:       float              = 0.0      # original event timestamp
    published_at:    float              = field(default_factory=time.time)
    quality:         DataQuality        = DataQuality.UNKNOWN
    payload:         Any                = None     # typed market data object
    event_id:        str                = field(default_factory=lambda: str(uuid.uuid4()))
    sequence_no:     int                = 0
    is_replay:       bool               = False    # True if replaying historical
    topic:           str                = ""       # routing topic
    metadata:        dict[str, Any]     = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.topic and self.symbol:
            self.topic = f"{self.exchange.value}.{self.symbol}.{self.event_type.value}"

    def age_ms(self, now: float | None = None) -> float:
        if now is None:
            now = time.time()
        return (now - self.published_at) * 1000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "event_type":    self.event_type.value,
            "symbol":        self.symbol,
            "exchange":      self.exchange.value,
            "source":        self.source,
            "topic":         self.topic,
            "timestamp":     self.timestamp,
            "published_at":  self.published_at,
            "quality":       self.quality.value,
            "sequence_no":   self.sequence_no,
            "is_replay":     self.is_replay,
        }
