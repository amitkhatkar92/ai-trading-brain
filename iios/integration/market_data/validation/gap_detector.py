"""iios/integration/market_data/validation/gap_detector.py

Detects time-series gaps in market data streams.
"""
from __future__ import annotations

from typing import Any

from iios.integration.market_data.core.market_candle import MarketCandle
from iios.integration.market_data.core.market_quote  import MarketQuote
from iios.integration.market_data.core.market_tick   import MarketTick
from iios.integration.market_data.market_data_constants import (
    AnomalyType,
    DEFAULT_MAX_GAP_SEC,
)
from iios.integration.market_data.validation.quality_report import QualityIssue


class GapDetector:
    """
    Detects time gaps in streaming market data.

    Maintains the last-seen timestamp per symbol.  If the next record
    arrives more than ``max_gap_sec`` after the previous one, a gap
    issue is reported.

    Gaps are expected during market-closed hours — callers are
    responsible for suppressing false positives outside trading sessions.
    """

    def __init__(self, max_gap_sec: float = DEFAULT_MAX_GAP_SEC) -> None:
        self._max_gap = max_gap_sec
        self._last:   dict[str, float] = {}   # symbol → last timestamp
        self._stats: dict[str, int] = {"checked": 0, "gaps": 0}

    # ── Public ─────────────────────────────────────────────────────────────────

    def check_tick(self, tick: MarketTick) -> QualityIssue | None:
        return self._check(tick.symbol, tick.timestamp, "tick")

    def check_quote(self, quote: MarketQuote) -> QualityIssue | None:
        return self._check(quote.symbol, quote.timestamp, "quote")

    def check_candle(self, candle: MarketCandle) -> QualityIssue | None:
        return self._check(candle.symbol, candle.timestamp, "candle")

    def reset(self, symbol: str | None = None) -> None:
        if symbol:
            self._last.pop(symbol, None)
        else:
            self._last.clear()

    def stats(self) -> dict[str, Any]:
        return {**self._stats, "tracked_symbols": len(self._last)}

    # ── Internals ──────────────────────────────────────────────────────────────

    def _check(self, symbol: str, timestamp: float, record_type: str) -> QualityIssue | None:
        self._stats["checked"] += 1
        prev = self._last.get(symbol)
        self._last[symbol] = timestamp
        if prev is None:
            return None
        gap = timestamp - prev
        if gap > self._max_gap:
            self._stats["gaps"] += 1
            return QualityIssue(
                anomaly_type = AnomalyType.GAP_IN_SERIES,
                symbol       = symbol,
                field_name   = "timestamp",
                message      = (
                    f"Gap of {gap:.1f}s detected in {record_type} stream "
                    f"for {symbol} (max={self._max_gap}s)."
                ),
                severity     = "warning",
                value        = gap,
            )
        return None
