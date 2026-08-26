"""
Equity Scanner AI — Layer 3 Agent 1
======================================
Scans the Nifty 500 universe for high-probability trade setups.

Scans for:
  • Breakouts above key resistance with volume confirmation
  • Momentum stocks with RSI 50–70 pullbacks
  • Volume spikes (≥ 2× 20-day avg volume)
  • Retests of broken resistance (acting as support)
"""

from __future__ import annotations
import random
import threading as _threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from models.market_data  import MarketSnapshot, RegimeLabel
from models.trade_signal import TradeSignal, SignalDirection, SignalStrength, SignalType
from models.agent_output import AgentOutput
from utils import get_logger
from config import (
    ATR_STOP_MULTIPLIER, ATR_ZONE_MULTIPLIER, VOLATILITY_GUARD_ATR_PCT,
)
# NOTE: position sizing is intentionally NOT done here.
# The Risk Engine (PortfolioAllocationAI) calculates quantity using:
#   qty = (account_equity * RISK_PER_TRADE) / abs(entry_price - stop_price)

log = get_logger(__name__)

# ── Live price cache ─────────────────────────────────────────────────────────
# Stale-while-revalidate: cache is returned immediately (even if stale) while
# a background daemon thread fetches fresh prices for the NEXT cycle.
# This guarantees _fetch_live_prices() returns in <1 ms — the 5-6 s yfinance
# call NEVER blocks a trading cycle again.
_PRICE_CACHE: Dict[str, float] = {}
_PRICE_CACHE_TS: float = 0.0
_PRICE_CACHE_TTL: float = 60.0          # stale threshold (seconds)
_PRICE_CACHE_LOCK  = _threading.Lock()   # guards _PRICE_CACHE / _PRICE_CACHE_TS
_PRICE_REFRESH_RUNNING = _threading.Event()  # prevents duplicate refresh threads
_PRICE_CACHE_READY = _threading.Event()      # set once cache is first populated; stays set

# ── P1 cycle-scoped telemetry counters (reset each scan() call) ─────────────
_OE_CYCLE_SEQ: List[int] = [0]   # [0] = monotonic cycle counter; mutable, no global needed
_oe_io_counters: Dict[str, int] = {
    "json_reads": 0, "file_reads": 0,
    "ltp_cache_hits": 0, "ltp_cache_misses": 0,
}

# ── Priority 2 (FallbackContaminationAudit): feed source provenance cache ───
# Updated in sync with _PRICE_CACHE by _do_fetch_prices().
# symbol → "DHAN" | "YAHOO" | "CACHE" | "SIM" | "" (unknown)
# Protected by _PRICE_CACHE_LOCK (written together with _PRICE_CACHE).
_FEED_SOURCE_CACHE: Dict[str, str] = {}

# ── Scan-attrition: per-cycle record of evaluated symbols ────────────────────
# symbol → {"ltp": float, "in_range": bool, "signal_generated": bool}
# Populated during each scan() call; read by scan_attrition hook in the
# orchestrator after scan() returns so it can write SCANNER_NO_SIGNAL records.
# Shared-read by pga_collector at EOD via load_last_cycle_evaluated().
_LAST_CYCLE_EVALUATED: Dict[str, Dict] = {}
_LAST_CYCLE_REGIME: str = ""

# ── PriceGuard cold-start constants ─────────────────────────────────────────
# On cold start the cache is empty; guard waits for background refresh before
# allowing a scan cycle.  System skips the cycle if prices can't be obtained.
_PRICE_GUARD_MAX_WAIT_S: float = 10.0   # max seconds to wait for price cache fill
_PRICE_GUARD_POLL_S:     float = 1.0    # polling interval while waiting

RR_STRONG_BREAKOUT = 4.0   # vol_ratio ≥ 3.0 → fat-tail bonus in DecisionEngine
RR_NORMAL_BREAKOUT = 2.5   # vol_ratio < 3.0
RR_TREND_PULLBACK  = 3.0   # confirmed bull-trend → asymmetry bonus in DecisionEngine
RR_DEFAULT         = 2.5   # all other setups


def _estimate_atr(ltp: float, support: float, resistance: float) -> float:
    """
    Estimate ATR(14) from price structure (support-resistance spread).
    Uses ~40% of daily range as a proxy for 14-period ATR.
    Replace with real broker ATR data in live trading.
    """
    daily_range = resistance - support
    if daily_range <= 0:
        daily_range = ltp * 0.02   # fallback: 2% of price
    return round(daily_range * 0.40, 4)

# ── Base watchlist — LTPs are refreshed each cycle via _live_watchlist() ────
# base_ltp is only a FALLBACK when live feed is unavailable.
# resistance / support are freshly computed 20-day technical levels.
# Levels with high ATR proxy/real divergence are ATR-anchored (noted inline).
# REFRESH SCHEDULE: run refresh_watchlist_data.py after market close weekly,
# or whenever Phase D market_scanner is not yet active.
_BASE_WATCHLIST: List[Dict[str, Any]] = [
# ── Base watchlist ─────────────────────────────────────────────────────────
    # base_ltp refreshed 2026-07-10 from yfinance live close prices
    # ATR_ANCHORED = 20d range diverged >40% from ATR(14); levels rebuilt from real ATR
    {"symbol": "RELIANCE    ", "base_ltp":  1307.80, "resistance":  1332.70, "support":  1275.90, "volume_ratio": 1.1, "rsi":  49.8, "adv_crore":  1744},
    {"symbol": "HDFCBANK    ", "base_ltp":   824.95, "resistance":   862.57, "support":   787.33, "volume_ratio": 1.0, "rsi":  67.9, "adv_crore":  2844},  # ATR_ANCHORED
    {"symbol": "ICICIBANK   ", "base_ltp":  1401.20, "resistance":  1464.79, "support":  1337.61, "volume_ratio": 0.9, "rsi":  62.8, "adv_crore":  1659},  # ATR_ANCHORED
    {"symbol": "TATASTEEL   ", "base_ltp":   191.19, "resistance":   200.42, "support":   181.96, "volume_ratio": 0.8, "rsi":  44.6, "adv_crore":   524},  # ATR_ANCHORED
    {"symbol": "INFY        ", "base_ltp":  1068.00, "resistance":  1149.73, "support":   986.27, "volume_ratio": 0.7, "rsi":  48.0, "adv_crore":  1496},  # ATR_ANCHORED
    {"symbol": "BANKBARODA  ", "base_ltp":   250.95, "resistance":   268.71, "support":   233.19, "volume_ratio": 1.2, "rsi":  38.1, "adv_crore":   340},  # ATR_ANCHORED
    {"symbol": "LT          ", "base_ltp":  3945.80, "resistance":  4131.65, "support":  3759.95, "volume_ratio": 1.4, "rsi":  38.6, "adv_crore":   832},  # ATR_ANCHORED
    {"symbol": "COALINDIA   ", "base_ltp":   429.30, "resistance":   455.75, "support":   428.95, "volume_ratio": 0.7, "rsi":  34.4, "adv_crore":   259},
    {"symbol": "HCLTECH     ", "base_ltp":  1164.10, "resistance":  1253.89, "support":  1074.31, "volume_ratio": 0.7, "rsi":  56.6, "adv_crore":   494},  # ATR_ANCHORED
    {"symbol": "SBIN        ", "base_ltp":  1036.00, "resistance":  1051.60, "support":  1015.30, "volume_ratio": 1.0, "rsi":  56.5, "adv_crore":  1058},
    {"symbol": "AXISBANK    ", "base_ltp":  1323.70, "resistance":  1383.43, "support":  1296.60, "volume_ratio": 0.9, "rsi":  46.7, "adv_crore":   768},
    {"symbol": "ONGC        ", "base_ltp":   244.96, "resistance":   248.20, "support":   233.10, "volume_ratio": 1.0, "rsi":  45.1, "adv_crore":   387},
    {"symbol": "KOTAKBANK   ", "base_ltp":   377.60, "resistance":   397.65, "support":   357.55, "volume_ratio": 1.3, "rsi":  38.3, "adv_crore":   676},  # ATR_ANCHORED
    {"symbol": "BHARTIARTL  ", "base_ltp":  1920.40, "resistance":  1931.10, "support":  1841.10, "volume_ratio": 1.2, "rsi":  59.6, "adv_crore":  1232},
    {"symbol": "ITC         ", "base_ltp":   281.75, "resistance":   292.50, "support":   280.65, "volume_ratio": 1.3, "rsi":  36.8, "adv_crore":   347},
    {"symbol": "BAJAJFINSV  ", "base_ltp":  1916.00, "resistance":  2018.06, "support":  1813.94, "volume_ratio": 1.1, "rsi":  68.4, "adv_crore":   239},  # ATR_ANCHORED
    {"symbol": "HINDALCO    ", "base_ltp":   967.45, "resistance":  1008.94, "support":   934.82, "volume_ratio": 1.0, "rsi":  41.1, "adv_crore":   630},
    {"symbol": "ULTRACEMCO  ", "base_ltp": 11711.00, "resistance": 11723.00, "support": 11253.00, "volume_ratio": 0.8, "rsi":  58.5, "adv_crore":   259},
    {"symbol": "TECHM       ", "base_ltp":  1454.80, "resistance":  1454.80, "support":  1327.70, "volume_ratio": 0.6, "rsi":  57.6, "adv_crore":   344},
    {"symbol": "NTPC        ", "base_ltp":   344.55, "resistance":   360.99, "support":   328.11, "volume_ratio": 1.0, "rsi":  29.7, "adv_crore":   465},  # ATR_ANCHORED
]

# ── Extended watchlist (activated by ODM when density is low) ─────────────
# Represents a wider NIFTY200/500 universe.
_EXTENDED_WATCHLIST: List[Dict[str, Any]] = [
# ── Extended watchlist ─────────────────────────────────────────────────────────
    # base_ltp refreshed 2026-07-10 from yfinance live close prices
    # ATR_ANCHORED = 20d range diverged >40% from ATR(14); levels rebuilt from real ATR
    {"symbol": "HINDUNILVR  ", "base_ltp":  2150.60, "resistance":  2210.60, "support":  2118.20, "volume_ratio": 1.1, "rsi":  47.7, "adv_crore":   342},
    {"symbol": "ASIANPAINT  ", "base_ltp":  2677.80, "resistance":  2754.90, "support":  2635.70, "volume_ratio": 0.9, "rsi":  48.9, "adv_crore":   341},
    {"symbol": "BAJFINANCE  ", "base_ltp":  1020.50, "resistance":  1079.33, "support":   961.67, "volume_ratio": 1.0, "rsi":  64.4, "adv_crore":   888},  # ATR_ANCHORED
    {"symbol": "MARUTI      ", "base_ltp": 13854.00, "resistance": 14665.27, "support": 13042.73, "volume_ratio": 0.9, "rsi":  52.2, "adv_crore":   790},  # ATR_ANCHORED
    {"symbol": "SUNPHARMA   ", "base_ltp":  1935.50, "resistance":  2014.42, "support":  1856.58, "volume_ratio": 1.5, "rsi":  73.7, "adv_crore":   355},  # ATR_ANCHORED
    {"symbol": "WIPRO       ", "base_ltp":   175.46, "resistance":   185.50, "support":   165.42, "volume_ratio": 0.7, "rsi":  39.8, "adv_crore":   386},  # ATR_ANCHORED
    {"symbol": "POWERGRID   ", "base_ltp":   283.10, "resistance":   292.25, "support":   279.70, "volume_ratio": 0.8, "rsi":  42.6, "adv_crore":   262},
    {"symbol": "DIVISLAB    ", "base_ltp":  6836.00, "resistance":  6857.50, "support":  6545.50, "volume_ratio": 1.0, "rsi":  58.1, "adv_crore":   217},
    {"symbol": "TITAN       ", "base_ltp":  4584.40, "resistance":  4811.25, "support":  4357.55, "volume_ratio": 1.3, "rsi":  70.4, "adv_crore":   403},  # ATR_ANCHORED
    {"symbol": "DRREDDY     ", "base_ltp":  1244.30, "resistance":  1331.31, "support":  1157.29, "volume_ratio": 2.5, "rsi":  33.9, "adv_crore":   317},  # ATR_ANCHORED
    {"symbol": "ADANIENT    ", "base_ltp":  3157.30, "resistance":  3212.10, "support":  2942.50, "volume_ratio": 1.1, "rsi":  59.2, "adv_crore":   644},
    {"symbol": "TATACONSUM  ", "base_ltp":  1111.90, "resistance":  1131.30, "support":  1075.60, "volume_ratio": 0.8, "rsi":  47.6, "adv_crore":   182},
    {"symbol": "NESTLEIND   ", "base_ltp":  1455.20, "resistance":  1466.65, "support":  1368.12, "volume_ratio": 0.9, "rsi":  60.5, "adv_crore":   251},
    {"symbol": "HAVELLS     ", "base_ltp":  1188.40, "resistance":  1225.00, "support":  1156.10, "volume_ratio": 2.4, "rsi":  51.4, "adv_crore":   115},
    {"symbol": "PIDILITIND  ", "base_ltp":  1598.50, "resistance":  1622.30, "support":  1566.70, "volume_ratio": 0.7, "rsi":  59.4, "adv_crore":   121},
    {"symbol": "GRASIM      ", "base_ltp":  3213.60, "resistance":  3213.60, "support":  3080.20, "volume_ratio": 1.1, "rsi":  59.6, "adv_crore":   188},
    {"symbol": "JSWSTEEL    ", "base_ltp":  1245.40, "resistance":  1289.10, "support":  1209.25, "volume_ratio": 0.9, "rsi":  49.6, "adv_crore":   169},
    {"symbol": "ADANIPORTS  ", "base_ltp":  1828.10, "resistance":  1883.20, "support":  1776.10, "volume_ratio": 0.7, "rsi":  51.7, "adv_crore":   373},
]


# ── Fix 4: RSI computation helper ─────────────────────────────────────────────
# ── V2: Scanner governance helpers ─────────────────────────────────────────────

