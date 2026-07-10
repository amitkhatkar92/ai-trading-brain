"""iios/integration/market_data/core/order_book.py

Full L2 / L3 order book.
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
    DEFAULT_MAX_ORDER_BOOK_DEPTH,
)


@dataclass
class OrderBookLevel:
    """One price level in the order book."""
    price:    float = 0.0
    size:     float = 0.0
    orders:   int   = 0   # number of resting orders at this level (L3)


@dataclass
class OrderBook:
    """Full order book snapshot — bids (descending) and asks (ascending)."""

    symbol:          str                    = ""
    exchange:        Exchange               = Exchange.UNKNOWN
    instrument_type: InstrumentType         = InstrumentType.EQUITY
    bids:            list[OrderBookLevel]   = field(default_factory=list)
    asks:            list[OrderBookLevel]   = field(default_factory=list)
    timestamp:       float                  = 0.0
    received_at:     float                  = field(default_factory=time.time)
    sequence_no:     int                    = 0
    provider_id:     str                    = ""
    quality:         DataQuality            = DataQuality.UNKNOWN
    book_id:         str                    = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:        dict[str, Any]         = field(default_factory=dict)

    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0

    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 0.0

    def mid(self) -> float:
        bb, ba = self.best_bid(), self.best_ask()
        if bb > 0 and ba > 0:
            return (bb + ba) / 2.0
        return 0.0

    def spread(self) -> float:
        return self.best_ask() - self.best_bid() if self.best_ask() > 0 and self.best_bid() > 0 else 0.0

    def total_bid_size(self, depth: int = DEFAULT_MAX_ORDER_BOOK_DEPTH) -> float:
        return sum(lvl.size for lvl in self.bids[:depth])

    def total_ask_size(self, depth: int = DEFAULT_MAX_ORDER_BOOK_DEPTH) -> float:
        return sum(lvl.size for lvl in self.asks[:depth])

    def imbalance(self, depth: int = DEFAULT_MAX_ORDER_BOOK_DEPTH) -> float:
        """Order book imbalance: +1 fully bid-side, −1 fully ask-side."""
        bid_sz = self.total_bid_size(depth)
        ask_sz = self.total_ask_size(depth)
        total  = bid_sz + ask_sz
        if total == 0:
            return 0.0
        return (bid_sz - ask_sz) / total

    def is_crossed(self) -> bool:
        return self.best_bid() > self.best_ask() and self.best_ask() > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "book_id":     self.book_id,
            "symbol":      self.symbol,
            "exchange":    self.exchange.value,
            "best_bid":    self.best_bid(),
            "best_ask":    self.best_ask(),
            "spread":      round(self.spread(), 4),
            "imbalance":   round(self.imbalance(), 4),
            "bid_depth":   len(self.bids),
            "ask_depth":   len(self.asks),
            "timestamp":   self.timestamp,
            "received_at": self.received_at,
            "sequence_no": self.sequence_no,
            "provider_id": self.provider_id,
            "quality":     self.quality.value,
        }
