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
MAX_RISK_PER_TRADE_PCT   = 0.0025    # 0.25% of capital per trade (calibrated OPS-02 2026-06-16; was 0.01)
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
    # ── Multi-Stage Market Preparation Engine ──────────────────────────────
    "post_market_scan":       "16:45",   # Phase D: full Nifty500 scanner   (runs ~20 min, after MF NAV settle)
    "premarket_refiner":      "08:45",   # Phase G: pre-open conviction decay + gap refresh
    # ── Legacy aliases (kept for backward compatibility) ───────────────────
    "market_regime_analysis": "09:05",
    "opportunity_scan":       "09:10",
    "mid_day_review":         "13:00",
    # ── Weekend intelligence ────────────────────────────────────────────────
    "saturday_intelligence":  "08:00",   # Saturday: deep accumulation cycle
    "sunday_intelligence":    "09:00",   # Sunday:   Monday tactical preparation
}

# Continuous monitoring (Q2 — light scan interval)
CONTINUOUS_SCAN_INTERVAL = 30   # seconds between price/volume/breakout checks

# ─────────────────────────────────────────────
# WEEKEND INTELLIGENCE OPERATING PRINCIPLE
# ─────────────────────────────────────────────
# Weekend periods are high-value intelligence accumulation windows.
# Saturday: deep market intelligence (rescan, sector, regime, telemetry review)
# Sunday:   Monday tactical preparation (global context, ranking, readiness)
#
# GOVERNANCE: weekend cycles are read-and-report ONLY.
#   - No threshold mutations
#   - No strategy enable/disable
#   - No adaptive weight updates
#   - Mutation freeze (MIN_CLEAN_PREPARED_TRADES) remains active
# Set False to idle the system on weekends (reverts to prior behaviour).
WEEKEND_INTELLIGENCE_ENABLED: bool = True

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
# MULTI-STAGE MARKET PREPARATION ENGINE
# Phase C-H feature flags — each independently disable-able at runtime.
# Set False to instantly revert any phase without redeployment.
# ─────────────────────────────────────────────

# Phase E — Prepared universe injection into OpportunityEngine
# When True: _prepared_watchlist() is consulted; falls back to static on failure.
# When False: scanner always uses static _BASE_WATCHLIST + _EXTENDED_WATCHLIST.
USE_PREPARED_UNIVERSE: bool = True   # ACTIVATED — Controlled Telemetry-Governed activation

# Minimum scan coverage for a candidate file to be considered valid.
# If scanner_stats.coverage_pct < this → file treated as invalid → static fallback.
PREPARED_UNIVERSE_MIN_COVERAGE_PCT: float = 60.0

# Phase F — Overnight macro/regime context overlay on candidate scores
USE_OVERNIGHT_OVERLAY: bool = True   # ACTIVATED — Controlled Telemetry-Governed activation

# Minimum regime confidence before overnight overlay fires.
# Below this threshold the adaptive_adjustment remains 0 (neutral).
OVERNIGHT_OVERLAY_REGIME_CONFIDENCE_MIN: float = 0.70

# Phase G — Premarket refinement (gap/decay re-scoring at 08:45 IST)
USE_PREMARKET_REFINEMENT: bool = True   # ACTIVATED — Controlled Telemetry-Governed activation

# UTC time of day after which premarket job is considered overdue.
# 03:40 UTC = 09:10 IST — 5 min buffer before first live cycle.
PREMARKET_DEADLINE_UTC_HHMM: str = "03:40"

# Phase H — Hybrid live engine (80% prepared core + 20% opportunistic exploration)
USE_HYBRID_EXPLORATION: bool = True    # ACTIVATED — 80/20 capital structure

# Fraction of the prepared candidate pool reserved for opportunistic discovery.
# Deliberate 80/20 decision (2026-05-22): exploration expanded from 3→20 after
# architecture review confirmed governance infrastructure is sufficient:
#   telemetry integrity, safe-mode, mutation freeze, fallback isolation,
#   validator enforcement, and deterministic routing all active.
# Bounded: [1, 20].  Mutation freeze (MIN_CLEAN_PREPARED_TRADES=100) remains.
# Do NOT increase to 25 without [ExplorationAudit] telemetry review.
EXPLORATION_BUDGET_PCT: int = 20

# Capital cap for the exploration bucket (% of deployable capital).
# Architectural placeholder — records the 80/20 intent at config level.
# Not yet wired into CapitalRiskEngine; wiring deferred until CRE review
# confirms no conflict with per-strategy _STRATEGY_SHARE buckets.
# Enforcement: manual review of [DhanPartialSuccess] + [ExplorationAudit] logs.
EXPLORATION_CAPITAL_CAP_PCT: int = 20