def get_pending_mini_rescan() -> Dict[str, Any]:
    """
    Return and clear the pending event-driven mini rescan request (if any).

    Called by master_orchestrator._check_scanner_events() in the 5-min loop.
    Thread-safe under CPython GIL (single dict swap, no nested mutation).

    Returns {} when no rescan was requested.
    Returns {"reason": str, "trigger_ts": float, "priority": str} otherwise.
    """
    global _PENDING_MINI_RESCAN
    event = _PENDING_MINI_RESCAN
    _PENDING_MINI_RESCAN = {}
    return event


def _check_breakout_invalidation(
    candidate: Dict[str, Any],
    live_ltp: float,
    live_rsi: Optional[float] = None,
) -> Tuple[bool, str]:
    """
    Detect explicit setup failure for a prepared candidate.

    Returns (invalidated, reason_code).
    invalidated=True removes the candidate from the prepared pipeline immediately.
    This is more decisive than TTL expiry — it detects confirmed structural breaks.

    Checks (in priority order):
      support_breakdown    LTP < support − 1×ATR (clear structural failure)
      failed_breakout      base_ltp was above resistance; LTP returned below
      atr_shock            price drifted > 3.5×ATR from base_ltp (runaway)
      momentum_rejection   stored RSI was strong (>60), now collapsed below 38
    """
    try:
        sup      = float(candidate.get("support",    0) or 0)
        res      = float(candidate.get("resistance", 0) or 0)
        base_ltp = float(candidate.get("base_ltp",   0) or 0)
        atr      = float(candidate.get("atr14",      0) or 0)
        stored_rsi = float(candidate.get("rsi", 50) or 50)

        if atr <= 0 and res > sup > 0:
            atr = (res - sup) * 0.40
        if atr <= 0 and live_ltp > 0:
            atr = live_ltp * 0.020

        if live_ltp <= 0 or atr <= 0:
            return False, ""   # insufficient data — do not invalidate

        # Price sanity guard: if live_ltp is on a completely different scale
        # from base_ltp (e.g. fallback simulation returning ~1000 for all
        # symbols), every check fires as a false positive.  Skip invalidation
        # if the move implies >35% drop or >55% rise — physically impossible
        # for large-cap Indian stocks in 1-2 trading days given circuit limits.
        if base_ltp > 0:
            _price_ratio = live_ltp / base_ltp
            if _price_ratio < 0.65 or _price_ratio > 1.55:
                return False, ""   # price from unreliable/fallback source

        # 1. Support breakdown — requires base_ltp for price scale validation.
        # Without base_ltp we cannot distinguish a genuine crash from a sim-price
        # artifact, so we skip this check when the reference price is missing.
        # Also skip if support > base_ltp × 1.05: that means the candidate was
        # prepared with a corrupted base_ltp (e.g. fallback sim price during scan)
        # while support was computed from real historical data.  Support must
        # always be below the entry price for a valid bullish breakout setup.
        if base_ltp > 0 and sup > 0 and sup < base_ltp * 1.05 and live_ltp < sup - atr:
            return True, f"support_breakdown(ltp={live_ltp:.2f}<sup-atr={sup-atr:.2f})"

        # 2. Failed breakout: was above resistance, returned below
        if base_ltp > 0 and res > 0 and base_ltp > res * 0.995 and live_ltp < res * 0.990:
            return True, f"failed_breakout(base={base_ltp:.2f}>res={res:.2f},ltp={live_ltp:.2f})"

        # 3. ATR shock: runaway move invalidates original entry thesis
        if base_ltp > 0 and abs(live_ltp - base_ltp) > 3.5 * atr:
            return True, f"atr_shock(drift={abs(live_ltp - base_ltp):.2f}>3.5×atr={3.5*atr:.2f})"

        # 4. Momentum rejection: RSI was strong, now collapsed
        rsi = live_rsi if live_rsi is not None else stored_rsi
        if stored_rsi > 60 and rsi < 38:
            return True, f"momentum_rejection(stored_rsi={stored_rsi:.0f}->live_rsi={rsi:.0f})"

        return False, ""
    except Exception:
        return False, ""   # never invalidate on error


def _fallback_severity_tier(live_coverage_pct: float) -> str:
    """Map live_coverage_pct to a 5-tier governance severity string."""
    if live_coverage_pct >= 70.0:
        return "NONE"
    if live_coverage_pct >= 50.0:
        return "LOW"
    if live_coverage_pct >= 30.0:
        return "MEDIUM"
    if live_coverage_pct >= 10.0:
        return "HIGH"
    return "CRITICAL"


def _get_fallback_trend() -> str:
    """Compute trend direction of live_coverage_pct over the last window."""
    if len(_FALLBACK_TREND) < 3:
        return "STABLE"
    first, last = _FALLBACK_TREND[0], _FALLBACK_TREND[-1]
    if last > first + 10.0:
        return "IMPROVING"
    if last < first - 10.0:
        return "DEGRADING"
    return "STABLE"


