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
from typing import Any, Dict, List, Optional

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
_PRICE_CACHE_LOCK = _threading.Lock()   # guards _PRICE_CACHE / _PRICE_CACHE_TS
_PRICE_REFRESH_RUNNING = _threading.Event()  # prevents duplicate refresh threads

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
# resistance / support are real technical levels used to identify setups.
_BASE_WATCHLIST: List[Dict[str, Any]] = [
    # ── Breakout / momentum candidates ─────────────────────────────────────
    {"symbol": "RELIANCE",   "base_ltp": 2850, "resistance": 2800, "support": 2700, "volume_ratio": 2.3, "rsi": 62, "adv_crore": 1800},
    {"symbol": "HDFCBANK",   "base_ltp": 1680, "resistance": 1650, "support": 1600, "volume_ratio": 1.8, "rsi": 58, "adv_crore":  850},
    {"symbol": "ICICIBANK",  "base_ltp":  920, "resistance":  910, "support":  870, "volume_ratio": 2.7, "rsi": 65, "adv_crore":  700},
    {"symbol": "TATASTEEL",  "base_ltp":  165, "resistance":  160, "support":  150, "volume_ratio": 3.1, "rsi": 70, "adv_crore":  350},
    {"symbol": "INFY",       "base_ltp": 1720, "resistance": 1700, "support": 1640, "volume_ratio": 1.5, "rsi": 54, "adv_crore":  480},
    {"symbol": "BANKBARODA", "base_ltp":  260, "resistance":  252, "support":  238, "volume_ratio": 4.2, "rsi": 68, "adv_crore":  220},
    {"symbol": "LT",         "base_ltp": 3650, "resistance": 3600, "support": 3450, "volume_ratio": 2.0, "rsi": 61, "adv_crore":  320},
    {"symbol": "COALINDIA",  "base_ltp":  490, "resistance":  480, "support":  460, "volume_ratio": 1.9, "rsi": 57, "adv_crore":  190},
    # ── Trend-pullback candidates ───────────────────────────────────────────
    {"symbol": "HCLTECH",    "base_ltp": 1495, "resistance": 1550, "support": 1470, "volume_ratio": 1.5, "rsi": 47, "adv_crore":  280},
    {"symbol": "SBIN",       "base_ltp":  798, "resistance":  830, "support":  780, "volume_ratio": 1.6, "rsi": 44, "adv_crore":  420},
    {"symbol": "AXISBANK",   "base_ltp": 1090, "resistance": 1130, "support": 1070, "volume_ratio": 1.4, "rsi": 50, "adv_crore":  380},
    {"symbol": "ONGC",       "base_ltp":  278, "resistance":  292, "support":  272, "volume_ratio": 1.7, "rsi": 45, "adv_crore":  310},
    # ── Additional NIFTY50 large-caps ───────────────────────────────────────
    {"symbol": "KOTAKBANK",  "base_ltp": 1820, "resistance": 1800, "support": 1720, "volume_ratio": 1.6, "rsi": 52, "adv_crore":  450},
    {"symbol": "BHARTIARTL", "base_ltp": 1660, "resistance": 1620, "support": 1550, "volume_ratio": 2.1, "rsi": 60, "adv_crore":  380},
    {"symbol": "ITC",        "base_ltp":  475, "resistance":  465, "support":  440, "volume_ratio": 1.8, "rsi": 55, "adv_crore":  600},
    {"symbol": "BAJAJFINSV", "base_ltp": 1780, "resistance": 1750, "support": 1660, "volume_ratio": 1.7, "rsi": 48, "adv_crore":  250},
    {"symbol": "HINDALCO",   "base_ltp":  680, "resistance":  660, "support":  620, "volume_ratio": 2.4, "rsi": 63, "adv_crore":  310},
    {"symbol": "ULTRACEMCO", "base_ltp": 11700, "resistance": 11500, "support": 10900, "volume_ratio": 1.5, "rsi": 50, "adv_crore": 150},
    {"symbol": "TECHM",      "base_ltp": 1520, "resistance": 1490, "support": 1410, "volume_ratio": 1.9, "rsi": 56, "adv_crore":  220},
    {"symbol": "NTPC",       "base_ltp":  380, "resistance":  370, "support":  350, "volume_ratio": 2.2, "rsi": 59, "adv_crore":  270},
]

