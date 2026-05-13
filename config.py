"""
Global Configuration — AI Trading Brain
All system-wide settings, constants, and environment variable bindings.
"""

import os
import datetime as _dt
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# BROKER CREDENTIALS
# ─────────────────────────────────────────────
ZERODHA_API_KEY       = os.getenv("ZERODHA_API_KEY", "")
ZERODHA_API_SECRET    = os.getenv("ZERODHA_API_SECRET", "")
ZERODHA_ACCESS_TOKEN  = os.getenv("ZERODHA_ACCESS_TOKEN", "")

DHAN_CLIENT_ID        = os.getenv("DHAN_CLIENT_ID", "")
DHAN_ACCESS_TOKEN     = os.getenv("DHAN_ACCESS_TOKEN", "")

ANGELONE_API_KEY      = os.getenv("ANGELONE_API_KEY", "")
ANGELONE_CLIENT_ID    = os.getenv("ANGELONE_CLIENT_ID", "")
ANGELONE_PASSWORD     = os.getenv("ANGELONE_PASSWORD", "")
ANGELONE_TOTP_SECRET  = os.getenv("ANGELONE_TOTP_SECRET", "")

# ─────────────────────────────────────────────
# ACTIVE BROKER
# ─────────────────────────────────────────────
ACTIVE_BROKER = os.getenv("ACTIVE_BROKER", "zerodha")   # zerodha | dhan | angelone

# ─────────────────────────────────────────────
# RISK PARAMETERS
# ─────────────────────────────────────────────
TOTAL_CAPITAL            = float(os.getenv("TOTAL_CAPITAL", 10_000_000))  # INR — ₹1Cr paper trading (increased from ₹10L for strategy validation coverage)
MAX_RISK_PER_TRADE_PCT   = 0.01      # 1% of capital per trade
MAX_PORTFOLIO_RISK_PCT   = 0.08      # 8% total portfolio risk (INCREASED 5→8 to unlock execution)
MAX_DRAWDOWN_PCT         = 0.10      # 10% drawdown → halt trading
MIN_CONFIDENCE_SCORE     = 6.8       # Minimum Decision AI score to execute (INCREASED 6.2→6.8 to filter weak trades)

# ─────────────────────────────────────────────
# ATR-BASED EXECUTION  (replaces all hardcoded % stops)
# ─────────────────────────────────────────────
ATR_STOP_MULTIPLIER      = 1.5       # stop_distance  = ATR(14) × multiplier  (raised 1.2→1.5 for FRAG robustness)
ATR_ZONE_MULTIPLIER      = 0.10      # entry_zone = entry ± ATR(14) × 0.10  (fallback when zone bounds not pre-computed)
VOLATILITY_GUARD_ATR_PCT = 4.0       # skip signal if ATR% of price exceeds this (normal NSE large-cap ~1.5-3%)

# ─────────────────────────────────────────────
# CAPITAL PROTECTION GOVERNOR
# ─────────────────────────────────────────────
DD_REDUCE_PCT            = 2.0       # daily loss %  → scale position to DD_REDUCE_FACTOR
DD_PAUSE_PCT             = 4.0       # daily loss %  → pause trading entirely
DD_REDUCE_FACTOR         = 0.5       # position size multiplier in reduce tier

# ─────────────────────────────────────────────
# LIQUIDITY CAPACITY GUARD
# ─────────────────────────────────────────────
# Prevents market impact / slippage as capital scales.
# Rule: position value ≤ ADV × MAX_ADV_PCT
# Stocks with ADV below MIN_ADV_CRORE are filtered out entirely.
MIN_ADV_CRORE            = 50.0      # minimum average daily volume (₹ crore) to trade
MAX_ADV_PCT              = 0.02      # max position value as fraction of daily ADV (2%)

# ─────────────────────────────────────────────
# CAPITAL ALLOCATION
# ─────────────────────────────────────────────
ALLOCATION = {
    "large_cap":     0.40,
    "mid_cap":       0.30,
    "small_cap":     0.15,
    "options_hedge": 0.15,
}

# ─────────────────────────────────────────────
# MARKET UNIVERSE
# ─────────────────────────────────────────────
INDICES = ["NIFTY 50", "NIFTY BANK", "NIFTY 500", "NIFTY MIDCAP 150",
           "NIFTY SMALLCAP 250", "NIFTY IT", "NIFTY PSU BANK",
           "NIFTY PHARMA", "NIFTY AUTO", "NIFTY FMCG"]

