"""iios/integration/market_data/validation/duplicate_detector.py

Detects duplicate market data records using a rolling hash set.
"""
from __future__ import annotations

import hashlib
import time
from collections import deque
from typing import Any

from iios.integration.market_data.core.market_candle  import MarketCandle
from iios.integration.market_data.core.market_quote   import MarketQuote
from iios.integration.market_data.core.market_tick    import MarketTick
from iios.integration.market_data.core.market_trade   import MarketTrade
from iios.integration.market_data.market_data_constants import AnomalyType
from iios.integration.market_data.validation.quality_report import QualityIssue


def _tick_key(t: MarketTick) -> str:
    return f"{t.symbol}|{t.timestamp}|{t.price}|{t.size}|{t.sequence_no}"


def _quote_key(q: MarketQuote) -> str:
    return f"{q.symbol}|{q.timestamp}|{q.bid}|{q.ask}|{q.sequence_no}"


def _trade_key(t: MarketTrade) -> str:
    # Exchange trade_id is the canonical dedup key when present
    if t.trade_id:
        return f"{t.symbol}|{t.trade_id}"
    return f"{t.symbol}|{t.timestamp}|{t.price}|{t.size}"


def _candle_key(c: MarketCandle) -> str:
    return f"{c.symbol}|{c.interval.value}|{c.timestamp}"


def _sha8(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


class DuplicateDetector:
    """
    Rolling-window duplicate detector.

    Maintains a bounded deque of recently seen record fingerprints.
    The window is bounded by both count (``window_size``) and age
    (``max_age_sec``).
    """

    def __init__(self, window_size: int = 50_000, max_age_sec: float = 60.0) -> None:
        self._max_size  = window_size
        self._max_age   = max_age_sec
        # deque of (fingerprint, inserted_at)
        self._seen:     deque[tuple[str, float]] = deque()
        self._seen_set: set[str]                 = set()
        self._stats: dict[str, int] = {"checked": 0, "duplicates": 0}

    # ── Public ─────────────────────────────────────────────────────────────────

    def check_tick(self, tick: MarketTick) -> QualityIssue | None:
        return self._check(_tick_key(tick), tick.symbol, "tick")

    def check_quote(self, quote: MarketQuote) -> QualityIssue | None:
        return self._check(_quote_key(quote), quote.symbol, "quote")

    def check_trade(self, trade: MarketTrade) -> QualityIssue | None:
        return self._check(_trade_key(trade), trade.symbol, "trade")

    def check_candle(self, candle: MarketCandle) -> QualityIssue | None:
        return self._check(_candle_key(candle), candle.symbol, "candle")

    def stats(self) -> dict[str, Any]:
        return {**self._stats, "window_size": len(self._seen)}

    # ── Internals ──────────────────────────────────────────────────────────────

    def _check(self, raw_key: str, symbol: str, record_type: str) -> QualityIssue | None:
        self._evict()
        fp = _sha8(raw_key)
        self._stats["checked"] += 1
        if fp in self._seen_set:
            self._stats["duplicates"] += 1
            return QualityIssue(
                anomaly_type = AnomalyType.DUPLICATE,
                symbol       = symbol,
                field_name   = record_type,
                message      = f"Duplicate {record_type} record detected for {symbol}.",
                severity     = "warning",
            )
        # Register
        self._seen.append((fp, time.time()))
        self._seen_set.add(fp)
        # Trim by size
        while len(self._seen) > self._max_size:
            old_fp, _ = self._seen.popleft()
            self._seen_set.discard(old_fp)
        return None

    def _evict(self) -> None:
        now = time.time()
        while self._seen and (now - self._seen[0][1]) > self._max_age:
            old_fp, _ = self._seen.popleft()
            self._seen_set.discard(old_fp)
