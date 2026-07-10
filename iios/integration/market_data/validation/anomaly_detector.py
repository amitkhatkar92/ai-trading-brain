"""iios/integration/market_data/validation/anomaly_detector.py

Statistical outlier / anomaly detection for price and volume.
Uses z-score and configurable thresholds.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Any

from iios.integration.market_data.core.market_candle    import MarketCandle
from iios.integration.market_data.core.market_quote     import MarketQuote
from iios.integration.market_data.core.market_tick      import MarketTick
from iios.integration.market_data.core.market_trade     import MarketTrade
from iios.integration.market_data.market_data_constants import (
    AnomalyType,
    DEFAULT_MAX_PRICE_DEVIATION_PCT,
    DEFAULT_MAX_VOLUME_DEVIATION_X,
)
from iios.integration.market_data.validation.quality_report import QualityIssue


class _RollingStats:
    """Online mean & std-dev via Welford's algorithm."""

    def __init__(self, window: int = 200) -> None:
        self._window = window
        self._buf:   deque[float] = deque(maxlen=window)
        self._n:     int          = 0
        self._mean:  float        = 0.0
        self._m2:    float        = 0.0

    def push(self, v: float) -> None:
        if len(self._buf) == self._window:
            # remove oldest — approximate re-computation
            self._buf.append(v)
            vals = list(self._buf)
            self._mean = sum(vals) / len(vals)
            self._m2   = sum((x - self._mean) ** 2 for x in vals)
            self._n    = len(vals)
        else:
            self._buf.append(v)
            self._n += 1
            delta     = v - self._mean
            self._mean += delta / self._n
            delta2    = v - self._mean
            self._m2  += delta * delta2

    def mean(self) -> float:
        return self._mean

    def std(self) -> float:
        if self._n < 2:
            return 0.0
        return math.sqrt(self._m2 / self._n)

    def z_score(self, v: float) -> float:
        s = self.std()
        if s == 0:
            return 0.0
        return abs(v - self._mean) / s

    def count(self) -> int:
        return self._n


class AnomalyDetector:
    """
    Detects price and volume anomalies via rolling z-score.

    Per-symbol rolling windows are maintained lazily.
    """

    def __init__(
        self,
        price_deviation_pct:   float = DEFAULT_MAX_PRICE_DEVIATION_PCT,
        volume_deviation_x:    float = DEFAULT_MAX_VOLUME_DEVIATION_X,
        z_score_threshold:     float = 4.0,
        warmup_periods:        int   = 20,
    ) -> None:
        self._price_dev_pct   = price_deviation_pct
        self._volume_dev_x    = volume_deviation_x
        self._z_threshold     = z_score_threshold
        self._warmup          = warmup_periods

        self._price_stats:  dict[str, _RollingStats] = {}
        self._volume_stats: dict[str, _RollingStats] = {}
        self._stats: dict[str, int] = {"checked": 0, "anomalies": 0}

    # ── Public ─────────────────────────────────────────────────────────────────

    def check_tick(self, tick: MarketTick) -> list[QualityIssue]:
        return self._check_price_volume(tick.symbol, tick.price, tick.size)

    def check_quote(self, quote: MarketQuote) -> list[QualityIssue]:
        issues = self._check_price_volume(quote.symbol, quote.mid, 0.0)
        if quote.is_inverted():
            issues.append(QualityIssue(
                anomaly_type = AnomalyType.SPREAD_INVERSION,
                symbol       = quote.symbol,
                field_name   = "bid_ask",
                message      = f"Inverted spread for {quote.symbol}: bid={quote.bid} > ask={quote.ask}.",
                severity     = "error",
            ))
        return issues

    def check_trade(self, trade: MarketTrade) -> list[QualityIssue]:
        return self._check_price_volume(trade.symbol, trade.price, trade.size)

    def check_candle(self, candle: MarketCandle) -> list[QualityIssue]:
        issues = self._check_price_volume(candle.symbol, candle.close, candle.volume)
        if not candle.is_valid():
            issues.append(QualityIssue(
                anomaly_type = AnomalyType.BAD_OHLC,
                symbol       = candle.symbol,
                field_name   = "ohlc",
                message      = f"Invalid OHLC for {candle.symbol}: O={candle.open} H={candle.high} L={candle.low} C={candle.close}.",
                severity     = "error",
            ))
        return issues

    def stats(self) -> dict[str, Any]:
        return {**self._stats, "tracked_symbols": len(self._price_stats)}

    # ── Internals ──────────────────────────────────────────────────────────────

    def _check_price_volume(
        self, symbol: str, price: float, volume: float
    ) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        self._stats["checked"] += 1

        # Zero / negative price
        if price <= 0.0:
            atype = AnomalyType.ZERO_PRICE if price == 0.0 else AnomalyType.NEGATIVE_PRICE
            issues.append(QualityIssue(
                anomaly_type=atype, symbol=symbol, field_name="price",
                message=f"Non-positive price {price} for {symbol}.",
                severity="error", value=price,
            ))
            return issues  # no point running stats on invalid price

        p_stats = self._price_stats.setdefault(symbol, _RollingStats())
        v_stats = self._volume_stats.setdefault(symbol, _RollingStats())

        if p_stats.count() >= self._warmup:
            z = p_stats.z_score(price)
            if z > self._z_threshold:
                self._stats["anomalies"] += 1
                issues.append(QualityIssue(
                    anomaly_type = AnomalyType.PRICE_SPIKE,
                    symbol       = symbol,
                    field_name   = "price",
                    message      = f"Price spike for {symbol}: {price:.2f} (z={z:.2f}).",
                    severity     = "warning",
                    value        = price,
                ))

        if volume > 0 and v_stats.count() >= self._warmup:
            mean_vol = v_stats.mean()
            if mean_vol > 0 and volume > mean_vol * self._volume_dev_x:
                self._stats["anomalies"] += 1
                issues.append(QualityIssue(
                    anomaly_type = AnomalyType.VOLUME_SPIKE,
                    symbol       = symbol,
                    field_name   = "volume",
                    message      = f"Volume spike for {symbol}: {volume:.0f} ({volume/mean_vol:.1f}× avg).",
                    severity     = "warning",
                    value        = volume,
                ))

        p_stats.push(price)
        if volume > 0:
            v_stats.push(volume)

        return issues
