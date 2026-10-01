"""
Feature Extractor — Edge Discovery Engine Module 1
===================================================
Builds a rich numerical feature vector from a MarketSnapshot.

A feature vector captures the quantitative "state of the market"
at a point in time.  The EDE's pattern miner operates on these
vectors to find which states historically precede profitable moves.

Feature categories (≈70 total features):
  • Price action     — momentum across multiple time-frames
  • Volume           — ratio, spike, consistency
  • Technical        — RSI, MACD, Bollinger Band position
  • Market structure — regime, VIX, breadth, PUT/CALL ratio
  • Institutional    — FII/DII flow proxy via breadth/pcr
  • Sector           — momentum, rotation signal
  • Options          — IV environment, skew proxy
  • Cross-market     — global bias, correlation regime

DTA-EDGE-FEATURE-REAL-001: per-symbol technical features (momentum, RSI,
MACD, Bollinger position, realized vol, ADX, gap) are now computed from
REAL OHLCV history (data/market_behavior.db's ohlcv_daily table, the same
store the live daily OIOS refresh maintains) instead of being randomly
sampled. iv_rank/sector_strength/liquidity_score remain PROXIES (real
options-chain IV and bid/ask spread are not available for this symbol
universe) but are now derived from real historical-volatility/momentum/
volume data rather than gaussian noise -- clearly commented as proxies
below. Falls back to the original seeded-random synthetic generation,
UNCHANGED, whenever a symbol lacks sufficient real history (<25 bars) --
this guarantees the pipeline never breaks or goes silent, only degrades
to its pre-existing (already-shipped) behavior for that one symbol.
"""

from __future__ import annotations

import math
import random
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from utils import get_logger

log = get_logger(__name__)

# ── Feature vector type alias ───────────────────────────────────────────────
FeatureVector = Dict[str, float]

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OHLCV_DB = _ROOT / "data" / "market_behavior.db"

# Index symbols are stored under their Yahoo routing ticker in ohlcv_daily,
# not a ".NS" suffix -- same convention used throughout this repo (see
# data_feeds/yahoo_feed.py's GLOBAL_SYMBOL_MAP).
_INDEX_OHLCV_SYMBOL = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}

# Need enough bars for RSI(14)/ADX(14)/BB(20)/mom_20d with a safety margin.
_MIN_REAL_HISTORY_BARS = 25
_REAL_HISTORY_LOOKBACK_DAYS = 90


def _ohlcv_symbol(symbol: str) -> str:
    return _INDEX_OHLCV_SYMBOL.get(symbol, f"{symbol}.NS")


@dataclass
class SymbolFeatures:
    """Feature vector for one symbol at one point in time."""
    symbol: str
    features: FeatureVector
    label: Optional[float] = None   # forward return if known (for training)
    ts_str: str = ""


# ── Real-data technical indicator helpers (pure Python, no new deps) ───────

