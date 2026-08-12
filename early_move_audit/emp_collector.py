"""
early_move_audit/emp_collector.py — EMP-001 data collection layer.

Fetches:
  • Daily OHLCV bars (90 days) via yfinance — for previous-day features
  • 5-minute intraday bars (60 days) via yfinance — for snapshot prices
  • PGA learning actions — for previous-day scanner flag context
  • Scan attrition JSONL — for scanner coverage context

All operations are READ-ONLY.  No live trading objects are touched.
Data quality gaps are recorded explicitly; values are never fabricated.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .emp_config import (
    EmpConfig, SNAPSHOT_TIMES, DAILY_INTERVAL, INTRADAY_INTERVAL,
    DAILY_PERIOD, INTRADAY_PERIOD, VOLUME_RATIO_WINDOW, YF_TIMEOUT,
    ROOT, classify_gap,
)

log = logging.getLogger(__name__)

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    yf = None  # type: ignore
    _YF_AVAILABLE = False

try:
    import pandas as pd
    _PD_AVAILABLE = True
except ImportError:
    pd = None  # type: ignore
    _PD_AVAILABLE = False

# Paths to existing pipeline outputs (read-only)
_PGA_DIR        = ROOT / "data" / "pga"
_ATTRITION_DIR  = ROOT / "data" / "scan_attrition"


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class DayRecord:
    """All available information for one (symbol, trading_date) pair."""
    date: str
    symbol: str

    # ── Previous trading day ──────────────────────────────────────────────────
    prev_close:        Optional[float] = None
    prev_return_pct:   Optional[float] = None   # (close_T-1 - close_T-2) / close_T-2 * 100
    prev_volume:       Optional[float] = None
    prev_20d_avg_vol:  Optional[float] = None
    prev_volume_ratio: Optional[float] = None   # prev_volume / prev_20d_avg_vol
    prev_high:         Optional[float] = None
    prev_low:          Optional[float] = None
    prev_range_pct:    Optional[float] = None   # (high - low) / close * 100

    # ── Current trading day OHLCV ─────────────────────────────────────────────
    open_price:      Optional[float] = None
    close_price:     Optional[float] = None
    day_high:        Optional[float] = None
    day_low:         Optional[float] = None
    day_volume:      Optional[float] = None

    # ── Derived scalar metrics ─────────────────────────────────────────────────
    gap_pct:         Optional[float] = None   # (open - prev_close) / prev_close * 100
    gap_class:       str             = "UNKNOWN"
    close_return_pct: Optional[float] = None  # (close - prev_close) / prev_close * 100

    # ── Intraday snapshot prices (None = data unavailable) ────────────────────
    p930:  Optional[float] = None
    p945:  Optional[float] = None
    p1000: Optional[float] = None
    p1100: Optional[float] = None
    p1300: Optional[float] = None
    p1500: Optional[float] = None

    # ── Returns from open to each snapshot ───────────────────────────────────
    # Computed as (p_snapshot - open) / open * 100
    ret_to_930:  Optional[float] = None
    ret_to_945:  Optional[float] = None
    ret_to_1000: Optional[float] = None
    ret_to_1100: Optional[float] = None
    ret_to_1300: Optional[float] = None
    ret_to_1500: Optional[float] = None

    # ── Previous-day scanner / learning context ───────────────────────────────
    was_in_prev_scan:  bool = False  # appeared in yesterday's scanner output
    was_prev_pga_flag: bool = False  # flagged by PGA the previous day
    was_prev_leader:   bool = False  # top-15 gainer/loser the previous day
    prev_leader_type:  str = "NONE"  # "WINNER" | "LOSER" | "NONE"

    # ── Data quality metadata ─────────────────────────────────────────────────
    has_daily:          bool = False
    has_intraday:       bool = False
    missing_snapshots:  List[str] = field(default_factory=list)
    data_note:          str = ""


@dataclass
class CollectionQuality:
    """Aggregate data quality summary for the full dataset."""
    total_symbol_days:    int = 0
    with_daily:           int = 0
    with_intraday:        int = 0
    with_prev_context:    int = 0
    snapshot_coverage:    Dict[str, float] = field(default_factory=dict)
    missing_dates:        List[str] = field(default_factory=list)
    yf_available:         bool = _YF_AVAILABLE
    notes:                List[str] = field(default_factory=list)


# ── Public API ────────────────────────────────────────────────────────────────

def collect_dataset(
    config: EmpConfig,
) -> Tuple[List[DayRecord], CollectionQuality]:
    """
    Build the full research dataset using yfinance + existing pipeline files.

    Returns (records, quality) where records is a flat list of DayRecord,
    one per (symbol, trading_date) pair.
    """
    if not _YF_AVAILABLE or not _PD_AVAILABLE:
        log.warning("[EmpCollector] yfinance or pandas unavailable — returning empty dataset")
        return [], CollectionQuality(notes=["yfinance/pandas not installed"])

    symbols = config.universe
    ns_syms = config.ns_symbols()

    log.info("[EmpCollector] Downloading daily bars for %d symbols (%s)", len(symbols), DAILY_PERIOD)
    daily_df = _download_daily(ns_syms)

    log.info("[EmpCollector] Downloading intraday bars (%s, %s)", INTRADAY_INTERVAL, INTRADAY_PERIOD)
    intraday_df = _download_intraday(ns_syms)

    # Build context from existing pipeline outputs
    pga_flags   = _load_pga_flags()
    attrition   = _load_attrition_symbols()

    records: List[DayRecord] = []
    quality = CollectionQuality()

    for sym, ns_sym in zip(symbols, ns_syms):
        sym_records = _build_symbol_records(
            sym, ns_sym, daily_df, intraday_df, pga_flags, attrition, config,
        )
        records.extend(sym_records)

    _compute_quality(records, quality)
    log.info(
        "[EmpCollector] Built %d records for %d symbols: daily=%d intraday=%d",
        len(records), len(symbols), quality.with_daily, quality.with_intraday,
    )
    return records, quality


# ── Download helpers ──────────────────────────────────────────────────────────

def _download_daily(ns_symbols: List[str]) -> "pd.DataFrame":
    """Download daily OHLCV for all symbols.  Returns MultiIndex DataFrame."""
    try:
        data = yf.download(
            " ".join(ns_symbols),
            period=DAILY_PERIOD,
            interval=DAILY_INTERVAL,
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=False,
            timeout=YF_TIMEOUT,
        )
        return data
    except Exception as exc:
        log.warning("[EmpCollector] Daily download failed: %s", exc)
        return pd.DataFrame()


def _download_intraday(ns_symbols: List[str]) -> "pd.DataFrame":
    """Download 5m intraday for all symbols.  Returns MultiIndex DataFrame."""
    try:
        data = yf.download(
            " ".join(ns_symbols),
            period=INTRADAY_PERIOD,
            interval=INTRADAY_INTERVAL,
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=False,
            timeout=YF_TIMEOUT,
        )
        return data
    except Exception as exc:
        log.warning("[EmpCollector] Intraday download failed: %s", exc)
        return pd.DataFrame()


# ── Per-symbol record building ────────────────────────────────────────────────

def _build_symbol_records(
    symbol:    str,
    ns_symbol: str,
    daily_df:  "pd.DataFrame",
    intraday_df: "pd.DataFrame",
    pga_flags: Dict[str, Set[str]],
    attrition: Dict[str, Set[str]],
    config:    EmpConfig,
) -> List[DayRecord]:
    """Build all DayRecords for one symbol across all available trading dates."""
    # Extract per-symbol slices
    daily   = _extract_symbol_daily(ns_symbol, daily_df)
    intraday = _extract_symbol_intraday(ns_symbol, intraday_df)

    if daily is None or daily.empty:
        return []

    records: List[DayRecord] = []
    daily_dates = [d.strftime("%Y-%m-%d") for d in daily.index]
    closes  = daily["Close"].values.tolist()
    opens   = daily["Open"].values.tolist()
    highs   = daily["High"].values.tolist()
    lows    = daily["Low"].values.tolist()
    vols    = daily["Volume"].values.tolist()

    # Limit to lookback_days most recent trading days
    max_days = config.lookback_days
    start_idx = max(0, len(daily_dates) - max_days)

    for i in range(start_idx, len(daily_dates)):
        date_str = daily_dates[i]
        rec = DayRecord(date=date_str, symbol=symbol)

        # Current day daily data
        close = _safe_float(closes[i])
        open_ = _safe_float(opens[i])
        high  = _safe_float(highs[i])
        low   = _safe_float(lows[i])
        vol   = _safe_float(vols[i])

        if close is not None:
            rec.has_daily    = True
            rec.open_price   = open_
            rec.close_price  = close
            rec.day_high     = high
            rec.day_low      = low
            rec.day_volume   = vol

        # Previous day data
        if i >= 1:
            prev_close = _safe_float(closes[i - 1])
            prev_high  = _safe_float(highs[i - 1])
            prev_low   = _safe_float(lows[i - 1])
            prev_vol   = _safe_float(vols[i - 1])
            rec.prev_close = prev_close
            rec.prev_high  = prev_high
            rec.prev_low   = prev_low
            rec.prev_volume = prev_vol

            if prev_close and close:
                # Previous-day return: T-1 close vs T-2 close
                if i >= 2:
                    prev_prev_close = _safe_float(closes[i - 2])
                    if prev_prev_close:
                        rec.prev_return_pct = (prev_close - prev_prev_close) / prev_prev_close * 100.0
                # Previous-day range
                if prev_high and prev_low:
                    rec.prev_range_pct = (prev_high - prev_low) / prev_close * 100.0

            # Volume ratio: prev_vol / 20-day avg
            window_start = max(0, i - VOLUME_RATIO_WINDOW)
            avg_vols = [_safe_float(vols[j]) for j in range(window_start, i)]
            valid_vols = [v for v in avg_vols if v and v > 0]
            if valid_vols and prev_vol:
                rec.prev_20d_avg_vol  = sum(valid_vols) / len(valid_vols)
                rec.prev_volume_ratio = prev_vol / rec.prev_20d_avg_vol

            # Gap
            if open_ and prev_close and prev_close != 0:
                rec.gap_pct   = (open_ - prev_close) / prev_close * 100.0
                rec.gap_class = classify_gap(rec.gap_pct)

            # Close return
            if close and prev_close and prev_close != 0:
                rec.close_return_pct = (close - prev_close) / prev_close * 100.0

        # Intraday snapshots
        _fill_snapshots(rec, intraday, date_str)

        # Returns from open to each snapshot
        if rec.open_price:
            for label, p in [
                ("ret_to_930",  rec.p930),
                ("ret_to_945",  rec.p945),
                ("ret_to_1000", rec.p1000),
                ("ret_to_1100", rec.p1100),
                ("ret_to_1300", rec.p1300),
                ("ret_to_1500", rec.p1500),
            ]:
                if p and rec.open_price != 0:
                    setattr(rec, label, (p - rec.open_price) / rec.open_price * 100.0)

        # Context: PGA flags, scan attrition
        prev_date = _prev_date_str(date_str)
        if prev_date:
            rec.was_prev_pga_flag = symbol in pga_flags.get(prev_date, set())
            rec.was_in_prev_scan  = symbol in attrition.get(prev_date, set())

        records.append(rec)

    return records


def _fill_snapshots(rec: DayRecord, intraday: "Optional[pd.DataFrame]", date_str: str) -> None:
    """Extract snapshot prices from 5m bars for the given date."""
    if intraday is None or intraday.empty:
        rec.missing_snapshots = list(SNAPSHOT_TIMES.keys())
        return

    try:
        # Filter to this trading date
        day_bars = _filter_day(intraday, date_str)
        if day_bars is None or day_bars.empty:
            rec.missing_snapshots = list(SNAPSHOT_TIMES.keys())
            return

        rec.has_intraday = True

        for label, time_str in SNAPSHOT_TIMES.items():
            price = _price_at_time(day_bars, time_str)
            setattr(rec, label, price)
            if price is None:
                rec.missing_snapshots.append(label)

        # Intraday high/low from 5m bars
        highs = day_bars["High"].dropna().tolist()
        lows  = day_bars["Low"].dropna().tolist()
        if highs:
            rec.day_high = max(rec.day_high or 0, max(highs)) or rec.day_high
        if lows and any(l > 0 for l in lows):
            valid_lows = [l for l in lows if l > 0]
            if valid_lows:
                rec.day_low = min(rec.day_low or float("inf"), min(valid_lows)) or rec.day_low

    except Exception as exc:
        log.debug("[EmpCollector] Snapshot fill failed %s %s: %s", rec.symbol, date_str, exc)
        rec.missing_snapshots = list(SNAPSHOT_TIMES.keys())
        rec.data_note = str(exc)


# ── DataFrame extraction helpers ──────────────────────────────────────────────

def _extract_symbol_daily(ns_sym: str, df: "pd.DataFrame") -> "Optional[pd.DataFrame]":
    if df is None or df.empty:
        return None
    try:
        if isinstance(df.columns, pd.MultiIndex):
            return df[ns_sym].dropna(how="all")
        return df.dropna(how="all")
    except (KeyError, TypeError):
        return None


def _extract_symbol_intraday(ns_sym: str, df: "pd.DataFrame") -> "Optional[pd.DataFrame]":
    if df is None or df.empty:
        return None
    try:
        if isinstance(df.columns, pd.MultiIndex):
            return df[ns_sym].dropna(how="all")
        return df.dropna(how="all")
    except (KeyError, TypeError):
        return None


def _filter_day(df: "pd.DataFrame", date_str: str) -> "Optional[pd.DataFrame]":
    """Return rows from df whose index date matches date_str."""
    try:
        idx = df.index
        if hasattr(idx, "tz") and idx.tz is not None:
            # Convert to IST for comparison
            idx_ist = idx.tz_convert("Asia/Kolkata")
        else:
            idx_ist = idx
        mask = idx_ist.normalize().strftime("%Y-%m-%d") == date_str
        result = df.loc[mask]
        return result if not result.empty else None
    except Exception:
        # Fallback: string comparison on index
        try:
            mask = [str(ts)[:10] == date_str for ts in df.index]
            result = df.loc[mask]
            return result if not result.empty else None
        except Exception:
            return None


def _price_at_time(day_bars: "pd.DataFrame", time_str: str) -> Optional[float]:
    """
    Return the close price of the 5m bar covering time_str (HH:MM, IST).

    We use the FIRST bar whose start time >= time_str and < time_str + 5min.
    This represents the price "as of time_str" without look-ahead: it uses
    only data available at that moment.
    """
    try:
        idx = day_bars.index
        if hasattr(idx, "tz") and idx.tz is not None:
            idx_ist = idx.tz_convert("Asia/Kolkata")
        else:
            idx_ist = idx

        h, m = map(int, time_str.split(":"))
        target_minutes = h * 60 + m

        for ts, row in zip(idx_ist, day_bars.itertuples()):
            bar_h = ts.hour
            bar_m = ts.minute
            bar_minutes = bar_h * 60 + bar_m
            if bar_minutes == target_minutes:
                val = _safe_float(row.Close)
                return val
        return None
    except Exception:
        return None


# ── PGA / attrition context loaders ──────────────────────────────────────────

def _load_pga_flags() -> Dict[str, Set[str]]:
    """
    Return dict: {date_str -> set of symbols flagged by PGA as Cat-E that day}.
    """
    flags: Dict[str, Set[str]] = {}
    if not _PGA_DIR.exists():
        return flags
    for date_dir in _PGA_DIR.iterdir():
        if not date_dir.is_dir():
            continue
        la_file = date_dir / "pga_learning_actions.json"
        if not la_file.exists():
            continue
        try:
            actions = json.loads(la_file.read_text(encoding="utf-8", errors="replace"))
            cat_e_syms = {a["symbol"] for a in actions if a.get("category") == "E"}
            flags[date_dir.name] = cat_e_syms
        except Exception as exc:
            log.debug("[EmpCollector] PGA flags load failed %s: %s", date_dir.name, exc)
    return flags


def _load_attrition_symbols() -> Dict[str, Set[str]]:
    """
    Return dict: {date_str -> set of symbols that appeared in scan attrition}.
    """
    syms: Dict[str, Set[str]] = {}
    if not _ATTRITION_DIR.exists():
        return syms
    for f in _ATTRITION_DIR.glob("*.jsonl"):
        date_str = f.stem
        try:
            seen: Set[str] = set()
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                seen.add(rec.get("symbol", ""))
            syms[date_str] = seen
        except Exception as exc:
            log.debug("[EmpCollector] Attrition load failed %s: %s", date_str, exc)
    return syms


# ── Quality computation ───────────────────────────────────────────────────────

def _compute_quality(records: List[DayRecord], quality: CollectionQuality) -> None:
    quality.total_symbol_days = len(records)
    quality.with_daily        = sum(1 for r in records if r.has_daily)
    quality.with_intraday     = sum(1 for r in records if r.has_intraday)
    quality.with_prev_context = sum(1 for r in records if r.was_prev_pga_flag or r.was_in_prev_scan)

    for label in SNAPSHOT_TIMES:
        present = sum(1 for r in records if getattr(r, label) is not None)
        total   = max(len(records), 1)
        quality.snapshot_coverage[label] = round(present / total * 100, 1)


# ── Misc utilities ────────────────────────────────────────────────────────────

def _safe_float(val) -> Optional[float]:
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _prev_date_str(date_str: str) -> Optional[str]:
    """Return the calendar day before date_str (not necessarily a trading day)."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (d - timedelta(days=1)).isoformat()
    except ValueError:
        return None
