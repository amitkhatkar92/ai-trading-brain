"""
Historical Data Loader
======================
Fetches the last N NSE trading days (default 30) of OHLCV + VIX data from
yfinance for both market indices AND individual Nifty 100 stocks.

Per-day output
--------------
Each DayData contains:

  raw_data   — dict that MarketDataAI.fetch() normally returns
               keys: indices, vix, pcr, breadth, fii_dii, data_source
  stock_watchlist — list of dicts that EquityScannerAI's _live_watchlist()
               returns, with REAL prices, RSI, resistance, support,
               volume_ratio — computed from the rolling historical window.

Both are injected by ReplayOrchestrator per day so ALL 12 layers run on
real historical data.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

# ── Index tickers ─────────────────────────────────────────────────────────────
_INDEX_MAP: Dict[str, str] = {
    "^NSEI":     "NIFTY 50",
    "^NSEBANK":  "NIFTY BANK",
    "^INDIAVIX": "__VIX__",
}

_SECTOR_MAP: Dict[str, str] = {
    "^CNXIT":     "NIFTY IT",
    "^CNXPHARMA": "NIFTY PHARMA",
    "^CNXFMCG":   "NIFTY FMCG",
    "^CNXAUTO":   "NIFTY AUTO",
}

# ── Nifty 100 equity watchlist (yfinance .NS suffix) ─────────────────────────
# Covers all 8 originally in EquityScannerAI._BASE_WATCHLIST + 22 more
# for broad Nifty 50/100 coverage across all sectors.
NSE_STOCKS: List[str] = [
    # Financials
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "BANKBARODA.NS",
    "BAJFINANCE.NS", "BAJAJFINSV.NS",
    # IT
    "TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS",
    # Energy / Commodities
    "RELIANCE.NS", "ONGC.NS", "BPCL.NS", "COALINDIA.NS",
    # Capital goods / Infra
    "LT.NS", "POWERGRID.NS", "NTPC.NS",
    # Metals
    "TATASTEEL.NS", "HINDALCO.NS",
    # FMCG / Consumer
    "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS",
    # Auto
    "MARUTI.NS", "M&M.NS", "TATAMOTORS.NS",
    # Pharma
    "SUNPHARMA.NS", "DRREDDY.NS",
    # Diversified
    "TITAN.NS", "ULTRACEMCO.NS", "GRASIM.NS",
]

# Replay window
TARGET_DAYS = 30
# Calendar-day fetch buffer: trading days are ~5/7 of calendar days,
# plus 25 extra for rolling-indicator warm-up (RSI-14 + resistance-20).
# Formula: ceil(target_days / 0.71) + 30
# Preset examples:
#   30  trading days → 72  + 30 = 102  (we use 90 as the default minimum)
#   63  trading days → 89  + 30 = 119  (~3 months)
#   126 trading days → 177 + 30 = 207  (~6 months)
#   252 trading days → 355 + 30 = 385  (~12 months)
FETCH_PERIOD_DAYS = 90   # default; overridden dynamically by load_historical_days()


def _fetch_period(target_days: int) -> int:
    """Compute calendar-day download window from a trading-day target."""
    import math
    return max(90, math.ceil(target_days / 0.71) + 30)

# Technical indicator windows
RSI_PERIOD    = 14
RESIST_WINDOW = 20   # rolling high  = resistance
SUPPORT_WINDOW= 20   # rolling low   = support
VOL_AVG_WINDOW= 20   # avg volume for vol_ratio


# ── Data containers ───────────────────────────────────────────────────────────

@dataclass
class DayData:
    """One trading day's worth of data ready for injection."""
    date:             date
    raw_data:         Dict[str, Any]         # for MarketDataAI.fetch()
    stock_watchlist:  List[Dict[str, Any]]   # for EquityScannerAI._live_watchlist()
    day_num:          int = 0                # 1-based index set by loader


# ── Public entry point ────────────────────────────────────────────────────────

