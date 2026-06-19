"""
analysis/nse_data_loader.py
==============================
REAL_OPTIONS_AUDIT_002 — Real market data loader.

Downloads NIFTY 50, BANKNIFTY, and India VIX history from yfinance.
Caches to CSV so subsequent runs are instant.

No imports from live trading system.
No writes to any production database.

Regime classification uses the same VIX threshold (22.0) and
trend-strength model as option_regime_classifier.py so that
REAL_OPTIONS_AUDIT_002 results are directly comparable to
OPTIONS_AUDIT_001 synthetic results.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

# Silence yfinance FutureWarning noise
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import pandas as pd

_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR  = os.path.join(_ROOT, "data", "real_options")

TICKERS = {
    "NIFTY":     "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "VIX":       "^INDIAVIX",
}

# Regime thresholds — must match option_regime_classifier.py exactly
VIX_HIGH        = 22.0
VIX_TIGHT       = 14.0
ADX_TREND       = 25.0    # ADX above this → trending
EMA_FAST_DAYS   = 20
EMA_SLOW_DAYS   = 50
ATR_PERIOD      = 14


# ── Column names in the returned DataFrame ────────────────────────────────────
# date, open, high, low, close, volume, vix, atr, trend_strength,
# ema_fast, ema_slow, regime, sub_regime, vix_bucket, direction,
# ret_1d, ret_5d, ret_10d, ret_21d

@dataclass
class MarketDay:
    """One row of processed market data for one underlying."""
    date:           str
    underlying:     str
    open:           float
    high:           float
    low:            float
    close:          float
    vix:            float
    atr:            float
    trend_strength: float   # 0–1 (ADX / 40 capped)
    ema_fast:       float
    ema_slow:       float
    regime:         str     # HIGH_VOL / TRENDING / RANGING
    vix_bucket:     str     # LOW / MEDIUM / HIGH
    direction:      str     # BULL / BEAR / NEUTRAL (based on EMA cross)
    ret_1d:         float   # next 1-day return (%)
    ret_5d:         float   # next 5-day return (%)
    ret_10d:        float   # next 10-day return (%)
    ret_21d:        float   # next 21-day return (%)
    abs_move_5d:    float   # |ret_5d|
    abs_move_10d:   float   # |ret_10d|


def _cache_path(underlying: str, period: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    date_tag = datetime.now().strftime("%Y%m%d")
    return os.path.join(CACHE_DIR, f"{underlying}_{period}_{date_tag}.csv")


def _download_raw(ticker: str, period: str) -> pd.DataFrame:
    """Download OHLCV from yfinance."""
    import yfinance as yf
    df = yf.download(
        ticker, period=period, auto_adjust=True,
        progress=False, timeout=30,
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df.columns = [c.lower() for c in df.columns]
    df.index.name = "date"
    df.index = pd.to_datetime(df.index)
    return df.dropna(subset=["close"])


def _download_vix(period: str) -> pd.Series:
    """Download India VIX as a Series indexed by date."""
    import yfinance as yf
    df = yf.download(
        "^INDIAVIX", period=period, auto_adjust=True,
        progress=False, timeout=30,
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df.columns = [c.lower() for c in df.columns]
    df.index = pd.to_datetime(df.index)
    return df["close"].dropna()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    """Simple ATR (no pandas_ta dependency)."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def _classify_regime(vix: float, ts: float) -> str:
    if vix > VIX_HIGH:
        return "HIGH_VOL"
    return "TRENDING" if ts > 0.65 else "RANGING"


def _classify_vix_bucket(vix: float) -> str:
    if vix < VIX_TIGHT:
        return "LOW"
    if vix < VIX_HIGH:
        return "MEDIUM"
    return "HIGH"


def _classify_direction(ema_fast: float, ema_slow: float, tolerance: float = 0.005) -> str:
    ratio = ema_fast / ema_slow - 1
    if ratio > tolerance:
        return "BULL"
    if ratio < -tolerance:
        return "BEAR"
    return "NEUTRAL"


