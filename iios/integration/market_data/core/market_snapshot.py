"""iios/integration/market_data/core/market_snapshot.py

Point-in-time summary of an instrument's market state.
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
class MarketSnapshot:
    """
    Full market state snapshot — best used for polling and bootstrapping
    subscriptions.
    """

    symbol:          str            = ""
    exchange:        Exchange       = Exchange.UNKNOWN
    instrument_type: InstrumentType = InstrumentType.EQUITY
    session:         TradingSession = TradingSession.REGULAR

    # Prices
    last:            float          = 0.0
    bid:             float          = 0.0
    ask:             float          = 0.0
    open:            float          = 0.0
    high:            float          = 0.0
    low:             float          = 0.0
    prev_close:      float          = 0.0

    # Derived
    change:          float          = 0.0      # last - prev_close
    change_pct:      float          = 0.0      # %
    vwap:            float          = 0.0

    # Volume / OI
    volume:          float          = 0.0
    avg_volume:      float          = 0.0      # rolling average
    open_interest:   float          = 0.0

    # Misc
    circuit_high:    float          = 0.0      # upper circuit
    circuit_low:     float          = 0.0      # lower circuit
    week_52_high:    float          = 0.0
    week_52_low:     float          = 0.0

    timestamp:       float          = 0.0
    received_at:     float          = field(default_factory=time.time)
    provider_id:     str            = ""
    quality:         DataQuality    = DataQuality.UNKNOWN
    snapshot_id:     str            = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:        dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.change == 0.0 and self.last > 0 and self.prev_close > 0:
            self.change = self.last - self.prev_close
        if self.change_pct == 0.0 and self.prev_close > 0:
            self.change_pct = self.change / self.prev_close * 100.0

    def spread(self) -> float:
        return self.ask - self.bid if self.ask >= self.bid else 0.0

    def is_upper_circuit(self) -> bool:
        return self.circuit_high > 0 and self.last >= self.circuit_high

    def is_lower_circuit(self) -> bool:
        return self.circuit_low > 0 and self.last <= self.circuit_low

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":   self.snapshot_id,
            "symbol":        self.symbol,
            "exchange":      self.exchange.value,
            "session":       self.session.value,
            "last":          self.last,
            "bid":           self.bid,
            "ask":           self.ask,
            "open":          self.open,
            "high":          self.high,
            "low":           self.low,
            "prev_close":    self.prev_close,
            "change":        round(self.change, 4),
            "change_pct":    round(self.change_pct, 4),
            "vwap":          self.vwap,
            "volume":        self.volume,
            "avg_volume":    self.avg_volume,
            "open_interest": self.open_interest,
            "timestamp":     self.timestamp,
            "received_at":   self.received_at,
            "provider_id":   self.provider_id,
            "quality":       self.quality.value,
        }