def load_historical_days(
    target_days: int = TARGET_DAYS,
    include_stocks: bool = True,
) -> List[DayData]:
    """
    Download *target_days* of historical NSE data and return a chronological
    list of DayData objects (oldest first).

    Parameters
    ----------
    target_days    : how many trading days to replay
    include_stocks : if True, download individual NSE stocks for scanner injection
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError(
            "yfinance is required: pip install yfinance"
        ) from exc

    fetch_days = _fetch_period(target_days)

    # ── 1. Download indices ──────────────────────────────────────────────
    index_tickers = list(_INDEX_MAP.keys()) + list(_SECTOR_MAP.keys())
    log.info("[HistLoader] Downloading %dd index data (%d tickers) …",
             fetch_days, len(index_tickers))
    idx_df = _download(yf, index_tickers, fetch_days)

    # ── 2. Download NSE stocks ──────────────────────────────────────────
    stock_df = None
    if include_stocks:
        log.info("[HistLoader] Downloading %dd stock data (%d tickers) …",
                 fetch_days, len(NSE_STOCKS))
        stock_df = _download(yf, NSE_STOCKS, fetch_days)

    if idx_df is None or idx_df.empty:
        raise RuntimeError("[HistLoader] yfinance returned empty index DataFrame.")

    all_dates   = sorted(idx_df.index)
    replay_dates = all_dates[-target_days:]

    if len(replay_dates) < target_days:
        log.warning("[HistLoader] Only %d trading days available (requested %d).",
                    len(replay_dates), target_days)

    log.info("[HistLoader] Replay window: %s → %s  (%d days)",
             replay_dates[0].date(), replay_dates[-1].date(), len(replay_dates))

    # ── 3. Pre-build per-stock technical series ───────────────────────────────
    stock_series: Dict[str, Dict[str, list]] = {}
    if stock_df is not None and not stock_df.empty:
        stock_series = _build_stock_series(stock_df, NSE_STOCKS, all_dates)

    # ── 4. Assemble per-day DayData ───────────────────────────────────────────
    days: List[DayData] = []
    for day_num, ts in enumerate(replay_dates, start=1):
        try:
            raw  = _build_index_raw(idx_df, ts)
            wl   = _build_stock_watchlist(stock_series, ts, all_dates) if stock_series else []

            days.append(DayData(
                date            = ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10]),
                raw_data        = raw,
                stock_watchlist = wl,
                day_num         = day_num,
            ))

            nifty_ltp = raw["indices"].get("NIFTY 50", {}).get("ltp", 0)
            vix       = raw["vix"]
            chg       = raw["indices"].get("NIFTY 50", {}).get("change_pct", 0)
            bias = "BULL" if chg > 0.5 else ("BEAR" if chg < -0.5 else "RANGE")
            log.info(
                "  [Day %02d / %s]  NIFTY=%.0f (%+.2f%%)  "
                "VIX=%.1f  Bias=%-5s  Stocks=%d",
                day_num, str(ts.date()), nifty_ltp, chg, vix, bias, len(wl),
            )
        except Exception as exc:
            log.warning("[HistLoader] Skipping %s — %s", ts, exc)

    log.info("[HistLoader] Loaded %d trading days.", len(days))
    return days


# ── Helpers — downloading ─────────────────────────────────────────────────────

def _download(yf, tickers: List[str], period_days: int):
    """Download OHLCV data; returns None on failure.

    Uses explicit start/end dates because yfinance only accepts specific
    period strings (1mo, 3mo, 6mo, 1y, 2y, 5y, max) — arbitrary "544d"
    silently falls back to 1mo (~30 trading days).
    """
    from datetime import datetime, timedelta
    end_dt   = datetime.today()
    start_dt = end_dt - timedelta(days=period_days)
    start    = start_dt.strftime("%Y-%m-%d")
    end      = end_dt.strftime("%Y-%m-%d")
    log.debug("[HistLoader] _download: start=%s  end=%s  tickers=%d", start, end, len(tickers) if hasattr(tickers, '__len__') else 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            df = yf.download(
                tickers,
                start=start,
                end=end,
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=True,
                timeout=25,
            )
            return df if df is not None and not df.empty else None
        except Exception as exc:
            log.warning("[HistLoader] Download failed: %s", exc)
            return None


def _get_val(df, field: str, ticker: str, ts) -> Optional[float]:
    """Safely extract one cell from a (possibly multi-level) DataFrame."""
    try:
        col = (field, ticker)
        if col in df.columns:
            v = df.loc[ts, col]
        elif field in df.columns:
            v = df.loc[ts, field]
        else:
            return None
        return float(v) if v is not None and str(v) not in ("nan", "None") else None
    except (KeyError, TypeError):
        return None


# ── Helpers — index raw_data ──────────────────────────────────────────────────

def _build_index_raw(idx_df, ts) -> Dict[str, Any]:
    """Build the raw_data dict that MarketDataAI.fetch() normally returns."""
    indices: Dict[str, Any] = {}
    vix_val = 15.0
    all_map = {**_INDEX_MAP, **_SECTOR_MAP}

    for ticker, fname in all_map.items():
        close  = _get_val(idx_df, "Close",  ticker, ts)
        if close is None:
            continue
        open_  = _get_val(idx_df, "Open",   ticker, ts) or close
        high_  = _get_val(idx_df, "High",   ticker, ts) or close
        low_   = _get_val(idx_df, "Low",    ticker, ts) or close
        volume = _get_val(idx_df, "Volume", ticker, ts) or 0.0

        # Previous close for change %
        all_dates = list(idx_df.index)
        try:
            idx  = all_dates.index(ts)
            prev = _get_val(idx_df, "Close", ticker, all_dates[idx - 1]) if idx > 0 else close
        except (ValueError, IndexError):
            prev = close
        prev = prev or close
        chg  = (close - prev) / prev * 100 if prev else 0.0

        if fname == "__VIX__":
            vix_val = close
            continue

        indices[fname] = {
            "symbol":     fname,
            "ltp":        close,
            "open":       open_,
            "high":       high_,
            "low":        low_,
            "close":      close,
            "volume":     int(volume),
            "change_pct": round(chg, 4),
            "source":     "HISTORICAL",
        }

    if not indices:
        raise ValueError("No index data for this date — possible market holiday.")

    nifty_chg = indices.get("NIFTY 50", {}).get("change_pct", 0.0)
    return {
        "indices":     indices,
        "vix":         round(vix_val, 2),
        "pcr":         _pcr_from_vix(vix_val),
        "breadth":     _breadth_from_change(nifty_chg),
        "fii_dii":     {"fii_buy": 0, "fii_sell": 0, "dii_buy": 0, "dii_sell": 0},
        "data_source": "HISTORICAL",
        "vix_source":  "HISTORICAL",
    }


# ── Helpers — stock watchlist ─────────────────────────────────────────────────

def _build_stock_series(stock_df, tickers: List[str], all_dates) -> Dict[str, Dict[str, list]]:
    """
    Pre-compute per-stock time-series of (closes, highs, lows, volumes, dates).
    Returns {ticker: {"dates": [...], "closes": [...], "highs": [...], "lows": [...], "volumes": [...]}}
    Used to compute rolling indicators and intraday ranges at each replay day.
    """
    series: Dict[str, Dict[str, list]] = {}
    for ticker in tickers:
        closes  = []
        highs   = []
        lows    = []
        volumes = []
        dates   = []
        for ts in all_dates:
            c = _get_val(stock_df, "Close",  ticker, ts)
            h = _get_val(stock_df, "High",   ticker, ts)
            l = _get_val(stock_df, "Low",    ticker, ts)
            v = _get_val(stock_df, "Volume", ticker, ts)
            if c is not None:
                closes.append(c)
                highs.append(h if h is not None else c)
                lows.append(l if l is not None else c)
                volumes.append(v or 0.0)
                dates.append(ts)
        if len(closes) > RSI_PERIOD + 2:
            series[ticker] = {
                "dates":   dates,
                "closes":  closes,
                "highs":   highs,
                "lows":    lows,
                "volumes": volumes,
            }
    log.info("[HistLoader] Stock series built for %d / %d tickers.",
             len(series), len(tickers))
    return series


def _build_stock_watchlist(
    stock_series: Dict[str, Dict[str, list]],
    ts,
    all_dates,
) -> List[Dict[str, Any]]:
    """
    For timestamp *ts*, compute real RSI / resistance / support / volume_ratio
    for every ticker in stock_series and return in EquityScannerAI format.
    """
    rows: List[Dict[str, Any]] = []
    for ticker, s in stock_series.items():
        try:
            dates  = s["dates"]
            closes = s["closes"]
            vols   = s["volumes"]

            # Position index in this ticker's own date list
            if ts not in dates:
                continue
            i = dates.index(ts)
            if i < RSI_PERIOD + 1:
                continue   # not enough history yet

            cur_close = closes[i]
            day_high  = s["highs"][i]  if "highs" in s else cur_close
            day_low   = s["lows"][i]   if "lows"  in s else cur_close

            # Resistance = max close over prior RESIST_WINDOW days (not including today)
            w_start = max(0, i - RESIST_WINDOW)
            hist_closes = closes[w_start:i]
            resistance  = max(hist_closes) if hist_closes else cur_close * 1.01

            # Support = min close over prior SUPPORT_WINDOW days
            support     = min(hist_closes) if hist_closes else cur_close * 0.99

            # RSI (14-period)
            rsi   = _compute_rsi(closes[max(0, i - RSI_PERIOD - 5): i + 1])

            # Volume ratio = today vol / 20-day avg vol
            v_start  = max(0, i - VOL_AVG_WINDOW)
            avg_vol  = sum(vols[v_start:i]) / max(len(vols[v_start:i]), 1)
            vol_ratio= round(vols[i] / avg_vol, 2) if avg_vol > 0 else 1.0

            # Strip .NS suffix for display symbol
            symbol = ticker.replace(".NS", "")

            rows.append({
                "symbol":       symbol,
                "ltp":          round(cur_close, 2),
                "day_high":     round(day_high, 2),
                "day_low":      round(day_low, 2),
                "resistance":   round(resistance, 2),
                "support":      round(support, 2),
                "volume_ratio": min(vol_ratio, 10.0),
                "rsi":          round(rsi, 1),
            })
        except Exception:
            pass   # silently skip tickers with data gaps

    return rows


# ── Technical indicators ──────────────────────────────────────────────────────

def _compute_rsi(closes: List[float], period: int = RSI_PERIOD) -> float:
    """Wilder's RSI.  Returns 50 when insufficient history."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-period:]
    gains  = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]
    avg_g  = sum(gains)  / period
    avg_l  = sum(losses) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100 - (100 / (1 + rs)), 2)


def _breadth_from_change(nifty_change_pct: float) -> float:
    if nifty_change_pct > 1.5:  return 0.72
    if nifty_change_pct > 0.5:  return 0.62
    if nifty_change_pct < -1.5: return 0.28
    if nifty_change_pct < -0.5: return 0.38
    return 0.50


def _pcr_from_vix(vix: float) -> float:
    if vix >= 20: return 1.3
    if vix >= 16: return 1.1
    if vix >= 12: return 0.9
    return 0.8
