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
from datetime import datetime
from typing import Any, Dict, List

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
# Replace the entire block with real broker API calls (KiteConnect, etc.)
_BASE_WATCHLIST: List[Dict[str, Any]] = [
    # ── Breakout / momentum candidates (LTP above resistance) ──────────────
    {"symbol": "RELIANCE",   "base_ltp": 2850, "resistance": 2800, "support": 2700, "volume_ratio": 2.3, "rsi": 62, "adv_crore": 1800},
    {"symbol": "HDFCBANK",   "base_ltp": 1680, "resistance": 1650, "support": 1600, "volume_ratio": 1.8, "rsi": 58, "adv_crore":  850},
    {"symbol": "ICICIBANK",  "base_ltp":  920, "resistance":  910, "support":  870, "volume_ratio": 2.7, "rsi": 65, "adv_crore":  700},
    {"symbol": "TATASTEEL",  "base_ltp":  165, "resistance":  160, "support":  150, "volume_ratio": 3.1, "rsi": 70, "adv_crore":  350},
    {"symbol": "INFY",       "base_ltp": 1720, "resistance": 1700, "support": 1640, "volume_ratio": 1.5, "rsi": 54, "adv_crore":  480},
    {"symbol": "BANKBARODA", "base_ltp":  260, "resistance":  252, "support":  238, "volume_ratio": 4.2, "rsi": 68, "adv_crore":  220},
    {"symbol": "LT",         "base_ltp": 3650, "resistance": 3600, "support": 3450, "volume_ratio": 2.0, "rsi": 61, "adv_crore":  320},
    {"symbol": "COALINDIA",  "base_ltp":  490, "resistance":  480, "support":  460, "volume_ratio": 1.9, "rsi": 57, "adv_crore":  190},
    # ── Trend-pullback candidates (LTP between support and resistance) ──────
    # These represent large-caps in an uptrend that have temporarily pulled
    # back to the 50-EMA zone — the primary Trend_Pullback entry condition.
    {"symbol": "HCLTECH",    "base_ltp": 1495, "resistance": 1550, "support": 1470, "volume_ratio": 1.5, "rsi": 47, "adv_crore":  280},
    {"symbol": "SBIN",       "base_ltp":  798, "resistance":  830, "support":  780, "volume_ratio": 1.6, "rsi": 44, "adv_crore":  420},
    {"symbol": "AXISBANK",   "base_ltp": 1090, "resistance": 1130, "support": 1070, "volume_ratio": 1.4, "rsi": 50, "adv_crore":  380},
    {"symbol": "ONGC",       "base_ltp":  278, "resistance":  292, "support":  272, "volume_ratio": 1.7, "rsi": 45, "adv_crore":  310},
]

# ── Extended watchlist (activated by ODM when density is low) ─────────────
# Represents a wider NIFTY200/500 universe.  Swap with real broker data.
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
]


def _live_watchlist(extended: bool = False) -> List[Dict[str, Any]]:
    """
    Simulate a live price fetch seeded per-minute so that each cycle
    shows a fresh LTP.  Swap this with real broker quote calls.
    When ``extended=True`` the wider NIFTY200/500 universe is also included
    (activated by ODM when opportunity density drops below threshold).
    """
    source = _BASE_WATCHLIST + (_EXTENDED_WATCHLIST if extended else [])
    rng = random.Random(int(datetime.now().timestamp()) // 60)
    rows = []
    for s in source:
        # ±0.8 % intra-minute price noise around base LTP
        noise = rng.uniform(-0.008, 0.008)
        live_ltp = round(s["base_ltp"] * (1 + noise), 2)
        # Volume and RSI get a small tick-level jitter too
        vol_jitter = round(s["volume_ratio"] + rng.uniform(-0.2, 0.2), 2)
        rsi_jitter = round(s["rsi"] + rng.uniform(-2, 2), 1)
        rows.append({
            "symbol":       s["symbol"],
            "ltp":          live_ltp,           # ← LIVE price fetched this cycle
            "resistance":   s["resistance"],
            "support":      s["support"],
            "volume_ratio": max(0.1, vol_jitter),
            "rsi":          max(0, min(100, rsi_jitter)),
            "adv_crore":    s.get("adv_crore", 0.0),   # ← pass-through for LiquidityGuard
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
            sig = TradeSignal(
                symbol          = stock["symbol"],
                direction       = SignalDirection.BUY,
                signal_type     = SignalType.EQUITY,
                strength        = SignalStrength.STRONG if vol_ratio >= 3.0 else SignalStrength.MODERATE,
                entry_price     = ltp,
                stop_loss       = round(ltp - stop_dist, 2),
                target_price    = round(ltp + 2.5 * stop_dist, 2),
                quantity        = 1,   # placeholder — Risk Engine will overwrite
                strategy_name   = "Breakout_Volume",
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
                target_price    = round(ltp + 2.5 * stop_dist, 2),
                quantity        = 1,   # placeholder — Risk Engine will overwrite
                strategy_name   = "Momentum_Retest",
                confidence      = 6.5,
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
            sig = TradeSignal(
                symbol          = stock["symbol"],
                direction       = SignalDirection.BUY,
                signal_type     = SignalType.EQUITY,
                strength        = SignalStrength.STRONG,
                entry_price     = ltp,
                stop_loss       = round(ltp - stop_dist, 2),
                target_price    = round(ltp + 2.5 * stop_dist, 2),  # trend runs further
                quantity        = 1,   # placeholder — Risk Engine will overwrite
                strategy_name   = "Trend_Pullback",
                confidence      = 6.8,
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
                    strategy_name   = "Mean_Reversion",
                    confidence      = min(5.5 + rsi / 20, 8.5),
                    source_agent    = "EquityScannerAI",
                    atr             = atr,
                    adv_crore       = adv_crore,
                    entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                    entry_zone_high = round(ltp + atr * 0.10, 2),
                )
                return sig

        # ── Setup 5: Mean Reversion — oversold bounce ─────────────────
        if rsi <= 38 and ltp <= support * 1.02:
            sig = TradeSignal(
                symbol          = stock["symbol"],
                direction       = SignalDirection.BUY,
                signal_type     = SignalType.EQUITY,
                strength        = SignalStrength.MODERATE,
                entry_price     = ltp,
                stop_loss       = round(ltp - stop_dist, 2),
                target_price    = round(ltp + 2.5 * stop_dist, 2),
                quantity        = 1,   # placeholder — Risk Engine will overwrite
                strategy_name   = "Mean_Reversion",
                confidence      = min(5.5 + (40 - rsi) / 10, 8.5),
                source_agent    = "EquityScannerAI",
                atr             = atr,
                adv_crore       = adv_crore,
                entry_zone_low  = round(max(0.0, ltp - atr * 0.10), 2),
                entry_zone_high = round(ltp + atr * 0.10, 2),
            )
            return sig

        return None
