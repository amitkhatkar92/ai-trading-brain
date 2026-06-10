"""
Pre-Market Refiner — Phase G
=============================
Scheduled at 08:45 IST (03:15 UTC) on trading days.
Applies overnight gap data and conviction decay to candidates already prepared
by market_scanner.py (Phase D), then updates daily_candidates.json in place.

Hard timeout: must complete before PREMARKET_DEADLINE_UTC_HHMM (09:10 IST / 03:40 UTC).
If the deadline is missed, existing candidates are used as-is by the live engine.

Responsibilities:
  1. Load today's prepared candidates from CandidateStore
  2. Fetch overnight gap (last-close → pre-open) from Yahoo for each candidate
  3. Apply conviction_decay: reduce volume_ratio / RSI scores for slow setups
  4. Apply sector_regime_bias from GlobalDataAI.get_sector_regime_bias()
  5. Set valid_until_utc per setup type:
       - breakout      → 11:00 IST (03:30 UTC)  — momentum fades mid-session
       - trend_pullback → 14:00 IST (08:30 UTC)  — valid into afternoon
       - mean_reversion → 13:00 IST (07:30 UTC)  — oversold bounce window closes
       - neutral / other → 15:00 IST (09:30 UTC) — near close
  6. Write premarket_refresh_complete = True to candidate store

Design constraints:
  - MUST NOT import from Layers 5-17
  - MUST complete before PREMARKET_DEADLINE_UTC_HHMM
  - If any step fails, write partial results (better than stale file)
  - Every candidate still passes full debate + governance before execution
"""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from opportunity_engine.candidate_store import CandidateStore
from utils import get_logger

log = get_logger(__name__)

# ── Setup-type → valid_until_utc rules ───────────────────────────────────────
# Times in UTC (IST = UTC + 5:30)
_VALID_UNTIL_UTC: Dict[str, str] = {
    "breakout":           "03:30",   # 09:00 IST — must trigger at open or not at all
    "relative_strength":  "03:30",   # same as breakout
    "trend_pullback":     "08:30",   # 14:00 IST — valid through afternoon
    "mean_reversion":     "07:30",   # 13:00 IST — oversold bounce window
    "squeeze":            "08:00",   # 13:30 IST — squeeze resolves mid-afternoon
    "volume_expansion":   "06:00",   # 11:30 IST — volume expansion is an AM phenomenon
    "overbought_short_watch": "09:00", # 14:30 IST
    "neutral":            "09:30",   # 15:00 IST — default: valid all day
}

# Gap magnitude thresholds
GAP_UP_SIGNIFICANT   = 0.015   # >1.5% overnight gap up
GAP_DOWN_SIGNIFICANT = 0.015   # >1.5% overnight gap down

# Conviction decay: applied to candidates that were in the list for N+ days
# Already scored by market_scanner; here we adjust the RSI/volume_ratio to
# reflect potential staleness of the underlying setup
DECAY_RSI_DRIFT   = 2.0    # RSI drifts toward 50 per day of age
DECAY_VOL_FACTOR  = 0.90   # volume_ratio multiplied by this each day beyond day 1


