"""iios/integration/market_data/core/market_tick.py

Atomic last-price update — smallest unit of market data.
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
)


@dataclass
class MarketTick:
    """
    The most granular market data event:
    a single price/volume update for one instrument.
    """

    symbol:          str               = ""
    exchange:        Exchange          = Exchange.UNKNOWN
    instrument_type: InstrumentType    = InstrumentType.EQUITY
    price:           float             = 0.0
    size:            float             = 0.0       # shares / contracts / units
    timestamp:       float             = 0.0       # UTC epoch
    received_at:     float             = field(default_factory=time.time)
    provider_id:     str               = ""
    quality:         DataQuality       = DataQuality.UNKNOWN
    sequence_no:     int               = 0
    tick_id:         str               = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:        dict[str, Any]    = field(default_factory=dict)

    def age_sec(self, now: float | None = None) -> float:
        if now is None:
            now = time.time()
        return now - self.received_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick_id":        self.tick_id,
            "symbol":         self.symbol,
            "exchange":       self.exchange.value,
            "price":          self.price,
            "size":           self.size,
            "timestamp":      self.timestamp,
            "received_at":    self.received_at,
            "provider_id":    self.provider_id,
            "quality":        self.quality.value,
            "sequence_no":    self.sequence_no,
        }