# Signal threshold for opportunistic (non-prepared) candidates.
# Raised to 7.2 vs standard 6.8 to compensate for lack of overnight validation.
# Review after 10+ live sessions before any reduction.
EXPLORATION_THRESHOLD: float = 7.2

# ── Research Integrity — Architecture Generation Tagging ──────────────────
# Date when the Prepared Universe architecture was activated in production.
# All trades BEFORE this date carry architecture_generation="LEGACY_STATIC".
# All trades ON or AFTER carry architecture_generation="PREPARED_UNIVERSE_V1".
# This constant is the single source of truth for classification across all modules.
PREPARED_UNIVERSE_ACTIVATION_DATE: str = "2026-05-22"

# Research weight per architecture generation.
# LEGACY_STATIC trades contain execution/governance information but structurally
# biased setup-quality data (stale levels, narrow universe, proxy ATR distortion).
# Only PREPARED_UNIVERSE_V1 trades carry full research-grade market intelligence.
RESEARCH_WEIGHT_LEGACY_STATIC:     float = 0.25
RESEARCH_WEIGHT_PREPARED_V1:       float = 1.00

# Minimum number of PREPARED_UNIVERSE_V1 trades required per strategy before
# auto-disable, threshold mutation, or adaptive suppression may fire.
# Below this sample: strategy is protected — no punitive adaptive action.
MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT: int = 25

# System-wide adaptive mutation freeze (Patch 21/24).
# Until total PREPARED_UNIVERSE_V1 trades across all strategies reaches this
# threshold, ALL adaptive mutations are frozen:
#   • strategy auto-disabling
#   • adaptive threshold changes
#   • overlay amplification
#   • exploration budget expansion
#   • confidence auto-scaling / demotion
# Observation, reporting, ranking, and telemetry are always permitted.
MIN_CLEAN_PREPARED_TRADES: int = 100

# ── Scanner resource bounds (prevent silent infrastructure creep) ──────────
SCANNER_MAX_SYMBOLS:          int   = 600    # hard cap on symbols attempted per run
SCANNER_MAX_CANDIDATES:       int   = 120    # hard cap on candidates written to store
SCANNER_MAX_RUNTIME_MINUTES:  int   = 20     # abort if scanner exceeds this
PREMARKET_MAX_RUNTIME_MINUTES: int  = 25     # abort if premarket refiner exceeds this
SCANNER_MEMORY_RETENTION_DAYS: int  = 30     # days of concentration history to keep

# ── Shadow mode (validation before live activation) ────────────────────────
# When True: prepared universe is generated and logged but does NOT influence
# execution. Allows 5-10 sessions of silent validation before Phase E goes live.
SCANNER_SHADOW_MODE: bool = False  # set True when Phase D first runs, False after validation

# ── Candidate quality floor — Patch 4 ─────────────────────────────────────
# Candidates scored below this threshold by market_scanner are dropped before
# being written to the store.  Prevents weak/choppy-market candidates entering
# the prepared universe.  Do NOT weaken this dynamically.
MIN_PREPARED_SCORE: float = 0.55

# ── Absolute candidate cap — Patch 3 ──────────────────────────────────────
# Hard ceiling applied AFTER all ranking, sector-cap, and score-floor filters.
# Guarantees the prepared universe never silently expands beyond this count.
# Emits [PreparedUniverseCap] when truncation actually occurs.
MAX_PREPARED_CANDIDATES: int = 120

# ── Safe mode trigger thresholds — Patch 7 ────────────────────────────────
# SAFE MODE reduces system sophistication (disables prepared universe +
# exploration) but NEVER stops the engine or closes positions.
SAFE_MODE_MAX_FALLBACK_SESSIONS: int   = 3     # >N consecutive static fallbacks → safe mode
SAFE_MODE_MAX_MISSING_LTP_PCT:   float = 50.0  # >N% of prepared symbols have LTP=0 → safe mode

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


# ─────────────────────────────────────────────
# MLS Phase 6 — Autonomous Market Learning Scheduler
# ─────────────────────────────────────────────
AMLS_ENABLED: bool = True   # set False to disable without any behaviour change


def is_nse_holiday(d: "_dt.date | None" = None) -> bool:
    """Return True if *d* (default: today) is a weekend or in the NSE holiday list."""
    _d = d or _dt.date.today()
    if _d.weekday() >= 5:   # Saturday=5, Sunday=6 — NSE never trades on weekends
        return True
    return _d in NSE_HOLIDAYS