def _rsi_wilder(closes: List[float], period: int = 14) -> Optional[float]:
    """Wilder-smoothed RSI -- identical algorithm to
    opportunity_engine/equity_scanner_ai.py's _compute_rsi_list(), kept as
    a local copy to avoid a cross-package import edge."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 1)


def _ema_series(values: List[float], period: int) -> List[float]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _macd_histogram(closes: List[float]) -> float:
    """Standard MACD(12,26,9) histogram = MACD line - signal line."""
    if len(closes) < 26:
        return 0.0
    ema12 = _ema_series(closes, 12)
    ema26 = _ema_series(closes, 26)
    macd_line = [a - b for a, b in zip(ema12[-len(ema26):], ema26)]
    signal = _ema_series(macd_line, 9)
    return macd_line[-1] - signal[-1]


def _bollinger_position(closes: List[float], period: int = 20) -> float:
    """(close - SMA) / (2*std), clamped to [-1, 1] -- same bound contract
    as the prior synthetic bb_position."""
    window = closes[-period:]
    if len(window) < period:
        return 0.0
    sma = sum(window) / period
    variance = sum((c - sma) ** 2 for c in window) / period
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return max(-1.0, min(1.0, (closes[-1] - sma) / (2 * std)))


def _realized_vol(closes: List[float], window: int) -> float:
    """Std of daily pct returns over the trailing window (real volatility,
    not annualised)."""
    series = closes[-(window + 1):]
    if len(series) < 3:
        return 0.0
    rets = [(series[i] / series[i - 1]) - 1.0 for i in range(1, len(series)) if series[i - 1]]
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    variance = sum((r - mean) ** 2 for r in rets) / len(rets)
    return math.sqrt(variance)


def _adx_wilder(highs: List[float], lows: List[float], closes: List[float],
                period: int = 14) -> float:
    """Standard Wilder ADX. Returns 0.0 if insufficient history."""
    n = len(closes)
    if n < period * 2:
        return 0.0
    tr, plus_dm, minus_dm = [], [], []
    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm.append(up_move if (up_move > down_move and up_move > 0) else 0.0)
        minus_dm.append(down_move if (down_move > up_move and down_move > 0) else 0.0)
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    def _wilder_smooth(values: List[float]) -> List[float]:
        smoothed = [sum(values[:period])]
        for v in values[period:]:
            smoothed.append(smoothed[-1] - (smoothed[-1] / period) + v)
        return smoothed

    tr_s = _wilder_smooth(tr)
    plus_s = _wilder_smooth(plus_dm)
    minus_s = _wilder_smooth(minus_dm)

    dx_values = []
    for t, p, m in zip(tr_s, plus_s, minus_s):
        if t == 0:
            continue
        plus_di = 100.0 * p / t
        minus_di = 100.0 * m / t
        denom = plus_di + minus_di
        dx_values.append(100.0 * abs(plus_di - minus_di) / denom if denom else 0.0)

    if len(dx_values) < period:
        return (sum(dx_values) / len(dx_values) / 100.0) if dx_values else 0.0
    adx = sum(dx_values[:period]) / period
    for dx in dx_values[period:]:
        adx = (adx * (period - 1) + dx) / period
    return max(0.0, min(1.0, adx / 100.0))


class FeatureExtractor:
    """
    Converts a MarketSnapshot into per-symbol FeatureVectors.

    Market-wide features are shared across all symbols. Symbol-specific
    technical features are computed from real OHLCV history when
    available (DTA-EDGE-FEATURE-REAL-001); a symbol with insufficient
    real history falls back to the original seeded-random synthetic
    generation so the pipeline degrades gracefully rather than failing.
    """

    # ── Regime encoding ─────────────────────────────────────────────
    _REGIME_SCORE = {
        RegimeLabel.BULL_TREND:   1.0,
        RegimeLabel.RANGE_MARKET: 0.5,
        RegimeLabel.BEAR_MARKET:  0.0,
        RegimeLabel.VOLATILE:     0.3,
    }
    _VOL_SCORE = {
        VolatilityLevel.LOW:     0.2,
        VolatilityLevel.MEDIUM:  0.5,
        VolatilityLevel.HIGH:    0.8,
        VolatilityLevel.EXTREME: 1.0,
    }

    # ── Universe of symbols to analyse ──────────────────────────────
    SYMBOL_UNIVERSE = [
        "NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "INFY",
        "HDFC", "ICICIBANK", "LT", "AXISBANK", "WIPRO",
        "HDFCBANK", "BAJFINANCE", "SBIN", "MARUTI", "TATAMOTORS",
        "SUNPHARMA", "DRREDDY", "ONGC", "NTPC", "POWERGRID",
    ]

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or _DEFAULT_OHLCV_DB
        log.info("[FeatureExtractor] Initialised. Universe: %d symbols",
                 len(self.SYMBOL_UNIVERSE))

    # ── Public API ───────────────────────────────────────────────────

    def extract(self, snapshot: MarketSnapshot,
                symbols: Optional[List[str]] = None) -> List[SymbolFeatures]:
        """
        Build one FeatureVector per symbol.

        Args:
            snapshot: current MarketSnapshot
            symbols:  subset of SYMBOL_UNIVERSE (None → use all)
        Returns:
            List[SymbolFeatures]
        """
        syms = symbols or self.SYMBOL_UNIVERSE
        market_ctx = self._market_context(snapshot)

        bars_by_symbol = self._load_real_bars_batch(set(syms) | {"NIFTY"})
        nifty_bars = bars_by_symbol.get("NIFTY")

        results = []
        real_n, fallback_n = 0, 0
        for sym in syms:
            bars = bars_by_symbol.get(sym)
            if bars is not None:
                sym_feats = self._symbol_features_real(sym, bars, nifty_bars, market_ctx)
                real_n += 1
            else:
                sym_feats = self._symbol_features_synthetic(sym, snapshot, market_ctx)
                fallback_n += 1
            results.append(SymbolFeatures(
                symbol=sym,
                features={**market_ctx, **sym_feats},
                ts_str=snapshot.timestamp.strftime("%Y-%m-%d %H:%M"),
            ))
        log.info(
            "[FeatureExtractor] DTA-EDGE-FEATURE-REAL-001 real=%d synthetic_fallback=%d",
            real_n, fallback_n,
        )
        return results

    def feature_names(self) -> List[str]:
        """Return all feature names in a stable order."""
        return sorted(self._market_context(_dummy_snapshot()).keys()
                      | self._symbol_features_synthetic("X", _dummy_snapshot(), {}).keys())

    # ── Internal: real OHLCV loading ────────────────────────────────

    def _load_real_bars_batch(self, symbols) -> Dict[str, Dict[str, List[float]]]:
        """Bulk-loads real OHLCV history for `symbols` from ohlcv_daily.
        Returns {bare_symbol: {"open":[...], "high":[...], "low":[...],
        "close":[...], "volume":[...]}} (time-ordered ascending) only for
        symbols with >= _MIN_REAL_HISTORY_BARS rows. Never raises -- an
        empty dict means every symbol falls back to synthetic generation."""
        result: Dict[str, Dict[str, List[float]]] = {}
        try:
            db_symbol_to_bare = {_ohlcv_symbol(s): s for s in symbols}
            placeholders = ",".join("?" for _ in db_symbol_to_bare)
            conn = sqlite3.connect(str(self._db_path))
            try:
                rows = conn.execute(
                    f"""
                    SELECT symbol, trade_date, open, high, low, close, volume
                    FROM ohlcv_daily
                    WHERE symbol IN ({placeholders})
                      AND trade_date >= date('now', '-{_REAL_HISTORY_LOOKBACK_DAYS} days')
                    ORDER BY symbol, trade_date ASC
                    """,
                    list(db_symbol_to_bare.keys()),
                ).fetchall()
            finally:
                conn.close()
        except Exception as exc:
            log.debug("[FeatureExtractor] Real OHLCV load failed (%s) -- "
                      "falling back to synthetic for all symbols.", exc)
            return {}

        grouped: Dict[str, Dict[str, List[float]]] = {}
        for db_sym, _date, o, h, l, c, v in rows:
            bare = db_symbol_to_bare.get(db_sym)
            if bare is None:
                continue
            bucket = grouped.setdefault(bare, {"open": [], "high": [], "low": [], "close": [], "volume": []})
            bucket["open"].append(float(o or 0.0))
            bucket["high"].append(float(h or 0.0))
            bucket["low"].append(float(l or 0.0))
            bucket["close"].append(float(c or 0.0))
            bucket["volume"].append(float(v or 0.0))

        for bare, bars in grouped.items():
            if len(bars["close"]) >= _MIN_REAL_HISTORY_BARS and all(bars["close"]):
                result[bare] = bars
        return result

    # ── Internal: market-wide features ──────────────────────────────

    def _market_context(self, snap: MarketSnapshot) -> FeatureVector:
        regime = snap.regime or RegimeLabel.RANGE_MARKET
        vol    = snap.volatility or VolatilityLevel.MEDIUM
        vix    = float(snap.vix or 15.0)
        breadth = float(snap.market_breadth or 0.5)
        pcr    = float(snap.pcr or 1.0)
        global_bias = float(snap.global_sentiment_score or 0.0)

        # Regime one-hot
        is_bull   = 1.0 if regime == RegimeLabel.BULL_TREND   else 0.0
        is_range  = 1.0 if regime == RegimeLabel.RANGE_MARKET else 0.0
        is_bear   = 1.0 if regime == RegimeLabel.BEAR_MARKET  else 0.0
        is_vol    = 1.0 if regime == RegimeLabel.VOLATILE      else 0.0

        # VIX derived features
        vix_low   = 1.0 if vix < 14 else 0.0
        vix_high  = 1.0 if vix > 22 else 0.0
        vix_norm  = min(vix / 40.0, 1.0)

        # PCR features
        pcr_bullish = 1.0 if pcr < 0.7  else 0.0
        pcr_bearish = 1.0 if pcr > 1.3  else 0.0
        pcr_neutral = 1.0 - pcr_bullish - pcr_bearish

        # Breadth features
        breadth_strong   = 1.0 if breadth > 0.6 else 0.0
        breadth_weak     = 1.0 if breadth < 0.4 else 0.0

        return {
            # Regime
            "regime_score":       self._REGIME_SCORE.get(regime, 0.5),
            "regime_bull":        is_bull,
            "regime_range":       is_range,
            "regime_bear":        is_bear,
            "regime_volatile":    is_vol,
            "vol_score":          self._VOL_SCORE.get(vol, 0.5),
            # VIX
            "vix":                vix_norm,
            "vix_low":            vix_low,
            "vix_high":           vix_high,
            # Breadth
            "breadth":            breadth,
            "breadth_strong":     breadth_strong,
            "breadth_weak":       breadth_weak,
            # PCR
            "pcr":                min(pcr / 2.0, 1.0),
            "pcr_bullish":        pcr_bullish,
            "pcr_bearish":        pcr_bearish,
            "pcr_neutral":        pcr_neutral,
            # Global
            "global_bias":        (global_bias + 1.0) / 2.0,   # normalise -1..1 → 0..1
            # Sector flows (aggregate)
            "sector_flow_count":  float(len(snap.sector_flows or [])) / 10.0,
            # Events
            "event_count":        float(len(snap.events_today or [])) / 5.0,
        }

    # ── Internal: per-symbol features (REAL, from OHLCV history) ───

    def _symbol_features_real(self, symbol: str, bars: Dict[str, List[float]],
                               nifty_bars: Optional[Dict[str, List[float]]],
                               market_ctx: FeatureVector) -> FeatureVector:
        """DTA-EDGE-FEATURE-REAL-001: real technical features computed from
        actual OHLCV history. Same key names/bounds as the synthetic path
        it replaces. iv_rank/sector_strength/liquidity_score are clearly-
        labelled real-data PROXIES (true options IV and bid/ask spread are
        not available for this symbol universe)."""
        closes, highs, lows, vols = bars["close"], bars["high"], bars["low"], bars["volume"]
        opens = bars["open"]
        vix_norm = market_ctx.get("vix", 0.375)

        def _pct_change(n: int) -> float:
            if len(closes) <= n or not closes[-n - 1]:
                return 0.0
            return (closes[-1] / closes[-n - 1]) - 1.0

        mom_1d  = _pct_change(1)
        mom_5d  = _pct_change(min(5, len(closes) - 1))
        mom_10d = _pct_change(min(10, len(closes) - 1))
        mom_20d = _pct_change(min(20, len(closes) - 1))

        avg_vol20 = (sum(vols[-21:-1]) / len(vols[-21:-1])) if len(vols) >= 2 else 0.0
        volume_ratio = (vols[-1] / avg_vol20) if avg_vol20 > 0 else 1.0
        volume_spike = 1.0 if volume_ratio > 2.0 else 0.0

        rsi = _rsi_wilder(closes, 14)
        if rsi is None:
            rsi = 50.0
        rsi_oversold   = 1.0 if rsi < 35 else 0.0
        rsi_overbought = 1.0 if rsi > 65 else 0.0
        rsi_neutral    = 1.0 - rsi_oversold - rsi_overbought

        macd_signal = max(-1.0, min(1.0, _macd_histogram(closes) / max(closes[-1], 1e-6) * 100))
        macd_bull = 1.0 if macd_signal > 0.05 else 0.0
        macd_bear = 1.0 if macd_signal < -0.05 else 0.0

        bb_position = _bollinger_position(closes, 20)
        bb_upper = 1.0 if bb_position > 0.7 else 0.0
        bb_lower = 1.0 if bb_position < -0.7 else 0.0

        hist_vol_5d  = _realized_vol(closes, 5)
        hist_vol_20d = _realized_vol(closes, 20)
        vol_compression = 1.0 if hist_vol_5d < hist_vol_20d * 0.7 else 0.0

        # iv_rank PROXY: real options IV is not available for this symbol
        # universe -- use the symbol's own realized-vol percentile rank
        # over its available history as a real-data stand-in.
        vol_history = [abs(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes)) if closes[i - 1]]
        if len(vol_history) >= 5:
            rank = sum(1 for v in vol_history if v <= hist_vol_5d) / len(vol_history)
        else:
            rank = vix_norm
        iv_rank = max(0.0, min(1.0, rank))
        iv_spike = 1.0 if iv_rank > 0.8 else 0.0
        iv_low   = 1.0 if iv_rank < 0.3 else 0.0

        # sector_strength PROXY: relative momentum vs NIFTY (real data),
        # rescaled from [-1,1] relative-momentum spread into [0,1].
        if nifty_bars and len(nifty_bars["close"]) > 5:
            nifty_mom5 = (nifty_bars["close"][-1] / nifty_bars["close"][-6]) - 1.0 \
                if nifty_bars["close"][-6] else 0.0
            rel_strength = mom_5d - nifty_mom5
        else:
            rel_strength = 0.0
        sector_strength = max(0.0, min(1.0, 0.5 + rel_strength * 10))

        gap_pct = ((opens[-1] / closes[-2]) - 1.0) if len(closes) >= 2 and closes[-2] else 0.0
        gap_up   = 1.0 if gap_pct >  0.004 else 0.0
        gap_down = 1.0 if gap_pct < -0.004 else 0.0

        # liquidity_score PROXY: real bid/ask spread data is not available;
        # use volume consistency (lower coefficient of variation = more
        # liquid/consistent trading, a defensible real-data stand-in).
        if len(vols) >= 10 and sum(vols[-20:]) > 0:
            vol_window = vols[-20:]
            vmean = sum(vol_window) / len(vol_window)
            vstd = math.sqrt(sum((x - vmean) ** 2 for x in vol_window) / len(vol_window))
            vol_cov = (vstd / vmean) if vmean else 1.0
        else:
            vol_cov = 1.0
        bid_ask_spread_norm = max(0.0, min(1.0, vol_cov * 0.3))
        liquidity_score = max(0.0, 1.0 - bid_ask_spread_norm)

        adx_score = _adx_wilder(highs, lows, closes, 14)
        strong_trend = 1.0 if adx_score > 0.6 else 0.0

        return {
            # Momentum
            "mom_1d":           mom_1d,
            "mom_5d":           mom_5d,
            "mom_10d":          mom_10d,
            "mom_20d":          mom_20d,
            "mom_positive":     1.0 if mom_5d > 0 else 0.0,
            # Volume
            "volume_ratio":     min(volume_ratio / 4.0, 1.0),
            "volume_spike":     volume_spike,
            "volume_ratio_raw": volume_ratio,
            # RSI
            "rsi_norm":         rsi / 100.0,
            "rsi":              rsi,
            "rsi_oversold":     rsi_oversold,
            "rsi_overbought":   rsi_overbought,
            "rsi_neutral":      rsi_neutral,
            # MACD
            "macd_signal_norm": macd_signal,
            "macd_bull":        macd_bull,
            "macd_bear":        macd_bear,
            # Bollinger Bands
            "bb_position":      bb_position,
            "bb_upper":         bb_upper,
            "bb_lower":         bb_lower,
            # Volatility
            "hist_vol_5d":      hist_vol_5d,
            "hist_vol_20d":     hist_vol_20d,
            "vol_compression":  vol_compression,
            # IV (proxy, real-data-derived)
            "iv_rank":          iv_rank,
            "iv_spike":         iv_spike,
            "iv_low":           iv_low,
            # Sector (proxy, real-data-derived)
            "sector_strength":  sector_strength,
            # Gap
            "gap_pct":          gap_pct,
            "gap_up":           gap_up,
            "gap_down":         gap_down,
            # Liquidity (proxy, real-data-derived)
            "liquidity_score":  liquidity_score,
            # Trend
            "adx_score":        adx_score,
            "strong_trend":     strong_trend,
        }

    # ── Internal: per-symbol features (synthetic fallback) ─────────

    def _symbol_features_synthetic(self, symbol: str,
                                    snap: MarketSnapshot,
                                    market_ctx: FeatureVector) -> FeatureVector:
        """
        Generate per-symbol technical features.

        Fallback path only (DTA-EDGE-FEATURE-REAL-001) -- used whenever a
        symbol has fewer than _MIN_REAL_HISTORY_BARS rows of real OHLCV
        history available. Unchanged from the original implementation:
        generated from a seed derived from the symbol name and the market
        regime, so that different symbols produce meaningfully different
        (but reproducible) feature vectors per regime.
        """
        rng = random.Random(hash(symbol + str(snap.regime) + snap.timestamp.strftime("%Y%m%d")))

        regime_score = market_ctx.get("regime_score", 0.5)
        vix_norm     = market_ctx.get("vix", 0.375)

        # Price momentum — positively correlated with regime
        mom_1d  = rng.gauss(regime_score * 0.01 - 0.005, 0.008)
        mom_5d  = rng.gauss(regime_score * 0.03 - 0.015, 0.02)
        mom_10d = rng.gauss(regime_score * 0.06 - 0.03,  0.04)
        mom_20d = rng.gauss(regime_score * 0.10 - 0.05,  0.07)

        # Volume ratio — spikes more common near range extremes
        vol_base     = 1.0 + abs(rng.gauss(0, 0.35))
        volume_ratio = vol_base * (1.0 + vix_norm * 0.5)
        volume_spike = 1.0 if volume_ratio > 2.0 else 0.0

        # RSI (14-day) — anti-correlated with momentum in range, follows in trend
        if snap.regime == RegimeLabel.RANGE_MARKET:
            rsi_base = 50.0 + rng.gauss(0, 18)
        else:
            rsi_base = 50.0 + (regime_score - 0.5) * 40 + rng.gauss(0, 10)
        rsi = max(5.0, min(95.0, rsi_base))
        rsi_oversold  = 1.0 if rsi < 35 else 0.0
        rsi_overbought= 1.0 if rsi > 65 else 0.0
        rsi_neutral   = 1.0 - rsi_oversold - rsi_overbought

        # MACD
        macd_signal = rng.gauss(mom_5d * 100, 0.15)   # sign indicates direction
        macd_bull   = 1.0 if macd_signal > 0.05  else 0.0
        macd_bear   = 1.0 if macd_signal < -0.05 else 0.0

        # Bollinger Band position  (-1 = lower, 0 = mid, +1 = upper)
        bb_position = max(-1.0, min(1.0, rng.gauss(regime_score * 2 - 1.0, 0.5)))
        bb_upper     = 1.0 if bb_position > 0.7  else 0.0
        bb_lower     = 1.0 if bb_position < -0.7 else 0.0

        # Volatility
        hist_vol_5d  = max(0.0, rng.gauss(vix_norm * 0.3 + 0.05, 0.04))
        hist_vol_20d = max(0.0, rng.gauss(vix_norm * 0.25 + 0.08, 0.05))
        vol_compression = 1.0 if hist_vol_5d < hist_vol_20d * 0.7 else 0.0

        # IV environment (options-relevant)
        iv_rank       = max(0.0, min(1.0, rng.gauss(vix_norm, 0.2)))
        iv_spike      = 1.0 if iv_rank > 0.8 else 0.0
        iv_low        = 1.0 if iv_rank < 0.3 else 0.0

        # Sector
        sector_strength = max(0.0, min(1.0,
            regime_score * 0.6 + rng.gauss(0.2, 0.15)))

        # Gap
        gap_pct = rng.gauss(mom_1d * 0.5, 0.003)
        gap_up  = 1.0 if gap_pct >  0.004 else 0.0
        gap_down= 1.0 if gap_pct < -0.004 else 0.0

        # Liquidity
        bid_ask_spread_norm = max(0.0, rng.gauss(0.05 + vix_norm * 0.1, 0.03))
        liquidity_score     = max(0.0, 1.0 - bid_ask_spread_norm)

        # Trend strength
        adx_score = max(0.0, min(1.0, abs(regime_score - 0.5) * 2
                                 + rng.gauss(0, 0.1)))
        strong_trend = 1.0 if adx_score > 0.6 else 0.0

        return {
            # Momentum
            "mom_1d":           mom_1d,
            "mom_5d":           mom_5d,
            "mom_10d":          mom_10d,
            "mom_20d":          mom_20d,
            "mom_positive":     1.0 if mom_5d > 0 else 0.0,
            # Volume
            "volume_ratio":     min(volume_ratio / 4.0, 1.0),
            "volume_spike":     volume_spike,
            "volume_ratio_raw": volume_ratio,
            # RSI
            "rsi_norm":         rsi / 100.0,
            "rsi":              rsi,
            "rsi_oversold":     rsi_oversold,
            "rsi_overbought":   rsi_overbought,
            "rsi_neutral":      rsi_neutral,
            # MACD
            "macd_signal_norm": max(-1.0, min(1.0, macd_signal)),
            "macd_bull":        macd_bull,
            "macd_bear":        macd_bear,
            # Bollinger Bands
            "bb_position":      bb_position,
            "bb_upper":         bb_upper,
            "bb_lower":         bb_lower,
            # Volatility
            "hist_vol_5d":      hist_vol_5d,
            "hist_vol_20d":     hist_vol_20d,
            "vol_compression":  vol_compression,
            # IV
            "iv_rank":          iv_rank,
            "iv_spike":         iv_spike,
            "iv_low":           iv_low,
            # Sector
            "sector_strength":  sector_strength,
            # Gap
            "gap_pct":          gap_pct,
            "gap_up":           gap_up,
            "gap_down":         gap_down,
            # Liquidity
            "liquidity_score":  liquidity_score,
            # Trend
            "adx_score":        adx_score,
            "strong_trend":     strong_trend,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _dummy_snapshot() -> MarketSnapshot:
    """Returns a minimal snapshot for introspection (feature name listing)."""
    from datetime import datetime
    return MarketSnapshot(
        timestamp=datetime.now(),
        indices={},
        regime=RegimeLabel.RANGE_MARKET,
        volatility=VolatilityLevel.MEDIUM,
        vix=15.0,
    )

