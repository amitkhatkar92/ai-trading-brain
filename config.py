"""
Global Configuration — AI Trading Brain
All system-wide settings, constants, and environment variable bindings.
"""

import os
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
TOTAL_CAPITAL            = float(os.getenv("TOTAL_CAPITAL", 1_000_000))   # INR
MAX_RISK_PER_TRADE_PCT   = 0.01      # 1% of capital per trade
MAX_PORTFOLIO_RISK_PCT   = 0.05      # 5% total portfolio risk
MAX_DRAWDOWN_PCT         = 0.10      # 10% drawdown → halt trading
MIN_CONFIDENCE_SCORE     = 6.2       # Minimum Decision AI score to execute (keep fixed)

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
    "trade_decision":         "09:45",   # first trade window
    # ── Intraday deep scans ────────────────────────────────────────────────
    "mid_morning_scan":       "10:30",   # re-check regime + new setups
    "afternoon_scan":         "13:00",   # post-lunch session
    "closing_analysis":       "15:00",   # pre-expiry / closing trades
    # ── EOD ────────────────────────────────────────────────────────────────
    "eod_learning":           "15:35",   # performance learning cycle
    # ── Legacy aliases (kept for backward compatibility) ───────────────────
    "market_regime_analysis": "09:05",
    "opportunity_scan":       "09:10",
    "mid_day_review":         "13:00",
}

# Continuous monitoring (Q2 — light scan interval)
CONTINUOUS_SCAN_INTERVAL = 30   # seconds between price/volume/breakout checks

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
LOG_DIR   = os.path.join(os.path.dirname(__file__), "data", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

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