def _check_mini_rescan_triggers(
    snapshot: "MarketSnapshot",
    prepared_count: int,
    live_coverage_pct: float,
) -> None:
    """
    Evaluate event-driven rescan triggers after each scan cycle.
    Posts to _PENDING_MINI_RESCAN if a replenishment trigger fires.
    Respects _MINI_RESCAN_COOLDOWN to prevent rapid-fire rescans.

    Trigger conditions (first match wins):
      POOL_EXHAUSTION        prepared < POOL_FLOOR_MIN/2 and live_cov < 20%
      REGIME_TRANSITION      current regime differs from previous cycle
      BREADTH_COLLAPSE       market_breadth < 0.25 (heavy selling)
      VIX_SURGE              vix > 22.0
      EXPLORATION_STARVATION evaluated==0 and prepared < POOL_FLOOR_MIN
    """
    global _PENDING_MINI_RESCAN, _LAST_MINI_RESCAN_TS, _LAST_REGIME

    now_m = time.monotonic()
    if now_m - _LAST_MINI_RESCAN_TS < _MINI_RESCAN_COOLDOWN:
        return
    if _PENDING_MINI_RESCAN:   # previous event not yet consumed
        return

    trigger_reason   = ""
    trigger_priority = "NORMAL"

    current_regime = getattr(snapshot.regime, "value", str(snapshot.regime))

    if prepared_count < max(1, _POOL_FLOOR_MIN // 2) and live_coverage_pct < 20.0:
        trigger_reason   = f"POOL_EXHAUSTION:prepared={prepared_count}"
        trigger_priority = "HIGH"
    elif _LAST_REGIME is not None and current_regime != _LAST_REGIME:
        trigger_reason   = f"REGIME_TRANSITION:{_LAST_REGIME}→{current_regime}"
        trigger_priority = "HIGH"
    elif getattr(snapshot, "market_breadth", 0.5) < 0.25:
        trigger_reason   = f"BREADTH_COLLAPSE:breadth={snapshot.market_breadth:.2f}"
        trigger_priority = "NORMAL"
    elif getattr(snapshot, "vix", 15.0) > 22.0:
        trigger_reason   = f"VIX_SURGE:vix={snapshot.vix:.1f}"
        trigger_priority = "NORMAL"
    elif _EXPLORE_STATS.get("evaluated", 0) == 0 and prepared_count < _POOL_FLOOR_MIN:
        trigger_reason   = f"EXPLORATION_STARVATION:prepared={prepared_count}"
        trigger_priority = "LOW"

    _LAST_REGIME = current_regime

    if trigger_reason:
        _PENDING_MINI_RESCAN = {
            "reason":      trigger_reason,
            "trigger_ts":  now_m,
            "priority":    trigger_priority,
        }
        _LAST_MINI_RESCAN_TS = now_m
        log.info("[MiniRescanTriggered] %s priority=%s — event posted for orchestrator.",
                 trigger_reason, trigger_priority)


# ── Fix 4: RSI computation helper ─────────────────────────────────────────────
def _compute_rsi_list(closes: List[float], period: int = 14) -> Optional[float]:
    """
    Wilder-smoothed RSI(14) from a plain list of close prices.
    Returns None if fewer than period+1 data points available.
    """
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


def _do_fetch_prices(symbols: List[str]) -> Dict[str, float]:
    """Blocking call to the live feed. Returns {} on any error.

    Priority 2 (FallbackContaminationAudit): As a side effect, populates
    _FEED_SOURCE_CACHE with the feed_source tag ('DHAN'/'YAHOO'/'CACHE'/'SIM')
    for each successfully fetched symbol.  This lets the enrichment pipeline
    know whether each live price was live-grade or fallback.
    """
    global _FEED_SOURCE_CACHE
    try:
        from data_feeds.data_feed_manager import get_feed_manager
        feed = get_feed_manager()
        ns_symbols = [f"{s.strip()}.NS" for s in symbols]
        quotes = feed.get_multiple_quotes(ns_symbols)
        prices: Dict[str, float] = {}
        sources: Dict[str, str] = {}
        for ns_sym, q in quotes.items():
            bare = ns_sym.replace(".NS", "").strip()
            if q is not None and hasattr(q, "ltp") and q.ltp and q.ltp > 0:
                prices[bare] = float(q.ltp)
                sources[bare] = (getattr(q, "feed_source", "") or "").upper()
        # Update source cache alongside prices (atomic dict replacement — no lock
        # needed: single-writer pattern, GIL-safe on CPython, forensic-only data)
        if sources:
            _FEED_SOURCE_CACHE = sources
        if prices:
            log.debug("[EquityScannerAI] Fetched live prices: %d/%d symbols.",
                      len(prices), len(symbols))
        return prices
    except Exception as exc:
        log.debug("[EquityScannerAI] Live price fetch skipped (%s) — using simulation.", exc)
        return {}


def _background_price_refresh(symbols: List[str]) -> None:
    """Daemon thread: refresh _PRICE_CACHE without blocking the scan."""
    global _PRICE_CACHE, _PRICE_CACHE_TS
    try:
        prices = _do_fetch_prices(symbols)  # also updates _FEED_SOURCE_CACHE (side effect)
        if prices:
            with _PRICE_CACHE_LOCK:
                _PRICE_CACHE    = prices
                _PRICE_CACHE_TS = time.monotonic()
            _PRICE_CACHE_READY.set()   # wake any PriceGuard waiter immediately
            log.debug("[EquityScannerAI] Background price refresh complete (%d symbols).",
                      len(prices))
    finally:
        _PRICE_REFRESH_RUNNING.clear()


# ── Fix 4: Background RSI refresh ──────────────────────────────────────────────
def _background_rsi_refresh(symbols: List[str]) -> None:
    """
    Daemon thread: compute live RSI(14) from last 22 daily bars for each symbol.
    Updates _RSI_CACHE — never blocks a scan cycle.
    Runs at most once per _RSI_CACHE_TTL seconds (guarded by _RSI_REFRESH_RUNNING).
    """
    global _RSI_CACHE, _RSI_CACHE_TS
    try:
        from data_feeds.data_feed_manager import get_feed_manager as _gfm_rsi
        _feed_rsi = _gfm_rsi()
        fresh: Dict[str, float] = {}
        for sym in symbols:
            try:
                bars = _feed_rsi.get_history(f"{sym}.NS", days=22, interval="1d")
                if bars and len(bars) >= 15:
                    closes = [
                        float(b.close) for b in bars
                        if hasattr(b, 'close') and b.close and b.close > 0
                        and isinstance(b.close, (int, float))
                    ]
                    rsi_val = _compute_rsi_list(closes[-20:])
                    # ── Patch 4: RSI cache sanity validation ────────────────────
                    if rsi_val is not None and not (0.0 <= rsi_val <= 100.0):
                        try:
                            from data_feeds.data_integrity_tracker import get_data_integrity_tracker as _gdit_rsi
                            _gdit_rsi().record_sanity_fail(
                                sym, "rsi", rsi_val, f"out_of_bounds:{rsi_val:.1f}"
                            )
                        except Exception:
                            pass
                        rsi_val = None  # discard — force recalculation next cycle
                    if rsi_val is not None:
                        fresh[sym] = rsi_val
            except Exception:
                continue
        if fresh:
            with _RSI_CACHE_LOCK:
                _RSI_CACHE.update(fresh)
                _RSI_CACHE_TS = time.monotonic()
            log.debug("[EquityScannerAI] Background RSI refresh: %d/%d symbols updated.",
                      len(fresh), len(symbols))
    except Exception as _rsi_exc:
        log.debug("[EquityScannerAI] Background RSI refresh failed: %s", _rsi_exc)
    finally:
        _RSI_REFRESH_RUNNING.clear()


def _fetch_live_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Return the best available price map — always in < 1 ms.

    Strategy (stale-while-revalidate):
      FRESH cache  → return immediately.
      STALE cache  → return stale data now; background thread updates for
                     the next cycle (~60 s later).
      EMPTY cache  → fire background thread; return {} this cycle so
                     _live_watchlist() falls back to simulated prices.
                     (Negligible impact in paper mode; only on cold start)
    """
    now = time.monotonic()
    with _PRICE_CACHE_LOCK:
        is_fresh = bool(_PRICE_CACHE) and (now - _PRICE_CACHE_TS < _PRICE_CACHE_TTL)
        snapshot = dict(_PRICE_CACHE)   # local copy under lock

    if is_fresh:
        return snapshot   # hot path — no blocking ever

    # Cache is stale or empty: trigger background refresh if not already running.
    if not _PRICE_REFRESH_RUNNING.is_set():
        _PRICE_REFRESH_RUNNING.set()
        t = _threading.Thread(
            target=_background_price_refresh,
            args=(symbols,),
            daemon=True,
            name="PriceRefresh",
        )
        t.start()
        log.debug("[EquityScannerAI] Background price refresh triggered (%d symbols).",
                  len(symbols))

    return snapshot   # stale or {} — never blocks the cycle


# ── Module-level price pre-warm ─────────────────────────────────────────────
# Trigger a background price fetch immediately at import time so the first
# scan cycle (which may fire within seconds of a container restart) never
# stalls on PriceGuard cold-start wait.
# The orchestrator imports this module during __init__, typically 30-60 s
# before the first scan — plenty of time for yfinance to populate the cache.
_PRICE_REFRESH_RUNNING.set()
_threading.Thread(
    target=_background_price_refresh,
    args=([s["symbol"] for s in _BASE_WATCHLIST + _EXTENDED_WATCHLIST],),
    daemon=True,
    name="PricePrewarm",
).start()

# ── Phase A — Baseline telemetry timestamp ──────────────────────────────────
# Emitted once at import to mark when technical levels were last refreshed.
# Used to track level staleness and measure improvement after Phase D activates.
log.info(
    "[ScannerBaseline] symbols_evaluated=0 base_symbols=%d extended_symbols=%d"
    " technical_level_age_days=0 last_level_update=2026-05-29"
    " phase=STATIC_WATCHLIST prepared_universe_active=False",
    len(_BASE_WATCHLIST), len(_EXTENDED_WATCHLIST),
)

# ── Patch 1 / 5 / 7 — operational health state (module-level) ───────────────
# Populated by _prepared_watchlist() and _check_safe_mode_triggers().
# Read by _emit_prepared_universe_health() each scan() cycle.
_LAST_PREPARED_STATS: dict = {}   # last run stats for health heartbeat
_SAFE_MODE_ACTIVE:    bool = False  # Patch 7: reduced sophistication, not stopped
_SAFE_MODE_REASON:    str  = ""     # human-readable reason for current safe mode

# ── Section 4/5 — Exploration session counters ───────────────────────────────
# Reset at container restart.  Consumed by [ExplorationAudit] (EOD) and
# [ExplorationCandidate] (per-signal).  Never persisted to disk.
_EXPLORE_STATS: dict = {
    "evaluated":         0,  # symbols entered exploration eval this session
    "signals_generated": 0,  # signals that passed EXPLORATION_THRESHOLD
}

# ── Fix 5: Exploration rotation — prevent a single symbol blocking the slot ──
# After _EXPLORE_SKIP_THRESHOLD consecutive failures the symbol is skipped for
# the rest of the session.  Counters reset at container restart (session-scoped).
_EXPLORE_FAIL_COUNTS: Dict[str, int] = {}
_EXPLORE_SKIP_THRESHOLD: int = 3

# ── Patch 2/3 — Invalidation tracking for enrichment persistence ───────────────────
# Populated by _prepared_watchlist(), consumed by scan() for update_enrichment().
# Keys: bare symbol; values: invalidation reason string.
# Cleared at the start of each _prepared_watchlist() call.
_INVALIDATED_THIS_CYCLE: Dict[str, str] = {}

# ── S/R level refresh guard — prevents repeated yfinance calls within same day ──
# Set to today's ISO date after a successful validate_and_refresh_sr_levels() run.
_sr_last_refresh_date: str = ""

# ── Fix 6: Symbol→sector lookup (from nifty500_universe.json) ────────────────
# Built once at import time so exploration candidates from _live_watchlist()
# (which carries no sector metadata) can receive a proper sector tag.
_SYMBOL_SECTOR_MAP: Dict[str, str] = {}
try:
    import json as _json_smap
    _universe_file = Path(__file__).parent.parent / "data" / "nifty500_universe.json"
    if _universe_file.exists():
        for _entry in _json_smap.loads(_universe_file.read_text(encoding="utf-8")):
            if isinstance(_entry, dict) and _entry.get("symbol") and _entry.get("sector"):
                _SYMBOL_SECTOR_MAP[_entry["symbol"]] = _entry["sector"]
        log.debug("[EquityScannerAI] Sector map loaded: %d symbols.", len(_SYMBOL_SECTOR_MAP))
except Exception:
    pass

# ── Fix 4: Live RSI cache — background-refreshed from daily bars ──────────────
# Keyed by bare symbol (e.g. 'COLPAL').  Updated every 5 min by a daemon thread.
# Overlaid onto prepared candidates in _prepared_watchlist() to replace the
# frozen pre-market RSI snapshot with the current session's RSI(14) value.
_RSI_CACHE: Dict[str, float] = {}
_RSI_CACHE_TS: float = 0.0
_RSI_CACHE_TTL: float = 300.0          # 5-minute stale threshold
_RSI_CACHE_LOCK = _threading.Lock()
_RSI_REFRESH_RUNNING = _threading.Event()

# ── V2: Prepared-pool governance ────────────────────────────────────────────────
# _POOL_FLOOR_MIN: trigger background TTL refresh below this prepared count
# _FALLBACK_TREND: rolling window of live_coverage_pct for trend detection
_POOL_FLOOR_MIN:      int        = 8
_FALLBACK_TREND:      List[float] = []
_FALLBACK_TREND_WINDOW: int      = 10

# ── V2: Event-driven mini rescan ──────────────────────────────────────────────
# Pending event consumed by master_orchestrator 5-min monitor.
# Cleared automatically when orchestrator calls get_pending_mini_rescan().
_PENDING_MINI_RESCAN: Dict[str, Any] = {}
_MINI_RESCAN_COOLDOWN: float = 900.0    # 15 min between events
_LAST_MINI_RESCAN_TS:  float = 0.0
_LAST_REGIME:          Optional[str] = None


def _prepared_watchlist() -> List[Dict[str, Any]]:
    """
    Phase E hook — returns freshly-prepared candidates from the daily candidate store.
    Each row has the same schema as _live_watchlist() output so _identify_setup() works
    unchanged. Returns [] (triggering static fallback) when:
      - USE_PREPARED_UNIVERSE is False in config
      - candidate store file is absent, stale, or invalid
      - coverage below PREPARED_UNIVERSE_MIN_COVERAGE_PCT
    Jitter is intentionally NOT applied to prepared candidates — their technical
    levels are already freshly computed by market_scanner.py.

    Patch 1: populates _LAST_PREPARED_STATS for the health heartbeat.
    Patch 5: calls record_stale_fallback() / record_prepared_success() and
             emits [PreparedUniverseDegraded] when threshold exceeded.
    Patch 7: returns [] immediately if _SAFE_MODE_ACTIVE is True.
    """
    global _LAST_PREPARED_STATS, _INVALIDATED_THIS_CYCLE
    _INVALIDATED_THIS_CYCLE.clear()
    _pu_t0 = time.monotonic()  # P1 diagnostic
    try:
        from config import USE_PREPARED_UNIVERSE
        if not USE_PREPARED_UNIVERSE:
            return []

        # Patch 7: safe mode → disable prepared universe silently
        if _SAFE_MODE_ACTIVE:
            _LAST_PREPARED_STATS = {
                "prepared_count": 0, "expired_count": 0,
                "fallback_used": True, "reason": "SAFE_MODE",
            }
            return []

        from opportunity_engine.candidate_store import CandidateStore
        _pu_t_rd0 = time.monotonic()  # P1 diagnostic
        candidates = CandidateStore.read()
        _pu_t_read_ms = (time.monotonic() - _pu_t_rd0) * 1000  # P1 diagnostic
        _oe_io_counters["json_reads"] += 1
        if candidates is None:
            # Patch 5 — escalation tracking
            count = CandidateStore.record_stale_fallback()
            try:
                from config import SAFE_MODE_MAX_FALLBACK_SESSIONS
                _threshold = SAFE_MODE_MAX_FALLBACK_SESSIONS
            except ImportError:
                _threshold = 3
            if count > _threshold:
                log.warning(
                    "[PreparedUniverseDegraded] consecutive_sessions=%d reason=STALE_STORE"
                    " threshold=%d — consider investigating CandidateStore health.",
                    count, _threshold,
                )
            _LAST_PREPARED_STATS = {
                "prepared_count": 0, "expired_count": 0,
                "fallback_used": True, "reason": "NO_VALID_STORE",
                "fallback_sessions": count,
            }
            return []

        # Universal baseline backfill — one-shot per session if candidates lack enrichment.
        # Ensures all store candidates start enriched even if written before Phase 3.
        try:
            _un_enriched = sum(
                1 for c in candidates
                if c.get("strategy") is None
                or c.get("lifecycle_state") in (None, "", "NA")
            )
            if _un_enriched > 0:
                log.info(
                    "[BaselineEnrichment] %d candidates missing enrichment — triggering backfill.",
                    _un_enriched,
                )
                CandidateStore.backfill_baseline_enrichment()
                candidates = CandidateStore.read() or candidates
        except Exception as _bf_exc:
            log.debug("[BaselineEnrichment] Backfill skipped: %s", _bf_exc)

        from datetime import datetime, timezone as _tz
        now_utc = datetime.now(_tz.utc)
        expired_count      = 0
        _invalidated_count = 0

        # Lazy import of lifecycle computation (avoids top-level circular import concern)
        try:
            from opportunity_engine.candidate_store import compute_lifecycle_state as _compute_lc
        except ImportError:
            _compute_lc = None

        _pu_t_lp0 = time.monotonic()  # P1 diagnostic
        rows: List[Dict[str, Any]] = []
        for c in candidates:
            # Validate required fields before adding to live pipeline
            if not all([c.get("symbol"), c.get("resistance"), c.get("support")]):
                continue
            # Phase E — valid_until_utc filter: skip candidates whose setup window has closed
            valid_until = c.get("valid_until_utc")
            if valid_until:
                try:
                    expiry = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
                    if now_utc > expiry:
                        expired_count += 1
                        continue
                except Exception:
                    pass  # malformed timestamp → keep candidate (safe default)

            # ── V2: Breakout invalidation engine ────────────────────────────────
            # Explicitly remove candidates whose setups have structurally failed.
            # More decisive than TTL expiry — acts on confirmed price-action evidence.
            _sym_c = c["symbol"]
            _ltp_c = float(_PRICE_CACHE.get(_sym_c, c.get("base_ltp", 0.0)) or 0.0)
            _rsi_c = dict(_RSI_CACHE).get(_sym_c)   # None if cache not yet populated

            # ── Phase D: Feed-Unreliable Suppression ────────────────────────
            # Skip invalidation processing entirely for symbols with accumulated
            # feed-artifact invalidations and zero genuine ones.  The symbol stays
            # in the prepared pool so a genuine price move can still reject it.
            try:
                from opportunity_engine.invalidation_tracker import get_invalidation_tracker as _git
                if _git().is_feed_suppressed(_sym_c):
                    # [FeedUnreliableSuppression] already emitted by is_feed_suppressed()
                    # on the first call that crossed the threshold; subsequent calls log
                    # at DEBUG to avoid noise.
                    log.debug(
                        "[FeedUnreliableSuppression] symbol=%s  skipping invalidation check"
                        " (feed-artifact suppression active)",
                        _sym_c,
                    )
                    # fall through to the normal candidate path below (no continue)
                else:
                    _inv, _inv_r = _check_breakout_invalidation(c, _ltp_c, _rsi_c)
                    if _inv:
                        _invalidated_count += 1
                        _INVALIDATED_THIS_CYCLE[_sym_c] = _inv_r   # ← Phase A fix: was never written
                        log.info("[BreakoutInvalidation] %s: %s — removed from prepared pool.",
                                 _sym_c, _inv_r)
                        # Forensic telemetry: record invalidation event (observational only)
                        try:
                            from control_tower.pipeline_forensic_reporter import get_forensic_reporter as _gfr
                            _gfr().record_invalidation(_sym_c, _inv_r)
                        except Exception:
                            pass
                        # ── Patch 6: FalseBreakoutLearning telemetry ────────────────────
                        try:
                            from data_feeds.false_breakout_tracker import get_false_breakout_tracker as _gfbt
                            _gfbt().record_invalidation(
                                symbol=_sym_c,
                                failure_reason=_inv_r,
                                sector=c.get("sector", ""),
                            )
                        except Exception:
                            pass
                        # ── Phase A/B/C: InvalidationTracker — persistence + feed classification + recurrence ──
                        _git().record_invalidation(
                            symbol=_sym_c,
                            reason=_inv_r,
                            live_ltp=_ltp_c,
                            base_ltp=float(c.get("base_ltp", 0.0) or 0.0),
                            raw_source=_FEED_SOURCE_CACHE.get(_sym_c, ""),
                        )
                        continue
            except Exception:
                # Fallback: run original logic if suppression check itself fails
                _inv, _inv_r = _check_breakout_invalidation(c, _ltp_c, _rsi_c)
                if _inv:
                    _invalidated_count += 1
                    _INVALIDATED_THIS_CYCLE[_sym_c] = _inv_r
                    log.info("[BreakoutInvalidation] %s: %s — removed from prepared pool.",
                             _sym_c, _inv_r)
                    try:
                        from control_tower.pipeline_forensic_reporter import get_forensic_reporter as _gfr
                        _gfr().record_invalidation(_sym_c, _inv_r)
                    except Exception:
                        pass
                    try:
                        from data_feeds.false_breakout_tracker import get_false_breakout_tracker as _gfbt
                        _gfbt().record_invalidation(
                            symbol=_sym_c,
                            failure_reason=_inv_r,
                            sector=c.get("sector", ""),
                        )
                    except Exception:
                        pass
                    try:
                        from opportunity_engine.invalidation_tracker import get_invalidation_tracker as _git2
                        _git2().record_invalidation(
                            symbol=_sym_c,
                            reason=_inv_r,
                            live_ltp=_ltp_c,
                            base_ltp=float(c.get("base_ltp", 0.0) or 0.0),
                            raw_source=_FEED_SOURCE_CACHE.get(_sym_c, ""),
                        )
                    except Exception:
                        pass
                    continue
            # ── Phase A: Recovery check — emits [InvalidationRecovery] if symbol had prior record ──
            try:
                from opportunity_engine.invalidation_tracker import get_invalidation_tracker as _git
                _git().check_recovery(_sym_c)
            except Exception:
                pass
            # ──────────────────────────────────────────────────────────────────

            # ── V2: Lifecycle state (telemetry tag) ───────────────────────────────
            _lifecycle = (
                _compute_lc(c, live_ltp=_ltp_c, live_rsi=_rsi_c, now_utc=now_utc)
                if _compute_lc else "ACTIVE"
            )

            # ── Patch 7: data_trust_score (observational — does not gate execution) ──
            _trust_score = 1.0
            try:
                from data_feeds.data_integrity_tracker import get_data_integrity_tracker as _gdit_tw
                _trust_score = _gdit_tw().get_trust_score(_sym_c)
            except Exception:
                pass

            rows.append({
                "symbol":           c["symbol"],
                "ltp":              _PRICE_CACHE.get(c["symbol"], c.get("base_ltp", 0.0)),
                "resistance":       c["resistance"],
                "support":          c["support"],
                "volume_ratio":     c.get("volume_ratio", 1.0),
                "rsi":              c.get("rsi", 50.0),
                "adv_crore":        c.get("adv_crore", 0.0),
                "score":            c.get("score", 0.5),   # V2: sector re-rank + conviction decay
                "sector":           c.get("sector", ""),   # V2: sector re-rank (was missing)
                "_prepared":        True,                  # audit tag — never read by _identify_setup()
                "_lifecycle_state": _lifecycle,            # V2 lifecycle telemetry
                "_atr14":           c.get("atr14", 0.0),  # V2 conviction decay
                "_base_ltp":        c.get("base_ltp", 0.0),
                "data_trust_score": round(_trust_score, 2), # Patch 7: observational only
            })

        _pu_t_loop_ms = (time.monotonic() - _pu_t_lp0) * 1000  # P1 diagnostic
        if expired_count:
            log.debug("[PreparedWatchlist] Dropped %d candidates with expired valid_until_utc.", expired_count)

        # ── Fix 4: Live RSI overlay (stale-while-revalidate) ──────────────────
        # Trigger a background RSI refresh if the cache is stale (>5 min).
        # This cycle immediately overlays whatever is in _RSI_CACHE (may be
        # fresh or from the previous refresh cycle — never blocks).
        _now_m = time.monotonic()
        with _RSI_CACHE_LOCK:
            _rsi_is_stale = (not _RSI_CACHE) or (_now_m - _RSI_CACHE_TS > _RSI_CACHE_TTL)
            _rsi_snapshot = dict(_RSI_CACHE)

        if _rsi_is_stale and rows and not _RSI_REFRESH_RUNNING.is_set():
            _RSI_REFRESH_RUNNING.set()
            _threading.Thread(
                target=_background_rsi_refresh,
                args=([r["symbol"] for r in rows],),
                daemon=True,
                name="RSIRefresh",
            ).start()
            log.debug("[PreparedWatchlist] Background RSI refresh triggered for %d symbols.",
                      len(rows))

        _rsi_updated = 0
        for row in rows:
            live_rsi = _rsi_snapshot.get(row["symbol"])
            if live_rsi is not None and abs(live_rsi - row.get("rsi", 50.0)) > 0.01:
                row["rsi"] = live_rsi
                _rsi_updated += 1
        if _rsi_updated:
            log.debug("[PreparedWatchlist] Live RSI overlay applied to %d/%d candidates.",
                      _rsi_updated, len(rows))
        # ─────────────────────────────────────────────────────────────────────

        if _invalidated_count:
            log.info("[PreparedWatchlist] Breakout invalidation engine removed %d structurally-failed candidates.",
                     _invalidated_count)

        # ── V2: Smart conviction decay ──────────────────────────────────────────────
        # In-memory score adjustment for this cycle’s sector re-ranking priority.
        # Uses single worst-applicable decay rule (no stacking).
        # Store file is unchanged — only affects evaluation order within this cycle.
        _pu_t_dc0 = time.monotonic()  # P1 diagnostic
        _decay_log: List[str] = []
        with _RSI_CACHE_LOCK:
            _rsi_snap_d = dict(_RSI_CACHE)
        for _row_d in rows:
            _sym_d  = _row_d["symbol"]
            _sc_d   = float(_row_d.get("score", 0.5))
            _vol_d  = float(_row_d.get("volume_ratio", 1.0))
            _rsi_d  = _rsi_snap_d.get(_sym_d) or float(_row_d.get("rsi", 50))
            _ltp_d  = float(_row_d.get("ltp", 0))
            _atr_d  = float(_row_d.get("_atr14", 0)) or (_ltp_d * 0.020 if _ltp_d > 0 else 0)
            _res_d  = float(_row_d.get("resistance", 0))
            _nr     = _res_d > 0 and _ltp_d > 0 and abs(_ltp_d - _res_d) / _res_d <= 0.025

            if _vol_d < 0.40:
                _rate, _dr = 0.840, "vol_collapse"
            elif _rsi_d > 72 or _rsi_d < 28:
                _rate, _dr = 0.910, "momentum_extreme"
            elif _atr_d > 0 and _ltp_d > 0 and _atr_d / _ltp_d < 0.005:
                _rate, _dr = 0.925, "vol_compression"
            elif _vol_d >= 3.0 and _nr:
                _rate, _dr = 0.988, "strong_breakout"
            elif _vol_d >= 2.0:
                _rate, _dr = 0.972, "vol_continuation"
            else:
                _rate, _dr = 0.980, "normal"

            _ns = round(_sc_d * _rate, 4)
            _row_d["score"] = _ns
            if _dr != "normal" and abs(_ns - _sc_d) > 0.001:
                _decay_log.append(f"{_sym_d}:{_sc_d:.3f}→{_ns:.3f}[{_dr}]")
                # Forensic telemetry: record conviction decay event (observational only)
                try:
                    from control_tower.pipeline_forensic_reporter import get_forensic_reporter as _gfr
                    _gfr().record_conviction_decay()
                except Exception:
                    pass
        if _decay_log:
            log.debug("[ConvictionDecay] %s", " | ".join(_decay_log[:8]))

        # ── V2: Lifecycle distribution telemetry ─────────────────────────────────────
        if rows:
            from collections import Counter as _LCC
            _lc_dist = dict(_LCC(r.get("_lifecycle_state", "ACTIVE") for r in rows))
            log.debug("[LifecycleDistribution] %s total=%d", _lc_dist, len(rows))

        log.info(  # P1 diagnostic
            "[OELatencyProfilePU] total_ms=%.0f  store_read_ms=%.0f"
            "  candidate_loop_ms=%.0f  conviction_decay_ms=%.0f"
            "  n_candidates=%d  n_rows=%d",
            (time.monotonic() - _pu_t0) * 1000, _pu_t_read_ms,
            _pu_t_loop_ms, (time.monotonic() - _pu_t_dc0) * 1000,
            len(candidates) if candidates else 0, len(rows),
        )
        # Patch 5 — reset fallback counter on success
        CandidateStore.record_prepared_success()

        # Patch 1 — update stats for health heartbeat
        _LAST_PREPARED_STATS = {
            "prepared_count":    len(rows),
            "raw_candidates":    len(candidates),
            "expired_count":     expired_count,
            "invalidated_count": _invalidated_count,   # V2
            "fallback_used":     False,
            "reason":            "OK",
            "fallback_sessions":  0,
        }
        return rows

    except Exception as exc:
        log.warning("[PreparedWatchlist] Failed to load prepared universe — falling back to static: %s", exc)
        _LAST_PREPARED_STATS = {
            "prepared_count": 0, "expired_count": 0,
            "fallback_used": True, "reason": f"EXCEPTION:{type(exc).__name__}",
        }
        return []


def _check_safe_mode_triggers(prepared: list) -> None:
    """
    Patch 7 — Evaluate safe-mode trigger conditions every scan() cycle.

    Sets _SAFE_MODE_ACTIVE = True (+ _SAFE_MODE_REASON) if ANY condition fires.
    Emits [PreparedUniverseSafeMode] on state change (trigger or recovery).

    SAFE MODE only disables the prepared-universe and exploration layers.
    It NEVER stops the engine, closes positions, or pauses monitoring.
    The system continues running on the static watchlist — same as before
    Phase D was introduced.

    Clears safe mode when all conditions are resolved.
    """
    global _SAFE_MODE_ACTIVE, _SAFE_MODE_REASON
    reasons: list = []

    try:
        from config import SAFE_MODE_MAX_FALLBACK_SESSIONS, SAFE_MODE_MAX_MISSING_LTP_PCT
        _max_fallback = SAFE_MODE_MAX_FALLBACK_SESSIONS
        _max_ltp_miss = SAFE_MODE_MAX_MISSING_LTP_PCT
    except ImportError:
        _max_fallback = 3
        _max_ltp_miss = 50.0

    # ── Pre-compute time context ──────────────────────────────────────────────
    from datetime import datetime as _sm_dt, timezone as _sm_tz
    _now_utc  = _sm_dt.now(_sm_tz.utc)
    _mins_utc = _now_utc.hour * 60 + _now_utc.minute
    # Market hours = Mon–Fri, 03:45–10:00 UTC (= IST 09:15–15:30)
    _in_market_hours = _now_utc.weekday() < 5 and 225 <= _mins_utc <= 600

    # ── Pre-compute store age; auto-reset stale counter on fresh store ────────
    # If the store was written < 2h ago the scanner clearly ran successfully,
    # so reset the fallback counter immediately.  This prevents false safe_mode
    # lock after VPS restarts or fresh deploys where the counter accumulated
    # over a gap but the data is now good.
    _store_age_h = 999.0  # default: treat as old when unreadable
    try:
        from opportunity_engine.candidate_store import CandidateStore as _CSa
        _oe_io_counters["json_reads"] += 1
        _ctx = _CSa.read_context()
        if _ctx and _ctx.get("prepared_at"):
            _pa = _sm_dt.fromisoformat(_ctx["prepared_at"].replace("Z", "+00:00"))
            _store_age_h = (_now_utc - _pa).total_seconds() / 3600.0
            if _store_age_h < 2.0:
                _CSa.record_prepared_success()
                log.debug(
                    "[SafeMode] Store is fresh (age=%.1fh) — fallback counter auto-reset.",
                    _store_age_h,
                )
    except Exception:
        pass

    # Trigger 1: repeated stale fallback sessions
    # Gated by: (1) store is genuinely old (>24h) AND (2) currently in market hours.
    # Without both gates this trigger fires falsely after VPS restarts, weekend
    # gaps, and missed pre-market jobs — none of which are data-quality failures.
    try:
        from opportunity_engine.candidate_store import CandidateStore
        fallback_count = CandidateStore.get_consecutive_fallback_count()
        if fallback_count > _max_fallback and _in_market_hours and _store_age_h > 24.0:
            reasons.append(f"REPEATED_STALE_FALLBACK:sessions={fallback_count}")
    except Exception:
        pass

    # Trigger 2: excessive missing LTPs in prepared candidates
    if prepared:
        missing_ltp = sum(1 for r in prepared if not r.get("ltp", 0) or r.get("ltp", 0) <= 0)
        missing_pct = missing_ltp / len(prepared) * 100.0
        if missing_pct > _max_ltp_miss:
            reasons.append(f"MISSING_LTP:{missing_pct:.1f}%>{_max_ltp_miss:.0f}%")

    # Trigger 3: corrupted/incomplete premarket refresh past market open
    try:
        from opportunity_engine.candidate_store import CandidateStore as _CS
        _oe_io_counters["json_reads"] += 1
        context = _CS.read_context()
        if context and not context.get("premarket_refresh_complete", True):
            # Past 09:30 IST (04:00 UTC) without premarket completion → degraded
            if _now_utc.hour >= 4:
                reasons.append("PREMARKET_INCOMPLETE_AT_OPEN")
    except Exception:
        pass

    previously_active = _SAFE_MODE_ACTIVE

    if reasons:
        _SAFE_MODE_ACTIVE = True
        _SAFE_MODE_REASON = " | ".join(reasons)
        if not previously_active:
            log.warning(
                "[PreparedUniverseSafeMode] ACTIVATED reasons=%s"
                " — prepared universe DISABLED, static fallback active."
                " Engine/positions/monitoring unaffected.",
                _SAFE_MODE_REASON,
            )
            # Immediate Telegram alert so operator knows before the next manual check.
            # Without this, safe_mode can silently block an entire trading day
            # (confirmed May 25 2026: 7 cycles blocked, discovered only in EOD review).
            try:
                from notifications.notifier_manager import get_notifier
                get_notifier().market_alert(
                    "⚠️ Scanner Safe Mode ACTIVE",
                    f"Reason: {_SAFE_MODE_REASON}\n"
                    "All NEW signals blocked — only static 20-symbol fallback active.\n"
                    "Carry positions and monitoring are unaffected.\n"
                    "Auto-recovers when candidate store is refreshed.",
                )
            except Exception:
                pass
    else:
        _SAFE_MODE_ACTIVE = False
        _SAFE_MODE_REASON = ""
        if previously_active:
            log.info("[PreparedUniverseSafeMode] RECOVERED — conditions cleared,"
                     " prepared universe re-enabled.")
            try:
                from notifications.notifier_manager import get_notifier
                get_notifier().market_alert(
                    "✅ Scanner Safe Mode CLEARED",
                    "All trigger conditions resolved.\n"
                    "Prepared universe re-enabled — full candidate list restored.",
                )
            except Exception:
                pass


def _emit_prepared_universe_health(
    prepared_count: int,
    fallback_used: bool,
    watchlist_total: int,
) -> None:
    """
    Patch 1 — Operational telemetry heartbeat for the entire prepared-universe
    subsystem.  Fires once per scan() cycle after the prepared/static merge.
    Emits [PreparedUniverseHealth] — the single operational status tag for
    all prepared-universe components (scanner, premarket refiner, store, feed).

    Never raises — if anything fails the heartbeat is silently omitted.
    Emits even in fallback mode so gaps are visible in logs.
    """
    try:
        store_age_min: Optional[float] = None
        premarket_complete: bool = False
        coverage_pct: float = 0.0
        shadow_mode: bool = False

        try:
            from config import SCANNER_SHADOW_MODE
            shadow_mode = SCANNER_SHADOW_MODE
        except ImportError:
            pass

        # Pull live stats from candidate store (cheap file read, already cached by OS)
        try:
            from opportunity_engine.candidate_store import CandidateStore, STORE_FILE
            import json as _json
            if STORE_FILE.exists():
                _oe_io_counters["file_reads"] += 1
                _payload = _json.loads(STORE_FILE.read_text(encoding="utf-8"))
                _stats = _payload.get("scanner_stats", {})
                coverage_pct = float(_stats.get("coverage_pct", 0.0))
                premarket_complete = bool(_payload.get("premarket_refresh_complete", False))
                _prepared_at = _payload.get("prepared_at", "")
                if _prepared_at:
                    from datetime import datetime, timezone as _tz
                    _ts = datetime.fromisoformat(_prepared_at.replace("Z", "+00:00"))
                    store_age_min = round(
                        (datetime.now(_tz.utc) - _ts).total_seconds() / 60.0, 1
                    )
        except Exception:
            pass

        stats = _LAST_PREPARED_STATS
        expired_count = stats.get("expired_count", 0)

        # Fix 2: compute live coverage from the fraction of the prepared store
        # that is still valid this cycle (not the frozen pre-market scan ratio).
        total_in_store = prepared_count + expired_count
        live_coverage_pct = round(prepared_count / total_in_store * 100.0, 1) if total_in_store > 0 else 0.0

        # V2 — Fallback governance: track rolling trend + escalate on HIGH/CRITICAL severity
        _FALLBACK_TREND.append(live_coverage_pct)
        while len(_FALLBACK_TREND) > _FALLBACK_TREND_WINDOW:
            _FALLBACK_TREND.pop(0)
        _fallback_sev  = _fallback_severity_tier(live_coverage_pct)
        _pool_trend    = _get_fallback_trend()
        if _fallback_sev in ("HIGH", "CRITICAL") and not _SAFE_MODE_ACTIVE:
            log.warning(
                "[FallbackGovernance] severity=%s live_cov=%.1f%% prepared=%d floor=%d"
                " trend=%s — prepared pool requires replenishment.",
                _fallback_sev, live_coverage_pct, prepared_count, _POOL_FLOOR_MIN, _pool_trend,
            )

        _explore_budget = 3
        try:
            from config import EXPLORATION_BUDGET_PCT
            _explore_budget = EXPLORATION_BUDGET_PCT
        except ImportError:
            pass

        log.info(
            "[PreparedUniverseHealth]"
            " coverage_pct=%.1f"
            " live_coverage_pct=%.1f"
            " fallback_severity=%s"
            " pool_trend=%s"
            " prepared_count=%d"
            " expired_count=%d"
            " invalidated_count=%d"
            " fallback_used=%s"
            " premarket_complete=%s"
            " exploration_budget_pct=%d"
            " scanner_feed=YAHOO_FALLBACK"
            " store_age_min=%s"
            " shadow_mode=%s"
            " safe_mode=%s"
            " watchlist_total=%d",
            coverage_pct,
            live_coverage_pct,
            _fallback_sev,
            _pool_trend,
            prepared_count,
            expired_count,
            stats.get("invalidated_count", 0),
            fallback_used,
            premarket_complete,
            _explore_budget,
            f"{store_age_min:.1f}" if store_age_min is not None else "N/A",
            shadow_mode,
            _SAFE_MODE_ACTIVE,
            watchlist_total,
        )
    except Exception:
        pass   # health emit must never propagate exceptions


def get_session_exploration_stats() -> dict:
    """
    Returns a snapshot of this session's exploration counters.
    Called by master_orchestrator._run_exploration_audit() at EOD.
    Read-only — never clears the counters (reset on container restart).
    """
    return dict(_EXPLORE_STATS)


def _live_watchlist(extended: bool = False) -> List[Dict[str, Any]]:
    """
    Returns watchlist rows with the best available LTP:
      1. Real-time price from data feed (yfinance/.NS) — 60s cached
      2. Per-minute seeded simulation as fallback (only for warm-cache misses)

    Cold-start guard: if the price cache is empty on the first call after a
    container restart, waits up to _PRICE_GUARD_MAX_WAIT_S for live data.
    Returns [] if live prices still cannot be obtained — scan() will return no
    signals, preventing trades on stale base_ltp fallback values.
    When ``extended=True`` the wider NIFTY200/500 universe is also included.
    """
    global _PRICE_CACHE, _PRICE_CACHE_TS

    source = _BASE_WATCHLIST + (_EXTENDED_WATCHLIST if extended else [])
    all_symbols = [s["symbol"] for s in source]
    live_prices = _fetch_live_prices(all_symbols)

    # ── PriceGuard: cold-start protection ───────────────────────────────────
    # _fetch_live_prices() returns {} on cold start (cache empty) and fires a
    # background thread.  Guard waits for that thread, then falls back to a
    # direct blocking fetch.  If both fail, the cycle is skipped entirely.
    if not live_prices:
        # Re-check immediately — background thread may have just finished
        with _PRICE_CACHE_LOCK:
            live_prices = dict(_PRICE_CACHE)

        if not live_prices:
            log.info(
                "[PriceGuard] Cache empty — waiting up to %.0fs for price refresh...",
                _PRICE_GUARD_MAX_WAIT_S,
            )
            _t_guard = time.monotonic()
            _PRICE_CACHE_READY.wait(timeout=_PRICE_GUARD_MAX_WAIT_S)
            waited = time.monotonic() - _t_guard
            with _PRICE_CACHE_LOCK:
                live_prices = dict(_PRICE_CACHE)
            if live_prices:
                log.info(
                    "[PriceGuard] Cache populated after %.2fs wait (%d symbols).",
                    waited, len(live_prices),
                )

            # Background thread returned no data (yfinance down?) —
            # attempt one direct blocking fetch as last resort
            if not live_prices:
                log.info(
                    "[PriceGuard] Background refresh yielded no data — trying direct fetch..."
                )
                live_prices = _do_fetch_prices(all_symbols)
                if live_prices:
                    with _PRICE_CACHE_LOCK:
                        _PRICE_CACHE    = live_prices
                        _PRICE_CACHE_TS = time.monotonic()
                    _PRICE_CACHE_READY.set()
                    log.info(
                        "[PriceGuard] Direct fetch succeeded (%d symbols).", len(live_prices)
                    )
                else:
                    log.warning(
                        "[PriceGuard] Skipping cycle — no live price data after %.0fs wait.",
                        _PRICE_GUARD_MAX_WAIT_S,
                    )
                    return []

    rng = random.Random(int(datetime.now().timestamp()) // 60)
    rows = []
    for s in source:
        real_ltp = live_prices.get(s["symbol"].strip(), 0.0)
        if real_ltp > 0:
            live_ltp = real_ltp
        else:
            noise    = rng.uniform(-0.008, 0.008)
            live_ltp = round(s["base_ltp"] * (1 + noise), 2)

        vol_jitter = round(s["volume_ratio"] + rng.uniform(-0.2, 0.2), 2)
        rsi_jitter = round(s["rsi"]          + rng.uniform(-2,   2),   1)
        rows.append({
            # Strip trailing spaces: watchlist entries are column-aligned with
            # padding (e.g. "ITC         "). Without stripping these propagate
            # into OrderRecord.symbol, order IDs, and InstrumentRegistry lookups,
            # silently bypassing the SL Integrity Gate for all scanner symbols.
            "symbol":       s["symbol"].strip(),
            "ltp":          live_ltp,
            "resistance":   s["resistance"],
            "support":      s["support"],
            "volume_ratio": max(0.1, vol_jitter),
            "rsi":          max(0, min(100, rsi_jitter)),
            "adv_crore":    s.get("adv_crore", 0.0),
        })
    return rows


class EquityScannerAI:
    """Scans equity universe for breakout, momentum, and retest setups."""

    def __init__(self):
        log.info("[EquityScannerAI] Initialised. Watchlist: %d stocks (base) + %d extended.",
                 len(_BASE_WATCHLIST), len(_EXTENDED_WATCHLIST))

    def scan(self, snapshot: MarketSnapshot, odm_directive=None) -> List[TradeSignal]:
        """
        Scan the watchlist for trade setups.

        Parameters
        ----------
        snapshot     : current market context
        odm_directive: optional ODMDirective from OpportunityDensityMonitor;
                       controls universe expansion, volume threshold, and
                       which secondary strategies are active.
        """
        # Unpack ODM directive (or use defaults if none supplied)
        use_extended    = getattr(odm_directive, 'expand_universe',  False)
        vol_ratio_min   = getattr(odm_directive, 'volume_ratio_min', 2.0)
        extra_strats    = getattr(odm_directive, 'extra_strategies',  [])
        odm_tier        = getattr(odm_directive, 'tier', 'NORMAL')

        _OE_CYCLE_SEQ[0] += 1
        _oe_cycle_id = _OE_CYCLE_SEQ[0]
        _oe_ts = datetime.now().strftime("%H:%M:%S")
        _oe_io_counters.update(json_reads=0, file_reads=0, ltp_cache_hits=0, ltp_cache_misses=0)

        # ── Phase E: merge prepared universe with static watchlist ───────────
        # Prepared candidates (from market_scanner.py) take priority;
        # static symbols fill any gap. LTPs are refreshed for prepared candidates.
        _sc_t0 = time.monotonic()  # P1 diagnostic
        prepared   = _prepared_watchlist()
        _sc_t1 = time.monotonic()  # P1 diagnostic — after prepared universe

        # Priority 4 (RankingInstabilityAudit): initialised here so they're
        # always defined regardless of whether `if len(prepared) > 0` fires.
        _rank_snapshot:  Dict[str, int]   = {}
        _score_snapshot: Dict[str, float] = {}

        # V2 — Pool floor governance: trigger background TTL refresh below critical threshold
        if 0 < len(prepared) < _POOL_FLOOR_MIN:
            log.warning(
                "[PoolFloorBreach] prepared=%d < floor=%d — launching background TTL refresh.",
                len(prepared), _POOL_FLOOR_MIN,
            )
            try:
                from opportunity_engine.candidate_store import CandidateStore as _CS_pf
                with _PRICE_CACHE_LOCK:
                    _pf_prices = dict(_PRICE_CACHE)
                if _pf_prices:
                    _threading.Thread(
                        target=lambda p=_pf_prices: _CS_pf.refresh_expired(p, extend_hours=4.0),
                        daemon=True,
                        name="PoolFloorRefresh",
                    ).start()
            except Exception as _pf_exc:
                log.debug("[PoolFloorBreach] Refresh thread failed: %s", _pf_exc)

        # Patch 7: evaluate safe-mode conditions using the freshly-loaded prepared list
        _check_safe_mode_triggers(prepared)
        # Re-fetch after safe-mode check (may have cleared prepared list)
        if _SAFE_MODE_ACTIVE and prepared:
            prepared = []

        static_raw = _live_watchlist(extended=use_extended)
        if prepared:
            prepared_syms  = {r["symbol"] for r in prepared}
            # Inject fresh LTPs from price cache into prepared candidates
            for row in prepared:
                cached_ltp = _PRICE_CACHE.get(row["symbol"], 0.0)
                if cached_ltp > 0:
                    row["ltp"] = cached_ltp
                    _oe_io_counters["ltp_cache_hits"] += 1
                else:
                    _oe_io_counters["ltp_cache_misses"] += 1

            # ── Fix 6: Re-rank prepared candidates by live sector rotation ────
            # Candidates in sectors currently receiving inflow move to the front
            # of the evaluation queue, improving signal priority intraday.
            _leaders = getattr(snapshot, "sector_leaders", None) or []
            if _leaders:
                _leaders_lower = [s.lower() for s in _leaders]
                def _sector_rank(cand: dict) -> int:
                    sec = cand.get("sector", "UNKNOWN").lower()
                    for i, ts in enumerate(_leaders_lower):
                        if ts in sec or sec in ts:
                            return i
                    return 99
                prepared.sort(key=lambda c: (_sector_rank(c), -float(c.get("score", 0))))
                log.debug("[SectorRerank] Prepared candidates reordered by sector momentum; "
                          "top-5: %s", [c["symbol"] for c in prepared[:5]])
            # ──────────────────────────────────────────────────────────────────

            # Priority 4 (RankingInstabilityAudit): snapshot rank after sort
            _rank_snapshot  = {c["symbol"]: i for i, c in enumerate(prepared)}
            _score_snapshot = {c["symbol"]: float(c.get("score", 0.0)) for c in prepared}

            gap_fill   = [s for s in static_raw if s["symbol"] not in prepared_syms]
            watchlist  = prepared + gap_fill
            # Fix 3: static_dominant flag — True when static gap-fill is ≥50% of pool
            _gap_fill_count = len(gap_fill)
            _static_dominant = (len(watchlist) > 0 and _gap_fill_count / len(watchlist) >= 0.50)
            log.info(
                "[CandidateStoreRead] prepared=%d static_gap_fill=%d total=%d"
                " use_extended=%s static_dominant=%s",
                len(prepared), _gap_fill_count, len(watchlist), use_extended, _static_dominant,
            )
        else:
            _static_dominant = True
            watchlist = static_raw
            if use_extended:
                pass  # ODM already logged this below
            else:
                log.debug("[StaticFallbackActivated] prepared_universe_unavailable=True"
                          " reason=NO_PREPARED_FILE_OR_DISABLED fallback_symbols=%d",
                          len(watchlist))

        # Patch 1 — operational health heartbeat (fires every scan cycle)
        _emit_prepared_universe_health(
            prepared_count=len(prepared),
            fallback_used=(len(prepared) == 0),
            watchlist_total=len(watchlist),
        )
        _sc_t2 = time.monotonic()  # P1 diagnostic — after setup (3 JSON reads done)

        # V2 — Event-driven mini rescan: evaluate trigger conditions post-cycle
        _lp_s = _LAST_PREPARED_STATS
        _lp_denom = max(1, _lp_s.get("prepared_count", 0) + _lp_s.get("expired_count", 0))
        _live_cov_now = _lp_s.get("prepared_count", 0) / _lp_denom * 100.0
        _check_mini_rescan_triggers(snapshot, len(prepared), _live_cov_now)

        if use_extended:
            log.info("[EquityScannerAI] ODM %s — scanning %d stocks (extended universe).",
                     odm_tier, len(watchlist))

        _sc_t3 = time.monotonic()  # P1 diagnostic — scanner AI loop start
        signals: List[TradeSignal] = []
        # Rejection reason counters
        _r: dict = {}
        # Patch 2/3: per-symbol signal result; populated for prepared candidates only
        _per_sym_result: Dict[str, Any] = {}
        for stock in watchlist:
            sig, reason = self._identify_setup(stock, snapshot,
                                               vol_ratio_min=vol_ratio_min,
                                               extra_strategies=extra_strats)
            # Patch 2/3: record per-symbol result for enrichment persistence
            if stock.get("_prepared"):
                _per_sym_result[stock["symbol"]] = {"sig": sig, "reason": reason}
            if sig:
                # ── MOP-RC-001: Attach observational fields (telemetry only — never gating) ─
                try:
                    _rr_obs = sig.risk_reward_ratio
                    if sig.atr and sig.entry_price and sig.entry_price > 0 and _rr_obs > 0:
                        sig.expected_move_pct = round(
                            sig.atr / sig.entry_price * _rr_obs * 100, 4
                        )
                    sig._obs_candidate_score = stock.get("score")
                    sig._obs_regime = getattr(snapshot.regime, "value", str(snapshot.regime))
                    # Stamp regime label and VIX onto signal for rejection audit context
                    sig.scanner_regime_label = sig._obs_regime
                    sig._vix = float(snapshot.vix or 0.0)
                except Exception:
                    pass
                # ── Universal opportunity lineage ID — generated ONCE here ─────────
                # Threads through LOL → KLP → KDA → broker for end-to-end traceability.
                try:
                    import uuid as _uuid
                    if not sig.opportunity_id:
                        sig.opportunity_id = str(_uuid.uuid4())
                except Exception:
                    pass
                # ─────────────────────────────────────────────────────────────────
                signals.append(sig)
                # ── EdgeTelemetry: lightweight signal feature snapshot ─────────
                # Each accepted signal is logged with the feature values that drove
                # selection so that log analysis can build an edge fingerprint over
                # time (which regime / setup types / ATR bands actually produce edge).
                _ltp    = stock.get("ltp", sig.entry_price) or sig.entry_price
                _res    = stock.get("resistance", 0.0) or 0.0
                _atr_pct= (sig.atr / _ltp * 100.0) if (sig.atr and _ltp > 0) else 0.0
                _rr_e   = (
                    abs(sig.target_price - sig.entry_price)
                    / abs(sig.entry_price - sig.stop_loss)
                    if sig.entry_price and sig.entry_price != sig.stop_loss else 0.0
                )
                _in_bull = (snapshot.regime == RegimeLabel.BULL_TREND)
                if sig.direction == SignalDirection.SHORT:
                    _setup = "high_rsi_short"
                elif _ltp > _res > 0:
                    _setup = "breakout"
                elif _res > 0 and (_res * 0.995) <= _ltp <= (_res * 1.01):
                    _setup = "momentum_retest"
                elif _in_bull:
                    _setup = "trend_pullback"
                else:
                    _setup = "mean_reversion_bounce"
                log.info(
                    "[EdgeTelemetry] signal_id=%s_%s  regime=%s  setup_type=%s"
                    "  atr_pct=%.2f  rsi=%.0f  vol_ratio=%.1f  entry=%.2f  rr=%.1f"
                    "  expected_move_pct=%s  candidate_score=%s",
                    stock["symbol"], datetime.now().strftime("%H%M%S"),
                    getattr(snapshot.regime, "value", str(snapshot.regime)),
                    _setup, _atr_pct,
                    stock.get("rsi", 0), stock.get("volume_ratio", 0),
                    sig.entry_price, _rr_e,
                    f"{sig.expected_move_pct:.4f}" if sig.expected_move_pct is not None else "null",
                    f"{sig._obs_candidate_score:.4f}" if sig._obs_candidate_score is not None else "null",
                )
                # ── MOP-RC-001: Record signal observation (never raises) ───────
                try:
                    from opportunity_engine.mop_rc001_observer import record_signal_observation
                    record_signal_observation(sig, stock)
                except Exception:
                    pass
                # ─────────────────────────────────────────────────────────────
            _r[reason] = _r.get(reason, 0) + 1
            log.debug(
                "[UniverseAudit] %-14s reason=%-22s rsi=%4.0f vol=%.1fx regime=%s",
                stock["symbol"], reason,
                stock.get("rsi", 0), stock.get("volume_ratio", 0),
                getattr(snapshot.regime, "value", snapshot.regime),
            )

        _sc_t4 = time.monotonic()  # P1 diagnostic — after scanner AI loop
        _regime_str = getattr(snapshot.regime, "value", str(snapshot.regime))
        _no_setup_detail = "  ".join(
            f"{k}={v}" for k, v in sorted(_r.items()) if k != "signal_found"
        )
        log.info(
            "[UniverseAudit] regime=%-14s total=%d signals=%d | %s",
            _regime_str, len(watchlist), len(signals),
            _no_setup_detail or "(no rejections)",
        )

        # ── Priority 4 (RankingInstabilityAudit): rank position churn ────────────
        # Compares this cycle's prepared-candidate rank order against previous cycle.
        # _rank_snapshot / _score_snapshot are populated by the sector-sort block
        # above (when prepared candidates exist); empty dict when static fallback.
        try:
            from opportunity_engine.ranking_instability_audit import get_ranking_audit as _gra
            _ra = _gra()
            _ra.record_cycle(
                current_ranks  = _rank_snapshot,
                current_scores = _score_snapshot,
                signals_found  = {s.symbol for s in signals},
            )
            _ra.emit_cycle_audit()
        except Exception:
            pass

        # ── Forensic telemetry: record scan-cycle metrics (observational only) ──
        try:
            from control_tower.pipeline_forensic_reporter import get_forensic_reporter as _gfr
            _gfr().record_scan_cycle(
                watchlist_total=len(watchlist),
                rejection_reasons=_r,
                signals_found=len(signals),
                regime=_regime_str,
            )
        except Exception:
            pass

        # ── Priority 3 (FilterFunnelAudit): per-stage candidate attrition ──────
        # Buckets all rejection reasons into named funnel stages so we can
        # distinguish over-filtering from market-driven silence.
        # Pre-filter counts (TTL expiry, invalidation) come from _LAST_PREPARED_STATS
        # which is updated by _prepared_watchlist() before scan() runs each cycle.
        try:
            from opportunity_engine.filter_funnel_audit import get_filter_funnel_audit as _gffa
            _ffa = _gffa()
            _ffa.record_cycle(
                prepared_count    = len(watchlist),
                ttl_rejected      = _LAST_PREPARED_STATS.get("expired_count", 0),
                invalidated       = _LAST_PREPARED_STATS.get("invalidated_count", 0),
                rejection_reasons = _r,
            )
            _ffa.emit_cycle_audit()
            # [Audit 1] emit full funnel compression after both scanner + scan stages
            _ffa.emit_funnelcompression()
        except Exception:
            pass

        # ── Universal enrichment persistence: ALL store candidates get metadata ──
        # Universal Baseline Enrichment Patchset (Phase 3):
        # Step 1 — UNIVERSAL BASELINE: build enrichment for ALL store candidates
        # Step 2 — SCAN OVERRIDE: refine prepared candidates with live scan data
        # Step 3 — INVALIDATION: mark this cycle's invalidated candidates
        _sc_t5 = time.monotonic()  # P1 diagnostic — enrichment start (4th JSON read)
        try:
            from opportunity_engine.candidate_store import CandidateStore as _CS_enrich
            from datetime import datetime as _dt_enrich, timezone as _tz_enrich

            _enrichment_map: Dict[str, Any] = {}

            # Step 1 — Universal baseline: cover ALL candidates in the store
            # (includes expired, previously-invalidated, and non-prepared candidates)
            try:
                _all_store_raw = _CS_enrich.read() or []
                _oe_io_counters["json_reads"] += 1
                _now_e = _dt_enrich.now(_tz_enrich.utc)
                for _raw_c in _all_store_raw:
                    _sym_e = _raw_c.get("symbol", "")
                    if not _sym_e:
                        continue
                    _rsi_e = float(_raw_c.get("rsi") or 50)
                    # Preserve existing lifecycle; derive EXPIRED from TTL for non-invalidated
                    _lc_e = _raw_c.get("lifecycle_state") or "ACTIVE"
                    if _lc_e not in ("INVALIDATED",):
                        _vu_e = _raw_c.get("valid_until_utc") or ""
                        if _vu_e:
                            try:
                                _exp_e = _dt_enrich.fromisoformat(_vu_e.replace("Z", "+00:00"))
                                if _now_e > _exp_e:
                                    _lc_e = "EXPIRED"
                            except Exception:
                                pass
                    # Fix: compute actual freshness age from prepared_at; use prepared_at as last_refresh_time
                    _fpa_e = _raw_c.get("prepared_at", "")
                    try:
                        _fage_e = max(0, int((_now_e - _dt_enrich.fromisoformat(
                            _fpa_e.replace("Z", "+00:00")
                        )).total_seconds() / 60)) if _fpa_e else 0
                    except Exception:
                        _fage_e = 0
                    # Fix: compute actual freshness age from prepared_at (was hardcoded 0)
                    _fpa_e = _raw_c.get("prepared_at", "")
                    try:
                        _fage_e = max(0, int((_now_e - _dt_enrich.fromisoformat(
                            _fpa_e.replace("Z", "+00:00")
                        )).total_seconds() / 60)) if _fpa_e else 0
                    except Exception:
                        _fage_e = 0
                    _enrichment_map[_sym_e] = {
                        "strategy":            _raw_c.get("strategy") or "pending_scan",
                        "lifecycle_state":     _lc_e,
                        "data_trust_score":    float(_raw_c.get("data_trust_score") or 1.0),
                        "conviction_score":    float(_raw_c.get("conviction_score") or 0.0),
                        "invalidation_state":  _raw_c.get("invalidation_state") or "valid",
                        "exploration_flag":    bool(_raw_c.get("exploration_flag", False)),
                        "refinement_status":   _raw_c.get("refinement_status") or "raw",
                        "candidate_origin":    "prepared_universe",
                        "momentum_state":      (
                            "overbought" if _rsi_e > 70 else
                            "oversold"   if _rsi_e < 30 else
                            "strong"     if _rsi_e > 60 else
                            "weak"       if _rsi_e < 40 else
                            "neutral"
                        ),
                        "breakout_state":      _raw_c.get("breakout_state") or "unknown",
                        "freshness_age_minutes": _fage_e,
                        "last_refresh_time":   _raw_c.get("prepared_at") or _raw_c.get("valid_until_utc") or "",
                        "fallback_contaminated": bool(_raw_c.get("fallback_contaminated", False)),
                        "corruption_flags":    _raw_c.get("corruption_flags") or [],
                        "simulation_status":   "live",
                        "rerank_reason":       _raw_c.get("rerank_reason") or "",
                        "regime_bias_applied": _regime_str,
                    }
                log.debug(
                    "[UniversalEnrichmentPass] Baseline built for %d store candidates.",
                    len(_enrichment_map),
                )
                # Priority 5 (LifecycleTransitionAudit): snapshot lifecycle states
                # before this cycle's scan overrides them, so we can diff after.
                _lc_before_map: Dict[str, str] = {
                    _bc.get("symbol", ""): _bc.get("lifecycle_state") or "UNKNOWN"
                    for _bc in _all_store_raw if _bc.get("symbol")
                }
            except Exception as _ue_err:
                log.debug("[UniversalEnrichmentPass] Store read skipped: %s", _ue_err)
                _lc_before_map = {}

            # Step 2 — Scan override: enrich prepared candidates with scan-time data
            for _erow in prepared:
                _esym = _erow.get("symbol", "")
                if not _esym:
                    continue
                _eresult   = _per_sym_result.get(_esym, {})
                _esig      = _eresult.get("sig")
                _estrategy = (
                    getattr(_esig, "strategy_name", None) or _eresult.get("reason", "no_setup")
                    if _esig is not None
                    else _eresult.get("reason", "no_setup")
                )
                _ersi  = float(_erow.get("rsi") or 50)
                _eltp  = float(_erow.get("ltp") or 0)
                _eres  = float(_erow.get("resistance") or 0)
                _emom  = (
                    "overbought" if _ersi > 70 else
                    "oversold"   if _ersi < 30 else
                    "strong"     if _ersi > 60 else
                    "weak"       if _ersi < 40 else
                    "neutral"
                )
                _ebrkout = (
                    "above_resistance" if (_eres > 0 and _eltp > _eres) else
                    "near_resistance"  if (_eres > 0 and _eltp >= _eres * 0.99) else
                    "below_resistance"
                )
                _etrust = float(_erow.get("data_trust_score") or 1.0)

                # ── Priority 2 (FallbackContaminationAudit): source-aware trust ──
                # Read which feed actually served this symbol's live price.
                # Apply a multiplicative trust penalty based on feed quality tier.
                _esrc = (_FEED_SOURCE_CACHE.get(_esym) or "").upper()
                _esrc_multiplier = {
                    "DHAN":  1.00,   # live broker feed — no reduction
                    "YAHOO": 0.85,   # real data, slight delay/spread
                    "CACHE": 0.80,   # stale cached quote
                    "SIM":   0.60,   # synthetic / simulated
                }.get(_esrc, 1.00)   # 1.00 when source not yet known (first cycle)
                _etrust_final = round(_etrust * _esrc_multiplier, 3)
                _efallback = _esrc in ("YAHOO", "CACHE", "SIM")

                # Record enrichment provenance for this symbol
                try:
                    from data_feeds.fallback_contamination_audit import get_fallback_audit as _gfa_e
                    _gfa_e().record_enrichment(_esym, _esrc)
                except Exception:
                    pass

                # Build corruption flags: preserve existing + append source tag
                _eflags: list = list(_erow.get("corruption_flags") or [])
                if _etrust_final < 0.7 and "low_trust" not in _eflags:
                    _eflags.append("low_trust")
                if _efallback:
                    _fsrc_tag = f"fallback_{_esrc.lower()}"
                    if _fsrc_tag not in _eflags:
                        _eflags.append(_fsrc_tag)
                # ── end Priority 2 ───────────────────────────────────────────

                # Fix: compute actual freshness age from prepared_at (was hardcoded 0)
                _epa_str = _erow.get("prepared_at", "")
                try:
                    _efreshness = max(0, int((_dt_enrich.now(_tz_enrich.utc) - _dt_enrich.fromisoformat(
                        _epa_str.replace("Z", "+00:00")
                    )).total_seconds() / 60)) if _epa_str else 0
                except Exception:
                    _efreshness = 0
                _enrichment_map[_esym] = {
                    "strategy":            _estrategy,
                    "lifecycle_state":     _erow.get("_lifecycle_state", "ACTIVE"),
                    "data_trust_score":    _etrust_final,
                    "conviction_score":    getattr(_esig, "confidence", 0.0) if _esig else 0.0,
                    "invalidation_state":  "valid",
                    "exploration_flag":    False,
                    "refinement_status":   "premarket_refined",
                    "candidate_origin":    "prepared_universe",
                    "momentum_state":      _emom,
                    "breakout_state":      _ebrkout,
                    "freshness_age_minutes": _efreshness,
                    "last_refresh_time":   _erow.get("prepared_at", "") or _erow.get("valid_until_utc", ""),
                    "fallback_contaminated": _efallback,
                    "corruption_flags":    _eflags,
                    "simulation_status":   "live",
                    "rerank_reason":       f"sector:{_erow.get('sector', 'unknown')}",
                    "regime_bias_applied": _regime_str,
                }

            # Step 3 — Invalidation override: mark this cycle's invalidated candidates
            for _isym, _ireason in _INVALIDATED_THIS_CYCLE.items():
                _existing_trust = float(
                    (_enrichment_map.get(_isym) or {}).get("data_trust_score") or 1.0
                )
                _enrichment_map[_isym] = {
                    "strategy":            "invalidated",
                    "lifecycle_state":     "INVALIDATED",
                    "data_trust_score":    _existing_trust,
                    "conviction_score":    0.0,
                    "invalidation_state":  _ireason,
                    "exploration_flag":    False,
                    "refinement_status":   "premarket_refined",
                    "candidate_origin":    "prepared_universe",
                    "momentum_state":      "neutral",
                    "breakout_state":      "below_resistance",
                    # Fix: carry forward actual age computed in Step 1 baseline
                    "freshness_age_minutes": (_enrichment_map.get(_isym) or {}).get("freshness_age_minutes", 0),
                    "last_refresh_time":   "",
                    "fallback_contaminated": False,
                    "corruption_flags":    [],
                    "simulation_status":   "live",
                    "rerank_reason":       "invalidated",
                    "regime_bias_applied": _regime_str,
                }

            # ── [Audit 3] FreshnessValidation: confirm freshness_age_minutes is now accurate ──
            # Bugs fixed: Steps 1/2/3 now compute age from prepared_at; last_refresh_time
            # now stores prepared_at (not valid_until_utc). This block validates the fix:
            # always_zero_pct should be ~0% post-fix.
            try:
                from datetime import datetime as _fv_dt, timezone as _fv_tz
                _fv_now  = _fv_dt.now(_fv_tz.utc)
                _fv_raw_list = locals().get("_all_store_raw") or []
                _fv_total = len(_enrichment_map)
                _fv_zero  = sum(
                    1 for _v in _enrichment_map.values()
                    if _v.get("freshness_age_minutes", -1) == 0
                )
                _fv_expiry_mismatch = 0  # last_refresh_time == valid_until_utc (wrong field)
                _fv_ages: list = []
                for _fv_raw in _fv_raw_list:
                    _fv_sym  = _fv_raw.get("symbol", "")
                    _fv_pa   = _fv_raw.get("prepared_at", "")
                    _fv_vuu  = _fv_raw.get("valid_until_utc", "")
                    _fv_lrt  = (_enrichment_map.get(_fv_sym) or {}).get("last_refresh_time", "")
                    if _fv_lrt and _fv_vuu and _fv_lrt == _fv_vuu:
                        _fv_expiry_mismatch += 1
                    if _fv_pa:
                        try:
                            _fv_prepared = _fv_dt.fromisoformat(_fv_pa.replace("Z", "+00:00"))
                            _fv_ages.append(int((_fv_now - _fv_prepared).total_seconds() / 60))
                        except Exception:
                            pass
                log.info(
                    "[FreshnessValidation] enrichment_candidates=%d"
                    " always_zero_pct=%.1f%%"
                    " expiry_used_as_refresh=%d"
                    " candidates_with_prepared_at=%d"
                    " true_age_min_avg=%.1f true_age_min_max=%d"
                    " note=freshness_age_minutes_fixed_computed_from_prepared_at",
                    _fv_total,
                    (_fv_zero / _fv_total * 100.0) if _fv_total > 0 else 0.0,
                    _fv_expiry_mismatch,
                    len(_fv_ages),
                    sum(_fv_ages) / len(_fv_ages) if _fv_ages else 0.0,
                    max(_fv_ages) if _fv_ages else 0,
                )
            except Exception as _fv_err:
                log.debug("[FreshnessValidation] equity_scanner emit failed: %s", _fv_err)

            # ── Priority 5 (LifecycleTransitionAudit): diff before→after ────────
            try:
                from opportunity_engine.lifecycle_transition_audit import get_lifecycle_audit as _glt
                _lc_after_map = {
                    _asym: _av.get("lifecycle_state", "UNKNOWN")
                    for _asym, _av in _enrichment_map.items()
                }
                _glt().record_cycle(
                    before_states = locals().get("_lc_before_map", {}),
                    after_states  = _lc_after_map,
                )
                _glt().emit_cycle_audit()
            except Exception:
                pass

            # Write all enrichment — throttled internally by update_enrichment()
            if _enrichment_map:
                _CS_enrich.update_enrichment(_enrichment_map)
                log.debug(
                    "[UniversalEnrichmentPass] Submitted enrichment for %d candidates"
                    " (prepared=%d invalidated=%d).",
                    len(_enrichment_map), len(prepared), len(_INVALIDATED_THIS_CYCLE),
                )

            # Priority 2 (FallbackContaminationAudit): emit per-scan breakdown
            try:
                from data_feeds.fallback_contamination_audit import get_fallback_audit as _gfa_emit
                _gfa_emit().emit_scan_audit(scan_prepared_count=len(prepared))
            except Exception:
                pass

        except Exception as _enrich_err:
            log.debug("[EnrichedCandidateWrite] Enrichment persistence skipped: %s", _enrich_err)
        _sc_t6 = time.monotonic()  # P1 diagnostic — after enrichment
        _n_signals_pre_phase_h = len(signals)

        # ── Phase H — Hybrid exploration budget ──────────────────────────────
        # When USE_HYBRID_EXPLORATION is True and safe mode is NOT active,
        # allocate a small fraction of the per-cycle slot to opportunistic
        # discovery from the static watchlist.
        # Opportunistic signals use a higher confidence gate (EXPLORATION_THRESHOLD)
        # to compensate for the lack of overnight validation.
        # This only fires when prepared candidates were actually used (prepared list
        # was non-empty) — never adds exploration slots when fully in static mode.
        try:
            from config import USE_HYBRID_EXPLORATION, EXPLORATION_BUDGET_PCT, EXPLORATION_THRESHOLD
            if USE_HYBRID_EXPLORATION and prepared and not _SAFE_MODE_ACTIVE:
                # Calculate exploration slots as a fraction of total prepared slots
                explore_slots = max(1, len(prepared) * EXPLORATION_BUDGET_PCT // max(100 - EXPLORATION_BUDGET_PCT, 1))
                # Opportunistic candidates: static symbols not already in prepared set
                prepared_syms = {r["symbol"] for r in prepared}
                static_only = [s for s in _live_watchlist(extended=use_extended)
                               if s["symbol"] not in prepared_syms]
                # Run _identify_setup() on static_only symbols; keep only those
                # meeting the higher exploration threshold
                exploratory_signals = []
                for stock in static_only:
                    if len(exploratory_signals) >= explore_slots:
                        break
                    _sym = stock["symbol"]
                    # Fix 5: skip symbols that have failed the threshold too many times
                    if _EXPLORE_FAIL_COUNTS.get(_sym, 0) >= _EXPLORE_SKIP_THRESHOLD:
                        continue
                    try:
                        # Fix: _identify_setup returns (signal, reason) tuple
                        sig, _reason = self._identify_setup(stock, snapshot)
                    except Exception:
                        continue
                    # Section 4 — increment evaluated counter
                    _EXPLORE_STATS["evaluated"] += 1
                    if sig is None:
                        continue
                    raw_score = getattr(sig, "confidence", 0.0)
                    # Fix 5: resolve sector from nifty500 map when static watchlist has none
                    _sector = stock.get("sector") or _SYMBOL_SECTOR_MAP.get(_sym, "UNKNOWN")
                    _regime_label = getattr(snapshot.regime, "value", str(snapshot.regime))
                    # Section 4 — [ExplorationCandidate] emit when signal enters evaluation
                    log.info(
                        "[ExplorationCandidate] symbol=%s score=%.2f sector=%s"
                        " regime=%s threshold=%.1f passed=%s",
                        _sym, raw_score, _sector, _regime_label,
                        EXPLORATION_THRESHOLD, raw_score >= EXPLORATION_THRESHOLD,
                    )
                    if raw_score >= EXPLORATION_THRESHOLD:
                        sig = sig._replace(entry_label=getattr(sig, "entry_label", "") + "[EXPLORATORY]") if hasattr(sig, "_replace") else sig
                        exploratory_signals.append(sig)
                        _EXPLORE_STATS["signals_generated"] += 1
                        _EXPLORE_FAIL_COUNTS[_sym] = 0  # reset on pass
                    else:
                        # Fix 5: increment fail counter; symbol rotated out after threshold
                        _EXPLORE_FAIL_COUNTS[_sym] = _EXPLORE_FAIL_COUNTS.get(_sym, 0) + 1
                        if _EXPLORE_FAIL_COUNTS[_sym] == _EXPLORE_SKIP_THRESHOLD:
                            log.info(
                                "[ExplorationRotation] symbol=%s failed threshold %d times "
                                "— rotating out for rest of session.",
                                _sym, _EXPLORE_SKIP_THRESHOLD,
                            )

                if exploratory_signals:
                    log.info(
                        "[HybridExploration] Added %d opportunistic signals (budget=%d slots"
                        " threshold=%.1f safe_mode=%s).",
                        len(exploratory_signals), explore_slots, EXPLORATION_THRESHOLD,
                        _SAFE_MODE_ACTIVE,
                    )
                    signals.extend(exploratory_signals)
            elif USE_HYBRID_EXPLORATION and _SAFE_MODE_ACTIVE:
                log.debug("[HybridExploration] Skipped — safe_mode=True reason=%s", _SAFE_MODE_REASON)
        except Exception as _hex_err:
            log.debug("[HybridExploration] Skipped: %s", _hex_err)

        log.info(  # P1 diagnostic
            "[OELatencyProfile] cycle=%d  ts=%s"
            "  total=%.0fms  pu=%.0fms  setup=%.0fms"
            "  scanner=%.0fms  enrichment=%.0fms  phase_h=%.0fms"
            "  n_universe=%d  n_filtered=%d  n_ranked=%d"
            "  n_scanner_signals=%d  n_pre_phase_h=%d  n_final=%d"
            "  json_reads=%d  file_reads=%d  ltp_hits=%d  ltp_misses=%d",
            _oe_cycle_id, _oe_ts,
            (time.monotonic() - _sc_t0) * 1000,
            (_sc_t1 - _sc_t0) * 1000,
            (_sc_t2 - _sc_t1) * 1000,
            (_sc_t4 - _sc_t3) * 1000,
            (_sc_t6 - _sc_t5) * 1000,
            (time.monotonic() - _sc_t6) * 1000,
            _LAST_PREPARED_STATS.get("raw_candidates", len(prepared)),
            len(prepared),
            len(watchlist),
            _r.get("signal_found", 0), _n_signals_pre_phase_h, len(signals),
            _oe_io_counters["json_reads"], _oe_io_counters["file_reads"],
            _oe_io_counters["ltp_cache_hits"], _oe_io_counters["ltp_cache_misses"],
        )
        return signals

    def as_agent_output(self, snapshot: MarketSnapshot) -> AgentOutput:
        signals = self.scan(snapshot)  # uses _live_watchlist() internally
        return AgentOutput(
            agent_name="EquityScannerAI",
            status="ok",
            summary=f"{len(signals)} equity setups identified",
            confidence=7.0,
            data={"signals": signals},
        )

    # ─────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────

    def _identify_setup(
        self,
        stock: Dict[str, Any],
        snapshot: MarketSnapshot,
        vol_ratio_min: float = 2.0,
        extra_strategies: list | None = None,
    ) -> "tuple[TradeSignal | None, str]":
        """
        Returns (TradeSignal, 'signal_found') on match.
        Returns (None, reason_code) on rejection.

        Reason codes (for [UniverseAudit] breakdown):
          high_atr          — ATR% > volatility guard threshold
          bear_market       — hard regime block
          breakout_vol_low  — LTP above resistance; vol_ratio < min
          breakout_rsi_hi   — LTP above resistance + volume; RSI ≥ 75
          retest_rsi_oob    — LTP in resistance retest zone; RSI outside 50-65
          pullback_miss     — bull trend; near support; RSI/vol not in zone
          bull_gate         — bull trend; no breakout/retest/pullback; S4+S5 blocked
          short_conditions  — range/volatile; RSI < 67 or price < resistance*0.99
          bounce_price_hi   — RSI oversold but price above support zone
          rsi_neutral       — RSI 46-66, price in mid-range (no extreme setup)
        """
        ltp        = stock["ltp"]
        resistance = stock["resistance"]
        support    = stock["support"]
        vol_ratio  = stock.get("volume_ratio", 1.0)
        rsi        = stock.get("rsi", 50)
        adv_crore  = stock.get("adv_crore", 0.0)   # ₹ crore — used downstream by LiquidityGuard
        if extra_strategies is None:
            extra_strategies = []

        # ── Volatility guard ──────────────────────────────────────────
        # Skip signal if market is too noisy for reliable mean-reversion entries.
        atr     = _estimate_atr(ltp, support, resistance)
        atr_pct = (atr / ltp * 100.0) if ltp > 0 else 0.0
        if atr_pct > VOLATILITY_GUARD_ATR_PCT:
            return None, "high_atr"

        # ── Regime guard ──────────────────────────────────────────────
        # Hard-skip all setups in bear market; mean-reversion blocked in bull trend.
        if snapshot.regime == RegimeLabel.BEAR_MARKET:
            return None, "bear_market"
        in_bull_trend = (snapshot.regime == RegimeLabel.BULL_TREND)

        # ── Stop distance (market-logic only — ATR-based, no capital awareness) ────
        # The strategy is responsible ONLY for defining stop_price from market
        # mechanics (ATR * multiplier).  Position sizing is delegated entirely
        # to the Risk Engine (PortfolioAllocationAI).
        stop_dist = max(atr * ATR_STOP_MULTIPLIER, ltp * 0.010)  # floor at 1% of price

        # ── Setup 1: Breakout with volume ─────────────────────────────
        # Active in all non-bear regimes including BULL_TREND.
        # vol_ratio_min may be relaxed by ODM (default 2.0 → as low as 1.4 in SECONDARY).
        if ltp > resistance:
            if vol_ratio < vol_ratio_min:
                return None, "breakout_vol_low"
            if rsi >= 75:
                return None, "breakout_rsi_hi"
            # Setup 1 matched
            _rr = RR_STRONG_BREAKOUT if vol_ratio >= 3.0 else RR_NORMAL_BREAKOUT
            sig = TradeSignal(
                symbol          = stock["symbol"],
                direction       = SignalDirection.BUY,
                signal_type     = SignalType.EQUITY,
                strength        = SignalStrength.STRONG if vol_ratio >= 3.0 else SignalStrength.MODERATE,
                entry_price     = ltp,
                stop_loss       = round(ltp - stop_dist, 2),
                target_price    = round(ltp + _rr * stop_dist, 2),
                quantity        = 1,   # placeholder — Risk Engine will overwrite
                strategy_name   = "breakout",
                confidence      = min(6.0 + vol_ratio, 9.5),
                source_agent    = "EquityScannerAI",
                atr             = atr,
                adv_crore       = adv_crore,
                entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                entry_zone_high = round(ltp + atr * 0.10, 2),
            )
            return sig, "signal_found"

        # ── Setup 2: Momentum retest ───────────────────────────────────
        # Active in all non-bear regimes including BULL_TREND.
        if resistance * 0.995 <= ltp <= resistance * 1.01:
            if not (50 <= rsi <= 65):
                return None, "retest_rsi_oob"
            sig = TradeSignal(
                symbol          = stock["symbol"],
                direction       = SignalDirection.BUY,
                signal_type     = SignalType.EQUITY,
                strength        = SignalStrength.MODERATE,
                entry_price     = ltp,
                stop_loss       = round(ltp - stop_dist, 2),
                target_price    = round(ltp + RR_DEFAULT * stop_dist, 2),
                quantity        = 1,   # placeholder — Risk Engine will overwrite
                strategy_name   = "momentum_retest",
                confidence      = round(min(5.5 + vol_ratio * 0.4 + (rsi - 50) / 25.0, 9.0), 2),
                source_agent    = "EquityScannerAI",
                atr             = atr,
                adv_crore       = adv_crore,
                entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                entry_zone_high = round(ltp + atr * 0.10, 2),
            )
            return sig, "signal_found"

        # ── Setup 3: Trend Pullback (BULL_TREND only) ─────────────────────────
        # Professional systematic entry: buy the dip inside an uptrend.
        # NSE large/mid-cap stocks in BULL_TREND hold the 50-EMA zone (proxied
        # by the static `support` level).  After a momentum reset (RSI 38–56)
        # price tends to resume the prior trend.
        #
        # vol_ratio >= 1.2 : normal/slight-above-average volume — buyers
        #   returning to the pullback.  No spike needed (unlike breakout).
        # target = 2.5× stop : trends typically run further than range trades.
        #
        # This closes the Trend Participation Gap: the system was previously
        # inactive in BULL_TREND because the only active setups (Breakout,
        # Momentum_Retest) require price near/above resistance, which is rare
        # in low-VIX smooth-uptrend environments.
        if in_bull_trend:
            if (support * 0.97 <= ltp <= support * 1.04
                    and 38 <= rsi <= 56
                    and vol_ratio >= 1.2):
                # Setup 3 matched
                sig = TradeSignal(
                    symbol          = stock["symbol"],
                    direction       = SignalDirection.BUY,
                    signal_type     = SignalType.EQUITY,
                    strength        = SignalStrength.STRONG,
                    entry_price     = ltp,
                    stop_loss       = round(ltp - stop_dist, 2),
                    target_price    = round(ltp + RR_TREND_PULLBACK * stop_dist, 2),
                    quantity        = 1,   # placeholder — Risk Engine will overwrite
                    strategy_name   = "trend_pullback",
                    confidence      = round(min(5.8 + vol_ratio * 0.3 + (56 - rsi) / 20.0, 9.0), 2),
                    source_agent    = "EquityScannerAI",
                    atr             = atr,
                    adv_crore       = adv_crore,
                    entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                    entry_zone_high = round(ltp + atr * 0.10, 2),
                )
                return sig, "signal_found"
            # Setup 3 failed — in bull trend setups 4+5 (mean-reversion) are blocked
            return None, "bull_gate"

        # ── Range / Volatile regimes only past this point ─────────────
        # Setup 4: High RSI Short
        if rsi >= 67 and ltp >= resistance * 0.99:
            target = ltp - 2.5 * stop_dist
            if target > 0:
                sig = TradeSignal(
                    symbol          = stock["symbol"],
                    direction       = SignalDirection.SHORT,
                    signal_type     = SignalType.EQUITY,
                    strength        = SignalStrength.MODERATE,
                    entry_price     = ltp,
                    stop_loss       = round(ltp + stop_dist, 2),
                    target_price    = round(target, 2),
                    quantity        = 1,   # placeholder — Risk Engine will overwrite
                    strategy_name   = "high_rsi_short",
                    confidence      = min(5.5 + rsi / 20, 8.5),
                    source_agent    = "EquityScannerAI",
                    atr             = atr,
                    adv_crore       = adv_crore,
                    entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                    entry_zone_high = round(ltp + atr * 0.10, 2),
                )
                return sig, "signal_found"

        # Setup 5: Mean Reversion — oversold bounce
        # RSI threshold widened from 38→45 to capture stocks pulling back
        # to support within the normal distribution (fix for backlog #10).
        if rsi <= 45:
            if ltp > support * 1.02:
                return None, "bounce_price_hi"
            sig = TradeSignal(
                symbol          = stock["symbol"],
                direction       = SignalDirection.BUY,
                signal_type     = SignalType.EQUITY,
                strength        = SignalStrength.MODERATE,
                entry_price     = ltp,
                stop_loss       = round(ltp - stop_dist, 2),
                target_price    = round(ltp + 2.5 * stop_dist, 2),
                quantity        = 1,   # placeholder — Risk Engine will overwrite
                strategy_name   = "mean_reversion_bounce",
                confidence      = min(5.5 + (40 - rsi) / 10, 8.5),
                source_agent    = "EquityScannerAI",
                atr             = atr,
                adv_crore       = adv_crore,
                entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                entry_zone_high = round(ltp + atr * 0.10, 2),
            )
            return sig, "signal_found"

        # RSI 46-66, price in middle of range — no extreme setup matches
        return None, "rsi_neutral"


# ── Fix 2: Pre-market S/R Level Validator ──────────────────────────────────
def validate_and_refresh_sr_levels() -> dict:
    """
    Validate all watchlist S/R levels against current LTPs and auto-repair
    any broken entries (resistance < LTP or support > LTP).

    Returns dict: {repaired: int, total: int, broken_symbols: list, error: str|None}
    Called by orchestrator._premarket_init() at 08:00 and at the start of each
    run_full_cycle() — the same-day guard (_sr_last_refresh_date) makes it a
    no-op after the first successful run each calendar day.
    """
    global _sr_last_refresh_date
    import yfinance as _yf
    import re as _re
    from datetime import date as _date, datetime as _datetime
    from pathlib import Path as _Path

    _today_str = _date.today().isoformat()
    if _sr_last_refresh_date == _today_str:
        log.debug("[SR_Validator] Already refreshed today (%s) — skipped.", _today_str)
        return {"repaired": 0, "total": len(_BASE_WATCHLIST + _EXTENDED_WATCHLIST),
                "broken_symbols": [], "error": None, "skipped": True}

    _scanner_path = _Path(__file__)
    _log_prefix   = "[SR_Validator]"

    try:
        all_entries = _BASE_WATCHLIST + _EXTENDED_WATCHLIST
        symbols_ns  = [e["symbol"].strip() + ".NS" for e in all_entries]

        # Batch LTP fetch (single yfinance call)
        log.info("%s Fetching LTPs for %d watchlist symbols…", _log_prefix, len(all_entries))
        _data = _yf.download(
            " ".join(symbols_ns),
            period="2d", interval="1d",
            auto_adjust=True, progress=False, timeout=15,
        )
        if _data.empty:
            return {"repaired": 0, "total": len(all_entries), "broken_symbols": [], "error": "yfinance returned empty"}

        # Extract last close per symbol
        _ltps: dict = {}
        if isinstance(_data.columns, _pd_MultiIndex if hasattr(_data.columns, "levels") else type(None)):
            pass  # handled below

        try:
            import pandas as _pd
            if isinstance(_data.columns, _pd.MultiIndex):
                _close = _data["Close"]
                for ns_sym in symbols_ns:
                    if ns_sym in _close.columns:
                        _v = _close[ns_sym].dropna()
                        if not _v.empty:
                            _ltps[ns_sym.replace(".NS", "")] = float(_v.iloc[-1])
            else:
                _close = _data["Close"]
                _v = _close.dropna()
                if not _v.empty:
                    sym = symbols_ns[0].replace(".NS", "")
                    _ltps[sym] = float(_v.iloc[-1])
        except Exception as _pe:
            log.warning("%s LTP parse error: %s", _log_prefix, _pe)

        if not _ltps:
            return {"repaired": 0, "total": len(all_entries), "broken_symbols": [], "error": "no LTPs parsed"}

        # Detect broken entries
        _broken: list = []
        for entry in all_entries:
            sym   = entry["symbol"].strip()
            ltp   = _ltps.get(sym)
            if ltp is None:
                continue
            res = entry["resistance"]
            sup = entry["support"]
            if res <= ltp or sup >= ltp:
                _broken.append((sym, ltp, res, sup))

        if not _broken:
            log.info("%s All %d S/R levels valid — no repair needed.", _log_prefix, len(all_entries))
            _sr_last_refresh_date = _today_str  # mark as done even when no repair needed
            return {"repaired": 0, "total": len(all_entries), "broken_symbols": [], "error": None}

        log.warning(
            "%s Found %d broken S/R entries: %s — rebuilding with ATR(14)…",
            _log_prefix, len(_broken), [b[0] for b in _broken],
        )

        # Rebuild ATR-anchored levels for broken symbols
        _new_levels: dict = {}  # symbol -> (resistance, support)
        for sym, ltp, _old_res, _old_sup in _broken:
            try:
                _hist = _yf.download(
                    sym + ".NS", period="30d", interval="1d",
                    auto_adjust=True, progress=False, timeout=12,
                )
                if _hist.empty or len(_hist) < 10:
                    log.warning("%s %s: insufficient history — skipping", _log_prefix, sym)
                    continue
                _hi  = _hist["High"].values
                _lo  = _hist["Low"].values
                _cl  = _hist["Close"].values
                _tr  = [max(_hi[i] - _lo[i],
                            abs(_hi[i] - _cl[i-1]),
                            abs(_lo[i] - _cl[i-1]))
                        for i in range(1, len(_cl))]
                _atr = sum(_tr[-14:]) / min(14, len(_tr))
                _new_res = round(ltp + 2.0 * _atr, 2)
                _new_sup = round(ltp - 2.0 * _atr, 2)
                _new_levels[sym] = (_new_res, _new_sup, round(ltp, 2))
                log.info(
                    "%s %s: LTP=%.2f ATR=%.2f → res=%.2f sup=%.2f",
                    _log_prefix, sym, ltp, _atr, _new_res, _new_sup,
                )
            except Exception as _exc:
                log.warning("%s %s rebuild failed: %s", _log_prefix, sym, _exc)

        if not _new_levels:
            return {
                "repaired": 0, "total": len(all_entries),
                "broken_symbols": [b[0] for b in _broken],
                "error": "all rebuilds failed",
            }

        # Patch the source file — replace individual lines matching each symbol
        _src = _scanner_path.read_text(encoding="utf-8")
        _repaired = 0
        for sym, (new_res, new_sup, new_ltp) in _new_levels.items():
            # Match lines like:  {"symbol": "RELIANCE    ", "base_ltp":..., "resistance":..., "support":...,...}
            _pattern = (
                r'(\{"symbol":\s*"' + _re.escape(sym) + r'\s*"'
                r',\s*"base_ltp":\s*)[\d.]+(\s*,\s*"resistance":\s*)[\d.]+'
                r'(\s*,\s*"support":\s*)[\d.]+'
            )
            _repl = (
                r'\g<1>' + f'{new_ltp:.2f}' +
                r'\g<2>' + f'{new_res:.2f}' +
                r'\g<3>' + f'{new_sup:.2f}'
            )
            _new_src, _count = _re.subn(_pattern, _repl, _src)
            if _count:
                _src  = _new_src
                _repaired += 1
            else:
                log.warning("%s Could not patch %s in source — regex miss", _log_prefix, sym)

        # Update last_level_update date
        _today = _date.today().isoformat()
        _src = _re.sub(
            r'last_level_update=\d{4}-\d{2}-\d{2}',
            f'last_level_update={_today}',
            _src,
        )

        _scanner_path.write_text(_src, encoding="utf-8")
        _sr_last_refresh_date = _today_str  # mark as done for today
        log.info(
            "%s Repair complete: %d/%d symbols patched. last_level_update=%s",
            _log_prefix, _repaired, len(_broken), _today,
        )
        return {
            "repaired": _repaired,
            "total": len(all_entries),
            "broken_symbols": [b[0] for b in _broken],
            "error": None,
        }

    except Exception as _exc:
        log.exception("%s Unexpected error: %s", _log_prefix, _exc)
        return {"repaired": 0, "total": 0, "broken_symbols": [], "error": str(_exc)}