def load_market_history(
    underlying: str = "NIFTY",
    period:     str = "2y",
    use_cache:  bool = True,
) -> list[MarketDay]:
    """
    Load, enrich, and return real market history for one underlying.

    Args:
        underlying: "NIFTY" or "BANKNIFTY"
        period:     yfinance period string e.g. "2y", "1y", "6mo"
        use_cache:  if True, saves/reads CSV cache (one per calendar day)

    Returns:
        List of MarketDay objects — one per trading session
        Only rows where all forward returns are calculable are included.
    """
    ticker      = TICKERS[underlying]
    cache_file  = _cache_path(underlying, period)

    if use_cache and os.path.exists(cache_file):
        df = pd.read_csv(cache_file, index_col="date", parse_dates=True)
    else:
        # ── Download underlying ──────────────────────────────────────────────
        price = _download_raw(ticker, period)

        # ── Download VIX (same period) ───────────────────────────────────────
        vix_series = _download_vix(period)

        # ── Align VIX to price dates (forward-fill) ──────────────────────────
        vix_aligned = vix_series.reindex(price.index, method="ffill").fillna(15.0)

        # ── Technical indicators ─────────────────────────────────────────────
        price["vix"]       = vix_aligned
        price["atr"]       = _atr(price["high"], price["low"], price["close"], ATR_PERIOD)
        price["ema_fast"]  = price["close"].ewm(span=EMA_FAST_DAYS, adjust=False).mean()
        price["ema_slow"]  = price["close"].ewm(span=EMA_SLOW_DAYS, adjust=False).mean()

        # Trend strength: ADX proxy via directional price velocity
        # We use a 14-day rolling Sharpe of daily returns as a clean proxy.
        ret     = price["close"].pct_change()
        roll_mu = ret.rolling(14).mean()
        roll_sd = ret.rolling(14).std().replace(0, 1e-9)
        # Normalise to 0–1 (cap at 0 and 1)
        ts_raw  = (roll_mu / roll_sd).clip(-2, 2)          # range -2 to +2
        price["trend_strength"] = ((ts_raw + 2) / 4).round(4)  # 0–1

        # ── Forward returns ──────────────────────────────────────────────────
        c = price["close"]
        price["ret_1d"]  = (c.shift(-1)  / c - 1) * 100
        price["ret_5d"]  = (c.shift(-5)  / c - 1) * 100
        price["ret_10d"] = (c.shift(-10) / c - 1) * 100
        price["ret_21d"] = (c.shift(-21) / c - 1) * 100
        price["abs_move_5d"]  = price["ret_5d"].abs()
        price["abs_move_10d"] = price["ret_10d"].abs()

        # ── Derived regime fields ────────────────────────────────────────────
        price["regime"]     = price.apply(
            lambda r: _classify_regime(r["vix"], r["trend_strength"]), axis=1
        )
        price["vix_bucket"] = price["vix"].apply(_classify_vix_bucket)
        price["direction"]  = price.apply(
            lambda r: _classify_direction(r["ema_fast"], r["ema_slow"]), axis=1
        )

        df = price.dropna(subset=["ret_21d"])   # drop rows without full forward window
        df.index.name = "date"
        if use_cache:
            df.to_csv(cache_file)

    df.index.name = "date"
    result = []
    for date, row in df.iterrows():
        try:
            result.append(MarketDay(
                date           = str(date)[:10],
                underlying     = underlying,
                open           = float(row["open"]),
                high           = float(row["high"]),
                low            = float(row["low"]),
                close          = float(row["close"]),
                vix            = float(row["vix"]),
                atr            = float(row.get("atr", 0) or 0),
                trend_strength = float(row.get("trend_strength", 0.5)),
                ema_fast       = float(row["ema_fast"]),
                ema_slow       = float(row["ema_slow"]),
                regime         = str(row["regime"]),
                vix_bucket     = str(row["vix_bucket"]),
                direction      = str(row["direction"]),
                ret_1d         = float(row["ret_1d"]),
                ret_5d         = float(row["ret_5d"]),
                ret_10d        = float(row["ret_10d"]),
                ret_21d        = float(row["ret_21d"]),
                abs_move_5d    = float(row["abs_move_5d"]),
                abs_move_10d   = float(row["abs_move_10d"]),
            ))
        except (KeyError, ValueError, TypeError):
            continue

    return result


def regime_distribution(days: list[MarketDay]) -> dict:
    """Count of sessions per regime."""
    counts: dict[str, int] = {}
    for d in days:
        counts[d.regime] = counts.get(d.regime, 0) + 1
    return counts