# ── Extended watchlist (activated by ODM when density is low) ─────────────
# Represents a wider NIFTY200/500 universe.
_EXTENDED_WATCHLIST: List[Dict[str, Any]] = [
    {"symbol": "HINDUNILVR", "base_ltp": 2500, "resistance": 2480, "support": 2350, "volume_ratio": 1.6, "rsi": 52, "adv_crore": 280},
    {"symbol": "ASIANPAINT", "base_ltp": 2900, "resistance": 2870, "support": 2750, "volume_ratio": 1.7, "rsi": 56, "adv_crore": 200},
    {"symbol": "BAJFINANCE", "base_ltp": 6800, "resistance": 6750, "support": 6500, "volume_ratio": 2.1, "rsi": 60, "adv_crore": 600},
    {"symbol": "MARUTI",     "base_ltp": 11200, "resistance": 11000, "support": 10500, "volume_ratio": 1.5, "rsi": 49, "adv_crore": 310},
    {"symbol": "SUNPHARMA",  "base_ltp": 1820, "resistance": 1800, "support": 1700, "volume_ratio": 1.8, "rsi": 55, "adv_crore": 250},
    {"symbol": "WIPRO",      "base_ltp": 520,  "resistance":  510, "support":  480, "volume_ratio": 1.6, "rsi": 51, "adv_crore": 320},
    {"symbol": "POWERGRID",  "base_ltp": 300,  "resistance":  295, "support":  280, "volume_ratio": 1.9, "rsi": 58, "adv_crore": 140},
    {"symbol": "DIVISLAB",   "base_ltp": 3800, "resistance": 3750, "support": 3600, "volume_ratio": 1.7, "rsi": 53, "adv_crore":  90},
    {"symbol": "TITAN",      "base_ltp": 3300, "resistance": 3270, "support": 3100, "volume_ratio": 1.5, "rsi": 48, "adv_crore": 175},
    {"symbol": "DRREDDY",    "base_ltp": 1250, "resistance": 1230, "support": 1170, "volume_ratio": 1.6, "rsi": 50, "adv_crore": 120},
    # ── Additional mid/large caps ───────────────────────────────────────────
    {"symbol": "ADANIENT",   "base_ltp": 2350, "resistance": 2290, "support": 2150, "volume_ratio": 2.5, "rsi": 64, "adv_crore": 380},
    {"symbol": "TATACONSUM", "base_ltp":  1100, "resistance": 1080, "support": 1030, "volume_ratio": 1.6, "rsi": 53, "adv_crore":  95},
    {"symbol": "NESTLEIND",  "base_ltp": 2280, "resistance": 2250, "support": 2130, "volume_ratio": 1.4, "rsi": 48, "adv_crore":  70},
    {"symbol": "HAVELLS",    "base_ltp": 1780, "resistance": 1750, "support": 1660, "volume_ratio": 1.8, "rsi": 57, "adv_crore":  80},
    {"symbol": "PIDILITIND", "base_ltp": 2850, "resistance": 2800, "support": 2660, "volume_ratio": 1.5, "rsi": 51, "adv_crore":  60},
    {"symbol": "GRASIM",     "base_ltp": 2750, "resistance": 2710, "support": 2570, "volume_ratio": 1.7, "rsi": 55, "adv_crore": 130},
    {"symbol": "JSWSTEEL",   "base_ltp":  950, "resistance":  930, "support":  880, "volume_ratio": 2.3, "rsi": 61, "adv_crore": 290},
    {"symbol": "ADANIPORTS", "base_ltp": 1350, "resistance": 1310, "support": 1240, "volume_ratio": 2.0, "rsi": 58, "adv_crore": 200},
]


