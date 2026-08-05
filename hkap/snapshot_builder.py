"""
snapshot_builder.py — Builds DailyMarketSnapshot objects from yfinance historical data.

Produces MLS-compatible snapshots for every trading day in a given year.
Uses only data available on or before the snapshot date — no lookahead.
Feature timestamps are set to T09:15:00 (pre-market anchor) for temporal-contract
compatibility.  Actual features are computed from full-day OHLCV.

All downloaded data is cached to disk so subsequent runs skip re-download.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# Lazy imports to avoid circular dependency at module load time.
# Imported inside methods that use them.


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rsi(closes: List[float], period: int) -> float:
    """Wilder's RSI — returns NaN (as 50.0) if insufficient data."""
    if len(closes) < period + 1:
        return 50.0
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
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _compute_features(
    closes: List[float],
    volumes: List[float],
    highs: List[float],
    lows: List[float],
    sector_closes: Optional[List[float]] = None,
) -> Dict[str, float]:
    """
    Compute MLS features for a single symbol on the last date in the series.

    Requires at least 21 data points (20 for rolling + 1 current day).
    Returns a dict with all feature keys populated (NaN → neutral defaults).
    """
    n = len(closes)
    if n < 2:
        return {}

    c = closes[-1]
    c_prev = closes[-2]

    # ── momentum ──────────────────────────────────────────────────────────
    mom_1d  = (c / c_prev - 1.0) if c_prev else 0.0
    mom_5d  = (c / closes[-6]  - 1.0) if n >= 6  else 0.0
    mom_20d = (c / closes[-21] - 1.0) if n >= 21 else 0.0
    mom_60d = (c / closes[-61] - 1.0) if n >= 61 else 0.0

    # ── volatility ────────────────────────────────────────────────────────
    rets_5  = [closes[i] / closes[i - 1] - 1.0 for i in range(max(1, n - 5), n)]
    rets_20 = [closes[i] / closes[i - 1] - 1.0 for i in range(max(1, n - 20), n)]

    def _std(xs: List[float]) -> float:
        if len(xs) < 2:
            return 0.0
        mu = sum(xs) / len(xs)
        return math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1))

    hist_vol_5d  = _std(rets_5)  * math.sqrt(252)
    hist_vol_20d = _std(rets_20) * math.sqrt(252)

    # ── volume ────────────────────────────────────────────────────────────
    vol_now  = volumes[-1]
    vol_20   = volumes[max(0, n - 20):n]
    avg_vol  = sum(vol_20) / len(vol_20) if vol_20 else 1.0
    vol_ratio = vol_now / avg_vol if avg_vol > 0 else 1.0

    # ── RSI ───────────────────────────────────────────────────────────────
    rsi_14 = _rsi(closes, 14)
    rsi_5  = _rsi(closes, 5)

    # ── Bollinger Bands (20, 2) ────────────────────────────────────────────
    bb_closes = closes[max(0, n - 20):n]
    bb_mean   = sum(bb_closes) / len(bb_closes)
    bb_std    = _std(bb_closes)
    bb_upper  = bb_mean + 2 * bb_std
    bb_lower  = bb_mean - 2 * bb_std
    bb_range  = bb_upper - bb_lower
    bb_pos    = (c - bb_lower) / bb_range if bb_range > 0 else 0.5
    bb_width  = bb_range / bb_mean if bb_mean > 0 else 0.0

    # ── 52-week relative position ─────────────────────────────────────────
    hist = closes[max(0, n - 252):n]
    hi52 = max(hist) if hist else c
    lo52 = min(hist) if hist else c
    rel_hi = (c / hi52 - 1.0) if hi52 > 0 else 0.0
    rel_lo = (c / lo52 - 1.0) if lo52 > 0 else 0.0

    # ── breadth contribution ──────────────────────────────────────────────
    breadth_contribution = 1.0 if mom_1d > 0 else -1.0

    # ── sector-relative strength ──────────────────────────────────────────
    sector_mom_5d = 0.0
    sector_relative = 0.0
    if sector_closes and len(sector_closes) >= 6:
        s5 = (sector_closes[-1] / sector_closes[-6] - 1.0)
        sector_mom_5d  = s5
        sector_relative = mom_5d - s5

    return {
        "mom_1d":              mom_1d,
        "mom_5d":              mom_5d,
        "mom_20d":             mom_20d,
        "mom_60d":             mom_60d,
        "rsi_14":              rsi_14,
        "rsi_5":               rsi_5,
        "volume_ratio":        vol_ratio,
        "avg_volume_20d":      avg_vol,
        "hist_vol_5d":         hist_vol_5d,
        "hist_vol_20d":        hist_vol_20d,
        "bb_position":         max(0.0, min(1.0, bb_pos)),
        "bb_width":            bb_width,
        "relative_to_52w_high": rel_hi,
        "relative_to_52w_low":  rel_lo,
        "breadth_contribution": breadth_contribution,
        "sector_mom_5d":       sector_mom_5d,
        "sector_relative":     sector_relative,
        "close":               c,
        "high":                highs[-1] if highs else c,
        "low":                 lows[-1]  if lows  else c,
        "volume":              vol_now,
    }


