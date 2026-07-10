"""iios/integration/market_data/core/market_candle.py

OHLCV candle with optional VWAP, open interest, trade count.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.market_data.market_data_constants import (
    CandleInterval,
    DataQuality,
    Exchange,
    InstrumentType,
)


@dataclass
class MarketCandle:
    """Aggregated OHLCV bar for a specific instrument and interval."""

    symbol:          str             = ""
    exchange:        Exchange        = Exchange.UNKNOWN
    instrument_type: InstrumentType  = InstrumentType.EQUITY
    interval:        CandleInterval  = CandleInterval.M1
    timestamp:       float           = 0.0     # Start of candle period (UTC epoch)
    open:            float           = 0.0
    high:            float           = 0.0
    low:             float           = 0.0
    close:           float           = 0.0
    volume:          float           = 0.0
    vwap:            float           = 0.0     # Volume-weighted average price
    trade_count:     int             = 0
    open_interest:   float           = 0.0
    is_complete:     bool            = False   # False while candle is forming
    received_at:     float           = field(default_factory=time.time)
    provider_id:     str             = ""
    quality:         DataQuality     = DataQuality.UNKNOWN
    candle_id:       str             = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:        dict[str, Any]  = field(default_factory=dict)

    def body(self) -> float:
        return abs(self.close - self.open)

    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    def is_bullish(self) -> bool:
        return self.close >= self.open

    def is_valid(self) -> bool:
        return (
            self.high >= self.low
            and self.open >= self.low
            and self.open <= self.high
            and self.close >= self.low
            and self.close <= self.high
            and self.volume >= 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candle_id":      self.candle_id,
            "symbol":         self.symbol,
            "exchange":       self.exchange.value,
            "interval":       self.interval.value,
            "timestamp":      self.timestamp,
            "open":           self.open,
            "high":           self.high,
            "low":            self.low,
            "close":          self.close,
            "volume":         self.volume,
            "vwap":           self.vwap,
            "trade_count":    self.trade_count,
            "open_interest":  self.open_interest,
            "is_complete":    self.is_complete,
            "received_at":    self.received_at,
            "provider_id":    self.provider_id,
            "quality":        self.quality.value,
        }
