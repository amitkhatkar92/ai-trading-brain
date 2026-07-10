"""iios/integration/market_data/core/market_trade.py

A single executed trade (print).
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


class TradeSide(str):
    BUY     = "buy"
    SELL    = "sell"
    UNKNOWN = "unknown"


@dataclass
class MarketTrade:
    """One executed trade as reported by the exchange."""

    symbol:          str            = ""
    exchange:        Exchange       = Exchange.UNKNOWN
    instrument_type: InstrumentType = InstrumentType.EQUITY
    price:           float          = 0.0
    size:            float          = 0.0
    side:            str            = TradeSide.UNKNOWN
    timestamp:       float          = 0.0
    received_at:     float          = field(default_factory=time.time)
    trade_id:        str            = ""     # Exchange-assigned trade ID
    aggressor:       str            = ""     # "buyer" | "seller" | ""
    conditions:      list[str]      = field(default_factory=list)   # e.g. ["regular"]
    provider_id:     str            = ""
    quality:         DataQuality    = DataQuality.UNKNOWN
    sequence_no:     int            = 0
    internal_id:     str            = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:        dict[str, Any] = field(default_factory=dict)

    def notional(self) -> float:
        return self.price * self.size

    def is_buyer_initiated(self) -> bool:
        return self.side == TradeSide.BUY or self.aggressor == "buyer"

    def to_dict(self) -> dict[str, Any]:
        return {
            "internal_id":   self.internal_id,
            "trade_id":      self.trade_id,
            "symbol":        self.symbol,
            "exchange":      self.exchange.value,
            "price":         self.price,
            "size":          self.size,
            "notional":      round(self.notional(), 2),
            "side":          self.side,
            "aggressor":     self.aggressor,
            "timestamp":     self.timestamp,
            "received_at":   self.received_at,
            "provider_id":   self.provider_id,
            "quality":       self.quality.value,
            "sequence_no":   self.sequence_no,
        }
