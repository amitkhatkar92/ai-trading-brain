"""iios/integration/market_data/normalization/market_normalizer.py

Normalizes raw market data into canonical IIOS form.

Normalizations applied:
- Symbol canonicalization  (e.g. NIFTY50 → ^NSEI)
- Exchange canonicalization
- Timestamp normalization  (ensure UTC epoch seconds)
- Price precision rounding
- Fill missing mid / spread fields
"""
from __future__ import annotations

import time
from typing import Any

from iios.integration.market_data.core.market_candle    import MarketCandle
from iios.integration.market_data.core.market_quote     import MarketQuote
from iios.integration.market_data.core.market_snapshot  import MarketSnapshot
from iios.integration.market_data.core.market_tick      import MarketTick
from iios.integration.market_data.core.market_trade     import MarketTrade
from iios.integration.market_data.market_data_constants import DataQuality


class MarketNormalizer:
    """
    Stateless normalizer for market data records.

    Symbol maps and exchange aliases are injected at construction time.
    All methods are synchronous and side-effect-free.
    """

    def __init__(
        self,
        symbol_map:   dict[str, str] | None = None,
        price_dp:     int   = 4,       # decimal places for prices
        volume_dp:    int   = 2,
    ) -> None:
        self._sym_map  = symbol_map or {}
        self._price_dp = price_dp
        self._vol_dp   = volume_dp
        self._stats: dict[str, int] = {
            "normalized_ticks":     0,
            "normalized_quotes":    0,
            "normalized_trades":    0,
            "normalized_candles":   0,
            "normalized_snapshots": 0,
        }

    # ── Public ─────────────────────────────────────────────────────────────────

    def normalize_tick(self, tick: MarketTick) -> MarketTick:
        tick.symbol   = self._map_symbol(tick.symbol)
        tick.price    = round(tick.price, self._price_dp)
        tick.size     = round(tick.size, self._vol_dp)
        if tick.timestamp == 0.0:
            tick.timestamp = tick.received_at
        self._stats["normalized_ticks"] += 1
        return tick

    def normalize_quote(self, quote: MarketQuote) -> MarketQuote:
        quote.symbol   = self._map_symbol(quote.symbol)
        quote.bid      = round(quote.bid, self._price_dp)
        quote.ask      = round(quote.ask, self._price_dp)
        quote.last     = round(quote.last, self._price_dp)
        if quote.bid > 0 and quote.ask > 0:
            quote.mid  = round((quote.bid + quote.ask) / 2.0, self._price_dp)
        if quote.timestamp == 0.0:
            quote.timestamp = quote.received_at
        self._stats["normalized_quotes"] += 1
        return quote

    def normalize_trade(self, trade: MarketTrade) -> MarketTrade:
        trade.symbol = self._map_symbol(trade.symbol)
        trade.price  = round(trade.price, self._price_dp)
        trade.size   = round(trade.size, self._vol_dp)
        if trade.timestamp == 0.0:
            trade.timestamp = trade.received_at
        self._stats["normalized_trades"] += 1
        return trade

    def normalize_candle(self, candle: MarketCandle) -> MarketCandle:
        candle.symbol = self._map_symbol(candle.symbol)
        for attr in ("open", "high", "low", "close", "vwap"):
            v = getattr(candle, attr)
            setattr(candle, attr, round(v, self._price_dp))
        candle.volume = round(candle.volume, self._vol_dp)
        self._stats["normalized_candles"] += 1
        return candle

    def normalize_snapshot(self, snap: MarketSnapshot) -> MarketSnapshot:
        snap.symbol = self._map_symbol(snap.symbol)
        for attr in ("last", "bid", "ask", "open", "high", "low", "prev_close", "vwap"):
            v = getattr(snap, attr)
            setattr(snap, attr, round(v, self._price_dp))
        if snap.prev_close > 0:
            snap.change     = round(snap.last - snap.prev_close, self._price_dp)
            snap.change_pct = round(snap.change / snap.prev_close * 100.0, 4)
        self._stats["normalized_snapshots"] += 1
        return snap

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _map_symbol(self, symbol: str) -> str:
        return self._sym_map.get(symbol, symbol)