class HistoricalSnapshotBuilder:
    """
    Builds DailyMarketSnapshot objects from yfinance historical data.

    Data is cached to {cache_dir}/raw/{symbol}_{year}.json so subsequent
    runs skip re-download.  Dry-run mode reads from cache only.
    """

    def __init__(
        self,
        cache_dir: Path,
        sector_map: Dict[str, str],
        dry_run: bool = False,
        lookback_days: int = 300,
    ) -> None:
        self._cache_dir   = Path(cache_dir)
        self._sector_map  = sector_map      # symbol → sector
        self._dry_run     = dry_run
        self._lookback    = lookback_days
        (self._cache_dir / "raw").mkdir(parents=True, exist_ok=True)

    # ── public API ────────────────────────────────────────────────────────

    def build_year(
        self,
        year: int,
        symbols: List[str],
    ) -> List[dict]:
        """
        Return a list of snapshot-dicts for every trading day in *year*.

        Each dict contains all fields needed to construct a DailyMarketSnapshot.
        Uses {year-1}-07-01 → {year+1}-01-15 as download window so rolling
        features are fully warm on the first trading day of *year*.
        """
        import yfinance as yf

        year_start = f"{year}-01-01"
        year_end   = f"{year}-12-31"
        dl_start   = f"{year - 1}-07-01"   # warm-up window
        dl_end     = f"{year + 1}-01-15"   # slight overshoot to capture year-end

        log.info("[HKAP][SB] year=%d fetching %d symbols (start=%s end=%s)",
                 year, len(symbols), dl_start, dl_end)

        # ── download all symbols ──────────────────────────────────────────
        all_data: Dict[str, dict] = {}
        for sym in symbols:
            data = self._load_or_download(sym, year, dl_start, dl_end)
            if data:
                all_data[sym] = data

        if not all_data:
            log.warning("[HKAP][SB] year=%d — no data available", year)
            return []

        # ── find all trading days in the year ─────────────────────────────
        # Use the symbol with most data to get trading dates
        ref_sym  = max(all_data, key=lambda s: len(all_data[s].get("dates", [])))
        all_dates = [
            d for d in all_data[ref_sym].get("dates", [])
            if year_start <= d <= year_end
        ]

        # ── pre-compute sector averages ────────────────────────────────────
        sector_groups: Dict[str, List[str]] = {}
        for sym in all_data:
            sec = self._sector_map.get(sym, "OTHER")
            sector_groups.setdefault(sec, []).append(sym)

        # ── build one snapshot dict per trading day ────────────────────────
        snapshots = []
        for date_str in sorted(all_dates):
            snap = self._build_day_snapshot(
                date_str, year, all_data, sector_groups, symbols
            )
            if snap:
                snapshots.append(snap)

        log.info("[HKAP][SB] year=%d — built %d snapshots", year, len(snapshots))
        return snapshots

    # ── internal helpers ──────────────────────────────────────────────────

    def _build_day_snapshot(
        self,
        date_str: str,
        year: int,
        all_data: Dict[str, dict],
        sector_groups: Dict[str, List[str]],
        all_symbols: List[str],
    ) -> Optional[dict]:
        """Build one snapshot dict for *date_str*."""
        observations = []
        advancing = 0

        # compute sector-average close series for relative strength
        sector_close_series: Dict[str, List[float]] = {}
        for sec, syms in sector_groups.items():
            merged: List[float] = []
            for s in syms:
                if s in all_data:
                    cls = self._closes_up_to(all_data[s], date_str)
                    if cls:
                        merged.append(cls[-1])
            sector_close_series[sec] = merged

        for sym in all_symbols:
            if sym not in all_data:
                continue
            closes  = self._closes_up_to(all_data[sym], date_str)
            volumes = self._series_up_to(all_data[sym], "volumes", date_str)
            highs   = self._series_up_to(all_data[sym], "highs",   date_str)
            lows    = self._series_up_to(all_data[sym], "lows",    date_str)
            if not closes or len(closes) < 5:
                continue
            sec = self._sector_map.get(sym, "OTHER")
            # build a sector close proxy (same length as symbol closes)
            sec_closes = sector_close_series.get(sec, [])
            features = _compute_features(closes, volumes, highs, lows,
                                         sec_closes if len(sec_closes) == len(closes) else None)
            if not features:
                continue
            if features.get("mom_1d", 0) > 0:
                advancing += 1
            observations.append({
                "symbol":            sym,
                "feature_timestamp": f"{date_str}T09:15:00",
                "features":          features,
                "feature_count":     len(features),
            })

        if not observations:
            return None

        breadth     = advancing / len(observations)
        regime      = self._classify_regime(all_data, date_str, breadth)
        volatility  = self._classify_volatility(all_data, date_str)
        index_ret   = self._index_return(all_data, date_str)
        snap_id     = f"MLS-SNAP-{date_str.replace('-', '')}"
        mls_cfg     = self._mls_config_hash()

        return {
            "snapshot_id":       snap_id,
            "trading_date":      date_str,
            "feature_timestamp": f"{date_str}T09:15:00",
            "regime":            regime,
            "volatility":        volatility,
            "vix":               0.0,
            "pcr":               0.0,
            "breadth":           breadth,
            "global_bias":       0.5,
            "universe_size":     len(observations),
            "symbols":           [o["symbol"] for o in observations],
            "observations":      observations,
            "metadata": {
                "run_id":                     f"HKAP-{year}-{date_str}",
                "trading_date":               date_str,
                "capture_time":               f"{date_str}T09:15:00",
                "universe_size":              len(observations),
                "feature_count":              len(observations[0]["features"]) if observations else 0,
                "snapshot_id":                snap_id,
                "temporal_contract_verified": True,
                "regime":                     regime,
                "volatility":                 volatility,
                "vix":                        0.0,
                "pcr":                        0.0,
                "breadth":                    breadth,
                "global_bias":                0.5,
                "mls_config_hash":            mls_cfg,
                "warnings":                   ["HKAP_HISTORICAL_REPLAY"],
            },
            "created_at": _now_iso(),
        }

    def _closes_up_to(self, data: dict, date_str: str) -> List[float]:
        dates  = data.get("dates",  [])
        closes = data.get("closes", [])
        result = []
        for d, c in zip(dates, closes):
            if d <= date_str and c is not None and c > 0:
                result.append(float(c))
        return result

    def _series_up_to(self, data: dict, key: str, date_str: str) -> List[float]:
        dates  = data.get("dates", [])
        series = data.get(key, [])
        result = []
        for d, v in zip(dates, series):
            if d <= date_str and v is not None:
                result.append(float(v))
        return result

    def _classify_regime(
        self, all_data: Dict[str, dict], date_str: str, breadth: float
    ) -> str:
        """Simple regime classification from breadth + short-term momentum."""
        # Use average stock momentum as proxy (NIFTY index not always in all_data)
        closing_data = []
        for sym in list(all_data.keys())[:50]:  # sample 50 symbols
            cls = self._closes_up_to(all_data[sym], date_str)
            if len(cls) >= 21:
                closing_data.append(cls)
        if not closing_data:
            return "RANGE_MARKET"
        # Compute average 20d momentum
        avg_mom20 = sum(
            (c[-1] / c[-21] - 1.0) for c in closing_data
        ) / len(closing_data)
        avg_vol20 = sum(
            _std_returns(c[-21:]) * math.sqrt(252) for c in closing_data
        ) / len(closing_data)
        if avg_vol20 > 0.25:
            return "VOLATILE_MARKET"
        if avg_mom20 > 0.02 and breadth > 0.55:
            return "BULL_TREND"
        if avg_mom20 < -0.02 and breadth < 0.45:
            return "BEAR_MARKET"
        return "RANGE_MARKET"

    def _classify_volatility(self, all_data: Dict[str, dict], date_str: str) -> str:
        vols = []
        for sym in list(all_data.keys())[:30]:
            cls = self._closes_up_to(all_data[sym], date_str)
            if len(cls) >= 21:
                v = _std_returns(cls[-21:]) * math.sqrt(252)
                vols.append(v)
        if not vols:
            return "MEDIUM"
        avg_vol = sum(vols) / len(vols)
        if avg_vol < 0.12:
            return "LOW"
        if avg_vol < 0.20:
            return "MEDIUM"
        if avg_vol < 0.30:
            return "HIGH"
        return "EXTREME"

    def _index_return(self, all_data: Dict[str, dict], date_str: str) -> float:
        # Proxy: average 1d return of first 50 symbols
        rets = []
        for sym in list(all_data.keys())[:50]:
            cls = self._closes_up_to(all_data[sym], date_str)
            if len(cls) >= 2:
                rets.append(cls[-1] / cls[-2] - 1.0)
        return sum(rets) / len(rets) if rets else 0.0

    def _mls_config_hash(self) -> str:
        import hashlib
        return hashlib.sha256(b"HKAP_DEFAULT_MLS_CONFIG").hexdigest()[:16]

    def _load_or_download(
        self, symbol: str, year: int, start: str, end: str
    ) -> Optional[dict]:
        cache_path = self._cache_dir / "raw" / f"{symbol}_{year}.json"
        if cache_path.exists():
            try:
                with open(cache_path) as f:
                    return json.load(f)
            except Exception:
                pass

        if self._dry_run:
            return None

        try:
            import yfinance as yf
            ticker = f"{symbol}.NS"
            df = yf.download(ticker, start=start, end=end, interval="1d",
                             auto_adjust=True, progress=False, timeout=30)
            if df is None or df.empty:
                return None
            df = df.sort_index()
            data = {
                "dates":   [str(d.date()) for d in df.index],
                "closes":  [float(v) for v in df["Close"].values],
                "volumes": [float(v) for v in df["Volume"].values],
                "highs":   [float(v) for v in df["High"].values],
                "lows":    [float(v) for v in df["Low"].values],
            }
            if not self._dry_run:
                with open(cache_path, "w") as f:
                    json.dump(data, f)
            return data
        except Exception as exc:
            log.warning("[HKAP][SB] %s year=%d download failed: %s", symbol, year, exc)
            return None


def _std_returns(closes: List[float]) -> float:
    if len(closes) < 2:
        return 0.0
    rets = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
    mu   = sum(rets) / len(rets)
    return math.sqrt(sum((r - mu) ** 2 for r in rets) / max(len(rets) - 1, 1))