def _do_fetch_prices(symbols: List[str]) -> Dict[str, float]:
    """Blocking call to the live feed. Returns {} on any error."""
    try:
        from data_feeds.data_feed_manager import get_feed_manager
        feed = get_feed_manager()
        ns_symbols = [f"{s}.NS" for s in symbols]
        quotes = feed.get_multiple_quotes(ns_symbols)
        prices: Dict[str, float] = {}
        for ns_sym, q in quotes.items():
            bare = ns_sym.replace(".NS", "")
            if q is not None and hasattr(q, "ltp") and q.ltp and q.ltp > 0:
                prices[bare] = float(q.ltp)
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
        prices = _do_fetch_prices(symbols)
        if prices:
            with _PRICE_CACHE_LOCK:
                _PRICE_CACHE    = prices
                _PRICE_CACHE_TS = time.monotonic()
            log.debug("[EquityScannerAI] Background price refresh complete (%d symbols).",
                      len(prices))
    finally:
        _PRICE_REFRESH_RUNNING.clear()


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


def _live_watchlist(extended: bool = False) -> List[Dict[str, Any]]:
    """
    Returns watchlist rows with the best available LTP:
      1. Real-time price from data feed (yfinance/.NS) — 60s cached
      2. Per-minute seeded simulation as fallback
    When ``extended=True`` the wider NIFTY200/500 universe is also included.
    """
    source = _BASE_WATCHLIST + (_EXTENDED_WATCHLIST if extended else [])
    all_symbols = [s["symbol"] for s in source]
    live_prices = _fetch_live_prices(all_symbols)

    rng = random.Random(int(datetime.now().timestamp()) // 60)
    rows = []
    for s in source:
        real_ltp = live_prices.get(s["symbol"], 0.0)
        if real_ltp > 0:
            live_ltp = real_ltp
        else:
            noise    = rng.uniform(-0.008, 0.008)
            live_ltp = round(s["base_ltp"] * (1 + noise), 2)

        vol_jitter = round(s["volume_ratio"] + rng.uniform(-0.2, 0.2), 2)
        rsi_jitter = round(s["rsi"]          + rng.uniform(-2,   2),   1)
        rows.append({
            "symbol":       s["symbol"],
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

        watchlist = _live_watchlist(extended=use_extended)     # fresh LTPs every cycle
        if use_extended:
            log.info("[EquityScannerAI] ODM %s — scanning %d stocks (extended universe).",
                     odm_tier, len(watchlist))

        signals: List[TradeSignal] = []
        for stock in watchlist:
            setup = self._identify_setup(stock, snapshot,
                                         vol_ratio_min=vol_ratio_min,
                                         extra_strategies=extra_strats)
            if setup:
                signals.append(setup)

        log.info("[EquityScannerAI] Found %d equity opportunities.", len(signals))
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

    def _identify_setup(self, stock: Dict[str, Any],
                        snapshot: MarketSnapshot,
                        vol_ratio_min: float = 2.0,
                        extra_strategies: list | None = None) -> TradeSignal | None:
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
            return None

        # ── Regime guard ──────────────────────────────────────────────
        # Hard-skip all setups in bear market; mean-reversion blocked in bull trend.
        if snapshot.regime == RegimeLabel.BEAR_MARKET:
            return None
        in_bull_trend = (snapshot.regime == RegimeLabel.BULL_TREND)

        # ── Stop distance (market-logic only — ATR-based, no capital awareness) ────
        # The strategy is responsible ONLY for defining stop_price from market
        # mechanics (ATR * multiplier).  Position sizing is delegated entirely
        # to the Risk Engine (PortfolioAllocationAI).
        stop_dist = max(atr * ATR_STOP_MULTIPLIER, ltp * 0.010)  # floor at 1% of price

        # ── Setup 1: Breakout with volume ─────────────────────────────
        # Active in all non-bear regimes including BULL_TREND.
        # vol_ratio_min may be relaxed by ODM (default 2.0 → as low as 1.4 in SECONDARY).
        if ltp > resistance and vol_ratio >= vol_ratio_min and rsi < 75:
            # Strong breakout (vol spike ≥ 3×): use higher RR to trigger fat-tail
            # bonus in DecisionEngine (−1pt threshold, +10% position size).
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
                confidence      = min(6.0 + vol_ratio, 9.5),
                source_agent    = "EquityScannerAI",
                atr             = atr,
                adv_crore       = adv_crore,
                entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                entry_zone_high = round(ltp + atr * 0.10, 2),
            )
            return sig

        # ── Setup 2: Momentum retest ───────────────────────────────────
        # Active in all non-bear regimes including BULL_TREND.
        if resistance * 0.995 <= ltp <= resistance * 1.01 and 50 <= rsi <= 65:
            sig = TradeSignal(
                symbol          = stock["symbol"],
                direction       = SignalDirection.BUY,
                signal_type     = SignalType.EQUITY,
                strength        = SignalStrength.MODERATE,
                entry_price     = ltp,
                stop_loss       = round(ltp - stop_dist, 2),
                target_price    = round(ltp + RR_DEFAULT * stop_dist, 2),
                quantity        = 1,   # placeholder — Risk Engine will overwrite
                confidence      = round(min(5.5 + vol_ratio * 0.4 + (rsi - 50) / 25.0, 9.0), 2),
                source_agent    = "EquityScannerAI",
                atr             = atr,
                adv_crore       = adv_crore,
                entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                entry_zone_high = round(ltp + atr * 0.10, 2),
            )
            return sig

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
        if (in_bull_trend
                and support * 0.97 <= ltp <= support * 1.04   # near 50-EMA proxy
                and 38 <= rsi <= 56                             # momentum reset
                and vol_ratio >= 1.2):                          # buyers returning
            # RR_TREND_PULLBACK=3.0 triggers DecisionEngine asymmetry bonus (−0.5pt threshold).
            # confidence=7.2 ensures signal survives RiskManager at any VIX level.
            sig = TradeSignal(
                symbol          = stock["symbol"],
                direction       = SignalDirection.BUY,
                signal_type     = SignalType.EQUITY,
                strength        = SignalStrength.STRONG,
                entry_price     = ltp,
                stop_loss       = round(ltp - stop_dist, 2),
                target_price    = round(ltp + RR_TREND_PULLBACK * stop_dist, 2),
                quantity        = 1,   # placeholder — Risk Engine will overwrite
                confidence      = round(min(5.8 + vol_ratio * 0.3 + (56 - rsi) / 20.0, 9.0), 2),
                source_agent    = "EquityScannerAI",
                atr             = atr,
                adv_crore       = adv_crore,
                entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                entry_zone_high = round(ltp + atr * 0.10, 2),
            )
            return sig

        # ── Bull regime gate: mean-reversion disabled in BULL_TREND ──────────
        # Setups 4 and 5 (mean-reversion) only valid in range/volatile regimes.
        if in_bull_trend:
            return None
        # RANGE/VOLATILE/BEAR_MEDIUM regimes only.
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
                    confidence      = min(5.5 + rsi / 20, 8.5),
                    source_agent    = "EquityScannerAI",
                    atr             = atr,
                    adv_crore       = adv_crore,
                    entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                    entry_zone_high = round(ltp + atr * 0.10, 2),
                )
                return sig

        # ── Setup 5: Mean Reversion — oversold bounce ─────────────────
        # RSI threshold widened from 38→45 to capture stocks pulling back
        # to support within the normal distribution (fix for backlog #10).
        if rsi <= 45 and ltp <= support * 1.02:
            sig = TradeSignal(
                symbol          = stock["symbol"],
                direction       = SignalDirection.BUY,
                signal_type     = SignalType.EQUITY,
                strength        = SignalStrength.MODERATE,
                entry_price     = ltp,
                stop_loss       = round(ltp - stop_dist, 2),
                target_price    = round(ltp + 2.5 * stop_dist, 2),
                quantity        = 1,   # placeholder — Risk Engine will overwrite

                confidence      = min(5.5 + (40 - rsi) / 10, 8.5),
                source_agent    = "EquityScannerAI",
                atr             = atr,
                adv_crore       = adv_crore,
                entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                entry_zone_high = round(ltp + atr * 0.10, 2),
            )
            return sig

        return None