def run_premarket_refinement() -> None:
    """
    Main entry point. Called by master_orchestrator at 08:45 IST.
    Safe: all exceptions are caught; partial results are written if possible.
    """
    start = time.monotonic()
    log.info("[PremarketRefiner] Starting pre-market refinement.")

    # ── Deadline check ────────────────────────────────────────────────────────
    try:
        from config import PREMARKET_DEADLINE_UTC_HHMM, PREMARKET_MAX_RUNTIME_MINUTES
        deadline_str = PREMARKET_DEADLINE_UTC_HHMM
        max_runtime  = PREMARKET_MAX_RUNTIME_MINUTES
    except ImportError:
        deadline_str = "03:40"
        max_runtime  = 25

    deadline = _parse_utc_hhmm(deadline_str)

    # ── Load candidates ───────────────────────────────────────────────────────
    candidates = CandidateStore.read()
    if not candidates:
        log.warning("[PremarketRefiner] No valid candidate store — nothing to refine.")
        return

    log.info("[PremarketRefiner] Loaded %d candidates for refinement.", len(candidates))

    # ── Fetch overnight gaps ──────────────────────────────────────────────────
    gap_map = _fetch_overnight_gaps([c["symbol"] for c in candidates])

    # ── Load sector bias from GlobalDataAI ────────────────────────────────────
    sector_bias = _get_sector_bias()

    # ── Load concentration memory for decay calculation ───────────────────────
    streak_counts = CandidateStore.get_consecutive_selection_counts()

    # ── Process each candidate ────────────────────────────────────────────────
    refined: List[Dict[str, Any]] = []
    expired_count  = 0
    adjusted_count = 0

    for c in candidates:
        # Abort if approaching deadline
        elapsed_min = (time.monotonic() - start) / 60.0
        if elapsed_min > max_runtime - 2:
            log.warning("[PremarketRefiner] Approaching runtime limit — writing partial results.")
            break
        if datetime.now(timezone.utc) >= deadline:
            log.warning("[PremarketRefiner] Deadline %s UTC reached — writing partial results.", deadline_str)
            break

        sym    = c.get("symbol", "?")
        sector = c.get("sector", "UNKNOWN")

        # 1. Conviction decay based on consecutive days in list
        streak = streak_counts.get(sym, 1)
        if streak > 1:
            decay_days  = streak - 1
            # Drift RSI toward 50 (decay of edge)
            rsi = c.get("rsi", 50.0)
            rsi = rsi + (50.0 - rsi) * (DECAY_RSI_DRIFT / 100.0) * decay_days
            c["rsi"] = round(max(0.0, min(100.0, rsi)), 1)
            # Decay volume_ratio
            vol = c.get("volume_ratio", 1.0)
            c["volume_ratio"] = round(max(0.1, vol * (DECAY_VOL_FACTOR ** decay_days)), 2)

        # 2. Overnight gap adjustment
        gap_pct = gap_map.get(sym, 0.0)
        if abs(gap_pct) > 0.001:
            adjusted_count += 1
            # Adjust support/resistance for gap
            res = c.get("resistance", 0.0)
            sup = c.get("support", 0.0)
            if gap_pct > GAP_UP_SIGNIFICANT:
                # Gap up: raise support floor; resistance already stretched
                c["support"]    = round(sup * (1 + gap_pct * 0.5), 2)
                c["resistance"] = round(res * (1 + gap_pct * 0.3), 2)
            elif gap_pct < -GAP_DOWN_SIGNIFICANT:
                # Gap down: lower resistance ceiling; support may be broken
                c["resistance"] = round(res * (1 + gap_pct * 0.5), 2)
                c["support"]    = round(sup * (1 + gap_pct * 0.3), 2)
            c["overnight_gap_pct"] = round(gap_pct * 100, 2)
            log.debug("[PremarketRefiner] %s gap=%.2f%% res=%.2f sup=%.2f",
                      sym, gap_pct * 100, c["resistance"], c["support"])

        # 3. Sector bias overlay (Phase F)
        adj = sector_bias.get(sector, 0.0)
        if adj != 0.0:
            # Apply the sector adjustment to volume_ratio (≈ setup attractiveness proxy)
            c["volume_ratio"] = round(
                max(0.1, min(8.0, c.get("volume_ratio", 1.0) * (1.0 + adj))), 2
            )
            c["overnight_adjustment"] = round(adj, 3)

        # 4. Assign valid_until_utc based on primary bucket
        buckets = c.get("buckets", ["neutral"])
        primary_bucket = buckets[0] if buckets else "neutral"
        valid_until_utc = _calc_valid_until(primary_bucket)
        c["valid_until_utc"] = valid_until_utc

        # 5. Drop candidates whose valid_until_utc is already past
        if _is_expired(valid_until_utc):
            expired_count += 1
            log.debug("[PremarketRefiner] %s valid_until=%s already expired — dropped.", sym, valid_until_utc)
            continue

        refined.append(c)

    log.info(
        "[PremarketRefiner] Refined: %d candidates → %d retained "
        "(expired=%d adjusted_for_gap=%d sector_bias_applied=%d)",
        len(candidates), len(refined),
        expired_count, adjusted_count, len([x for x in refined if x.get("overnight_adjustment", 0) != 0]),
    )

    # ── Write back to candidate store ────────────────────────────────────────
    complete = (len(refined) + expired_count) >= len(candidates)
    success  = CandidateStore.update_premarket(refined, complete=complete)

    duration = time.monotonic() - start
    if success:
        log.info("[PremarketRefiner] Complete in %.1fs. premarket_refresh_complete=%s",
                 duration, complete)
    else:
        log.error("[PremarketRefiner] Failed to write updated candidates.")

    # Patch 6 — performance telemetry
    _n_in  = len(candidates) if candidates else 0
    _n_out = len(refined)
    log.info(
        "[ScannerPerformance] premarket_runtime_sec=%.1f"
        " symbols_processed=%d candidates_retained=%d candidates_expired=%d",
        duration, _n_in, _n_out, expired_count,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_overnight_gaps(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch 2-day OHLCV for each symbol and return {symbol: overnight_gap_pct}.
    gap_pct = (today_open - yesterday_close) / yesterday_close
    Returns {} on failure.
    """
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        log.debug("[PremarketRefiner] yfinance unavailable — skipping gap fetch.")
        return {}

    gaps: Dict[str, float] = {}
    tickers = [s + ".NS" for s in symbols]

    try:
        df = yf.download(
            tickers, period="3d", interval="1d",
            progress=False, auto_adjust=True, group_by="ticker",
        )
        if df is None or df.empty:
            return {}

        for sym, ns in zip(symbols, tickers):
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    close = df["Close"][ns].dropna()
                    open_ = df["Open"][ns].dropna()
                else:
                    close = df["Close"].dropna()
                    open_ = df["Open"].dropna()

                if len(close) >= 2 and len(open_) >= 1:
                    prev_close  = float(close.iloc[-2])
                    today_open  = float(open_.iloc[-1])
                    if prev_close > 0:
                        gaps[sym] = (today_open - prev_close) / prev_close
            except Exception:
                pass

    except Exception as exc:
        log.debug("[PremarketRefiner] Gap fetch failed: %s", exc)

    log.debug("[PremarketRefiner] Overnight gaps computed for %d/%d symbols.", len(gaps), len(symbols))
    return gaps


def _get_sector_bias() -> Dict[str, float]:
    """Get sector bias from GlobalDataAI. Returns {} on any failure."""
    try:
        from global_intelligence.global_data_ai import GlobalDataAI
        gd = GlobalDataAI()
        snap = gd.fetch()  # uses cache if already fetched this cycle
        return gd.get_sector_regime_bias()
    except Exception as exc:
        log.debug("[PremarketRefiner] Sector bias unavailable: %s", exc)
        return {}


def _calc_valid_until(bucket: str) -> str:
    """
    Return ISO-8601 UTC datetime string for valid_until_utc of this candidate.
    Times are set for today's trading session.
    """
    now_utc  = datetime.now(timezone.utc)
    today    = now_utc.date()
    hhmm_str = _VALID_UNTIL_UTC.get(bucket, _VALID_UNTIL_UTC["neutral"])
    hh, mm   = (int(x) for x in hhmm_str.split(":"))
    dt       = datetime(today.year, today.month, today.day, hh, mm, 0, tzinfo=timezone.utc)
    # If we're past this time already (e.g. re-run) push to next day
    if dt < now_utc:
        dt += timedelta(days=1)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_expired(valid_until_utc: str) -> bool:
    """True if valid_until_utc is in the past."""
    try:
        expiry = datetime.fromisoformat(valid_until_utc.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > expiry
    except Exception:
        return False


def _parse_utc_hhmm(hhmm: str) -> datetime:
    """Parse 'HH:MM' as today's UTC datetime."""
    now   = datetime.now(timezone.utc)
    hh, mm = (int(x) for x in hhmm.split(":"))
    return now.replace(hour=hh, minute=mm, second=0, microsecond=0)