# ─────────────────────────────────────────────
# STRATEGY SETTINGS
# ─────────────────────────────────────────────
BACKTEST_LOOKBACK_DAYS   = 252       # 1 trading year
EVOLUTION_GENERATIONS    = 50
EVOLUTION_POPULATION     = 30

# ─────────────────────────────────────────────
# SCHEDULING  (24-hr HH:MM)
# ─────────────────────────────────────────────
SCHEDULE = {
    # ── Morning deep scans (matches MarketMonitor.DEEP_SCAN_SCHEDULE) ──────
    "market_open_regime":     "09:05",   # regime detection after open
    "first_opportunity_scan": "09:10",   # first equity + options scan
    "strategy_evaluation":    "09:20",   # select active strategies
    "trade_decision":         "09:45",   # first trade window (09:45 IST = 30 min after open)
    # ── Intraday deep scans ────────────────────────────────────────────────
    "mid_morning_scan":       "10:30",   # re-check regime + new setups    (10:30 IST)
    "mid_session_scan":        "11:30",   # post-circuit / momentum phase    (11:30 IST)
    "afternoon_scan":         "13:00",   # post-lunch session               (13:00 IST)
    "early_afternoon_scan":   "14:00",   # afternoon momentum window        (14:00 IST)
    "closing_analysis":       "15:00",   # pre-expiry / closing trades      (15:00 IST — matches MarketMonitor)
    # ── EOD ────────────────────────────────────────────────────────────────
    "eod_learning":           "15:35",   # performance learning cycle       (15:35 IST = post market close)
    # ── Legacy aliases (kept for backward compatibility) ───────────────────
    "market_regime_analysis": "09:05",
    "opportunity_scan":       "09:10",
    "mid_day_review":         "13:00",
}

# Continuous monitoring (Q2 — light scan interval)
CONTINUOUS_SCAN_INTERVAL = 30   # seconds between price/volume/breakout checks

# ─────────────────────────────────────────────
# EVALUATION BASELINE
# ─────────────────────────────────────────────
# Trades BEFORE this date are Ledger A — historical archive (engineering era).
# Trades ON/AFTER this date are Ledger B — official performance evaluation.
#
# The baseline is only *confirmed* after STABILITY_REQUIRED_SESSIONS consecutive
# clean sessions (no crashes, no false halts, no journaling corruption).
# Until then BASELINE_CANDIDATE_DATE is Day 1 of the candidate window.
BASELINE_CANDIDATE_DATE    = "2026-04-27"   # Day 1 of candidate stability window
STABILITY_REQUIRED_SESSIONS = 10             # consecutive clean sessions → baseline trusted

# ─────────────────────────────────────────────
# ADAPTIVE EXIT ENGINE  (Phase 1)
# Master toggle — set False to revert to pure rule-based exits instantly.
# ─────────────────────────────────────────────
ENABLE_ADAPTIVE_EXIT        = True

# Time-stale exit: exit if trade open this many minutes AND price barely moved
ADAPTIVE_TIME_STALE_MINUTES = 180        # 3 hours intraday lock-up limit
ADAPTIVE_STALE_MAX_R        = 0.30       # ≤ 0.3R movement = "no progress"

# Early loss control: exit early when approaching full SL
# Regime-aware: trending market gives more room, sideways/bear tightens
ADAPTIVE_EARLY_LOSS_R           = -0.60  # default: exit at -0.6R
ADAPTIVE_EARLY_LOSS_TRENDING_R  = -0.70  # bull_trend: wider — momentum needs breathing room
ADAPTIVE_EARLY_LOSS_SIDEWAYS_R  = -0.50  # range_market / bear_market: tighter — cuts dead weight faster

# Guardrails: never fire adaptive exits in these situations
ADAPTIVE_MIN_R_TO_GUARD     = 2.50      # do NOT apply time-exit if already ≥2.5R profit
ADAPTIVE_NEAR_TARGET_R      = 2.00      # do NOT apply early-loss if trade was ≥2R at any point

# ─────────────────────────────────────────────
# ADAPTIVE PROFIT EXTENSION  (Phase 2)
# When a trade nears its fixed target and conditions are strong,
# instead of exiting, tighten SL and let trailing take over.
# NEVER modifies order.target — only tightens order.stop_loss.
# ─────────────────────────────────────────────
ENABLE_ADAPTIVE_EXTENSION       = True
ADAPTIVE_EXTENSION_TRIGGER_R    = 2.80   # activate when trade reaches this R (near 3R target)
ADAPTIVE_EXTENSION_LOCK_R       = 2.50   # tighten SL to lock this much profit (moderate move)
ADAPTIVE_EXTENSION_LOCK_STRONG_R = 2.70  # tighter lock when move is very strong (3.1R+)
ADAPTIVE_EXTENSION_STRONG_R     = 3.10   # R threshold that defines a "very strong" move
ADAPTIVE_EXTENSION_MAX_VIX      = 20.0   # do NOT extend if VIX above this (volatile market)
ADAPTIVE_EXTENSION_TARGET_PCT   = 0.10   # only extend if within last 10% of target distance
ADAPTIVE_EXTENSION_TIME_CAP_MIN = 90     # extended trade still going after this many minutes
                                          # → tighten SL to 0.5R step (force trailing close)

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
LOG_DIR   = os.path.join(os.path.dirname(__file__), "data", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

# ─────────────────────────────────────────────
# NOTIFICATIONS (Telegram)
# ─────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

# ─────────────────────────────────────────────
# DHAN BROKER API
# ─────────────────────────────────────────────
# Get credentials from: https://dhan.co → My Profile → API → Create App
# Leave blank to run without live broker (paper trading still works via yfinance).
DHAN_CLIENT_ID    = os.getenv("DHAN_CLIENT_ID",    "")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")

# ─────────────────────────────────────────────
# PAPER TRADING & DATA MODE
# ─────────────────────────────────────────────
# PAPER_TRADING = True  (canonical default — system ships in paper mode)
# All orders are simulated; no real broker calls are made.
# Override via env:   PAPER_TRADING=false  (only when ready for live money)
# Override via CLI:   python run_live.py --mode paper   (explicit paper mode)
#                     python run_live.py --mode live    (requires PAPER_TRADING=false in .env)
PAPER_TRADING  = os.getenv("PAPER_TRADING", "true").lower() == "true"
USE_LIVE_DATA  = os.getenv("USE_LIVE_DATA",  "true").lower() == "true"

# ─────────────────────────────────────────────
# PILOT MODE  (₹10k–₹20k beginner capital)
# ─────────────────────────────────────────────
PILOT_CAPITAL        = float(os.getenv("PILOT_CAPITAL",         20_000))
PILOT_RISK_PCT       = float(os.getenv("PILOT_RISK_PCT",         0.005))   # 0.5% → ₹100
PILOT_MAX_TRADES     = int(os.getenv("PILOT_MAX_TRADES",             2))
PILOT_DAILY_LOSS_PCT = float(os.getenv("PILOT_DAILY_LOSS_PCT",    0.02))   # 2% → ₹400/day

# ─────────────────────────────────────────────
# NSE MARKET HOLIDAYS  (update annually)
# System skips ALL trading activity on these dates.
# ─────────────────────────────────────────────
NSE_HOLIDAYS: frozenset = frozenset({
    # ── FY 2025-26 (already past — harmless to keep) ──────────────────
    _dt.date(2026, 1, 26),   # Republic Day
    _dt.date(2026, 2, 19),   # Chhatrapati Shivaji Maharaj Jayanti
    _dt.date(2026, 3, 31),   # Mahavir Jayanti  ← CONFIRMED closed
    # ── FY 2026-27 ────────────────────────────────────────────────────
    _dt.date(2026, 4,  3),   # Good Friday
    _dt.date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    _dt.date(2026, 5,  1),   # Maharashtra Day
    _dt.date(2026, 8, 15),   # Independence Day
    _dt.date(2026, 10,  2),  # Gandhi Jayanti
    _dt.date(2026, 10, 20),  # Diwali – Laxmi Puja
    _dt.date(2026, 10, 21),  # Diwali – Balipratipada
    _dt.date(2026, 11,  5),  # Guru Nanak Jayanti
    _dt.date(2026, 12, 25),  # Christmas
})


def is_nse_holiday(d: "_dt.date | None" = None) -> bool:
    """Return True if *d* (default: today) is a weekend or in the NSE holiday list."""
    _d = d or _dt.date.today()
    if _d.weekday() >= 5:   # Saturday=5, Sunday=6 — NSE never trades on weekends
        return True
    return _d in NSE_HOLIDAYS
