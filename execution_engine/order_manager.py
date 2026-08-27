"""
Order Manager — Layer 8 Core
==============================
Central hub for all order routing. Selects the active broker adapter,
converts TradeSignal + DecisionResult into broker-specific calls,
and maintains the live Portfolio state.

Supports:
  • Zerodha (KiteConnect)
  • Dhan (DhanHQ)
  • AngelOne (SmartAPI)
"""

from __future__ import annotations
import csv
import json
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import config as _cfg
from models.trade_signal  import TradeSignal, SignalDirection, SignalType
from models.portfolio     import Portfolio, Position
from models.agent_output  import DecisionResult
from config import (ACTIVE_BROKER, TOTAL_CAPITAL,
                    ZERODHA_API_KEY, ZERODHA_ACCESS_TOKEN,
                    DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN,
                    ANGELONE_API_KEY, ANGELONE_CLIENT_ID,
                    ANGELONE_PASSWORD, ANGELONE_TOTP_SECRET,
                    ATR_ZONE_MULTIPLIER)
from utils import get_logger

log = get_logger(__name__)

# ── Phase 7: Re-entry audit tracking ─────────────────────────────────────────
# Populated by close_position(); checked by place_order().
# Telemetry only — does NOT block or reject any order.
_RECENT_CLOSE_TIMES: Dict[str, Dict] = {}    # symbol → {time, r, direction}
_REENTRY_AUDIT_LOG:  List[dict]      = []    # accumulated this session

# ── Retry configuration ────────────────────────────────────────────────────
MAX_ORDER_RETRIES = 3       # attempts before giving up
RETRY_BASE_DELAY  = 0.5    # seconds; doubles each attempt (0.5 → 1.0 → 2.0)

# ── Limit-order expiry ───────────────────────────────────────────────────────
# NSE 5-minute candle = 300 s.  Cancel any unfilled LIMIT order after
# LIMIT_CANDLE_EXPIRY candles (increased 3→8 × 5 min = 40 minutes for better fill).
LIMIT_CANDLE_EXPIRY  = 8     # number of candles before stale limit is cancelled [EXTENDED]
CANDLE_SECONDS       = 300   # seconds per candle (5-minute default)

# ── Re-entry window ────────────────────────────────────────────────────────
# After a LIMIT order expires by time (not by regime/distortion/VIX), the
# system enters a "re-entry window" during which it will automatically
# re-place the same limit if price revisits the signal level and the
# market context is still valid.
REENTRY_WINDOW_CANDLES = 10   # candles after expiry to allow re-placement
REENTRY_MAX_RETRIES    = 2    # maximum re-placements per expired signal
REENTRY_PRICE_BAND_PCT = 0.50 # ±% band from entry_price to accept re-entry
                               # set to 0.0 to skip the price-proximity check

# ── EARLY_LOSS re-entry cooldown ──────────────────────────────────────────────
# Block fresh entries into the same symbol for this many hours after an
# EARLY_LOSS adaptive exit.  Prevents same-session re-entry on a proven
# losing setup (ASIANPAINT/DRREDDY pattern seen Jun–Jul 2026).
# Genuine SL hits, targets, SESSION_EXPIRED do NOT trigger this cooldown.
_EARLY_LOSS_COOLDOWN_H = 24.0  # hours

# ── Entry Zone ─────────────────────────────────────────────────────────────────
# Instead of placing at the exact signal price, the zone-adjusted price is
# slightly more aggressive (toward market) to improve fill probability:
#   BUY  limit  = signal_price * (1 + zone_pct/100)  → fractionally higher
#   SELL limit  = signal_price * (1 − zone_pct/100)  → fractionally lower
# Zone width is VIX-scaled: widens in fear, narrows in calm markets.
ZONE_BASE_PCT       = 0.15  # base band width % at normal VIX
ZONE_VIX_NORMAL     = 15.0  # VIX level considered "normal" (factor = 1.0)
ZONE_VIX_MIN_FACTOR = 0.50  # minimum scale (calm markets: half the band)
ZONE_VIX_MAX_FACTOR = 2.00  # maximum scale (fear markets: double the band)

# ── Adaptive Entry Timing (AET) ─────────────────────────────────────────────────────
# AET selects one of three entry timing modes based on market micro-signals:
#
#   IMMEDIATE    — strong/neutral context; place at zone_price right away
#   PULLBACK     — trending regime; nudge limit deeper into zone to wait for
#                  a small retracement before filling
#   CONFIRMATION — elevated VIX or distortion present; defer placement for
#                  up to AET_MAX_WAIT_CANDLES and only place once conditions
#                  calm down (VIX drops below AET_VIX_CONFIRM_THRESHOLD)
#
# Interaction with Entry Zone: AET price is always calculated ON TOP of the
# zone-adjusted price, not on the raw signal price.
AET_VIX_CONFIRM_THRESHOLD = 32.0  # VIX must be below this to confirm entry [RAISED 18→32]
AET_PULLBACK_DIP_PCT      = 0.10  # extra % deeper into zone for PULLBACK mode
AET_MAX_WAIT_CANDLES      = 5     # max candles a CONFIRMATION slot may wait [RAISED 1→5]

# ── Paper trade journal ───────────────────────────────────────────────────
_DATA_DIR        = os.path.join(os.path.dirname(__file__), "..", "data")
PAPER_TRADE_LOG  = os.path.join(_DATA_DIR, "paper_trades.csv")
# Live execution journal — append-only JSONL, written in both paper and live modes.
# Provides position recovery on container restart independent of broker API.
_LIVE_DIR        = os.path.join(_DATA_DIR, "live")
LIVE_ORDER_LOG   = os.path.join(_LIVE_DIR, "live_orders.jsonl")
_JOURNAL_HEADER  = [
    "timestamp", "order_id", "symbol", "direction", "quantity",
    "entry_price", "stop_loss", "target", "strategy",
    "confidence", "rr", "event",
    "exit_price", "pnl", "reason",
]

# Closed-order registry: one order_id per line, new file each calendar day.
# Used by _restore_from_journal to filter ghost OPEN rows whose CLOSE event
# was written but the CSV write failed (e.g. process killed mid-write).
def _closed_registry_path() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(_DATA_DIR, f"closed_orders_{today}.txt")

# Sidecar that persists carry-expiry retry counts across restarts.
# Prevents a bad disk/permission issue from silently resetting the retry clock.
_EXPIRY_RETRIES_PATH = os.path.join(_DATA_DIR, "expiry_retries.json")

# ── Strategy-aware max carry days ────────────────────────────────────────
# Controls how many calendar days a position is allowed to carry before it
# is treated as a genuine orphan and given a SESSION_EXPIRED close.
# Matching is prefix-based and case/underscore-insensitive (same as StaleCarry).
_CARRY_DAYS_BY_TYPE: dict = {
    # Mean-reversion: short-duration thesis — max 3 days
    "meanreversion": 3, "reversion": 3, "range": 3, "hedging": 3,
    # Momentum / breakout: medium duration — max 5 days
    "momentum": 5, "breakout": 5, "edgmoment": 5,
    # Trend / swing: long-duration thesis — max 7 days
    "trend": 7, "pullback": 7, "swing": 7, "bullcall": 7, "bearput": 7,
}
_CARRY_DAYS_DEFAULT = 5   # fallback for unclassified strategies


def _carry_days_for(strategy: str) -> int:
    """Return the max carry days for a given strategy name (trading days)."""
    key = strategy.lower().replace("_", "").replace("-", "").replace(" ", "")
    for prefix, days in _CARRY_DAYS_BY_TYPE.items():
        if key.startswith(prefix):
            return days
    return _CARRY_DAYS_DEFAULT


def _trading_days_elapsed(placed_at: datetime, now: datetime) -> int:
    """Count weekdays (Mon-Fri) elapsed from placed_at to now.

    NSE public holidays are treated as trading days — conservative
    approximation.  A holiday-adjacent carry may fire one session early,
    which is the safe failure mode (earlier exit, not later).

    Rationale for weekday-only approach:
      • Zero external dependency — no holiday list to maintain.
      • Fixes the primary defect: weekends consuming carry budget.
      • Holidays add at most 1 session of over-counting per occurrence.
      • Design review (CarryDesignReview Jun 8 2026): Option B adopted.
    """
    count = 0
    d = placed_at.date()
    target = now.date()
    while d < target:
        d += timedelta(days=1)
        if d.weekday() < 5:   # Mon=0 … Fri=4
            count += 1
    return count


# Calendar-day hard ceiling per unit of max_carry (trading days).
# Prevents infinite deferral when a holiday cluster (e.g. Diwali week)
# extends the carry window beyond all reasonable bounds.
# Formula: max_carry_td × _CARRY_CAL_CEIL_FACTOR  →  e.g. 3td × 4 = 12cd
_CARRY_CAL_CEIL_FACTOR: int = 4

# ── Duplicate-guard LTP freshness thresholds ─────────────────────────────
_DUP_GUARD_STALE_AFTER_S    = 120  # LTP age (s) above which we mark stale
_DUP_GUARD_FRESH_COOLDOWN_S =  30  # after going stale, wait this long before fresh again
_DUP_GUARD_LTP_CONF_TICKS   =   2  # minimum consecutive fresh ticks for full R confidence

# ── Risk Guards (prevent trade volume explosion & duplicates) ──────────────
MAX_OPEN_POSITIONS = 15       # maximum concurrent positions (INCREASED 5→15 for capital deployment)
MAX_CAPITAL_PER_TRADE_PCT = 15.0  # max % of capital per single trade
MAX_TOTAL_OPEN_EXPOSURE_PCT = 85.0  # max % of total capital in open positions (INCREASED 65→85)

# ── Late-Day Entry Control (institutional time-based rules) ────────────────
# Before 13:30          → normal (min score 6.5 enforced by DecisionEngine)
# 13:30 – 14:30         → higher-conviction required (min score 7.0)
# After  14:30          → no fresh entries — monitoring / exits only
# Exempt: same-symbol swap replacements (position management, not fresh entry)
_LATE_ENTRY_CUTOFF_H, _LATE_ENTRY_CUTOFF_M   = 14, 30   # hard cutoff
_LATE_ENTRY_ELEVATED_H, _LATE_ENTRY_ELEVATED_M = 13, 30  # elevated-threshold window starts
_LATE_ENTRY_MIN_SCORE = 7.0                               # score floor in elevated window

# ── Early-Entry Governance (09:45 execution window) ────────────────────────
# No order may be placed before 09:45 IST regardless of how execute() is
# reached.  Layer 3 (last-resort) of the defence-in-depth stack:
#   Layer 1: orchestrator deep-scan handler  (suppresses task submission)
#   Layer 2: run_full_cycle() / options fast-path (skip cycle entirely)
#   Layer 3: order_manager.execute() hard block  ← this constant
_EXEC_WIN_OPEN_H, _EXEC_WIN_OPEN_M = 9, 45   # earliest permitted order time IST


@dataclass
class OrderRecord:
    """Represents a placed order and its lifecycle."""
    order_id:    str
    symbol:      str
    direction:   str
    quantity:    int
    entry_price: float
    stop_loss:   float
    target:      float
    strategy:    str
    status:      str = "open"           # open | closed | cancelled
    fill_price:  float = 0.0
    sl_order_id: str = ""
    closed_at:   Optional[datetime] = None
    pnl:         float = 0.0
    order_type:  str = "LIMIT"          # LIMIT | MARKET
    placed_at:   Optional[datetime] = None  # wall-clock time the order was sent
    zone_price:  float = 0.0               # actual limit price sent to broker
                                            # (entry_price = signal price for PnL)
    aet_mode:    str = "IMMEDIATE"         # IMMEDIATE | PULLBACK | CONFIRMATION
    # ── Signal-creation context (for context-based cancellation) ──────
    signal_regime:     str   = ""    # market regime at signal creation
    signal_vix:        float = 0.0   # India VIX at signal creation
    signal_distortion: bool  = False # was a distortion event active?
    confidence_score:  float = 0.0   # DecisionEngine score at entry (for smart-swap ranking)
    # Carry-expiry retry counter — incremented each time check_and_expire_carries
    # attempts but fails to write the CLOSE row.  Capped at _CARRY_EXPIRY_MAX_RETRIES
    # to prevent a persistently-broken symbol from silently blocking expiry forever.
    _expiry_retry_count: int = 0
    # Timestamp of last failed expiry attempt — used for 5-min backoff so a
    # transient file issue does not spam the write path every monitoring cycle.
    _last_retry_ts:      Optional[datetime] = None
    # Governance state — explicit lifecycle visibility for risk oversight.
    # Guarantees every position can report its supervision status at any time.
    # ACTIVE           : fresh execution, first-day position
    # ACTIVE_CARRY     : restored multi-day carry, fully governed
    # ORPHAN_WATCH     : past carry_limit; all risk controls active, execution restricted
    # EXPIRED_PENDING  : SESSION_EXPIRED written to CSV, pending deregister
    governance_state:    str  = "ACTIVE"   # see constants above
    orphan_watch:        bool = False       # True when past carry_limit (ORPHAN_WATCH state)
    # Exit reason stamped at close time — used by StrategyHealthMonitor to distinguish
    # genuine strategy outcomes from system-management events (SESSION_EXPIRED, REPLACEMENT…).
    close_reason:        str  = ""         # populated by close_position(); empty = unknown
    # Immutable historical risk anchor — the stop-loss distance that defined 1R at trade open.
    # Cleanup paths (SESSION_EXPIRED, orphan expiry) may zero out runtime stop_loss; this field
    # preserves the original value so evaluation layers always compute consistent R-multiples.
    initial_stop_loss:   float = 0.0      # set once at order creation; never modified afterwards
    # Post-expiry review engine (Phase C) — counts how many times this position
    # has been approved for extension by _review_carry_extension.
    # Phase B: always 0 (dry-run only).  Phase C: incremented on CONTINUE.
    # Persisted in expiry_retries.json sidecar when Phase C is active.
    extension_count:     int   = 0
    # ── Broker fill reconciliation ─────────────────────────────────────────
    # For live orders: populated by _reconcile_fill() after placement.
    # Never invented — stays at defaults (fill_status="") until confirmed.
    broker_order_id:       str   = ""    # echoes order_id; SIM_* for paper/sim
    fill_status:           str   = ""    # FILLED | PARTIALLY_FILLED | REJECTED | CANCELLED | PENDING | UNRESOLVED | ""
    actual_fill_price:     float = 0.0   # average fill price from broker (0 until confirmed)
    requested_price:       float = 0.0   # signal price at order time
    filled_quantity:       int   = 0     # actual filled qty (may differ from .quantity)
    slippage_abs:          float = 0.0   # actual_fill - requested_price (signed)
    slippage_pct:          float = 0.0   # slippage_abs / requested_price × 100
    reconciliation_ts:     str   = ""    # ISO timestamp of last reconciliation attempt
    reconciliation_source: str   = ""    # "DHAN_GET_ORDER_BY_ID" | "PAPER" | "SIM"
    # ── Universal opportunity lineage ID ──────────────────────────────────
    # Set from signal.opportunity_id at execute() time so every downstream
    # store (live journal, outcome, KEL) can join on this single key.
    opportunity_id:        str   = ""


@dataclass
class ReentrySlot:
    """
    Represents an expired LIMIT order that is eligible for re-placement.

    Created only when a LIMIT order expires by *time* (``limit_expired_N_candles``).
    Orders cancelled due to regime change, distortion, or VIX spike are
    NOT eligible for re-entry because the original signal context is
    fundamentally invalidated.

    Fields
    ------
    original_order_id : order_id of the initial (now-cancelled) LIMIT order
    window_expires_at : wall-clock deadline; re-entry attempts after this time
                        are silently dropped
    retry_count       : how many times this slot has already been re-entered
    """
    original_order_id: str
    symbol:            str
    direction:         str       # "BUY" | "SELL"
    entry_price:       float
    stop_loss:         float
    target:            float
    strategy:          str
    quantity:          int
    signal_regime:     str
    signal_vix:        float
    window_expires_at: datetime  # original placed_at + reentry_window_candles
    opportunity_id:    str  = ""  # D10-002: propagate from original OrderRecord
    retry_count:       int = 0
    max_retries:       int = REENTRY_MAX_RETRIES


class AdaptiveTimingMode(str, Enum):
    """
    Controls when inside the entry zone the AI actually fires the order.

    IMMEDIATE    — Place the limit order right away at zone_price.
                   Used in low-volatility or range-bound markets.
    PULLBACK     — Push the limit slightly deeper into the zone to wait
                   for a small intra-zone retracement before filling.
                   Used in trending (TREND / BULL) regimes.
    CONFIRMATION — Defer placement until VIX normalises or distortion
                   clears.  The slot is held in _aet_pending for up to
                   AET_MAX_WAIT_CANDLES cycles.
    """
    IMMEDIATE    = "IMMEDIATE"
    PULLBACK     = "PULLBACK"
    CONFIRMATION = "CONFIRMATION"


@dataclass
class AetPendingSlot:
    """
    A trade that has been approved but is waiting for CONFIRMATION before
    the limit order is actually sent to the broker.

    Created in ``execute()`` when ``_determine_aet_mode`` returns CONFIRMATION.
    Resolved (or expired) by ``attempt_aet_confirmations()`` each cycle.
    """
    slot_id:       str             # unique key, same as would-be order_id
    signal:        TradeSignal
    decision:      DecisionResult
    qty:           int
    zone_price:    float           # limit price to use when confirmed
    signal_regime: str
    signal_vix:    float
    created_at:    datetime
    candles_waited: int = 0
    max_wait:      int = AET_MAX_WAIT_CANDLES


class OrderManager:
    """Routes orders to the active broker and maintains portfolio state."""

    def __init__(self):
        self._paper_mode = getattr(_cfg, "PAPER_TRADING", True)
        # Defense in depth: require explicit LIVE_TRADING_AUTHORIZED to route real orders
        if not self._paper_mode and os.getenv("LIVE_TRADING_AUTHORIZED", "").lower() != "true":
            log.warning(
                "[OrderManager] PAPER_TRADING=False but LIVE_TRADING_AUTHORIZED not set "
                "— forcing paper mode. Broker will not be initialized."
            )
            self._paper_mode = True
        self._broker     = None if self._paper_mode else self._load_broker()
        self._portfolio  = Portfolio(capital=TOTAL_CAPITAL, peak_capital=TOTAL_CAPITAL)
        self._orders: Dict[str, OrderRecord] = {}
        self._reentry_slots: Dict[str, ReentrySlot] = {}
        self._aet_pending: Dict[str, AetPendingSlot] = {}
        # Per-symbol timestamp of when LTP was last demoted to stale state.
        # Used for hysteresis: symbol stays stale for at least
        # _DUP_GUARD_FRESH_COOLDOWN_S before cache is re-read.
        self._ltp_stale_at: Dict[str, datetime] = {}
        # Thread lock for all journal file operations.
        self._journal_lock = threading.Lock()
        # Serialises all reads + writes to expiry_retries.json so concurrent
        # monitoring threads can never interleave or produce a torn write.
        self._expiry_sidecar_lock = threading.Lock()
        # D11-003: guards _orders dict and _portfolio.positions against concurrent
        # reads-during-write from scheduler + TradeMonitor worker threads.
        self._orders_lock = threading.RLock()
        # Daily telemetry counters for dup-guard decisions.
        self._dup_guard_stats: Dict[str, Any] = {
            "overrides_by_profit":          0,
            "overrides_by_age":             0,
            "blocks_by_loss":               0,
            "blocks_by_age":                0,
            "ltp_unavailable_fallbacks":    0,
            "ltp_stale_fallbacks":          0,
            "ltp_lowconf_fallbacks":        0,
            "missed_opportunity_recovered": 0,
        }
        # Decision latency samples (seconds from restore → first confident R decision).
        self._decision_latency_samples: List[float] = []
        # Symbols recently blocked by an LTP issue; used for missed-opportunity detection.
        self._ltp_blocked_symbols: Dict[str, datetime] = {}
        # Optional TradeMonitor reference: set via inject_trade_monitor() after init.
        # Used to deregister positions that are closed by smart-swap so they are
        # not phantom-monitored and do not produce spurious SL/analytics events.
        self._trade_monitor = None
        # Optional RiskGuardian reference: set via inject_risk_guardian() after init.
        # D11-001: allows close_position() to call record_trade_result() exactly once.
        self._risk_guardian = None
        # D11-001: idempotency set — prevents double-counting if close_position() is
        # re-entered (e.g. emergency_close after a SmartSwap that already closed it).
        self._rg_recorded_oids: set = set()
        # Set of order_ids whose profit extension SL-lock was restored from the
        # journal. TradeMonitor reads this in register() to skip _can_extend().
        self._restored_extended_oids: set = set()
        # Belt-and-suspenders dedupe for carry-expiry: tracks order_ids that have
        # been SESSION_EXPIRED today so a second call can never re-close them.
        # Reset each calendar day at the top of check_and_expire_carries().
        self._closed_ids_today: set = set()
        self._closed_ids_today_date: Optional[str] = None
        # Daily rotation throttle for smart-swap (Pathway A).
        # Stores the calendar-date string of the last successful cross-signal
        # replacement.  A new date string never matches, so it resets itself
        # automatically on the first execute() call of each trading day.
        # Limits churn: at most 1 forced position replacement per day.
        self._swap_rotation_date: Optional[str] = None
        # Restore diagnostics: populated by _restore_from_journal() at each startup.
        # Exposed via get_restore_stats() so orchestrator and health monitors can
        # report restore integrity in startup Telegram pings and cycle reports.
        self._restore_stats: Dict[str, Any] = {
            "restored_today":          0,
            "restored_carry":          0,
            "expired_at_restore":      0,   # SESSION_EXPIRED written during _restore_from_journal
            "orphan_monitored_count":  0,   # positions past carry_limit kept under governance
            "monitoring_gap_seconds":  0,   # gap detected by post-restore governance pass
            "reconciled_count":        0,   # positions checked in post-restore governance pass
            "immediate_sl_hits":       0,   # SLs triggered in post-restore pass
            "immediate_expiries":      0,   # SESSION_EXPIREDs in post-restore pass
        }
        if self._paper_mode:
            os.makedirs(_DATA_DIR, exist_ok=True)
            # Clean up any orphaned expiry_retry_*.tmp files left by a crash
            # before os.replace() could complete. Scoped prefix avoids touching
            # unrelated .tmp files in the data directory.
            for _fn in os.listdir(_DATA_DIR):
                if _fn.startswith("expiry_retry_") and _fn.endswith(".tmp"):
                    try:
                        os.remove(os.path.join(_DATA_DIR, _fn))
                        log.debug("[OrderManager] Removed orphan temp file: %s", _fn)
                    except Exception:
                        pass
            log.info("[OrderManager] PAPER TRADING mode — no live orders will be sent.")
            log.info("[OrderManager] Trade journal: %s", os.path.abspath(PAPER_TRADE_LOG))
            self._restore_from_journal()   # re-hydrate open positions after any restart
            # Apply persisted expiry retry counts to restored orders so the
            # retry limit survives container restarts.
            try:
                if os.path.exists(_EXPIRY_RETRIES_PATH):
                    with open(_EXPIRY_RETRIES_PATH, encoding="utf-8") as _rf:
                        try:
                            _persisted_retries: dict = json.load(_rf)
                        except Exception:
                            log.warning(
                                "[ExpiryRetriesCorrupt] expiry_retries.json is malformed — "
                                "resetting sidecar. Retry counts will restart from 0."
                            )
                            _persisted_retries = {}
                    for _oid, _cnt in _persisted_retries.items():
                        if _oid in self._orders:
                            self._orders[_oid]._expiry_retry_count = int(_cnt)
                            log.debug(
                                "[OrderManager] Restored expiry_retry_count=%d for %s.",
                                _cnt, _oid,
                            )
            except Exception as _re_exc:
                log.debug("[OrderManager] Could not load expiry_retries.json: %s", _re_exc)
            self._prefetch_restored_ltps() # immediately resolve LTP for restored positions
        else:
            log.info("[OrderManager] Active broker: %s", ACTIVE_BROKER.upper())
            # Ensure live journal directory exists
            os.makedirs(_LIVE_DIR, exist_ok=True)
            log.info("[OrderManager] Live order journal: %s", os.path.abspath(LIVE_ORDER_LOG))
            # ORJ-001: reconcile historical SIM_ paper artifacts that were left
            # open before the PAPER→LIVE transition.  Append-only; never touches
            # live positions or Dhan orders.
            self._reconcile_sim_paper_artifacts()
            # H-001: Restore open positions from live journal (fast-path) or broker API
            # (authoritative path).  Ensures position state survives container restarts.
            self._restore_from_live_journal()
            # Startup fill reconciliation: query broker for any restored live orders
            # whose fill_status is unresolved from a prior run.
            try:
                self.reconcile_startup_fills()
            except Exception as _rsf_exc:
                log.debug("[StartupReconcile] Startup fill reconciliation skipped: %s", _rsf_exc)
            # D-006: AET confirmation slots are in-memory only and cannot survive restarts.
            # Any CONFIRMATION-deferred trade pending at crash time is permanently lost.
            # The scanner will re-identify the setup on the next cycle if conditions hold.
            # This is logged at startup so the operator is aware of the limitation.
            log.info(
                "[OrderManager] Note: AET confirmation slots are session-only. "
                "Any pending CONFIRMATION trades from a prior session are lost and "
                "will be re-evaluated by the scanner on the next cycle."
            )

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────────────────────────

    def inject_trade_monitor(self, trade_monitor) -> None:
        """Wire in the TradeMonitor so smart-swap can deregister replaced positions."""
        self._trade_monitor = trade_monitor

    def inject_risk_guardian(self, risk_guardian) -> None:
        """D11-001: Wire in FailSafeRiskGuardian so close_position() can call record_trade_result()."""
        self._risk_guardian = risk_guardian

    def execute(self, signal: TradeSignal,
                decision: DecisionResult,
                signal_context: Optional[dict] = None) -> Optional[OrderRecord]:
        """
        Execute a signal that has been approved by the Decision Engine.
        Adjusts quantity by the position modifier from the debate.

        ``signal_context`` carries the market state at the moment the signal
        was generated.  It is stored on the OrderRecord so that
        ``check_and_expire_stale_limits`` can detect if the context has
        drift beyond acceptable bounds before the limit is ever hit.

        Expected keys (all optional, safe to omit):
          regime    – str   e.g. "TREND", "RANGE"
          vix       – float India VIX value
          distortion – bool any distortion event active
        """
        # ── PRR-001 Phase 3: Signal Freshness Gate ───────────────────────────
        # Block execution of signals older than 15 trading days (EXPIRED).
        # WEAKENING signals (6–15 days) are allowed with a warning.
        try:
            from production_readiness.ph3_signal_freshness import is_signal_expired
            if is_signal_expired(signal):
                log.warning(
                    "[SignalFreshnessGate] BLOCKED %s — signal timestamp=%s is EXPIRED "
                    "(>15 trading days old). PRR-001 Phase 3 rule enforced.",
                    signal.symbol,
                    getattr(signal, "timestamp", "?"),
                )
                return None
        except Exception as _sf_exc:
            log.debug("[SignalFreshnessGate] Check skipped: %s", _sf_exc)
        # ── end Signal Freshness Gate ─────────────────────────────────────────

        # ── Layer 3: ExecutionWindowBlock ───────────────────────────────────
        # Last-resort hard block: reject any order placed before 09:45 IST.
        # Catches callers that bypass Layers 1 and 2 (e.g. test harnesses,
        # direct calls, future code paths not yet guarded upstream).
        _ewb_now = datetime.now()
        _ewb_win = _ewb_now.replace(
            hour=_EXEC_WIN_OPEN_H, minute=_EXEC_WIN_OPEN_M,
            second=0, microsecond=0,
        )
        if _ewb_now < _ewb_win:
            _ewb_mins = int((_ewb_win - _ewb_now).total_seconds() / 60)
            log.warning(
                "[ExecutionWindowBlock] symbol=%s strategy=%s "
                "attempt_time=%s allowed_window=09:45 "
                "minutes_early=%d action=ORDER_REJECTED",
                signal.symbol,
                getattr(signal, 'strategy_name', '?'),
                _ewb_now.strftime('%H:%M:%S'),
                _ewb_mins,
            )
            return None
        # ── end ExecutionWindowBlock ──────────────────────────────────────────

        # ── FIX 1: Guard against duplicate trades on same symbol ──────
        _new_score = float(getattr(decision, "confidence_score", 5.0))
        _is_same_symbol_swap = False  # True when we replace the *same* symbol (exempt from late-entry guard)
        if self._symbol_has_open_position(signal.symbol):
            if not self._dup_guard_reentry_check(
                signal.symbol,
                decision_score=_new_score,
                new_entry_price=signal.entry_price,
            ):
                # Smart swap: close weakest position if new signal is clearly better
                _swap = self._smart_swap_check(
                    signal.symbol, _new_score,
                    new_entry=signal.entry_price,
                    new_stop=signal.stop_loss,
                    new_target=signal.target_price,
                )
                if _swap:
                    _swap_oid, _swap_sym, _weak_score = _swap
                    # ── Daily rotation throttle (Pathway A, FIX 1) ───────────
                    _ss_today = datetime.now().strftime("%Y-%m-%d")
                    if self._swap_rotation_date == _ss_today:
                        log.info(
                            "[SmartSwapThrottle] rotation_date=%s old_symbol=%s "
                            "new_symbol=%s status=BLOCKED reason=DAILY_CAP_REACHED",
                            _ss_today, _swap_sym, signal.symbol,
                        )
                        return None
                    # ── PRE-EVICTION DUPGUARD CHECK (validate-first) ──────────
                    # If the weakest position belongs to a DIFFERENT symbol than
                    # the incoming signal, evicting it will NOT reduce the open
                    # count for signal.symbol.  DupGuard would still block the
                    # new trade, so the eviction achieves nothing but a realized
                    # loss.  Abort before touching any position.
                    if _swap_sym != signal.symbol and self._symbol_has_open_position(signal.symbol):
                        log.warning(
                            "[SmartSwap] Pre-eviction DupGuard check failed — closing %s "
                            "would NOT unblock %s (still has open position). "
                            "Skipping swap to avoid unnecessary loss.",
                            _swap_sym, signal.symbol,
                        )
                        return None
                    if _swap_sym == signal.symbol:
                        _is_same_symbol_swap = True  # same-symbol replacement — exempt from late-entry guard
                    _swap_rec = self._orders[_swap_oid]
                    _swap_pos = self._portfolio.positions.get(_swap_sym)
                    _exit_px = (
                        _swap_pos.ltp
                        if _swap_pos and _swap_pos.has_live_ltp and _swap_pos.ltp > 0
                        else _swap_rec.entry_price
                    )
                    # D-014: abort swap if close fails — do not consume rotation quota
                    if not self.close_position(_swap_oid, _exit_px, reason="REPLACEMENT"):
                        log.error(
                            "[SmartSwap] Close failed for %s — swap aborted. "
                            "New signal %s rejected to avoid duplicate exposure.",
                            _swap_sym, signal.symbol,
                        )
                        return None
                    self._swap_rotation_date = _ss_today
                    log.info(
                        "[SmartSwapThrottle] rotation_date=%s old_symbol=%s "
                        "new_symbol=%s status=CONSUMED",
                        _ss_today, _swap_sym, signal.symbol,
                    )
                    log.info(
                        "[Replace] Closed %s (score=%.1f) → new %s stronger (score=%.1f).",
                        _swap_sym, _weak_score, signal.symbol, _new_score,
                    )
                    # Remove closed symbol from portfolio so exposure guard is accurate
                    if not self._symbol_has_open_position(_swap_sym):
                        self._portfolio.positions.pop(_swap_sym, None)
                    # Fall through to execute the new trade
                else:
                    return None

        # ── FIX 2: Guard against position explosion ────────────────────
        open_count = len(self.get_open_orders())
        if open_count >= MAX_OPEN_POSITIONS:
            # Smart swap: close weakest position if new signal is clearly better
            _swap = self._smart_swap_check(
                signal.symbol, _new_score,
                new_entry=signal.entry_price,
                new_stop=signal.stop_loss,
                new_target=signal.target_price,
            )
            if _swap:
                _swap_oid, _swap_sym, _weak_score = _swap
                # ── Daily rotation throttle (Pathway A, FIX 2) ───────────
                _ss_today = datetime.now().strftime("%Y-%m-%d")
                if self._swap_rotation_date == _ss_today:
                    log.info(
                        "[SmartSwapThrottle] rotation_date=%s old_symbol=%s "
                        "new_symbol=%s status=BLOCKED reason=DAILY_CAP_REACHED",
                        _ss_today, _swap_sym, signal.symbol,
                    )
                    return None
                # ── PRE-EVICTION DUPGUARD CHECK (validate-first) ──────────
                # Max-positions guard: evicting a different symbol frees a
                # portfolio slot, but if signal.symbol already has an open
                # position that DupGuard would hard-block (>= 2 open), the
                # new trade still can't proceed.  Check before evicting.
                if _swap_sym != signal.symbol and self._symbol_has_open_position(signal.symbol):
                    open_same = sum(
                        1 for r in self._orders.values()
                        if r.symbol == signal.symbol and r.status == "open"
                    )
                    if open_same >= 2:
                        log.warning(
                            "[SmartSwap] Pre-eviction DupGuard check failed (MAX GUARD) — "
                            "closing %s would NOT unblock %s (%d open, max 2). "
                            "Skipping swap to avoid unnecessary loss.",
                            _swap_sym, signal.symbol, open_same,
                        )
                        return None
                if _swap_sym == signal.symbol:
                    _is_same_symbol_swap = True  # same-symbol replacement — exempt from late-entry guard
                _swap_rec = self._orders[_swap_oid]
                _swap_pos = self._portfolio.positions.get(_swap_sym)
                _exit_px = (
                    _swap_pos.ltp
                    if _swap_pos and _swap_pos.has_live_ltp and _swap_pos.ltp > 0
                    else _swap_rec.entry_price
                )
                # D-014: abort swap if close fails — do not consume rotation quota
                if not self.close_position(_swap_oid, _exit_px, reason="REPLACEMENT"):
                    log.error(
                        "[SmartSwap] Close failed for %s — swap aborted. "
                        "New signal %s rejected to avoid duplicate exposure.",
                        _swap_sym, signal.symbol,
                    )
                    return None
                self._swap_rotation_date = _ss_today
                log.info(
                    "[SmartSwapThrottle] rotation_date=%s old_symbol=%s "
                    "new_symbol=%s status=CONSUMED",
                    _ss_today, _swap_sym, signal.symbol,
                )
                log.info(
                    "[Replace] Closed %s (score=%.1f) → new %s stronger (score=%.1f).",
                    _swap_sym, _weak_score, signal.symbol, _new_score,
                )
                if not self._symbol_has_open_position(_swap_sym):
                    self._portfolio.positions.pop(_swap_sym, None)
                # Fall through to execute the new trade
            else:
                log.warning(
                    "[OrderManager] ❌ MAX GUARD: %d open positions already active "
                    "(limit: %d). Rejecting %s to prevent position explosion.",
                    open_count, MAX_OPEN_POSITIONS, signal.symbol
                )
                return None

        # ── EARLY_LOSS re-entry cooldown ──────────────────────────────────────
        # After an EARLY_LOSS adaptive exit, block fresh entries for the same
        # symbol for _EARLY_LOSS_COOLDOWN_H hours.  This prevents the pattern
        # where the scanner re-identifies the same setup the next morning on a
        # stock that already proved it wasn't working (e.g. ASIANPAINT Jun 30
        # EARLY_LOSS → re-entry Jul 1 09:45, DRREDDY Jun 24 → Jun 25).
        # Exempt: same-symbol swap replacements (position management, not new thesis)
        if not _is_same_symbol_swap:
            _prev_close = _RECENT_CLOSE_TIMES.get(signal.symbol.strip())
            if _prev_close is not None:
                _prev_reason = _prev_close.get("reason", "")
                _gap_h = (datetime.now() - _prev_close["time"]).total_seconds() / 3600
                if _prev_reason == "EARLY_LOSS" and _gap_h < _EARLY_LOSS_COOLDOWN_H:
                    log.info(
                        "[EarlyLossCooldown] BLOCKED %s — EARLY_LOSS exit %.1fh ago "
                        "(cooldown=%.0fh). Suppressing re-entry on losing setup.",
                        signal.symbol.strip(), _gap_h, _EARLY_LOSS_COOLDOWN_H,
                    )
                    return None

        # ── Late-day entry control (institutional rule) ───────────────────────
        # Before 13:30         → normal (6.5 floor enforced by DecisionEngine)
        # 13:30 – 14:30        → minimum score 7.0 required (higher conviction)
        # After  14:30         → no fresh entries; monitoring / exits only
        # Exempt: same-symbol swap replacements (position management, not fresh entry)
        if not _is_same_symbol_swap:
            _now = datetime.now()
            _cutoff  = _now.replace(hour=_LATE_ENTRY_CUTOFF_H,   minute=_LATE_ENTRY_CUTOFF_M,   second=0, microsecond=0)
            _elevated = _now.replace(hour=_LATE_ENTRY_ELEVATED_H, minute=_LATE_ENTRY_ELEVATED_M, second=0, microsecond=0)
            if _now >= _cutoff:
                log.info(
                    "[LateEntryBlock] %s rejected — no fresh entries after %02d:%02d "
                    "(current: %s, monitoring-only window).",
                    signal.symbol,
                    _LATE_ENTRY_CUTOFF_H, _LATE_ENTRY_CUTOFF_M,
                    _now.strftime("%H:%M"),
                )
                return None
            if _now >= _elevated and _new_score < _LATE_ENTRY_MIN_SCORE:
                log.info(
                    "[LateEntryBlock] %s rejected — score %.2f < %.1f required after "
                    "%02d:%02d (elevated-conviction window, 13:30–14:30).",
                    signal.symbol, _new_score, _LATE_ENTRY_MIN_SCORE,
                    _LATE_ENTRY_ELEVATED_H, _LATE_ENTRY_ELEVATED_M,
                )
                return None
        # ─────────────────────────────────────────────────────────────────────

        qty = int(signal.quantity * decision.position_size_modifier)
        if qty <= 0:
            log.warning("[OrderManager] Zero quantity after modifier for %s.", signal.symbol)
            return None

        # D11-004: hard block on invalid stop_loss before any broker call
        import math as _math
        if (not signal.stop_loss or signal.stop_loss <= 0
                or not _math.isfinite(signal.stop_loss)):
            log.error(
                "[OrderManager] BLOCKED %s — invalid stop_loss=%.4f "
                "(must be a finite positive number).",
                signal.symbol, signal.stop_loss or 0,
            )
            return None

        # ── FIX 3A: Guard against exceeding capital per single trade ──
        notional_capital = qty * signal.entry_price
        trade_utilization_pct = (notional_capital / self._portfolio.capital) * 100.0 if self._portfolio.capital > 0 else 0.0
        if trade_utilization_pct > MAX_CAPITAL_PER_TRADE_PCT:
            log.warning(
                "[OrderManager] ❌ CAPITAL/TRADE GUARD: Position %s (qty=%d @ %.2f) "
                "would use %.1f%% of capital (limit: %.1f%%). Rejecting.",
                signal.symbol, qty, signal.entry_price,
                trade_utilization_pct, MAX_CAPITAL_PER_TRADE_PCT
            )
            return None

        # ── FIX 3B: Guard against exceeding total open exposure ──────
        total_open_value = sum(
            (pos.quantity * pos.avg_entry_price) 
            for pos in self._portfolio.positions.values()
        )
        new_total_exposure = total_open_value + notional_capital
        exposure_pct = (new_total_exposure / self._portfolio.capital) * 100.0 if self._portfolio.capital > 0 else 0.0
        if exposure_pct > MAX_TOTAL_OPEN_EXPOSURE_PCT:
            log.warning(
                "[OrderManager] ❌ TOTAL EXPOSURE GUARD: Adding %s (₹%.0f notional) "
                "would reach %.1f%% total exposure (limit: %.1f%%). Rejecting.",
                signal.symbol, notional_capital,
                exposure_pct, MAX_TOTAL_OPEN_EXPOSURE_PCT
            )
            return None

        _trade_type = getattr(decision, "trade_type", "FULL")

        # ── PRE-ORDER PRICE INTEGRITY GUARD ───────────────────────────
        # Blocks phantom/SIM prices before any order is placed.
        # Catches cases where the feed fallback injected a bad price
        # (e.g. ₹995 SIM for COALINDIA instead of ₹468 live) that passed
        # all upstream guards but would book a trade at a nonsensical level.
        # This is the last-resort gate before actual execution.
        try:
            from data_integrity.price_integrity_validator import get_price_validator as _get_pv
            _integrity = _get_pv().validate(signal.symbol, signal.entry_price)
            if not _integrity.ok and _integrity.classification != "NO_BAND_REGISTERED":
                log.warning(
                    "[OrderManager] ❌ PRE-ORDER PRICE GUARD: %s entry=%.2f BLOCKED — "
                    "%s: %s",
                    signal.symbol, signal.entry_price,
                    _integrity.classification, _integrity.reason,
                )
                return None
        except Exception as _pv_exc:
            log.debug("[OrderManager] Pre-order price guard skipped: %s", _pv_exc)
        # ─────────────────────────────────────────────────────────────

        log.info("[OrderManager] ➡  Executing LIMIT %s %s qty=%d  signal=%.2f  "
                 "trade_type=%s  zone=%.2f  SL=%.2f  TGT=%.2f",
                 signal.direction.value, signal.symbol,
                 qty, signal.entry_price, _trade_type,
                 self._calc_entry_zone_price(
                     signal.entry_price, signal.direction.value,
                     float((signal_context or {}).get("vix", 0.0)),
                     atr=getattr(signal, 'atr', 0.0),
                     zone_low=getattr(signal, 'entry_zone_low', 0.0),
                     zone_high=getattr(signal, 'entry_zone_high', 0.0),
                 ),
                 signal.stop_loss, signal.target_price)

        # ── Place entry order (with retry) ──────────────────────────────
        _vix_ctx   = float((signal_context or {}).get("vix", 0.0))
        _regime_ctx = str((signal_context or {}).get("regime", ""))
        _conf_ctx  = float(getattr(decision, "confidence_score", 5.0))

        # Compute entry zone price using ATR bounds (entry ± ATR×0.10)
        _zone_px   = self._calc_entry_zone_price(
            signal.entry_price, signal.direction.value, _vix_ctx,
            atr=getattr(signal, 'atr', 0.0),
            zone_low=getattr(signal, 'entry_zone_low', 0.0),
            zone_high=getattr(signal, 'entry_zone_high', 0.0),
        )

        # Adaptive Entry Timing: choose mode, then adjust price
        _aet_mode  = self._determine_aet_mode(
            _vix_ctx, _regime_ctx,
            distortion_active=bool((signal_context or {}).get("distortion", False)),
        )
        _final_px  = self._apply_aet_price(_zone_px, signal.direction.value, _aet_mode)

        # Paper mode: always execute immediately — AET deferral is only meaningful
        # in live trading where order routing timing matters.
        if self._paper_mode:
            _aet_mode = AdaptiveTimingMode.IMMEDIATE
            log.debug("[OrderManager] Paper mode: AET forced to IMMEDIATE.")

        # CONFIRMATION mode: defer placement to next cycle(s)
        if _aet_mode == AdaptiveTimingMode.CONFIRMATION:
            _slot_id = f"AET_{signal.symbol}_{int(datetime.now().timestamp())}"
            log.info(
                "[OrderManager] ⏳ AET=CONFIRMATION: %s %s deferred — "
                "VIX=%.1f ≥ %.1f.  Slot=%s  max_wait=%d candles.",
                signal.direction.value, signal.symbol,
                _vix_ctx, AET_VIX_CONFIRM_THRESHOLD,
                _slot_id, AET_MAX_WAIT_CANDLES,
            )
            self._aet_pending[_slot_id] = AetPendingSlot(
                slot_id       = _slot_id,
                signal        = signal,
                decision      = decision,
                qty           = qty,
                zone_price    = _zone_px,   # use plain zone_price when confirmed
                signal_regime = _regime_ctx,
                signal_vix    = _vix_ctx,
                created_at    = datetime.now(),
                max_wait      = AET_MAX_WAIT_CANDLES,
            )
            return None   # order will be placed by attempt_aet_confirmations()

        order_id = self._place_entry_with_retry(signal, qty, zone_price=_final_px)
        if not order_id:
            log.error("[OrderManager] ❌ Entry order failed after %d attempts for %s — "
                      "signal discarded.", MAX_ORDER_RETRIES, signal.symbol)
            return None

        # ── Place stop-loss order ──────────────────────────────────────
        sl_id = self._place_stop_loss(signal, qty, order_id)

        # ── Record & update portfolio ──────────────────────────────────
        _ctx = signal_context or {}
        record = OrderRecord(
            order_id          = order_id,
            symbol            = signal.symbol,
            direction         = signal.direction.value,
            quantity          = qty,
            entry_price       = signal.entry_price,   # signal price; used for PnL
            stop_loss         = signal.stop_loss,
            target            = signal.target_price,
            strategy          = signal.strategy_name,
            sl_order_id       = sl_id or "",
            order_type        = "LIMIT",
            placed_at         = datetime.now(),
            zone_price        = _final_px,             # actual broker limit price
            aet_mode          = _aet_mode.value,
            signal_regime     = str(_ctx.get("regime", "")),
            signal_vix        = float(_ctx.get("vix", 0.0)),
            signal_distortion = bool(_ctx.get("distortion", False)),
            confidence_score  = float(getattr(decision, "confidence_score", 5.0)),
            initial_stop_loss = signal.stop_loss,   # immutable — never overwrite
            broker_order_id   = order_id,
            requested_price   = signal.entry_price,
            opportunity_id    = getattr(signal, "opportunity_id", "") or "",
        )
        # Reconcile fill immediately after placement (live: queries broker, paper/sim: marks synthetic)
        self._reconcile_fill(record)
        # If broker REJECTED this order, do not create a phantom open position
        if record.fill_status == "REJECTED":
            log.warning(
                "[OrderManager] Order %s REJECTED by broker — "
                "position NOT registered. No phantom position created.",
                order_id,
            )
            return None
        # D-011: Write to live journal BEFORE registering in local state.
        # If process crashes between journal write and _orders update, restart
        # recovers correctly via _restore_from_live_journal.
        if not self._paper_mode:
            self._append_live_journal("OPEN", record)
        with self._orders_lock:
            self._orders[order_id] = record
        # D-013: Use record.quantity (updated by _reconcile_fill for partial fills)
        # rather than original qty variable which reflects the requested quantity.
        self._update_portfolio(signal, record.quantity)
        # D11-001: notify RiskGuardian that a new trade is open
        if self._risk_guardian is not None:
            try:
                self._risk_guardian.record_open_trade()
            except Exception as _rg_exc:
                log.debug("[OrderManager] record_open_trade failed: %s", _rg_exc)

        # Phase 7 — [ReEntryAudit]: telemetry-only check (does NOT block the order)
        _prev = _RECENT_CLOSE_TIMES.get(signal.symbol)
        if _prev is not None:
            _gap_s = (datetime.now() - _prev["time"]).total_seconds()
            _same_dir = (record.direction == _prev["direction"])
            _event = {
                "symbol":        signal.symbol,
                "previous_exit": _prev["time"].isoformat(),
                "new_entry":     datetime.now().isoformat(),
                "gap_seconds":   round(_gap_s, 1),
                "same_direction": _same_dir,
                "previous_r":    _prev["r"],
            }
            _REENTRY_AUDIT_LOG.append(_event)
            log.info(
                "[ReEntryAudit] symbol=%s previous_exit=%s new_entry=%s "
                "gap_seconds=%.0f same_direction=%s previous_r=%+.3f",
                signal.symbol, _prev["time"].isoformat(),
                datetime.now().isoformat(),
                _gap_s, _same_dir, _prev["r"],
            )

        log.info("[OrderManager] ✅ Order %s registered (AET=%s).",
                 order_id, _aet_mode.value)
        if self._paper_mode:
            self._journal_write(
                order_id=order_id, signal=signal, qty=qty, event="OPEN"
            )
        try:
            from notifications.notifier_manager import get_notifier
            _mode = "paper" if self._paper_mode else "live"
            if self._paper_mode:
                # In paper mode, check if LTP (signal.entry_price = scanner LTP
                # at scan time) already satisfies the LIMIT fill condition.
                # BUY LIMIT fills when LTP <= zone_price.
                # SELL LIMIT fills when LTP >= zone_price.
                _ltp_now = signal.entry_price
                _is_long = signal.direction == SignalDirection.BUY
                _already_fillable = (
                    (_is_long  and _ltp_now <= _final_px) or
                    (not _is_long and _ltp_now >= _final_px)
                )
                if _already_fillable:
                    # Price already satisfies the limit — confirm fill immediately.
                    record.order_type = "MARKET"   # downgrade so monitor skips fill check
                    log.info(
                        "[OrderManager] ⚡ Immediate fill: %s LTP=%.2f already "
                        "satisfies limit=%.2f",
                        signal.symbol, _ltp_now, _final_px,
                    )
                    get_notifier().trade_opened(
                        symbol=signal.symbol, direction=signal.direction.value,
                        entry=_final_px, stop=signal.stop_loss,
                        target=signal.target_price, strategy=signal.strategy_name,
                        mode=_mode,
                    )
                else:
                    # Price not yet at limit — send pending notification.
                    get_notifier().limit_order_placed(
                        symbol=signal.symbol, direction=signal.direction.value,
                        entry=_final_px, stop=signal.stop_loss,
                        target=signal.target_price, strategy=signal.strategy_name,
                        mode=_mode,
                    )
            else:
                get_notifier().trade_opened(
                    symbol=signal.symbol, direction=signal.direction.value,
                    entry=signal.entry_price, stop=signal.stop_loss,
                    target=signal.target_price, strategy=signal.strategy_name,
                    mode=_mode,
                )
        except Exception:
            pass
        return record

    def close_position(self, order_id: str,
                        exit_price: float,
                        reason: str = "manual") -> bool:
        rec = self._orders.get(order_id)
        if not rec or rec.status != "open":
            return False

        # Phase 3 — integrity check before any computation
        if rec.initial_stop_loss <= 0:
            log.warning(
                "[RiskIntegrityViolation] symbol=%s order_id=%s "
                "initial_stop_loss=%s stop_loss=%s entry=%.4f "
                "— R-multiple cannot be computed for this trade",
                rec.symbol, order_id, rec.initial_stop_loss,
                rec.stop_loss, rec.entry_price,
            )

        # Reverse direction to close — use MARKET so exits always fill immediately
        close_dir = "SELL" if rec.direction == "BUY" else "BUY"
        _exit_order_id = self._broker_place(rec.symbol, close_dir, rec.quantity, exit_price,
                                            order_type="MARKET")
        # D-001: If live broker rejected the exit order, do NOT mark closed — position
        # stays open in local state so TradeMonitor will retry on the next cycle.
        if not self._paper_mode and _exit_order_id is None:
            log.error(
                "[OrderManager] ❌ EXIT ORDER FAILED for %s order_id=%s — "
                "broker returned None. Position remains OPEN. "
                "TradeMonitor will retry on next cycle.",
                rec.symbol, order_id,
            )
            try:
                from notifications.notifier_manager import get_notifier
                get_notifier().send_alert(
                    f"⚠️ <b>[ExitFailed]</b> Could not send exit order for "
                    f"<b>{rec.symbol}</b> ({order_id}). Position still OPEN at broker. "
                    f"Manual intervention may be required."
                )
            except Exception:
                pass
            return False

        # Use actual fill price (from broker reconciliation) when available for P&L accuracy
        _entry_for_pnl = rec.actual_fill_price if rec.actual_fill_price > 0 else rec.entry_price
        pnl = (exit_price - _entry_for_pnl) * rec.quantity
        if rec.direction in ("SELL", "SHORT"):
            pnl = -pnl

        # Deduct real transaction costs (brokerage, STT, exchange charges, GST)
        try:
            from models.transaction_costs import get_cost_model, InstrumentType
            _cost = get_cost_model().compute(
                symbol=rec.symbol,
                quantity=abs(rec.quantity),
                entry_price=rec.entry_price,
                exit_price=exit_price,
                instrument_type=InstrumentType.EQUITY_INTRADAY,
            )
            pnl -= _cost.total_cost
            log.debug("[OrderManager] TxnCost %s: ₹%.0f  NetPnL=₹%+.0f",
                      rec.symbol, _cost.total_cost, pnl)
        except Exception:
            pass

        rec.status       = "closed"
        rec.pnl          = round(pnl, 2)
        rec.closed_at    = datetime.now()
        rec.close_reason = reason          # stamp exit reason for downstream classification
        self._portfolio.realised_pnl += pnl

        # Phase 7 — record close for [ReEntryAudit] at next order creation
        _isl  = rec.initial_stop_loss if rec.initial_stop_loss > 0 else rec.stop_loss
        _risk = abs(rec.entry_price - _isl) * rec.quantity
        _r    = round(pnl / _risk, 3) if _risk > 0 else 0.0
        _RECENT_CLOSE_TIMES[rec.symbol.strip()] = {
            "time":      rec.closed_at,
            "r":         _r,
            "direction": rec.direction,
            "reason":    reason,   # canonical exit reason (EARLY_LOSS, STOP_HIT, etc.)
        }

        log.info("[OrderManager] Position closed: %s | PnL=₹%+.0f | Reason=%s",
                 rec.symbol, pnl, reason)
        # Deregister from TradeMonitor when this close is driven by smart-swap
        # (REPLACEMENT).  Without this, TradeMonitor keeps the order in its
        # _open_orders dict and produces phantom SL/target hits on dead positions,
        # polluting analytics with impossible R values (e.g. -25R).
        if reason == "REPLACEMENT" and self._trade_monitor is not None:
            try:
                self._trade_monitor.deregister(order_id)
            except Exception as _tm_exc:
                log.debug("[OrderManager] TradeMonitor deregister failed: %s", _tm_exc)
        if self._paper_mode:
            self._journal_write_close(rec, exit_price, reason)
            # Belt-and-suspenders: append to closed-order registry so that
            # _restore_from_journal can filter out ghost OPEN rows even if
            # the main CSV write was interrupted.
            try:
                with self._journal_lock:
                    with open(_closed_registry_path(), "a", encoding="utf-8") as rf:
                        rf.write(rec.order_id + "\n")
                        rf.flush()
                        os.fsync(rf.fileno())
            except Exception as rf_exc:
                log.debug("[OrderManager] Closed-registry write failed: %s", rf_exc)
        else:
            # Live mode: append CLOSE to live journal for restart recovery
            self._append_live_journal(
                "CLOSE", rec,
                extra={"exit_price": exit_price, "pnl": pnl, "reason": reason},
            )
        try:
            from notifications.notifier_manager import get_notifier
            _r_risk = abs(rec.entry_price - rec.stop_loss)
            _r_mult = (pnl / rec.quantity / _r_risk) if _r_risk > 0 and rec.quantity > 0 else 0.0
            _mode = "paper" if self._paper_mode else "live"
            get_notifier().trade_closed(
                symbol=rec.symbol, pnl=pnl, r_multiple=_r_mult,
                strategy=rec.strategy, mode=_mode,
            )
        except Exception:
            pass
        # ── Publish POSITION_CLOSED to EventBus (shadow-safe, fire-and-forget) ──
        try:
            from communication.event_bus import get_bus as _get_bus
            from communication.events import EventType as _ET, SystemEvent as _SE
            _pnl_pct = 0.0
            if rec.entry_price > 0 and rec.quantity > 0:
                _pnl_pct = round(pnl / (rec.entry_price * rec.quantity) * 100.0, 4)
            _get_bus().publish(_SE(
                event_type=_ET.POSITION_CLOSED,
                source_agent="OrderManager",
                payload={
                    "order_id":    rec.order_id,
                    "symbol":      rec.symbol,
                    "direction":   rec.direction,
                    "entry_price": rec.entry_price,
                    "exit_price":  exit_price,
                    "quantity":    rec.quantity,
                    "pnl":         round(pnl, 2),
                    "pnl_pct":     _pnl_pct,
                    "strategy":    rec.strategy,
                    "close_reason": reason,
                },
            ))
        except Exception:
            pass
        # ── K-002: exit analytics record (research-only, non-fatal) ──────────
        try:
            from learning_system.exit_analytics import record_exit
            record_exit(rec, exit_price=exit_price, pnl=pnl, reason=reason)
        except Exception:
            pass
        # D11-001: wire record_trade_result() exactly once per confirmed close.
        # Guard with _rg_recorded_oids to prevent double-counting on retry paths.
        # Use getattr for safety when OrderManager is constructed via __new__ in tests.
        _rg = getattr(self, "_risk_guardian", None)
        _rg_oids = getattr(self, "_rg_recorded_oids", None)
        if _rg is not None and (_rg_oids is None or order_id not in _rg_oids):
            try:
                if _rg_oids is not None:
                    _rg_oids.add(order_id)
                _rg.record_trade_result(pnl, pnl >= 0)
                _rg.record_closed_trade()
            except Exception as _rg_exc:
                log.error("[OrderManager] record_trade_result failed for %s: %s", order_id, _rg_exc)
        return True

    def close_all_positions(self):
        log.warning("[OrderManager] ⚠ Closing ALL positions.")
        for oid, rec in list(self._orders.items()):
            if rec.status == "open":
                # Exit price hierarchy (safest first):
                #   Priority 1 — LTPGuard-validated LTP from portfolio sync
                #                (has_live_ltp=True only after LTPGuard accepted it)
                #   Priority 2 — equity-scanner cache (independent of feed pipeline)
                #   Priority 3 — entry price (₹0 P&L fallback — never a corrupt price)
                _pos      = self._portfolio.positions.get(rec.symbol)
                _exit_px  = rec.entry_price  # Priority 3 fallback

                if _pos is not None and getattr(_pos, "has_live_ltp", False) and _pos.ltp > 0:
                    # Priority 1: portfolio LTP (already validated by LTPGuard in _do_monitor)
                    _exit_px = _pos.ltp
                    log.debug("[OrderManager] emergency_close %s: using validated LTP %.2f",
                              rec.symbol, _exit_px)
                else:
                    # Priority 2: equity-scanner cache as independent source
                    try:
                        from trade_monitoring.trade_monitor import TradeMonitor as _TM
                        _cache = _TM._fetch_from_scanner_cache(rec.symbol)
                        if _cache and _cache > 0:
                            _exit_px = _cache
                            log.debug("[OrderManager] emergency_close %s: using scanner cache %.2f",
                                      rec.symbol, _exit_px)
                        else:
                            log.debug("[OrderManager] emergency_close %s: no validated LTP — "
                                      "using entry %.2f", rec.symbol, _exit_px)
                    except Exception:
                        log.debug("[OrderManager] emergency_close %s: no validated LTP — "
                                  "using entry %.2f", rec.symbol, _exit_px)

                # Distinguish positions that were never monitored this session
                # (has_live_ltp=False, exit falls back to entry_price).
                # ORPHAN_CLOSE is excluded from EOD learning (see _do_eod_learning
                # _skip_reasons) so these synthetic zero-PnL rows never pollute
                # Win Rate / Expectancy / Sharpe calculations.
                _was_monitored = _pos is not None and getattr(_pos, "has_live_ltp", False)
                _close_reason  = "emergency_close" if _was_monitored else "ORPHAN_CLOSE"
                if not self.close_position(oid, _exit_px, reason=_close_reason):
                    log.warning(
                        "[OrderManager] Limit expiry close failed for %s %s — "
                        "position remains open. Will retry next cycle.",
                        rec.symbol, oid,
                    )

    def get_portfolio(self) -> Portfolio:
        return self._portfolio

    def get_open_orders(self) -> List[OrderRecord]:
        # D11-003: snapshot under lock to prevent RuntimeError during concurrent write
        with self._orders_lock:
            return [r for r in list(self._orders.values()) if r.status == "open"]

    def get_open_order_ids(self) -> frozenset:
        """Return frozenset of all open order_ids currently tracked in memory.
        Used by CycleHealthMonitor to distinguish carries from CSV orphans."""
        # D11-003: snapshot under lock to prevent RuntimeError during concurrent write
        with self._orders_lock:
            return frozenset(
                oid for oid, rec in list(self._orders.items()) if rec.status == "open"
            )

    def get_restore_stats(self) -> Dict[str, Any]:
        """Return restore diagnostics captured at startup by _restore_from_journal().
        Fields: restored_today, restored_carry, expired_at_restore,
                orphan_monitored_count, monitoring_gap_seconds,
                reconciled_count, immediate_sl_hits, immediate_expiries.
        Values are 0 before first restore completes or when PAPER_TRADING is False."""
        return dict(self._restore_stats)

    def get_reentry_summary(self) -> List[dict]:
        """Return the list of [ReEntryAudit] events accumulated this session.
        Used by _do_eod_learning() to emit [ReEntrySummary]. Telemetry only."""
        return list(_REENTRY_AUDIT_LOG)

    def update_restore_stats(self, **kwargs) -> None:
        """Allow orchestrator to populate post-restore governance fields."""
        self._restore_stats.update(kwargs)

    def reconcile_partial_fills(self) -> List[str]:
        """ARCH-004 LIVE-008 / ARCH-006: check open live orders for partial fills.
        In paper mode: no-op (all simulated fills are full).
        In live mode: queries broker for each open LIMIT order and adjusts
        quantity if the broker reports a partial fill.
        Also cancels the original SL (placed for requested qty) and resubmits
        it for the actual filled qty to prevent quantity mismatch on exchange.
        Returns list of order_ids that were updated.
        Safe to call every monitoring cycle.
        """
        if self._paper_mode or not self._broker:
            return []
        if not hasattr(self._broker, "get_order_status"):
            return []
        updated: List[str] = []
        for oid, rec in list(self._orders.items()):
            if rec.status != "open" or rec.order_type != "LIMIT":
                continue
            try:
                status = self._broker.get_order_status(oid)
                filled = int(status.get("filled_qty", 0) or 0)
                if filled <= 0 or filled >= rec.quantity:
                    continue
                old_qty = rec.quantity
                rec.quantity = filled
                log.warning(
                    "[PartialFill] %s %s order=%s filled=%d/%d — "
                    "adjusting record quantity and resubmitting SL.",
                    rec.symbol, rec.direction, oid, filled, old_qty,
                )
                # Cancel stale SL (placed for old_qty) and resubmit for filled qty.
                if rec.sl_order_id and hasattr(self._broker, "cancel_order"):
                    try:
                        self._broker.cancel_order(rec.sl_order_id)
                        log.info(
                            "[PartialFill] Cancelled stale SL %s (was qty=%d).",
                            rec.sl_order_id, old_qty,
                        )
                    except Exception as _cancel_exc:
                        log.warning(
                            "[PartialFill] SL cancel failed for %s: %s",
                            rec.sl_order_id, _cancel_exc,
                        )
                if hasattr(self._broker, "place_sl_order") and rec.stop_loss > 0:
                    close_dir = "SELL" if rec.direction == "BUY" else "BUY"
                    new_sl_id = self._broker.place_sl_order(
                        symbol           = rec.symbol,
                        exchange         = "NSE",
                        transaction_type = close_dir,
                        quantity         = filled,
                        trigger_price    = rec.stop_loss,
                        price            = round(rec.stop_loss * 0.995, 2),
                    )
                    rec.sl_order_id = new_sl_id or ""
                    log.info(
                        "[PartialFill] New SL %s placed for %s qty=%d trigger=%.2f.",
                        new_sl_id, rec.symbol, filled, rec.stop_loss,
                    )
                updated.append(oid)
            except Exception as exc:
                log.debug("[PartialFill] status check failed %s: %s", oid, exc)
        return updated

    def reconcile_pending_orders(self) -> List[str]:
        """D11-005: Re-query broker for any intraday orders still in PENDING/UNRESOLVED state.
        Called once per monitoring cycle so limit orders resolve without waiting for restart.
        Safe to call frequently — skips paper mode and resolved orders.
        Returns list of order_ids whose fill_status changed this cycle.
        """
        if self._paper_mode or not self._broker:
            return []
        if not hasattr(self._broker, "get_fill_details"):
            return []
        updated: List[str] = []
        for oid, rec in list(self._orders.items()):
            if rec.status != "open":
                continue
            if rec.fill_status not in ("PENDING", "UNRESOLVED", "API_ERROR", "UNKNOWN"):
                continue
            if oid.startswith("SIM_"):
                continue
            prev_status = rec.fill_status
            self._reconcile_fill(rec)
            if rec.fill_status != prev_status:
                log.info(
                    "[PendingReconcile] %s %s: %s → %s  fill_price=%.2f  qty=%d",
                    rec.symbol, oid, prev_status, rec.fill_status,
                    rec.actual_fill_price, rec.filled_quantity,
                )
                updated.append(oid)
                # If now REJECTED or CANCELLED: remove phantom position
                if rec.fill_status in ("REJECTED", "CANCELLED"):
                    with self._orders_lock:
                        self._orders.pop(oid, None)
                    self._portfolio.positions.pop(rec.symbol, None)
                    log.warning(
                        "[PendingReconcile] %s %s resolved as %s — "
                        "phantom position removed.",
                        rec.symbol, oid, rec.fill_status,
                    )
        return updated

    def attempt_aet_confirmations(
        self,
        current_vix:       float = 0.0,
        current_regime:    str   = "",
        distortion_active: bool  = False,
    ) -> List[OrderRecord]:
        """
        Scan deferred CONFIRMATION slots and place orders for any whose
        market context has now normalised.

        Called every cycle before new signal processing, right after
        ``attempt_all_reentries()``.

        A slot is placed when ALL of:
          * VIX has dropped below AET_VIX_CONFIRM_THRESHOLD
          * No active distortion event
          * Regime is unchanged from when the signal was generated
          * Max wait candles not yet exceeded

        A slot is abandoned (removed permanently) when:
          * Max wait candles exceeded
          * Regime changed (signal invalidated)

        Returns a list of new OrderRecord objects for caller to register.
        """
        now         = datetime.now()
        new_records = []
        to_remove   = []

        for sid, slot in list(self._aet_pending.items()):

            # ── Max wait exceeded ──────────────────────────────────────
            if slot.candles_waited >= slot.max_wait:
                log.info(
                    "[OrderManager] ⏹ AET slot %s ABANDONED — max wait "
                    "%d candles reached for %s.",
                    sid, slot.max_wait, slot.signal.symbol,
                )
                to_remove.append(sid)
                continue

            # ── Regime changed (permanently invalidated) ────────────────
            if (
                current_regime
                and slot.signal_regime
                and current_regime != slot.signal_regime
            ):
                log.info(
                    "[OrderManager] 🔀 AET slot %s ABANDONED — regime "
                    "changed %s→%s (%s).",
                    sid, slot.signal_regime, current_regime, slot.signal.symbol,
                )
                to_remove.append(sid)
                continue

            # ── Confirmation conditions not yet met ──────────────────
            if distortion_active:
                log.info("[OrderManager] ⚡ AET slot %s: distortion still "
                         "active — waiting (%s).", sid, slot.signal.symbol)
                slot.candles_waited += 1
                continue

            if current_vix >= AET_VIX_CONFIRM_THRESHOLD:
                log.info(
                    "[OrderManager] 📈 AET slot %s: VIX=%.1f still ≥ %.1f — "
                    "waiting candle %d/%d (%s).",
                    sid, current_vix, AET_VIX_CONFIRM_THRESHOLD,
                    slot.candles_waited + 1, slot.max_wait, slot.signal.symbol,
                )
                slot.candles_waited += 1
                continue

            # D11-007: re-check kill-switch before deferred broker placement
            if self._risk_guardian is not None and self._risk_guardian._trading_halted:
                log.warning(
                    "[OrderManager] AET slot %s BLOCKED — RiskGuardian halt active (%s). "
                    "Slot discarded.",
                    sid, self._risk_guardian._halt_reason,
                )
                to_remove.append(sid)
                continue

            # ── All conditions met — place the order now ───────────────
            # Re-evaluate the zone at current (now-calmer) VIX for best price
            _confirmed_zone = self._calc_entry_zone_price(
                slot.signal.entry_price, slot.signal.direction.value, current_vix,
                atr=getattr(slot.signal, 'atr', 0.0),
                zone_low=getattr(slot.signal, 'entry_zone_low', 0.0),
                zone_high=getattr(slot.signal, 'entry_zone_high', 0.0),
            )

            direction = "BUY" if slot.signal.direction == SignalDirection.BUY else "SELL"
            order_id  = self._broker_place(
                slot.signal.symbol, direction, slot.qty,
                _confirmed_zone, order_type="LIMIT",
            )
            if not order_id:
                log.warning("[OrderManager] AET confirmation broker call failed "
                            "for %s — abandoning slot %s.", slot.signal.symbol, sid)
                to_remove.append(sid)
                continue

            sl_id = self._place_stop_loss(slot.signal, slot.qty, order_id)
            rec   = OrderRecord(
                order_id      = order_id,
                symbol        = slot.signal.symbol,
                direction     = direction,
                quantity      = slot.qty,
                entry_price   = slot.signal.entry_price,
                stop_loss     = slot.signal.stop_loss,
                target        = slot.signal.target_price,
                strategy      = slot.signal.strategy_name,
                sl_order_id   = sl_id or "",
                order_type    = "LIMIT",
                placed_at     = now,
                zone_price    = _confirmed_zone,
                aet_mode      = AdaptiveTimingMode.CONFIRMATION.value,
                signal_regime     = slot.signal_regime,
                signal_vix        = slot.signal_vix,
                initial_stop_loss = slot.signal.stop_loss,   # immutable
                broker_order_id   = order_id,
                requested_price   = slot.signal.entry_price,
                opportunity_id    = getattr(slot.signal, "opportunity_id", "") or "",  # D10-001
            )
            # Reconcile fill with broker before registering position
            self._reconcile_fill(rec)
            if rec.fill_status == "REJECTED":
                log.warning(
                    "[OrderManager] AET order %s REJECTED by broker — "
                    "position NOT registered for %s.",
                    order_id, slot.signal.symbol,
                )
                to_remove.append(sid)
                continue
            # D-011: journal before local state; D-013: use reconciled quantity
            if not self._paper_mode:
                self._append_live_journal("OPEN", rec)  # D-010: live journal for AET
            with self._orders_lock:
                self._orders[order_id] = rec
            self._update_portfolio(slot.signal, rec.quantity)  # D-013

            log.info(
                "[OrderManager] ✅ AET CONFIRMED: %s %s  "
                "zone=%.2f  waited=%d candles  order=%s",
                direction, slot.signal.symbol,
                _confirmed_zone, slot.candles_waited, order_id,
            )
            if self._paper_mode:
                self._journal_write_aet_confirmed(rec, slot)

            # D11-001: notify RiskGuardian of new open trade
            if self._risk_guardian is not None:
                try:
                    self._risk_guardian.record_open_trade()
                except Exception as _rg_exc:
                    log.debug("[OrderManager] AET record_open_trade failed: %s", _rg_exc)

            new_records.append(rec)
            to_remove.append(sid)

        for k in to_remove:
            self._aet_pending.pop(k, None)

        return new_records

    # ── VIX spike: cancel if VIX has risen above this absolute threshold
    # AND also risen ≥ 30% relative to the VIX when the signal was created.
    VIX_SPIKE_ABSOLUTE  = 20.0   # absolute VIX floor that triggers check
    VIX_SPIKE_RELATIVE  = 1.30   # relative multiplier (current / signal_vix)

    def check_and_expire_stale_limits(
        self,
        candle_expiry:     int   = LIMIT_CANDLE_EXPIRY,
        candle_seconds:    int   = CANDLE_SECONDS,
        current_regime:    str   = "",
        current_vix:       float = 0.0,
        distortion_active: bool  = False,
        vix_spike_threshold: float = VIX_SPIKE_ABSOLUTE,
    ) -> List[str]:
        """
        Cancel open LIMIT orders that are no longer safe to fill.

        Checks (in priority order)
        --------------------------
        1. **Time expiry**  — order older than ``candle_expiry`` candles.
        2. **Distortion event** — a market-wide shock was detected this cycle
           (central bank surprise, war escalation, etc.). All pending limits
           are cancelled regardless of how fresh they are.
        3. **Regime change** — the market-regime *class* has changed since the
           signal was created (RANGE → TREND, TREND → VOLATILE, etc.).
           Minor intra-class fluctuations within the same label are NOT
           treated as a change, so the rule is stable without being hair-
           trigger.
        4. **VIX spike** — India VIX is both above ``vix_spike_threshold``
           AND has risen by ≥ ``VIX_SPIKE_RELATIVE`` × the VIX that was
           present when the signal fired, indicating an abrupt fear event.

        Returns a list of cancelled order_ids for audit / event publishing.

        Parameters
        ----------
        candle_expiry       : candles before time-based expiry (default 3)
        candle_seconds      : seconds per candle (default 300 = 5 min)
        current_regime      : regime label string from latest MarketSnapshot
        current_vix         : latest India VIX float
        distortion_active   : True if any distortion event is active this cycle
        vix_spike_threshold : absolute VIX level that activates spike check
        """
        expiry_secs = candle_expiry * candle_seconds
        now         = datetime.now()
        cancelled   = []

        for order_id, rec in list(self._orders.items()):
            if rec.status != "open":
                continue
            if rec.order_type != "LIMIT":
                continue
            if rec.placed_at is None:
                continue

            elapsed = (now - rec.placed_at).total_seconds()

            # ── Determine cancel reason ────────────────────────────────
            cancel_reason: str = ""

            if elapsed >= expiry_secs:
                cancel_reason = f"limit_expired_{candle_expiry}_candles"

            elif distortion_active:
                cancel_reason = "distortion_event"

            elif (
                rec.signal_regime
                and current_regime
                and rec.signal_regime != current_regime
            ):
                cancel_reason = (
                    f"regime_changed:{rec.signal_regime}->{current_regime}"
                )

            elif (
                current_vix >= vix_spike_threshold
                and rec.signal_vix > 0.0
                and current_vix >= rec.signal_vix * self.VIX_SPIKE_RELATIVE
            ):
                cancel_reason = (
                    f"vix_spike:{rec.signal_vix:.1f}->{current_vix:.1f}"
                )

            if not cancel_reason:
                continue   # order still valid — leave it open

            # ── Cancel this limit order ────────────────────────────────
            log.warning(
                "[OrderManager] ⛔ LIMIT order CANCELLED: %s  %s  entry=%.2f  "
                "age=%.0fs  reason=%s",
                rec.symbol, rec.direction, rec.entry_price,
                elapsed, cancel_reason,
            )

            # Try to cancel at broker
            if self._broker and hasattr(self._broker, "cancel_order"):
                try:
                    self._broker.cancel_order(rec.order_id)
                    log.info("[OrderManager] Broker cancel ACK for %s.", order_id)
                except Exception as cancel_exc:
                    log.warning("[OrderManager] Broker cancel failed (%s): %s",
                                order_id, cancel_exc)
            else:
                log.info("[OrderManager] [SIM] CANCEL limit order %s (%s)",
                         order_id, rec.symbol)

            # Mark cancelled, zero PnL (order never filled in the real sense)
            rec.status    = "cancelled"
            rec.closed_at = now
            rec.pnl       = 0.0

            # Remove from portfolio so capital is freed
            self._portfolio.positions.pop(rec.symbol, None)

            # ── Register for re-entry (time-expiry only) ──────────────
            # If the signal expired purely by time and hasn't hit max
            # retries, give it a re-entry window.  Context-invalidated
            # orders (regime, distortion, VIX) are NOT eligible.
            if cancel_reason.startswith("limit_expired_"):
                self._register_reentry(rec, candle_seconds)

            # D-018: journal the cancellation in both paper and live mode
            if self._paper_mode:
                self._journal_cancel(rec, reason=cancel_reason)
            else:
                self._append_live_journal(
                    "CANCELLED", rec, extra={"reason": cancel_reason}
                )

            cancelled.append(order_id)

        if cancelled:
            log.info("[OrderManager] Expired %d stale limit order(s): %s",
                     len(cancelled), cancelled)
        return cancelled

    def attempt_all_reentries(
        self,
        current_prices:    Dict[str, float] = None,
        current_regime:    str   = "",
        current_vix:       float = 0.0,
        distortion_active: bool  = False,
        price_band_pct:    float = REENTRY_PRICE_BAND_PCT,
    ) -> List[OrderRecord]:
        """
        Scan pending re-entry slots and re-place any whose context is still
        valid, price is within band, and retry budget remains.

        Call this once per cycle, right after ``check_and_expire_stale_limits``.

        Parameters
        ----------
        current_prices    : {symbol: last_price}.  Pass ``{}`` to skip the
                            price-proximity check (useful in sim/replay).
        current_regime    : latest regime label string
        current_vix       : latest India VIX
        distortion_active : True if any distortion event is active
        price_band_pct    : ±% tolerance around entry_price

        Returns
        -------
        List of new OrderRecord objects for each successful re-entry,
        so the caller can register them with TradeMonitor / EventBus.
        """
        if current_prices is None:
            current_prices = {}

        # D11-007: re-check kill-switch before any deferred placement
        if self._risk_guardian is not None and self._risk_guardian._trading_halted:
            log.warning(
                "[OrderManager] attempt_all_reentries: skipping all slots — "
                "RiskGuardian halt active (%s).",
                self._risk_guardian._halt_reason,
            )
            return []

        now         = datetime.now()
        new_records = []
        slots_to_remove = []

        for slot_key, slot in list(self._reentry_slots.items()):

            # ── Hard deadline ─────────────────────────────────────────
            if now > slot.window_expires_at:
                log.info(
                    "[OrderManager] ⏹ Re-entry window CLOSED for %s %s @ %.2f "
                    "(retries used: %d/%d)",
                    slot.symbol, slot.direction, slot.entry_price,
                    slot.retry_count, slot.max_retries,
                )
                slots_to_remove.append(slot_key)
                continue

            # ── Retry budget ──────────────────────────────────────────
            if slot.retry_count >= slot.max_retries:
                log.info(
                    "[OrderManager] ⛔ Re-entry budget exhausted for %s (max %d).",
                    slot.symbol, slot.max_retries,
                )
                slots_to_remove.append(slot_key)
                continue

            # ── Context guards ────────────────────────────────────────
            if distortion_active:
                log.info("[OrderManager] ⚡ Re-entry blocked — distortion active (%s).",
                         slot.symbol)
                continue   # check again next cycle

            if (
                current_regime
                and slot.signal_regime
                and current_regime != slot.signal_regime
            ):
                log.info(
                    "[OrderManager] 🔀 Re-entry blocked — regime changed "
                    "%s→%s (%s).",
                    slot.signal_regime, current_regime, slot.symbol,
                )
                slots_to_remove.append(slot_key)   # permanently invalid
                continue

            if (
                current_vix >= self.VIX_SPIKE_ABSOLUTE
                and slot.signal_vix > 0.0
                and current_vix >= slot.signal_vix * self.VIX_SPIKE_RELATIVE
            ):
                log.info("[OrderManager] 📈 Re-entry blocked — VIX spike (%s).",
                         slot.symbol)
                continue   # check again next cycle

            # ── Stale-signal guard ────────────────────────────────────
            # If price has drifted >1.5% from the original signal entry,
            # the setup thesis is invalidated — permanently drop the slot.
            if slot.symbol in current_prices:
                ltp = current_prices[slot.symbol]
                drift_pct = abs(ltp - slot.entry_price) / slot.entry_price * 100.0
                if drift_pct > 1.5:
                    log.info(
                        "[OrderManager] ⏭ Re-entry DROPPED — %s price %.2f "
                        "drifted %.1f%% from signal entry %.2f (stale signal).",
                        slot.symbol, ltp, drift_pct, slot.entry_price,
                    )
                    slots_to_remove.append(slot_key)
                    continue

            # ── Price proximity check (optional) ──────────────────────
            if price_band_pct > 0.0 and slot.symbol in current_prices:
                ltp = current_prices[slot.symbol]
                band = slot.entry_price * price_band_pct / 100.0
                if abs(ltp - slot.entry_price) > band:
                    log.debug(
                        "[OrderManager] 📍 Re-entry deferred — %s price %.2f "
                        "outside band %.2f ± %.2f.",
                        slot.symbol, ltp, slot.entry_price, band,
                    )
                    continue   # wait for price to come back

            # ── All checks passed — re-place the limit order ──────────
            _reentry_zone_px = self._calc_entry_zone_price(
                slot.entry_price, slot.direction, slot.signal_vix)
            new_oid = self._broker_place(
                slot.symbol, slot.direction, slot.quantity,
                _reentry_zone_px, order_type="LIMIT",
            )
            if not new_oid:
                log.warning("[OrderManager] Re-entry broker call failed for %s.",
                            slot.symbol)
                continue

            rec = OrderRecord(
                order_id      = new_oid,
                symbol        = slot.symbol,
                direction     = slot.direction,
                quantity      = slot.quantity,
                entry_price   = slot.entry_price,     # signal price (for PnL)
                stop_loss     = slot.stop_loss,
                target        = slot.target,
                strategy      = slot.strategy,
                order_type    = "LIMIT",
                placed_at     = now,
                zone_price    = _reentry_zone_px,     # actual broker limit price
                signal_regime     = slot.signal_regime,
                signal_vix        = slot.signal_vix,
                initial_stop_loss = slot.stop_loss,   # immutable
                opportunity_id    = slot.opportunity_id,  # D10-002: propagated
            )
            # D11-002: reconcile fill before registering — same lifecycle as execute()
            self._reconcile_fill(rec)
            if rec.fill_status == "REJECTED":
                log.warning(
                    "[OrderManager] Reentry %s REJECTED by broker — "
                    "position NOT registered. Slot retry budget consumed.",
                    new_oid,
                )
                slot.retry_count += 1
                continue
            # D-011: journal before local state; D-010: live mode journal write
            if not self._paper_mode:
                self._append_live_journal("OPEN", rec)
            with self._orders_lock:
                self._orders[new_oid] = rec

            # Re-add to portfolio
            pos = Position(
                symbol          = slot.symbol,
                quantity        = slot.quantity if slot.direction == "BUY" else -slot.quantity,
                avg_entry_price = slot.entry_price,
                ltp             = slot.entry_price,
                stop_loss       = slot.stop_loss,
                target_price    = slot.target,
                strategy_name   = slot.strategy,
            )
            self._portfolio.positions[slot.symbol] = pos

            slot.retry_count += 1
            log.info(
                "[OrderManager] 🔁 Re-entry %d/%d placed: %s %s  signal=%.2f  zone=%.2f  "
                "new_order_id=%s  window_left=%.0fs",
                slot.retry_count, slot.max_retries,
                slot.symbol, slot.direction,
                slot.entry_price, _reentry_zone_px,
                new_oid, (slot.window_expires_at - now).total_seconds(),
            )

            if self._paper_mode:
                self._journal_write_reentry(rec, slot)

            # D11-001: notify RiskGuardian of new open trade
            if self._risk_guardian is not None:
                try:
                    self._risk_guardian.record_open_trade()
                except Exception as _rg_exc:
                    log.debug("[OrderManager] reentry record_open_trade failed: %s", _rg_exc)

            new_records.append(rec)

        # Clean up exhausted/expired/permanently-invalid slots
        for k in slots_to_remove:
            self._reentry_slots.pop(k, None)

        return new_records

    # ─────────────────────────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────────────────────────

    def _calc_entry_zone_price(
        self,
        signal_price: float,
        direction:    str,
        vix:          float = 0.0,
        atr:          float = 0.0,
        zone_low:     float = 0.0,
        zone_high:    float = 0.0,
    ) -> float:
        """
        Return the zone-adjusted limit price for a BUY or SELL entry.

        Zone width hierarchy (first match wins):
          1. Precomputed zone bounds (entry_zone_low / entry_zone_high from signal):
             BUY  → entry_zone_high  (signal_price + ATR×0.10) — fills within zone
             SELL/SHORT → entry_zone_low (signal_price − ATR×0.10)
          2. ATR-based fallback: zone_pct = (atr / price) × ATR_ZONE_MULTIPLIER × 100
          3. VIX-scaled fallback: zone_pct = ZONE_BASE_PCT × vix_factor

        ``entry_price`` on OrderRecord always retains the original signal price
        so that PnL calculations remain correct.
        """
        is_buy = direction.upper() in ("BUY", "LONG")

        # Priority 1: use precomputed ATR zone bounds from the signal
        if is_buy and zone_high > 0.0:
            return round(zone_high, 2)
        if not is_buy and zone_low > 0.0:
            return round(zone_low, 2)

        # Priority 2: compute from raw ATR (ATR_ZONE_MULTIPLIER = 0.10)
        if atr > 0.0 and signal_price > 0.0:
            zone_offset = atr * ATR_ZONE_MULTIPLIER
        elif vix > 0.0:
            # Priority 3: VIX-scaled fallback
            raw_factor = vix / ZONE_VIX_NORMAL
            vix_factor = max(ZONE_VIX_MIN_FACTOR,
                             min(ZONE_VIX_MAX_FACTOR, raw_factor))
            zone_offset = signal_price * (ZONE_BASE_PCT * vix_factor / 100.0)
        else:
            zone_offset = signal_price * (ZONE_BASE_PCT / 100.0)

        if is_buy:
            return round(signal_price + zone_offset, 2)
        else:
            return round(signal_price - zone_offset, 2)

    # ------------------------------------------------------------------
    # Adaptive Entry Timing helpers
    # ------------------------------------------------------------------

    def _determine_aet_mode(
        self,
        vix:               float = 0.0,
        regime:            str   = "",
        distortion_active: bool  = False,
    ) -> "AdaptiveTimingMode":
        """
        Return the AET mode that governs how (and *when*) an ENTRY order
        is placed for the current market context.

        Priority (highest first):
          CONFIRMATION — When the environment is hostile: distortion is active
                         OR VIX has spiked above AET_VIX_CONFIRM_THRESHOLD.
                         The order is NOT placed this cycle; it waits up to
                         AET_MAX_WAIT_CANDLES for conditions to normalise.

          PULLBACK     — When directional momentum is strong (TREND / BULL
                         regime) the AI expects a micro-pullback before
                         continuation, so the limit price is nudged a fraction
                         deeper into the zone (see _apply_aet_price).

          IMMEDIATE    — All other regimes.  Place the limit order right now
                         at the zone price without adjustment.
        """
        if distortion_active or vix >= AET_VIX_CONFIRM_THRESHOLD:
            return AdaptiveTimingMode.CONFIRMATION
        if regime.upper() in ("TREND", "BULL", "BULLISH", "BULL_MARKET"):
            return AdaptiveTimingMode.PULLBACK
        return AdaptiveTimingMode.IMMEDIATE

    def _apply_aet_price(
        self,
        zone_price: float,
        direction:  str,
        mode:       "AdaptiveTimingMode",
    ) -> float:
        """
        Adjust *zone_price* based on the chosen AET mode.

        IMMEDIATE    → zone_price unchanged.
        PULLBACK     → shift the limit price AET_PULLBACK_DIP_PCT% deeper:
                         BUY  → limit × (1 − dip%)   [cheaper entry]
                         SELL → limit × (1 + dip%)   [higher entry]
        CONFIRMATION → not called for this mode (order is deferred); returns
                       zone_price unchanged as a safety fall-through.
        """
        if mode == AdaptiveTimingMode.PULLBACK:
            dip = AET_PULLBACK_DIP_PCT / 100.0
            if direction.upper() in ("BUY", "LONG"):
                return round(zone_price * (1.0 - dip), 2)
            else:
                return round(zone_price * (1.0 + dip), 2)
        return zone_price   # IMMEDIATE or CONFIRMATION

    def _journal_write_aet_confirmed(
        self,
        rec:  "OrderRecord",
        slot: "AetPendingSlot",
    ) -> None:
        """Append an AET_CONFIRMED_OPEN row to the paper trades CSV."""
        try:
            with open(self._journal_path, "a", newline="", encoding="utf-8") as fh:
                import csv
                writer = csv.writer(fh)
                writer.writerow([
                    rec.placed_at.isoformat(),
                    "AET_CONFIRMED_OPEN",
                    rec.order_id,
                    rec.symbol,
                    rec.direction,
                    rec.quantity,
                    rec.zone_price,
                    rec.entry_price,
                    rec.stop_loss,
                    rec.target,
                    rec.strategy,
                    rec.signal_regime,
                    f"vix={rec.signal_vix:.1f}",
                    f"waited={slot.candles_waited}",
                ])
        except Exception as exc:   # noqa: BLE001
            log.warning("[OrderManager] journal_write_aet_confirmed failed: %s", exc)

    def _register_reentry(        self,
        rec:           OrderRecord,
        candle_seconds: int = CANDLE_SECONDS,
        window_candles: int = REENTRY_WINDOW_CANDLES,
    ) -> None:
        """
        Create a ReentrySlot for an order that was cancelled by time-expiry.
        The slot window starts from ``rec.placed_at`` so the 10-candle count
        begins at when the signal was originally issued, not the cancel time.
        """
        if rec.order_id in self._reentry_slots:
            return   # already registered

        from datetime import timedelta
        base_time     = rec.placed_at or datetime.now()
        # Window measured from original placement: expiry candles + re-entry candles
        total_candles = LIMIT_CANDLE_EXPIRY + window_candles
        window_end    = base_time + timedelta(seconds=total_candles * candle_seconds)

        slot = ReentrySlot(
            original_order_id = rec.order_id,
            symbol            = rec.symbol,
            direction         = rec.direction,
            entry_price       = rec.entry_price,
            stop_loss         = rec.stop_loss,
            target            = rec.target,
            strategy          = rec.strategy,
            quantity          = rec.quantity,
            signal_regime     = rec.signal_regime,
            signal_vix        = rec.signal_vix,
            window_expires_at = window_end,
            opportunity_id    = getattr(rec, "opportunity_id", "") or "",  # D10-002
            max_retries       = REENTRY_MAX_RETRIES,
        )
        self._reentry_slots[rec.order_id] = slot
        log.info(
            "[OrderManager] 📋 Re-entry slot registered: %s %s @ %.2f  "
            "window=%d candles  max_retries=%d",
            rec.symbol, rec.direction, rec.entry_price,
            window_candles, REENTRY_MAX_RETRIES,
        )

    # ─────────────────────────────────────────────────────────────────
    # PAPER TRADE JOURNAL
    # ─────────────────────────────────────────────────────────────────

    def _journal_write(self, order_id: str, signal: TradeSignal,
                       qty: int, event: str) -> None:
        """Append an OPEN entry to the paper trade CSV journal."""
        try:
            write_header = not os.path.exists(PAPER_TRADE_LOG)
            with open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER)
                if write_header:
                    w.writeheader()
                w.writerow({
                    "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "order_id":    order_id,
                    "symbol":      signal.symbol,
                    "direction":   signal.direction.value,
                    "quantity":    qty,
                    "entry_price": round(signal.entry_price, 2),
                    "stop_loss":   round(signal.stop_loss, 2),
                    "target":      round(signal.target_price, 2),
                    "strategy":    signal.strategy_name,
                    "confidence":  round(signal.confidence, 2),
                    "rr":          round(signal.risk_reward_ratio, 2),
                    "event":       event,
                })
        except Exception as exc:
            log.warning("[OrderManager] Could not write paper trade journal: %s", exc)

    def _journal_write_close(self, rec: "OrderRecord",
                             exit_price: float, reason: str) -> None:
        """Append a CLOSE entry (with PnL) to the paper trade CSV journal."""
        try:
            with self._journal_lock:
                write_header = not os.path.exists(PAPER_TRADE_LOG)
                with open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER)
                    if write_header:
                        w.writeheader()
                    w.writerow({
                        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "order_id":    rec.order_id,
                        "symbol":      rec.symbol,
                        "direction":   rec.direction,
                        "quantity":    rec.quantity,
                        "entry_price": round(rec.entry_price, 2),
                        "stop_loss":   round(rec.stop_loss, 2),
                        "target":      round(rec.target, 2),
                        "strategy":    rec.strategy,
                        "confidence":  "",
                        "rr":          "",
                        "event":       "CLOSE",
                        "exit_price":  round(exit_price, 2),
                        "pnl":         rec.pnl,
                        "reason":      reason,
                    })
                    fh.flush()
                    os.fsync(fh.fileno())
        except Exception as exc:
            log.warning("[OrderManager] Could not write paper trade journal (close): %s", exc)

    def journal_write_extend(self, order_id: str, locked_sl: float) -> None:
        """Append an EXTEND event to the paper trade journal.

        Persists the locked stop-loss so _restore_from_journal can restore the
        correct SL (and set the extended flag) after a container restart.
        Called by TradeMonitor immediately when adaptive profit extension fires.
        """
        if not self._paper_mode:
            return
        try:
            rec = self._orders.get(order_id)
            if not rec:
                return
            with self._journal_lock:
                with open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER)
                    w.writerow({
                        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "order_id":    rec.order_id,
                        "symbol":      rec.symbol,
                        "direction":   rec.direction,
                        "quantity":    rec.quantity,
                        "entry_price": round(rec.entry_price, 2),
                        "stop_loss":   round(locked_sl, 2),  # KEY: the extension-locked SL
                        "target":      round(rec.target, 2) if rec.target else "",
                        "strategy":    rec.strategy,
                        "confidence":  "",
                        "rr":          "",
                        "event":       "EXTEND",
                    })
                    fh.flush()
                    os.fsync(fh.fileno())
        except Exception as exc:
            log.debug("[OrderManager] Could not write EXTEND journal event: %s", exc)

    def _journal_write_reentry(self, rec: "OrderRecord",
                               slot: "ReentrySlot") -> None:
        """Append a REENTRY_OPEN row to the paper trade CSV journal."""
        try:
            write_header = not os.path.exists(PAPER_TRADE_LOG)
            with open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER + ["retry_attempt"])
                if write_header:
                    w.writeheader()
                w.writerow({
                    "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "order_id":      rec.order_id,
                    "symbol":        rec.symbol,
                    "direction":     rec.direction,
                    "quantity":      rec.quantity,
                    "entry_price":   round(rec.entry_price, 2),
                    "stop_loss":     round(rec.stop_loss, 2),
                    "target":        round(rec.target, 2),
                    "strategy":      rec.strategy,
                    "confidence":    "",
                    "rr":            "",
                    "event":         "REENTRY_OPEN",
                    "exit_price":    "",
                    "pnl":           "",
                    "reason":        f"reentry_attempt_{slot.retry_count}_of_{slot.max_retries}",
                    "retry_attempt": slot.retry_count,
                })
        except Exception as exc:
            log.warning("[OrderManager] Could not write reentry journal: %s", exc)

    def _journal_cancel(self, rec: "OrderRecord",
                        reason: str = f"limit_expired_{LIMIT_CANDLE_EXPIRY}_candles") -> None:
        """Append a CANCELLED entry to the paper trade CSV journal."""
        try:
            write_header = not os.path.exists(PAPER_TRADE_LOG)
            with open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER)
                if write_header:
                    w.writeheader()
                w.writerow({
                    "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "order_id":    rec.order_id,
                    "symbol":      rec.symbol,
                    "direction":   rec.direction,
                    "quantity":    rec.quantity,
                    "entry_price": round(rec.entry_price, 2),
                    "stop_loss":   round(rec.stop_loss, 2),
                    "target":      round(rec.target, 2),
                    "strategy":    rec.strategy,
                    "confidence":  "",
                    "rr":          "",
                    "event":       "CANCELLED",
                    "exit_price":  "",
                    "pnl":         0.0,
                    "reason":      reason,
                })
        except Exception as exc:
            log.warning("[OrderManager] Could not write paper trade journal (cancel): %s", exc)

    def _load_broker(self):
        broker = ACTIVE_BROKER.lower()
        if broker == "zerodha":
            from execution_engine.brokers.zerodha_broker import ZerodhaBroker
            return ZerodhaBroker(ZERODHA_API_KEY, ZERODHA_ACCESS_TOKEN)
        elif broker == "dhan":
            from execution_engine.brokers.dhan_broker import DhanBroker
            return DhanBroker(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
        elif broker == "angelone":
            from execution_engine.brokers.angelone_broker import AngelOneBroker
            return AngelOneBroker(ANGELONE_API_KEY, ANGELONE_CLIENT_ID,
                                  ANGELONE_PASSWORD, ANGELONE_TOTP_SECRET)
        else:
            log.warning("[OrderManager] Unknown broker '%s' — simulation mode.", broker)
            return None

    def _place_entry(self, sig: TradeSignal, qty: int) -> Optional[str]:
        direction = "BUY" if sig.direction == SignalDirection.BUY else "SELL"
        return self._broker_place(sig.symbol, direction, qty, sig.entry_price)

    def _place_entry_with_retry(self, sig: TradeSignal, qty: int,
                                zone_price: Optional[float] = None) -> Optional[str]:
        """
        Attempt to place the entry order up to MAX_ORDER_RETRIES times.
        Uses exponential backoff between attempts.

        ``zone_price``
            If supplied, this is the actual limit price sent to the broker
            (entry zone-adjusted).  Falls back to ``sig.entry_price`` when
            not provided (e.g. legacy call-sites).

        Returns order_id on success, None if all attempts fail.
        """
        direction  = "BUY" if sig.direction == SignalDirection.BUY else "SELL"
        _lmt_price = zone_price if zone_price is not None else sig.entry_price
        for attempt in range(1, MAX_ORDER_RETRIES + 1):
            try:
                order_id = self._broker_place(
                    sig.symbol, direction, qty, _lmt_price)
                if order_id:
                    if attempt > 1:
                        log.info("[OrderManager] ✅ Order placed on attempt %d/%d "
                                 "for %s.", attempt, MAX_ORDER_RETRIES, sig.symbol)
                    return order_id
                log.warning("[OrderManager] Attempt %d/%d: broker returned None "
                            "for %s — retrying.",
                            attempt, MAX_ORDER_RETRIES, sig.symbol)
            except Exception as exc:
                log.error("[OrderManager] Attempt %d/%d exception for %s: %s",
                          attempt, MAX_ORDER_RETRIES, sig.symbol, exc)

            if attempt < MAX_ORDER_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))  # 0.5, 1.0, 2.0
                log.info("[OrderManager] Waiting %.1fs before retry %d/%d…",
                         delay, attempt + 1, MAX_ORDER_RETRIES)
                time.sleep(delay)

        return None

    def _place_stop_loss(self, sig: TradeSignal, qty: int,
                          entry_order_id: str) -> Optional[str]:
        close_dir = "SELL" if sig.direction == SignalDirection.BUY else "BUY"
        if not self._broker:
            log.info("[OrderManager] [SIM] SL %s %s @ %.2f",
                     close_dir, sig.symbol, sig.stop_loss)
            return f"SIM_SL_{sig.symbol}"
        if hasattr(self._broker, "place_sl_order"):
            return self._broker.place_sl_order(
                symbol=sig.symbol, exchange="NSE",
                transaction_type=close_dir, quantity=qty,
                trigger_price=sig.stop_loss,
                price=round(sig.stop_loss * 0.995, 2),
            )
        # D9-005: broker connected but lacks SL method — operator must be aware
        log.warning(
            "[OrderManager] SL placement skipped for %s — broker lacks place_sl_order(). "
            "Position will use software-only 5-minute monitoring cycle.",
            sig.symbol,
        )
        return None

    def _broker_place(self, symbol: str, direction: str,
                       qty: int, price: float,
                       order_type: str = "LIMIT") -> Optional[str]:
        if not self._broker:
            log.info("[OrderManager] [SIM-%s] %s %s qty=%d @ %.2f",
                     order_type, direction, symbol, qty, price)
            import time as _t
            _ms = _t.time_ns() // 1_000_000   # ms timestamp — guarantees uniqueness
            return f"SIM_{symbol}_{direction}_Q{qty}_P{price:.2f}_{_ms}"
        # Resolve NSE ticker → Dhan (security_id, exchange_segment) — EB001 + EB002 fix
        from data_feeds.dhan_feed import DHAN_SECURITY_MAP as _DSM
        _sym = symbol.upper().replace(".NS", "").replace(".BO", "")
        _meta = _DSM.get(_sym)
        if not _meta:
            log.error(
                "[OrderManager] [MISSING_DHAN_MAPPING] symbol=%s not in DHAN_SECURITY_MAP"
                " — order blocked. Add entry to data_feeds/dhan_feed.py.",
                symbol,
            )
            return None
        return self._broker.place_order(
            security_id      = _meta["security_id"],
            exchange_segment = _meta["segment"],
            transaction_type = direction,
            quantity         = qty,
            price            = price,
            order_type       = order_type,
        )

    def _reconcile_fill(self, rec: "OrderRecord") -> None:
        """
        Query the broker for actual fill details and update rec in place.

        Called immediately after a live order is placed.  Also called at
        startup for any order with fill_status="" (unresolved from a prior run).

        SAFETY: never raises; fill failure just leaves fill_status="UNRESOLVED".
        Paper and SIM modes record PAPER / SIM fill without a broker call.
        """
        from datetime import timezone as _tz
        _now_iso = datetime.now(_tz.utc).isoformat()
        # Paper / sim: record synthetic fill and return
        if self._paper_mode or not self._broker:
            rec.fill_status           = "PAPER" if self._paper_mode else "SIM"
            rec.actual_fill_price     = rec.entry_price  # signal price as assumed fill
            rec.requested_price       = rec.entry_price
            rec.filled_quantity       = rec.quantity
            rec.slippage_abs          = 0.0
            rec.slippage_pct          = 0.0
            rec.reconciliation_ts     = _now_iso
            rec.reconciliation_source = "PAPER" if self._paper_mode else "SIM"
            return
        # Live: query broker
        if not hasattr(self._broker, "get_fill_details"):
            rec.fill_status           = "UNRESOLVED"
            rec.reconciliation_ts     = _now_iso
            rec.reconciliation_source = "BROKER_API_UNAVAILABLE"
            return
        try:
            fill = self._broker.get_fill_details(rec.order_id)
            rec.fill_status           = fill.get("status", "UNKNOWN")
            rec.actual_fill_price     = float(fill.get("actual_fill_price") or 0.0)
            rec.requested_price       = rec.entry_price  # signal price (requested)
            rec.filled_quantity       = int(fill.get("filled_quantity") or 0)
            rec.reconciliation_ts     = _now_iso
            rec.reconciliation_source = fill.get("reconciliation_source", "DHAN_GET_ORDER_BY_ID")
            if rec.actual_fill_price > 0 and rec.requested_price > 0:
                rec.slippage_abs = rec.actual_fill_price - rec.requested_price
                rec.slippage_pct = (rec.slippage_abs / rec.requested_price) * 100.0
            # If partially filled: update quantity to actual filled qty
            if rec.fill_status == "PARTIALLY_FILLED" and rec.filled_quantity > 0:
                # D9-002: reject zero fill price — corrupted price poisons P&L and learning
                if rec.actual_fill_price <= 0:
                    log.error(
                        "[FillReconcile] %s PARTIAL FILL has zero fill price "
                        "(filled=%d price=%.2f) — marking UNRESOLVED for retry.",
                        rec.symbol, rec.filled_quantity, rec.actual_fill_price,
                    )
                    rec.fill_status = "UNRESOLVED"
                    rec.reconciliation_source = "PARTIAL_ZERO_PRICE"
                    return
                log.warning(
                    "[FillReconcile] %s PARTIAL FILL: requested=%d filled=%d "
                    "fill_price=%.2f slippage=%.2f%%",
                    rec.symbol, rec.quantity, rec.filled_quantity,
                    rec.actual_fill_price, rec.slippage_pct,
                )
                rec.quantity = rec.filled_quantity
            elif rec.fill_status == "PARTIALLY_FILLED" and rec.filled_quantity <= 0:
                # D11-006: zero-quantity partial fill — broker sent inconsistent state
                log.error(
                    "[FillReconcile] %s PARTIALLY_FILLED but filled_quantity=%d "
                    "\u2014 marking UNRESOLVED; no position will be registered.",
                    rec.symbol, rec.filled_quantity,
                )
                rec.fill_status = "UNRESOLVED"
                rec.reconciliation_source = "PARTIAL_ZERO_QTY"
            elif rec.fill_status == "REJECTED":
                log.warning(
                    "[FillReconcile] %s order REJECTED by broker — "
                    "position will NOT be registered.",
                    rec.symbol,
                )
            elif rec.fill_status == "FILLED":
                log.info(
                    "[FillReconcile] %s FILLED: qty=%d fill_price=%.2f "
                    "slippage=%.2f%%",
                    rec.symbol, rec.filled_quantity,
                    rec.actual_fill_price, rec.slippage_pct,
                )
            elif rec.fill_status in ("PENDING", "UNKNOWN", "UNRESOLVED", "API_ERROR"):
                log.info(
                    "[FillReconcile] %s order_id=%s fill_status=%s — "
                    "will retry on next reconciliation cycle.",
                    rec.symbol, rec.order_id, rec.fill_status,
                )
        except Exception as exc:
            rec.fill_status           = "UNRESOLVED"
            rec.reconciliation_ts     = _now_iso
            rec.reconciliation_source = "ERROR"
            # D8-004: escalate to ERROR — silent broker failures are invisible at DEBUG
            log.error("[FillReconcile] broker reconcile FAILED for %s: %s",
                      rec.order_id, exc, exc_info=True)

    def _update_portfolio(self, sig: TradeSignal, qty: int):
        pos = Position(
            symbol           = sig.symbol,
            quantity         = qty if sig.direction == SignalDirection.BUY else -qty,
            avg_entry_price  = sig.entry_price,
            ltp              = sig.entry_price,
            stop_loss        = sig.stop_loss,
            target_price     = sig.target_price,
            strategy_name    = sig.strategy_name,
        )
        self._portfolio.positions[sig.symbol] = pos

    def _prefetch_restored_ltps(self) -> None:
        """
        After _restore_from_journal, batch-fetch current LTP for every restored
        position so the duplicate guard can use live R immediately rather than
        waiting for the background equity-scanner cycle.

        IMPORTANT: Index/options symbols (NIFTY, BANKNIFTY, FINNIFTY) are
        intentionally skipped.  Their positions are priced in *options premium*
        units (e.g. entry=864.91 for a NIFTY SELL), not in spot-price units
        (~24,000).  Passing spot price through the GLOBAL_SYMBOL_MAP would set
        ltp=24,403 on a premium-priced position and produce a spurious unrealised
        loss of ~₹1,012,138, which falsely trips the MAX_DRAWDOWN_PCT halt on
        the very first cycle after restart.  The monitoring worker (_do_monitor)
        correctly resolves options premiums via Black-Scholes and will update the
        portfolio LTP on the first tick.
        """
        # Symbols whose ltp must be options premium, NOT underlying spot.
        # Fetching these via yfinance returns spot → completely wrong for P&L.
        _SKIP_OPT_INDICES = {"NIFTY", "BANKNIFTY", "FINNIFTY"}

        symbols = [
            sym for sym, pos in self._portfolio.positions.items()
            if not pos.has_live_ltp and sym not in _SKIP_OPT_INDICES
        ]
        # Add ".NS" suffix for Indian equity symbols so yfinance can find them.
        # Without this, raw names like "ICICIBANK" fail and fall back to a SIM
        # price of ~1000, which would corrupt the portfolio drawdown calculation.
        _INDEX_YF_MAP = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "INDIAVIX": "^INDIAVIX"}
        _INDEX_SYMS   = set(_INDEX_YF_MAP.keys())
        _fetch_syms  = [_INDEX_YF_MAP.get(s, f"{s}.NS") if s not in _INDEX_SYMS else _INDEX_YF_MAP[s]
                        for s in symbols]
        _sym_back    = {_INDEX_YF_MAP.get(s, f"{s}.NS") if s not in _INDEX_SYMS else _INDEX_YF_MAP[s]: s
                        for s in symbols}
        if not symbols:
            return
        try:
            from data_feeds import get_feed_manager
            quotes = get_feed_manager().get_multiple_quotes(_fetch_syms)
            fetched = 0
            now_dt = datetime.now()
            for fetch_sym, quote in (quotes or {}).items():
                sym = _sym_back.get(fetch_sym, fetch_sym.replace(".NS", ""))
                pos = self._portfolio.positions.get(sym)
                if pos is None:
                    continue
                if not (quote and quote.ltp and quote.ltp > 0):
                    continue
                # Sanity guard: reject obviously wrong prices.
                # SIM fallback returns ~1000 for unknown symbols; equities
                # should be within a realistic range relative to entry price.
                _entry = pos.avg_entry_price
                if _entry > 0 and (quote.ltp < _entry * 0.2 or quote.ltp > _entry * 5):
                    log.debug(
                        "[OrderManager] Pre-fetch: rejecting implausible LTP for %s: "
                        "%.2f vs entry %.2f — keeping entry price.",
                        sym, quote.ltp, _entry,
                    )
                    continue
                pos.ltp           = quote.ltp
                # NOTE: intentionally do NOT set has_live_ltp = True here.
                # has_live_ltp = True is only set by the monitoring cycle
                # (_do_monitor) after a proper market-data fetch.  Portfolio
                # drawdown_pct only counts has_live_ltp = True positions, so
                # keeping this False prevents a wrong pre-fetch price (e.g.
                # an outdated or SIM value) from falsely triggering a halt.
                pos.ltp_timestamp = now_dt
                fetched += 1
            if fetched:
                log.info(
                    "[OrderManager] Pre-fetched LTP for %d restored position(s).",
                    fetched,
                )
        except Exception as exc:
            log.debug(
                "[OrderManager] LTP pre-fetch failed (will resolve next cycle): %s", exc
            )

    def _flush_dup_guard_stats(self) -> None:
        """
        Persist intra-day dup-guard decision counters to
        data/trade_analytics_YYYY-MM-DD.json.

        Called at every decision point in _dup_guard_reentry_check so the
        file is always up-to-date; the JSON write is a small atomic overwrite.
        The file is shared with other analytics writers — we write only the
        ``dup_guard`` key, merging with any existing content.
        """
        try:
            import json
            today = datetime.now().strftime("%Y-%m-%d")
            path  = os.path.join(_DATA_DIR, f"trade_analytics_{today}.json")
            existing: dict = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                    if isinstance(loaded, dict):
                        existing = loaded
                    # else: stale list-format file — start fresh dict
            payload = dict(self._dup_guard_stats)
            if self._decision_latency_samples:
                payload["avg_decision_latency_sec"] = round(
                    sum(self._decision_latency_samples) / len(self._decision_latency_samples), 1
                )
                payload["max_decision_latency_sec"] = round(
                    max(self._decision_latency_samples), 1
                )
            existing["dup_guard"]  = payload
            existing["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(existing, fh, indent=2)
        except Exception as exc:
            log.debug("[DupGuard] Telemetry flush failed: %s", exc)

    def _symbol_has_open_position(self, symbol: str) -> bool:
        """Check if the symbol has any financially-live position.

        Counts positions with status != 'closed'/'cancelled', which includes
        'open' AND 'closing' (EXPIRED_PENDING) states.  This ensures that a
        position being expire-written to CSV still blocks new entries until
        the CLOSE confirmation is fully committed.
        """
        for rec in self._orders.values():
            if rec.symbol == symbol and rec.status not in ("closed", "cancelled"):
                log.debug(
                    "[ExposureIntegrity] %s counted  status=%s  gstate=%s  oid=%s",
                    symbol, rec.status, rec.governance_state, rec.order_id,
                )
                return True
        return False

    def _update_expiry_retry_sidecar(self, oid: str, count: int) -> None:
        """
        Persist carry-expiry retry counts to expiry_retries.json so the
        retry limit survives container restarts.

        Pass count=0 (or negative) to prune the entry on success.
        Uses atomic os.replace() so a mid-write crash never truncates the file.
        Serialised via _expiry_sidecar_lock for thread safety.
        Failure is silent — this is an observability aid, not a control path.
        """
        with self._expiry_sidecar_lock:
            try:
                existing: dict = {}
                if os.path.exists(_EXPIRY_RETRIES_PATH):
                    with open(_EXPIRY_RETRIES_PATH, encoding="utf-8") as _f:
                        try:
                            existing = json.load(_f)
                        except Exception:
                            existing = {}   # corrupt sidecar — start fresh
                if count > 0:
                    existing[oid] = count
                else:
                    existing.pop(oid, None)
                # Write to a temp file in the same directory, then atomically
                # replace the target so a crash mid-write never corrupts it.
                _dir = os.path.dirname(_EXPIRY_RETRIES_PATH)
                with tempfile.NamedTemporaryFile(
                    "w", dir=_dir, delete=False, prefix="expiry_retry_", suffix=".tmp", encoding="utf-8"
                ) as _tf:
                    json.dump(existing, _tf)
                    _tf.flush()
                    os.fsync(_tf.fileno())
                    _tmp = _tf.name
                os.replace(_tmp, _EXPIRY_RETRIES_PATH)  # atomic on POSIX and Windows
            except Exception as _e:
                log.debug("[OrderManager] expiry_retries.json update failed: %s", _e)

    def check_and_expire_carries(self, live_prices: Optional[Dict[str, float]] = None) -> int:
        """
        Deterministic carry-expiry check — runs every monitoring cycle.

        Iterates live in-memory open positions (not the CSV), closes any whose
        age exceeds the strategy carry limit, and appends SESSION_EXPIRED CLOSE
        rows to paper_trades.csv.

        Design intent: carry expiry must be *time-bound* (deterministic) not
        *restart-bound* (operational).  This method is called by the monitoring
        cycle so positions exit at real market prices during trading hours rather
        than at whatever price happens to be available at the next container
        restart.

        Args:
            live_prices: dict of {symbol: ltp} from the monitoring price fetch.
                         Used as exit price; falls back to feed query, then entry.

        Returns number of positions expired this call.
        """
        now = datetime.now()
        expired = 0
        to_expire = []

        # Daily reset of the order_id dedupe set.
        _today_str = now.strftime("%Y-%m-%d")
        if self._closed_ids_today_date != _today_str:
            self._closed_ids_today.clear()
            self._closed_ids_today_date = _today_str

        for oid, rec in list(self._orders.items()):
            # Guard 1: status must be "open".
            # "closing" means a previous cycle's write failed mid-way and
            # rolled back — treat it as "open" so it is retried this cycle.
            # Any other non-open status ("closed", "cancelled") is skipped.
            if rec.status == "closing":
                log.info(
                    "[CarryExpiry] %s %s found in 'closing' state — "
                    "previous write likely failed. Retrying this cycle.",
                    rec.symbol, oid,
                )
                rec.status = "open"   # explicit reset for retry
            if rec.status != "open":
                continue
            # Retry-limit guard: a symbol that has failed >10 consecutive expiry
            # attempts (e.g. persistent file-lock or disk-full) is aborted to
            # prevent it from silently blocking expiry of other positions.
            _MAX_EXPIRY_RETRIES = 10
            if rec._expiry_retry_count > _MAX_EXPIRY_RETRIES:
                log.error(
                    "[CarryExpiryAbort] %s %s exceeded retry limit (%d). "
                    "Manual intervention required — position not expired.",
                    rec.symbol, oid, _MAX_EXPIRY_RETRIES,
                )
                continue
            # Backoff guard: if the last attempt failed < 5 min ago, skip this
            # cycle to avoid hammering the filesystem on transient errors.
            if rec._last_retry_ts is not None:
                if (now - rec._last_retry_ts) < timedelta(minutes=5):
                    log.debug(
                        "[CarryExpiry] %s %s backoff active (last_fail=%s) — "
                        "skipping until 5-min window clears.",
                        rec.symbol, oid,
                        rec._last_retry_ts.strftime("%H:%M:%S"),
                    )
                    continue
            # ── Option B: trading-day carry (CarryDesignReview Jun 8 2026) ────
            age_td    = _trading_days_elapsed(rec.placed_at, now)
            age_cal   = (now - rec.placed_at).days
            max_carry = _carry_days_for(rec.strategy)  # now means trading days
            _cal_ceil = max_carry * _CARRY_CAL_CEIL_FACTOR  # e.g. 3td → 12cd ceiling
            # Primary trigger: trading days elapsed >= limit.
            # Secondary trigger: calendar ceiling breached (holiday-cluster guard).
            if age_td < max_carry and age_cal < _cal_ceil:
                continue
            # Guard 2: require a validated live price from LTPGuard (set by check_all
            # earlier in _do_monitor).  has_live_ltp lives on PortfolioPosition.
            # If the price for this symbol was rejected by LTPGuard this cycle
            # (e.g. >20% deviation), don't use it as an exit — defer to next cycle.
            # Exception: if the calendar ceiling is already breached, close regardless
            # to prevent infinite deferral during extended holiday clusters.
            _pos = self._portfolio.positions.get(rec.symbol)
            _has_valid_ltp = _pos is None or getattr(_pos, "has_live_ltp", True)
            if not _has_valid_ltp and age_td < max_carry * 2 and age_cal < _cal_ceil:
                log.info(
                    "[TradingDayCarry][CarryExpiryDeferred] %s age_td=%dtd no_valid_ltp "
                    "(max_carry=%dtd cal_ceil=%dcd age_cal=%dcd) — retry next cycle.",
                    rec.symbol, age_td, max_carry, _cal_ceil, age_cal,
                )
                continue
            to_expire.append((oid, rec, age_td, age_cal, max_carry))

        if not to_expire:
            return 0

        # Batch-fetch live prices for expiring symbols not already in live_prices
        _ltp_map: Dict[str, float] = dict(live_prices or {})
        missing_syms = [rec.symbol for _, rec, _, _, _ in to_expire
                        if rec.symbol not in _ltp_map]
        if missing_syms:
            try:
                from data_feeds.data_feed_manager import get_feed_manager as _gfm
                _ns_syms = [s + ".NS" for s in missing_syms]
                _q_map   = _gfm().get_multiple_quotes(_ns_syms)
                for _ns, _q in _q_map.items():
                    _bare = _ns.replace(".NS", "")
                    _ltp  = (getattr(_q, "ltp", None) or getattr(_q, "last_price", None))
                    _src  = (getattr(_q, "feed_source", "") or "").upper()
                    if _ltp and float(_ltp) > 0 and _src != "SIM":
                        _ltp_map[_bare] = round(float(_ltp), 2)
                    elif _src == "SIM":
                        log.warning(
                            "[CarryExpiry] REJECTED SIM exit price for %s (%.2f) — "
                            "phantom price; falling back to entry_price (₹0 PnL).",
                            _bare, float(_ltp or 0),
                        )
            except Exception as _e:
                log.debug("[CarryExpiry] LTP fetch failed: %s", _e)

        with self._journal_lock:
            try:
                fh = open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8")
            except Exception as exc:
                log.error("[CarryExpiry] Cannot open journal for writing: %s", exc)
                return 0

            try:
                w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER)
                for oid, rec, age_td, age_cal, max_carry in to_expire:
                    # ── Phase B dry-run review — logs WOULD_DECIDE before expiry ──
                    _dryrun_ltp = _ltp_map.get(rec.symbol, rec.entry_price)
                    self._review_carry_extension_dryrun(rec, age_td, max_carry, _dryrun_ltp)
                    # Guard B: order_id dedupe set — belt-and-suspenders
                    if oid in self._closed_ids_today:
                        log.debug(
                            "[CarryExpiry] Skipping %s %s — already in "
                            "_closed_ids_today. Duplicate expiry attempt.",
                            rec.symbol, oid,
                        )
                        continue

                    # Guard A: atomic intent marker (open → closing → closed).
                    # Flip status *before* the CSV write so any concurrent
                    # call that re-enters this loop sees a non-open record.
                    if rec.status != "open":
                        log.debug(
                            "[CarryExpiry] Skipping %s %s — status=%s "
                            "(not open). Concurrent expiry?",
                            rec.symbol, oid, rec.status,
                        )
                        continue
                    rec.status = "closing"          # atomic intent: open → closing
                    rec.governance_state = "EXPIRED_PENDING"  # remains exposure-active
                    log.info(
                        "[ExposureIntegrity] %s %s → EXPIRED_PENDING  "
                        "still counts toward DupGuard/cap until CLOSE committed.",
                        rec.symbol, oid,
                    )

                    exit_price = _ltp_map.get(rec.symbol, rec.entry_price)
                    _entry_for_pnl = rec.actual_fill_price if rec.actual_fill_price > 0 else rec.entry_price
                    if rec.direction == "BUY":
                        pnl = round((exit_price - _entry_for_pnl) * rec.quantity, 2)
                    else:
                        pnl = round((_entry_for_pnl - exit_price) * rec.quantity, 2)

                    # Per-position try/except: a write failure for one position
                    # rolls back to "open" so it retries cleanly next cycle rather
                    # than becoming a ghost stuck in "closing".
                    try:
                        w.writerow({
                            "timestamp":   now.strftime("%Y-%m-%d %H:%M:%S"),
                            "order_id":    oid,
                            "symbol":      rec.symbol,
                            "direction":   rec.direction,
                            "quantity":    rec.quantity,
                            "entry_price": rec.entry_price,
                            "stop_loss":   rec.stop_loss,
                            "target":      rec.target,
                            "strategy":    rec.strategy,
                            "confidence":  "",
                            "rr":          "",
                            "event":       "CLOSE",
                            "exit_price":  exit_price,
                            "pnl":         pnl,
                            "reason":      "SESSION_EXPIRED",
                        })
                        log.warning(
                            "[TradingDayCarry][CarryExpiry] SESSION_EXPIRED %s %s  "
                            "age_td=%dtd >= max_carry=%dtd  age_cal=%dcd  exit=%.2f  pnl=%+.0f",
                            rec.symbol, oid, age_td, max_carry, age_cal, exit_price, pnl,
                        )

                        # Complete lifecycle: EXPIRED_PENDING → CLOSED
                        rec.status = "closed"
                        rec.governance_state = "CLOSED"  # no longer exposure-active
                        rec.closed_at = now              # timestamp for GovernanceScoreAudit
                        rec._last_retry_ts = None   # clear backoff on success
                        self._closed_ids_today.add(oid)
                        self._portfolio.positions.pop(rec.symbol, None)
                        # Prune from the persistence sidecar — position is done.
                        self._update_expiry_retry_sidecar(oid, 0)
                        expired += 1

                    except Exception as row_exc:
                        # Rollback: position stays exposure-active, retry next cycle
                        rec.status = "open"
                        rec.governance_state = "ACTIVE_CARRY"  # restore to governed state
                        rec._expiry_retry_count += 1
                        rec._last_retry_ts = now
                        # Persist so the retry count survives a restart.
                        self._update_expiry_retry_sidecar(oid, rec._expiry_retry_count)
                        log.error(
                            "[CarryExpiryError] CSV write failed for %s %s — "
                            "rolled back to open, retry=%d. Error: %s",
                            rec.symbol, oid, rec._expiry_retry_count, row_exc,
                        )

                try:
                    fh.flush()
                    os.fsync(fh.fileno())
                except Exception as flush_exc:
                    log.warning("[CarryExpiry] Journal flush/fsync failed: %s", flush_exc)
            finally:
                fh.close()

        return expired

    def _review_carry_extension_dryrun(
        self, rec: "OrderRecord", age_td: int, max_carry: int, ltp: float,
    ) -> None:
        """Phase B dry-run Post-Expiry Review Engine.

        Computes a position-health score and logs what the review engine
        WOULD decide (CONTINUE or EXIT) but takes NO action.  SESSION_EXPIRED
        fires as normal regardless of the dry-run outcome.

        Scoring uses position-health factors only (max 7.0 in Phase B).
        Market context factors (regime, VIX, portfolio heat, opportunity cost)
        are deferred to Phase C once market_context is wired in.

        Log tag: [CarryReviewDryRun]
        Evidence gate: 50+ SESSION_EXPIRED trades under 3td carry rule before
        Phase C (live decisions) is activated.
        """
        try:
            if ltp <= 0 or rec.entry_price <= 0:
                return

            # ── Position health ─────────────────────────────────────────────
            if rec.direction == "BUY":
                pnl        = (ltp - rec.entry_price) * rec.quantity
                thesis_ok  = ltp >= rec.entry_price * 0.995
                tgt_range  = rec.target - rec.entry_price
                tgt_prog   = (ltp - rec.entry_price) / tgt_range * 100 if tgt_range > 0 else 0.0
            else:
                pnl        = (rec.entry_price - ltp) * rec.quantity
                thesis_ok  = ltp <= rec.entry_price * 1.005
                tgt_range  = rec.entry_price - rec.target
                tgt_prog   = (rec.entry_price - ltp) / tgt_range * 100 if tgt_range > 0 else 0.0

            sl_dist  = abs(rec.initial_stop_loss - rec.entry_price) if rec.initial_stop_loss \
                       else abs(rec.stop_loss - rec.entry_price)
            r_mult   = pnl / (sl_dist * abs(rec.quantity)) if sl_dist > 0 and rec.quantity else 0.0
            sl_prox  = abs(ltp - rec.stop_loss) / ltp * 100 if ltp else 100.0

            # ── Score (position-health factors, max 7.0) ────────────────────
            score = 0.0
            if pnl > 0:                score += 2.0
            if r_mult >= 0.5:          score += 1.0
            if thesis_ok:              score += 1.5
            if tgt_prog >= 50.0:       score += 1.0
            if rec.confidence_score >= 7.5: score += 0.5
            # Penalties
            if pnl < 0:                score -= 2.0
            if not thesis_ok:          score -= 2.0
            if sl_prox < 0.5:          score -= 1.0

            # ── Hard conditions ─────────────────────────────────────────────
            hard_exit_reason = None
            if sl_prox < 0.3:
                hard_exit_reason = "SL_PROXIMITY"
            elif rec.extension_count >= 3:
                hard_exit_reason = "MAX_EXTENSIONS"

            hard_continue = r_mult >= 2.0 and pnl > 0 and thesis_ok

            if hard_exit_reason:
                decision, reason = "EXIT",     hard_exit_reason
            elif hard_continue:
                decision, reason = "CONTINUE", "HARD_CONTINUE_2R"
            elif score >= 6.0:
                decision, reason = "CONTINUE", "scoring"
            else:
                decision, reason = "EXIT",     "scoring"

            log.info(
                "[CarryReviewDryRun] %s %s  age=%dtd/max=%dtd  ext=%d/3"
                "  would_decide=%s  score=%.1f/7.0(threshold=6.0)"
                "  pnl=%+.0f  r_mult=%+.2f  thesis=%s  sl_prox=%.1f%%"
                "  tgt_prog=%.0f%%  conf=%.1f  reason=%s"
                "  [regime/vix/heat deferred_PhaseC]",
                rec.symbol, rec.order_id, age_td, max_carry,
                rec.extension_count, decision, score,
                pnl, r_mult, "INTACT" if thesis_ok else "BROKEN",
                sl_prox, max(0.0, tgt_prog), rec.confidence_score, reason,
            )
        except Exception as _e:
            log.debug("[CarryReviewDryRun] score error %s %s: %s",
                      rec.symbol, getattr(rec, "order_id", "?"), _e)

    # ── Smart-Swap constants ───────────────────────────────────────────────
    _SWAP_MIN_AGE_MIN           = 20.0   # never evict a position younger than this
    _SWAP_SAFE_R                = 1.5    # never evict a position running at +1.5R or better
    _SWAP_SCORE_DELTA           = 0.5    # new signal must beat weakest entry score by this margin
    _SWAP_MIN_NEW_RR            = 1.5    # new signal must have target/risk >= this (expected R)
    _SWAP_MIN_PRICE_IMPROVE_PCT = 0.5    # same-symbol swap: new entry must be ≥0.5% better
    _SAME_ZONE_PCT              = 0.02   # DupGuard: entries within 2% → same thesis, not new opportunity

    def _smart_swap_check(
        self, new_symbol: str, new_signal_score: float,
        new_entry: float = 0.0, new_stop: float = 0.0, new_target: float = 0.0,
    ):
        """
        When the position cap is full, scan all open positions and identify
        the weakest one.  If the incoming signal is significantly stronger,
        return the order_id, symbol, and entry-score of the weakest position
        so the caller can close it and open the new trade.

        Returns (order_id, symbol, entry_score) or None.

        Safety gates (position is *never* evicted if):
          • Trade age < _SWAP_MIN_AGE_MIN   (20 min)  – too fresh
          • Current R >= _SWAP_SAFE_R       (+1.5R)   – strong winner
          • new_signal_score < weakest_entry_score + _SWAP_SCORE_DELTA
          • new signal expected R (target/risk) < _SWAP_MIN_NEW_RR (1.5R)

        Weakest selection priority (refinement 1 — loss-aware):
          1. R ascending   (most negative / lowest R first)
          2. confidence_score ascending (lowest entry quality)
          3. age descending (oldest dead-weight)
        """
        now = datetime.now()
        _NEG_INF = float("-inf")

        # ── Refinement 2: minimum expected R on the incoming signal ──────
        # Compute reward-to-risk ratio: |target - entry| / |entry - stop|.
        # Block the swap entirely if the new trade doesn't project ≥ 1.5R.
        if new_entry > 0 and new_stop > 0 and new_target > 0:
            _new_risk   = abs(new_entry - new_stop)
            _new_reward = abs(new_target - new_entry)
            _new_rr     = (_new_reward / _new_risk) if _new_risk > 0 else 0.0
            if _new_rr < self._SWAP_MIN_NEW_RR:
                log.info(
                    "[SwapBlocked] %s insufficient RR for replacement (RR=%.2f < %.1f).",
                    new_symbol, _new_rr, self._SWAP_MIN_NEW_RR,
                )
                return None

        # ── Build candidate list (all evictable open positions) ───────────
        candidates = []   # list of (r_mult_or_None, age_min, rec)

        for rec in self._orders.values():
            if rec.status != "open":
                continue

            # Safety: never touch fresh trades
            age_min = (
                (now - rec.placed_at).total_seconds() / 60.0
                if rec.placed_at else 0.0
            )
            if age_min < self._SWAP_MIN_AGE_MIN:
                continue

            # Compute current R from live LTP when available
            risk = (
                abs(rec.entry_price - rec.stop_loss)
                if rec.stop_loss and rec.stop_loss != rec.entry_price
                else 0.0
            )
            pos    = self._portfolio.positions.get(rec.symbol)
            r_mult = None
            if pos and pos.has_live_ltp and risk > 0:
                if rec.direction == "BUY":
                    r_mult = (pos.ltp - rec.entry_price) / risk
                else:
                    r_mult = (rec.entry_price - pos.ltp) / risk

            # Safety: never evict a strong winner
            if r_mult is not None and r_mult >= self._SWAP_SAFE_R:
                continue

            candidates.append((r_mult, age_min, rec))

        if not candidates:
            log.debug(
                "[SmartSwap] No evictable position found for %s (all fresh/winning).",
                new_symbol,
            )
            return None

        # ── Refinement 1: loss-aware sort ─────────────────────────────────
        # Sort key: (r_key ASC, score ASC, age DESC)
        # r_key: use actual R when available; treat missing as 0.0 (neutral)
        # so that confirmed losers always rank before unknowns.
        def _sort_key(item):
            r, age, rec = item
            r_key = r if r is not None else 0.0
            return (r_key, rec.confidence_score, -age)   # lower = weaker

        candidates.sort(key=_sort_key)
        _r_weakest, _age_weakest, weakest_rec = candidates[0]

        weakest_oid   = weakest_rec.order_id
        weakest_sym   = weakest_rec.symbol
        weakest_entry = weakest_rec.confidence_score
        weakest_r_str = f"{_r_weakest:.2f}" if _r_weakest is not None else "n/a"

        # ── Price-improvement gate (same-symbol replacements only) ──────────
        # Replacing RELIANCE with RELIANCE at virtually the same price is churn.
        # For BUY: new entry must be ≥ effective_threshold % BELOW old entry.
        # For SELL: new entry must be ≥ effective_threshold % ABOVE old entry.
        # Cross-symbol swaps skip this check (price comparison is meaningless).
        #
        # Volatility-aware threshold: max(fixed_min, 0.1 × R%)
        # Low-vol names (ITC): risk~3.5% → 0.1R~0.35% → fixed 0.5% wins.
        # High-vol names (MARUTI): risk~2.5%@16k = ~0.15% but range wider —
        # 0.1R keeps it proportional so we don’t need hand-tuned per-stock values.
        if new_symbol == weakest_sym and new_entry > 0 and weakest_rec.entry_price > 0:
            _old_entry  = weakest_rec.entry_price
            _old_risk   = abs(weakest_rec.entry_price - weakest_rec.stop_loss) \
                          if weakest_rec.stop_loss else 0.0
            _r_pct      = (_old_risk / _old_entry * 100.0) if _old_entry > 0 else 0.0
            _vol_thresh = 0.1 * _r_pct          # 0.1×R as a percentage of price
            _eff_thresh = max(self._SWAP_MIN_PRICE_IMPROVE_PCT, _vol_thresh)
            _threshold  = _eff_thresh / 100.0
            if weakest_rec.direction == "BUY":
                _price_ok = new_entry <= _old_entry * (1.0 - _threshold)
            else:
                _price_ok = new_entry >= _old_entry * (1.0 + _threshold)
            if not _price_ok:
                _improvement_pct = abs(new_entry - _old_entry) / _old_entry * 100
                log.info(
                    "[SwapBlocked] Same-symbol replacement for %s blocked: "
                    "price improvement insufficient (new=%.2f vs old=%.2f, "
                    "improvement=%.2f%% < %.2f%% required [vol-aware: 0.1R=%.2f%%]).",
                    new_symbol, new_entry, _old_entry,
                    _improvement_pct, _eff_thresh, _vol_thresh,
                )
                return None

        # ── Score-delta gate ──────────────────────────────────────────────
        if new_signal_score >= weakest_entry + self._SWAP_SCORE_DELTA:
            log.info(
                "[SmartSwap] %s (score=%.1f) qualifies to replace %s "
                "(entry_score=%.1f, R=%s, age=%.0fmin).",
                new_symbol, new_signal_score,
                weakest_sym, weakest_entry, weakest_r_str, _age_weakest,
            )
            return (weakest_oid, weakest_sym, weakest_entry)

        log.debug(
            "[SmartSwap] %s (score=%.1f) not strong enough to replace %s "
            "(entry_score=%.1f, delta=%.1f required).",
            new_symbol, new_signal_score,
            weakest_sym, weakest_entry, self._SWAP_SCORE_DELTA,
        )
        return None

    def _dup_guard_reentry_check(self, symbol: str,
                                   decision_score: float = 0.0,
                                   new_entry_price: float = 0.0) -> bool:
        """
        Re-entry unlock logic for the duplicate guard.

        Returns True  → allow the new trade (logs DupGuardOverride)
        Returns False → block the new trade (logs DupGuardBlock)

        Rules
        -----
        Block unconditionally if:
          • Already 2+ open positions for this symbol (hard cap)
          • The existing trade is < 15 minutes old
          • The existing trade R < -0.25 (already in significant loss)
          • Same-zone re-entry: new_entry_price within _SAME_ZONE_PCT (2%) of
            existing entry AND existing trade is flat or losing (R ≤ 0) —
            in the LTP-live path.
          • Same-zone re-entry: new_entry_price within _SAME_ZONE_PCT (2%) of
            existing entry — in the age-only (LTP unavailable) path, where
            we cannot compute R but proximity alone signals the same thesis.

        Allow if ANY of:
          • Condition A: existing trade R >= +1.0 (running well — stock has
            meaningfully moved, so same-zone concern is moot)
          • Condition B: trade age >= 90 minutes AND not same-zone
        """
        now = datetime.now()

        # Expire missed-opportunity records older than 30 minutes.
        _expired = [
            s for s, ts in self._ltp_blocked_symbols.items()
            if (now - ts).total_seconds() > 1800
        ]
        for s in _expired:
            self._ltp_blocked_symbols.pop(s, None)

        # Include financially-live positions (open + closing/EXPIRED_PENDING).
        # A position being expire-written still holds its portfolio slot until
        # the CSV CLOSE row is fully committed.
        open_recs = [
            rec for rec in self._orders.values()
            if rec.symbol == symbol and rec.status not in ("closed", "cancelled")
        ]
        log.debug(
            "[ExposureIntegrity] DupGuard %s  financially_live=%d  statuses=%s",
            symbol, len(open_recs),
            [r.status for r in open_recs],
        )

        # Hard cap: max 2 open per symbol
        if len(open_recs) >= 2:
            log.warning(
                "[DupGuardBlock] %s blocked → already %d open position(s) (max 2).",
                symbol, len(open_recs),
            )
            return False

        rec = open_recs[0]  # exactly one open trade exists

        # Trade age in minutes
        placed   = rec.placed_at or now
        age_min  = (now - placed).total_seconds() / 60.0

        # Safety: too fresh — never add within 15 minutes
        if age_min < 15:
            log.warning(
                "[DupGuardBlock] %s blocked → trade age %.0fmin < 15min minimum.",
                symbol, age_min,
            )
            return False

        # ── LTP freshness + confidence pipeline ──────────────────────────
        # Step 1: Freshness guard with hysteresis.
        #   If the cached LTP is older than _DUP_GUARD_STALE_AFTER_S, demote
        #   it to stale and record the transition time.  Once stale, the
        #   symbol must wait _DUP_GUARD_FRESH_COOLDOWN_S before a cache read
        #   can restore it — this prevents rapid flip-flopping at the boundary.
        # Step 2: Cache pull (only when cooldown elapsed).
        #   A new tick also increments ltp_tick_count.
        # Step 3: Confidence gate.
        #   Fewer than _DUP_GUARD_LTP_CONF_TICKS consecutive fresh ticks →
        #   treat as low-confidence and fall through to age-only path.
        # ─────────────────────────────────────────────────────────────────
        risk = (
            abs(rec.entry_price - rec.stop_loss)
            if rec.stop_loss and rec.stop_loss != rec.entry_price
            else 0.0
        )
        pos    = self._portfolio.positions.get(symbol)
        now_dt = datetime.now()

        # Step 1 — Freshness check (must come before cache pull)
        if pos is not None and pos.has_live_ltp:
            ltp_age_s = (
                (now_dt - pos.ltp_timestamp).total_seconds()
                if pos.ltp_timestamp is not None else float("inf")
            )
            if ltp_age_s > _DUP_GUARD_STALE_AFTER_S:
                log.info(
                    "[DupGuard] %s LTP stale (%.0fs old) → fallback to age-only.",
                    symbol, ltp_age_s,
                )
                pos.has_live_ltp   = False
                pos.ltp_timestamp  = None
                pos.ltp_tick_count = 0
                self._ltp_stale_at[symbol] = now_dt
                self._dup_guard_stats["ltp_stale_fallbacks"] += 1

        # Step 2 — Cache pull (with cooldown hysteresis)
        if pos is not None and not pos.has_live_ltp:
            stale_since = self._ltp_stale_at.get(symbol)
            cooldown_ok = (
                stale_since is None
                or (now_dt - stale_since).total_seconds() >= _DUP_GUARD_FRESH_COOLDOWN_S
            )
            if cooldown_ok:
                try:
                    from opportunity_engine.equity_scanner_ai import _PRICE_CACHE, _PRICE_CACHE_LOCK
                    with _PRICE_CACHE_LOCK:
                        cached_price = _PRICE_CACHE.get(symbol, 0.0)
                    if cached_price > 0:
                        was_stale           = symbol in self._ltp_stale_at
                        pos.ltp             = cached_price
                        pos.has_live_ltp    = True
                        pos.ltp_timestamp   = now_dt
                        pos.ltp_tick_count += 1
                        if was_stale:
                            self._ltp_stale_at.pop(symbol, None)
                            log.info(
                                "[DupGuard] %s LTP stale→fresh transition (tick=%d).",
                                symbol, pos.ltp_tick_count,
                            )
                        # Decision latency: log when confidence threshold is first met.
                        if (
                            pos.ltp_tick_count == _DUP_GUARD_LTP_CONF_TICKS
                            and pos.confidence_achieved_at is None
                            and pos.restore_time is not None
                        ):
                            pos.confidence_achieved_at = now_dt
                            latency_s = (now_dt - pos.restore_time).total_seconds()
                            self._decision_latency_samples.append(latency_s)
                            log.info(
                                "[DupGuard] %s Confidence achieved in %.0f sec (tick=%d).",
                                symbol, latency_s, pos.ltp_tick_count,
                            )
                except Exception:
                    pass  # cache not yet populated — flag stays False

        ltp_live = pos is not None and pos.has_live_ltp

        # ── Pre-flight loss guard (runs before score-bypass logic) ────────
        # Compute R now if LTP is available.  If the existing trade is already
        # at or below -0.25R, refuse the re-entry unconditionally — no signal
        # score is strong enough to justify scaling into a losing position.
        if ltp_live and pos is not None and risk > 0:
            _ltp_preflight = pos.ltp
            _r_preflight = (
                (_ltp_preflight - rec.entry_price) / risk
                if rec.direction == "BUY"
                else (rec.entry_price - _ltp_preflight) / risk
            )
            if _r_preflight < -0.25:
                log.warning(
                    "[DupGuardBlock] %s blocked → loss guard (R=%.2f).",
                    symbol, _r_preflight,
                )
                self._dup_guard_stats["blocks_by_loss"] += 1
                self._flush_dup_guard_stats()
                return False

        # Step 3 — Confidence gate: require at least 2 consecutive fresh ticks.
        # Exception: if the decision score is ≥ 7.5 (very strong signal) allow
        # even with only 1 tick — price is unlikely to be stale noise at that
        # score level and waiting for a second tick risks missing the entry.
        high_confidence_signal = decision_score >= 7.5
        if ltp_live and pos is not None and pos.ltp_tick_count < _DUP_GUARD_LTP_CONF_TICKS:
            if high_confidence_signal:
                log.info(
                    "[DupGuard] %s LTP low tick-count (%d/%d) but high-confidence signal (score=%.1f) — tick threshold bypassed.",  # D10-007
                    symbol, pos.ltp_tick_count, _DUP_GUARD_LTP_CONF_TICKS, decision_score,
                )
            else:
                log.info(
                    "[DupGuard] %s low tick-count LTP (%d/%d) → falling back to age-only evaluation.",  # D10-007
                    symbol, pos.ltp_tick_count, _DUP_GUARD_LTP_CONF_TICKS,
                )
                ltp_live = False
                self._dup_guard_stats["ltp_lowconf_fallbacks"] += 1

        if not ltp_live:
            # Feed not yet available — skip R checks, use age only.
            log.info(
                "[DupGuard] %s LTP unavailable → using age-only evaluation (age=%.0fmin).",
                symbol, age_min,
            )
            self._dup_guard_stats["ltp_unavailable_fallbacks"] += 1

            # Same-zone guard (age-only path): if the new entry is within 2% of
            # the existing entry, the stock hasn't moved enough to constitute a
            # fresh setup — block to prevent re-committing to the same unresolved thesis.
            if (
                new_entry_price > 0
                and rec.entry_price > 0
                and abs(new_entry_price - rec.entry_price) / rec.entry_price <= self._SAME_ZONE_PCT
            ):
                log.warning(
                    "[DupGuardBlock] %s blocked → same-zone re-entry with LTP unavailable "
                    "(new=%.2f vs existing=%.2f, Δ=%.2f%%) — same thesis, not a new opportunity.",
                    symbol, new_entry_price, rec.entry_price,
                    abs(new_entry_price - rec.entry_price) / rec.entry_price * 100,
                )
                self._dup_guard_stats["blocks_by_loss"] += 1
                self._flush_dup_guard_stats()
                return False

            if age_min >= 90:
                log.info(
                    "[DupGuardOverride] %s allowed → age=%.0fmin (LTP pending).",
                    symbol, age_min,
                )
                self._dup_guard_stats["overrides_by_age"] += 1
                self._flush_dup_guard_stats()
                return True
            log.warning(
                "[DupGuardBlock] %s blocked → age=%.0fmin < 180min and LTP pending.",
                symbol, age_min,
            )
            self._dup_guard_stats["blocks_by_age"] += 1
            self._ltp_blocked_symbols[symbol] = now_dt  # track for missed-opportunity recovery
            self._flush_dup_guard_stats()
            return False

        # LTP is live — compute R and apply full rule set.
        ltp = pos.ltp
        if risk > 0:
            r_mult = (
                (ltp - rec.entry_price) / risk
                if rec.direction == "BUY"
                else (rec.entry_price - ltp) / risk
            )
        else:
            r_mult = 0.0

        # Safety: existing trade already in loss — do not add (tightened -0.5 → -0.25)
        if r_mult < -0.25:
            log.warning(
                "[DupGuardBlock] %s blocked → loss guard (R=%.2f).",
                symbol, r_mult,
            )
            self._dup_guard_stats["blocks_by_loss"] += 1
            self._flush_dup_guard_stats()
            return False

        # Condition A: trade running well at +1R or better
        if r_mult >= 1.0:
            log.info(
                "[DupGuardOverride] %s allowed → R=%.1f age=%.0fmin",
                symbol, r_mult, age_min,
            )
            self._dup_guard_stats["overrides_by_profit"] += 1
            if symbol in self._ltp_blocked_symbols:
                prev_ts = self._ltp_blocked_symbols.pop(symbol)
                self._dup_guard_stats["missed_opportunity_recovered"] += 1
                log.info(
                    "[DupGuard] %s missed opportunity recovered (blocked %.0fs ago, R=%.2f).",
                    symbol, (now_dt - prev_ts).total_seconds(), r_mult,
                )
            self._flush_dup_guard_stats()
            return True

        # Condition B: position is stale / has been open 90+ minutes.
        # Same-zone guard applies here too: if the new entry is within 2% of the
        # existing entry AND the trade is flat or losing, it is the same unresolved
        # thesis — age alone is not enough justification to double into it.
        if (
            r_mult <= 0.0
            and new_entry_price > 0
            and rec.entry_price > 0
            and abs(new_entry_price - rec.entry_price) / rec.entry_price <= self._SAME_ZONE_PCT
        ):
            log.warning(
                "[DupGuardBlock] %s blocked → same-zone re-entry on flat/losing position "
                "(new=%.2f vs existing=%.2f, Δ=%.2f%%, R=%.2f) — age bypass denied.",
                symbol, new_entry_price, rec.entry_price,
                abs(new_entry_price - rec.entry_price) / rec.entry_price * 100,
                r_mult,
            )
            self._dup_guard_stats["blocks_by_loss"] += 1
            self._flush_dup_guard_stats()
            return False

        if age_min >= 90:
            log.info(
                "[DupGuardOverride] %s allowed → R=%.1f age=%.0fmin",
                symbol, r_mult, age_min,
            )
            self._dup_guard_stats["overrides_by_age"] += 1
            if symbol in self._ltp_blocked_symbols:
                prev_ts = self._ltp_blocked_symbols.pop(symbol)
                self._dup_guard_stats["missed_opportunity_recovered"] += 1
                log.info(
                    "[DupGuard] %s missed opportunity recovered (blocked %.0fs ago, age=%.0fmin).",
                    symbol, (now_dt - prev_ts).total_seconds(), age_min,
                )
            self._flush_dup_guard_stats()
            return True

        log.warning(
            "[DupGuardBlock] %s blocked → insufficient conditions (R=%.2f age=%.0fmin).",
            symbol, r_mult, age_min,
        )
        self._dup_guard_stats["blocks_by_age"] += 1
        self._flush_dup_guard_stats()
        return False

    def _restore_from_journal(self) -> None:
        # On startup, read the paper trade CSV and:
        #
        # PART A - Restore: re-hydrate any position where:
        #   - event=OPEN with no matching CLOSE, AND
        #   - age <= strategy-specific max carry days.
        #   Makes restarts safe for legitimate overnight / multi-day carries.
        #
        # PART B - Expire: append SESSION_EXPIRED CLOSE for any position where:
        #   - event=OPEN with no matching CLOSE, AND
        #   - age > strategy-specific max carry days.
        #   Append-only, idempotent — never modifies historical rows.
        #
        # Strategy-aware carry limits (from _carry_days_for):
        #   Mean_Reversion / Range / Hedging : 3 days
        #   Momentum / Breakout / EDG_MOMENT : 5 days
        #   Trend / Swing / BullCall          : 7 days
        #   Everything else (default)         : 5 days
        if not os.path.exists(PAPER_TRADE_LOG):
            return

        # Max lookback = largest strategy carry limit (Trend = 7 days).
        # Rows older than this window can never be valid carries.
        _MAX_LOOKBACK_DAYS = 7
        now       = datetime.now()
        cutoff_dt = now - timedelta(days=_MAX_LOOKBACK_DAYS)

        # Load closed-order registries for the past _MAX_LOOKBACK_DAYS days.
        # Any order_id listed here was explicitly closed even if the CSV CLOSE
        # row was lost due to a crash mid-write.
        closed_registry: set = set()
        try:
            for _d in range(_MAX_LOOKBACK_DAYS + 1):
                _reg_date = (now - timedelta(days=_d)).strftime("%Y-%m-%d")
                _reg_path = os.path.join(_DATA_DIR, f"closed_orders_{_reg_date}.txt")
                if os.path.exists(_reg_path):
                    with open(_reg_path, encoding="utf-8") as rf:
                        for line in rf:
                            oid_r = line.strip()
                            if oid_r:
                                closed_registry.add(oid_r)
        except Exception as reg_exc:
            log.debug("[OrderManager] Could not read closed registry: %s", reg_exc)

        try:
            # Pass 1: Build set of all order_ids with a CLOSE in the CSV.
            # Full scan (no date limit) so we never restore an order that was
            # closed in an older session whose CLOSE row is already in the CSV.
            closed_in_csv: set = set()
            _corrupt_pass1 = 0
            with open(PAPER_TRADE_LOG, newline="", encoding="utf-8") as fh:
                dr = csv.DictReader(fh)
                for row in dr:
                    try:
                        event = row.get("event", "").strip().upper()
                        if event in ("CLOSE", "CANCELLED"):
                            oid = row.get("order_id", "").strip()
                            if oid:
                                closed_in_csv.add(oid)
                    except Exception as _row_exc:
                        _corrupt_pass1 += 1
                        log.warning(
                            "[JournalCorruptRowSkipped] pass=1 line=%d: %s",
                            dr.reader.line_num, _row_exc,
                        )
                        continue

            # Pass 1.5: Collect locked SL from EXTEND events.
            # An EXTEND row is written by TradeMonitor when adaptive profit
            # extension fires (locks the SL above entry).  We restore the
            # locked SL so the position doesn't revert to the original SL
            # and isn't double-extended or prematurely closed at original target.
            #
            # We also store when the extension fired.  The 7-day extended carry
            # window is counted from that timestamp — NOT from the trade open date.
            # This prevents a weakened trade from getting indefinite protection
            # just because it was once a winner: e.g. if extension fired on day 2
            # and 10 days have passed since then, the window is exhausted even
            # though the position itself might still have days left in max_carry.
            _EXT_WINDOW_DAYS = 7   # calendar days of carry granted after extension fires
            extended_map: dict[str, tuple] = {}   # oid -> (locked_sl, extend_ts)
            _corrupt_pass15 = 0
            with open(PAPER_TRADE_LOG, newline="", encoding="utf-8") as fh:
                dr = csv.DictReader(fh)
                for row in dr:
                    try:
                        oid   = row.get("order_id", "").strip()
                        event = row.get("event", "").strip().upper()
                        if event == "EXTEND" and oid and oid not in closed_in_csv:
                            try:
                                ext_sl = float(row.get("stop_loss", 0) or 0)
                                ext_ts = datetime.strptime(
                                    row.get("timestamp", "")[:19], "%Y-%m-%d %H:%M:%S"
                                )
                                extended_map[oid] = (ext_sl, ext_ts)
                            except (ValueError, TypeError):
                                pass
                    except Exception as _row_exc:
                        _corrupt_pass15 += 1
                        log.warning(
                            "[JournalCorruptRowSkipped] pass=1.5 line=%d: %s",
                            dr.reader.line_num, _row_exc,
                        )
                        continue

            # Pass 1.9 — Deep orphan expiry for SIM_ paper records older than
            # the normal restore window.  These rows are invisible to Pass 2
            # (cutoff_dt skips them) but CycleHealthMonitor reads the full CSV
            # and reports them as stale every cycle, forever.
            #
            # Safety constraints:
            #   • Only SIM_-prefixed order_ids (paper records).  Real broker
            #     order_ids are never touched — they do NOT carry the SIM_ prefix.
            #   • Append-only: original OPEN row is preserved; we only add a CLOSE.
            #   • Idempotent: after the CLOSE is written, Pass 1 adds the oid to
            #     closed_in_csv, so re-runs are no-ops.
            #   • The oid is added to closed_in_csv before Pass 2 so Pass 2 also
            #     skips it cleanly.
            _DEEP_ORPHAN_DAYS = 60   # scan back this far for unmatched SIM_ OPENs
            _deep_cutoff = now - timedelta(days=_DEEP_ORPHAN_DAYS)
            _deep_orphan_rows: list = []   # (oid, row_dict, placed_at, age_days)
            try:
                with open(PAPER_TRADE_LOG, newline="", encoding="utf-8") as fh:
                    _dr = csv.DictReader(fh)
                    for _row in _dr:
                        try:
                            _ts = _row.get("timestamp", "")
                            try:
                                _rdt = datetime.strptime(_ts[:19], "%Y-%m-%d %H:%M:%S")
                            except (ValueError, TypeError):
                                continue
                            if _rdt < _deep_cutoff:
                                continue   # beyond extended scan window
                            if _rdt >= cutoff_dt:
                                continue   # within normal restore window — handled by Pass 2
                            _oid = _row.get("order_id", "").strip()
                            _ev  = _row.get("event", "").strip().upper()
                            if not _oid or not _oid.startswith("SIM_"):
                                continue   # safety: only paper SIM_ records
                            if _ev not in ("OPEN", "REENTRY_OPEN"):
                                continue
                            if _oid in closed_in_csv or _oid in closed_registry:
                                continue   # already closed — skip
                            try:
                                _placed_at = datetime.strptime(_ts[:19], "%Y-%m-%d %H:%M:%S")
                            except (ValueError, TypeError):
                                _placed_at = now
                            _age_d = (now - _placed_at).days
                            _deep_orphan_rows.append((_oid, _row, _placed_at, _age_d))
                        except Exception:
                            continue
            except Exception as _dop_scan_exc:
                log.debug("[OrderManager] Deep orphan scan error: %s", _dop_scan_exc)

            if _deep_orphan_rows:
                # Mark as closed so Pass 2 skips them
                for _oid, _, _, _ in _deep_orphan_rows:
                    closed_in_csv.add(_oid)
                try:
                    with self._journal_lock:
                        with open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8") as fh:
                            _w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER)
                            for _oid, _row, _placed_at, _age_d in _deep_orphan_rows:
                                _ep = float(_row.get("entry_price", 0) or 0)
                                _w.writerow({
                                    "timestamp":   now.strftime("%Y-%m-%d %H:%M:%S"),
                                    "order_id":    _oid,
                                    "symbol":      _row.get("symbol", ""),
                                    "direction":   _row.get("direction", ""),
                                    "quantity":    _row.get("quantity", 0),
                                    "entry_price": _ep,
                                    "stop_loss":   _row.get("stop_loss", ""),
                                    "target":      _row.get("target", ""),
                                    "strategy":    _row.get("strategy", ""),
                                    "confidence":  "",
                                    "rr":          "",
                                    "event":       "CLOSE",
                                    "exit_price":  _ep,
                                    "pnl":         0.0,
                                    "reason":      "SESSION_EXPIRED_DEEP_ORPHAN",
                                })
                                log.info(
                                    "[OrderManager] SESSION_EXPIRED_DEEP_ORPHAN: "
                                    "%s %s  age=%dd > restore_window=%dd  "
                                    "(SIM paper record — original OPEN preserved, "
                                    "CLOSE appended for auditability).",
                                    _row.get("symbol", ""), _oid,
                                    _age_d, _MAX_LOOKBACK_DAYS,
                                )
                            fh.flush()
                            os.fsync(fh.fileno())
                    log.info(
                        "[OrderManager] Deep orphan expiry: %d SIM record(s) reconciled. "
                        "CSV is now clean. (Real broker positions: untouched.)",
                        len(_deep_orphan_rows),
                    )
                except Exception as _dop_write_exc:
                    log.warning(
                        "[OrderManager] Deep orphan expiry write failed: %s",
                        _dop_write_exc,
                    )

            # Pass 2: Find OPEN rows within the lookback window.
            open_rows: dict[str, dict] = {}   # order_id -> latest OPEN row
            _corrupt_pass2 = 0
            with open(PAPER_TRADE_LOG, newline="", encoding="utf-8") as fh:
                dr = csv.DictReader(fh)
                for row in dr:
                    try:
                        ts_str = row.get("timestamp", "")
                        try:
                            row_dt = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
                        except (ValueError, TypeError):
                            continue
                        if row_dt < cutoff_dt:
                            continue   # too old to be a valid carry
                        oid   = row.get("order_id", "").strip()
                        event = row.get("event", "").strip().upper()
                        if not oid:
                            continue
                        if event in ("OPEN", "REENTRY_OPEN"):
                            open_rows[oid] = row
                        elif event in ("CLOSE", "CANCELLED"):
                            open_rows.pop(oid, None)
                    except Exception as _row_exc:
                        _corrupt_pass2 += 1
                        log.warning(
                            "[JournalCorruptRowSkipped] pass=2 line=%d: %s",
                            dr.reader.line_num, _row_exc,
                        )
                        continue

            _total_corrupt = _corrupt_pass1 + _corrupt_pass15 + _corrupt_pass2
            if _total_corrupt:
                log.warning(
                    "[JournalScanSummary] corrupt_rows=%d "
                    "(pass1=%d, pass1.5=%d, pass2=%d) — rows skipped during restore.",
                    _total_corrupt, _corrupt_pass1, _corrupt_pass15, _corrupt_pass2,
                )
            else:
                log.debug("[JournalScanSummary] corrupt_rows=0 — journal clean.")

            # Remove anything confirmed closed (CSV or crash-safe registry).
            ghost_count = 0
            for oid_c in list(open_rows.keys()):
                if oid_c in closed_in_csv or oid_c in closed_registry:
                    open_rows.pop(oid_c)
                    ghost_count += 1
            if ghost_count:
                log.info(
                    "[OrderManager] Filtered %d ghost OPEN row(s) (CLOSE found in CSV/registry).",
                    ghost_count,
                )

            # Part A: Restore  |  Part B: Expire
            restored    = 0
            expired     = 0
            expire_rows = []   # collect first, write after read loop

            for oid, row in open_rows.items():
                try:
                    ts_str = row.get("timestamp", "")
                    try:
                        original_placed_at = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        original_placed_at = now

                    age_days  = (now - original_placed_at).days
                    strategy  = row.get("strategy", "")
                    max_carry = _carry_days_for(strategy)

                    if age_days > max_carry:
                        # PART B: too old for this strategy.
                        # For extended winners: grant up to _EXT_WINDOW_DAYS from when
                        # extension FIRED (not from trade open).  This prevents a trade
                        # that was once at +2.8R but has since weakened from getting
                        # indefinite protection — the window shrinks based on elapsed
                        # time since the extension event.
                        if oid in extended_map:
                            _ext_sl, _ext_ts = extended_map[oid]
                            _extend_age_days  = (now - _ext_ts).days
                            if _extend_age_days <= _EXT_WINDOW_DAYS:
                                pass  # extension window still open → restore (Part A below)
                            else:
                                # Window exhausted: expire at locked_sl price (not entry)
                                # so P&L reflects the protection the SL provided.
                                expire_rows.append(
                                    (oid, row, original_placed_at, age_days, max_carry, _ext_sl)
                                )
                                continue
                        else:
                            expire_rows.append(
                                (oid, row, original_placed_at, age_days, max_carry, None)
                            )
                            continue

                    # PART A: within carry window (or active extension window) — restore
                    _ext_entry = extended_map.get(oid)   # (locked_sl, ext_ts) or None
                    effective_sl = _ext_entry[0] if _ext_entry else float(row.get("stop_loss", 0) or 0)
                    rec = OrderRecord(
                        order_id    = oid,
                        symbol      = row["symbol"],
                        direction   = row["direction"],
                        quantity    = int(float(row.get("quantity", 1))),
                        entry_price = float(row.get("entry_price", 0) or 0),
                        stop_loss   = effective_sl,
                        target      = float(row.get("target",      0) or 0),
                        strategy    = strategy,
                        status      = "open",
                        # Treat restored orders as MARKET so TradeMonitor
                        # skips the LIMIT fill simulation and goes straight
                        # to SL/target evaluation.
                        order_type  = "MARKET",
                        placed_at   = original_placed_at,
                        # Restore stored confidence score so smart-swap cannot
                        # immediately evict a restored position just because 0.0 < 0.5+delta.
                        confidence_score = float(row.get("confidence", 0) or 0),
                        # Explicit governance state so any observer can see lifecycle phase.
                        governance_state  = "ACTIVE_CARRY",
                        # Carry restore: use original CSV stop_loss (before extension adjustment)
                        # as the immutable risk anchor.
                        initial_stop_loss = float(row.get("stop_loss", 0) or 0),
                        # D9-008: restore zone_price; default to entry_price if missing in
                        # older journal rows (prevents zero zone_price in re-entry checks).
                        zone_price = float(row.get("zone_price") or row.get("entry_price") or 0) or float(row.get("entry_price", 0) or 0),
                    )
                    if _ext_entry:
                        # Tell TradeMonitor (via register()) not to re-fire extension.
                        self._restored_extended_oids.add(oid)
                        _ext_age = (now - _ext_entry[1]).days
                        log.info(
                            "[OrderManager] Extended winner carry restored: %s %s  "
                            "locked_sl=%.2f  trade_age=%dd  extend_age=%dd/%dd.",
                            row.get("symbol", ""), oid, effective_sl,
                            age_days, _ext_age, _EXT_WINDOW_DAYS,
                        )
                    self._orders[oid] = rec
                    qty_signed = rec.quantity if rec.direction == "BUY" else -rec.quantity
                    pos = Position(
                        symbol          = rec.symbol,
                        quantity        = qty_signed,
                        avg_entry_price = rec.entry_price,
                        ltp             = rec.entry_price,
                        stop_loss       = rec.stop_loss,
                        target_price    = rec.target,
                        strategy_name   = rec.strategy,
                        has_live_ltp    = False,
                        restore_time    = now,
                    )
                    self._portfolio.positions[rec.symbol] = pos
                    age_min = int((now - original_placed_at).total_seconds() / 60)
                    log.info(
                        "[OrderManager] Restored carry position: %s %s  "
                        "age=%dd %dmin  strategy=%s  (max_carry=%dd)",
                        rec.symbol, oid, age_days, age_min, strategy, max_carry,
                    )
                    restored += 1

                except Exception as row_exc:
                    log.debug("[OrderManager] Skipping malformed journal row '%s': %s",
                              oid, row_exc)

            # PART B: Write SESSION_EXPIRED CLOSE rows for orphaned positions.
            # Append-only. Idempotent: next restart finds CLOSE in closed_in_csv.
            if expire_rows:
                # Batch-fetch live LTPs for all expiring symbols BEFORE writing.
                # Eliminates ₹0 PnL on SESSION_EXPIRED when real moves occurred.
                # Exit price priority: locked_SL > live_LTP > entry_price_fallback
                _expire_ltp: dict = {}
                _exp_syms = list({r.get("symbol", "") for _, r, *_ in expire_rows
                                  if r.get("symbol")})
                # Build entry-price map for LTPGuard-equivalent sanity check below.
                # key=symbol, value=entry_price float  (0 if unavailable)
                _expire_entry: dict = {
                    r.get("symbol", ""): float(r.get("entry_price") or 0)
                    for _, r, *_ in expire_rows
                    if r.get("symbol")
                }
                if _exp_syms:
                    try:
                        from data_feeds.data_feed_manager import get_feed_manager as _gfm
                        _ns_syms = [s + ".NS" for s in _exp_syms]
                        _q_map   = _gfm().get_multiple_quotes(_ns_syms)
                        for _ns, _q in _q_map.items():
                            _bare = _ns.replace(".NS", "")
                            _ltp  = (getattr(_q, "ltp", None)
                                     or getattr(_q, "last_price", None))
                            _src  = (getattr(_q, "feed_source", "") or "").upper()
                            if _ltp and float(_ltp) > 0 and _src != "SIM":
                                # ── LTPGuard-equivalent sanity check ──────────────
                                # This path has no access to TradeMonitor.LTPGuard
                                # (no last_known_good baseline).  Use entry_price as
                                # the reference.  Reject if feed deviates >25% from
                                # entry — the same class of corruption that caused the
                                # MARICO phantom P&L (+₹334k) on 2026-06-11.
                                _entry_ref = _expire_entry.get(_bare, 0)
                                if _entry_ref > 0:
                                    _dev = abs(float(_ltp) - _entry_ref) / _entry_ref
                                    if _dev > 0.25:
                                        log.warning(
                                            "[SessionExpiry] REJECTED suspicious exit price "
                                            "for %s: feed=%.2f vs entry=%.2f (%.0f%% deviation "
                                            "> 25%% guard) — possible corrupt Dhan value; "
                                            "falling back to entry_price (₹0 PnL).",
                                            _bare, float(_ltp), _entry_ref, _dev * 100,
                                        )
                                        continue   # skip — don't add to _expire_ltp
                                _expire_ltp[_bare] = round(float(_ltp), 2)
                            elif _src == "SIM":
                                log.warning(
                                    "[SessionExpiry] REJECTED SIM exit price for %s (%.2f) — "
                                    "phantom price; falling back to entry_price (₹0 PnL).",
                                    _bare, float(_ltp or 0),
                                )
                        if _expire_ltp:
                            log.info(
                                "[OrderManager] SESSION_EXPIRED: live LTP fetched for "
                                "%d/%d symbol(s): %s",
                                len(_expire_ltp), len(_exp_syms), _expire_ltp,
                            )
                    except Exception as _ltp_err:
                        log.debug(
                            "[OrderManager] SESSION_EXPIRED: LTP fetch failed (%s) — "
                            "entry_price fallback for all", _ltp_err,
                        )
                try:
                    with self._journal_lock:
                        with open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8") as fh:
                            w = csv.DictWriter(
                                fh,
                                fieldnames=_JOURNAL_HEADER,
                            )
                            for oid, row, placed_at, age_days, max_carry, locked_sl in expire_rows:
                                entry_price = float(row.get("entry_price", 0) or 0)
                                _symbol     = row.get("symbol", "")
                                _direction  = row.get("direction", "BUY")
                                _qty        = int(float(row.get("quantity", 1) or 1))
                                # Priority 1: locked SL (trailing stop already at B/E+)
                                # Priority 2: live LTP — real market exit price
                                # Priority 3: entry_price fallback (₹0 PnL only if no data)
                                if locked_sl and locked_sl != entry_price:
                                    _exit_price = round(locked_sl, 2)
                                    _pnl        = round(
                                        (locked_sl - entry_price) * _qty
                                        if _direction == "BUY"
                                        else (entry_price - locked_sl) * _qty,
                                        2,
                                    )
                                    _reason = "SESSION_EXPIRED_EXTENDED"
                                elif _symbol in _expire_ltp:
                                    _exit_price = _expire_ltp[_symbol]
                                    _pnl        = round(
                                        (_exit_price - entry_price) * _qty
                                        if _direction == "BUY"
                                        else (entry_price - _exit_price) * _qty,
                                        2,
                                    )
                                    _reason = "SESSION_EXPIRED"
                                else:
                                    _exit_price = entry_price
                                    _pnl        = 0.0
                                    _reason     = "SESSION_EXPIRED"
                                w.writerow({
                                    "timestamp":   now.strftime("%Y-%m-%d %H:%M:%S"),
                                    "order_id":    oid,
                                    "symbol":      row.get("symbol", ""),
                                    "direction":   row.get("direction", ""),
                                    "quantity":    row.get("quantity", 0),
                                    "entry_price": entry_price,
                                    "stop_loss":   row.get("stop_loss", ""),
                                    "target":      row.get("target", ""),
                                    "strategy":    row.get("strategy", ""),
                                    "confidence":  "",
                                    "rr":          "",
                                    "event":       "CLOSE",
                                    "exit_price":  _exit_price,
                                    "pnl":         _pnl,
                                    "reason":      _reason,
                                })
                                log.info(
                                    "[OrderManager] %s -> %s %s  "
                                    "age=%dd > max_carry=%dd (strategy=%s)  "
                                    "exit=%.2f  pnl=₹%+.0f. CLOSE appended.",
                                    _reason, row.get("symbol", ""), oid,
                                    age_days, max_carry, row.get("strategy", ""),
                                    _exit_price, _pnl,
                                )
                                expired += 1
                            fh.flush()
                            os.fsync(fh.fileno())
                except Exception as exp_exc:
                    log.warning("[OrderManager] SESSION_EXPIRED write failed: %s", exp_exc)

            if restored:
                log.info(
                    "[OrderManager] \u2705 Restored %d carry position(s) "
                    "(strategy-aware cross-day restore active).  "
                    "governance_state=ACTIVE_CARRY  SL/adaptive/heat: ACTIVE.",
                    restored,
                )
            if expired:
                log.info(
                    "[OrderManager] \U0001f9f9 Expired %d orphaned OPEN row(s) -> SESSION_EXPIRED. "
                    "CSV is now clean.", expired,
                )
                # SESSION_EXPIRED at startup means stale carry positions were force-closed.
                # This alters P&L records and should prevent the stability streak from
                # advancing — the session is structurally affected.
                try:
                    from learning_system.strategy_performance_tracker import get_stability_ledger
                    get_stability_ledger().flag_session_issue(
                        f"JOURNAL_RESTORE_EXPIRED: {expired} position(s) force-closed at startup")
                except Exception:
                    pass

            # Persist restore diagnostics for orchestrator + health monitors.
            # monitoring_gap_seconds and post-restore reconciliation fields are
            # populated later by orchestrator._post_restore_governance_pass().
            self._restore_stats.update({
                "restored_today":          0,
                "restored_carry":          restored,
                "expired_at_restore":      expired,
                "orphan_monitored_count":  0,
                "monitoring_gap_seconds":  0,
                "reconciled_count":        0,
                "immediate_sl_hits":       0,
                "immediate_expiries":      expired,
            })

        except Exception as exc:
            log.warning("[OrderManager] Could not restore from journal: %s", exc)

    def _reconcile_sim_paper_artifacts(self) -> int:
        """
        ORJ-001: Append-only reconciliation of historical SIM_ paper records.

        In LIVE mode _restore_from_journal() is never called, so Pass 1.9 never
        writes SESSION_EXPIRED_DEEP_ORPHAN rows.  Without this, old SIM_ OPEN
        rows persist in paper_trades.csv forever and trigger ORPHAN POSITION
        ALERTs on every container restart.

        Safety conditions (ALL must hold to reconcile a single row):
          1. order_id starts with "SIM_"   — paper record; was never sent to Dhan
          2. event OPEN with no CLOSE      — genuinely unmatched in journal
          3. age > _MAX_LOOKBACK_DAYS (7d) — outside normal restore window
          4. age ≤ _DEEP_ORPHAN_DAYS (60d) — within extended scan horizon
          5. order_id not in self._orders  — not tracked as a live position

        Appends one CLOSE row per artifact:
          reason   = PAPER_MODE_ARTIFACT
          exit_price = entry_price (₹0 P&L — no real LTP used)
          pnl      = 0.0

        Never adds any entry to self._orders.
        Fully idempotent: re-runs detect the CLOSE row and skip.

        Returns: number of records reconciled this call.
        """
        _MAX_LOOKBACK_DAYS  = 7    # consistent with _restore_from_journal
        _DEEP_ORPHAN_DAYS   = 60   # consistent with Pass 1.9

        if not os.path.exists(PAPER_TRADE_LOG):
            return 0

        now         = datetime.now()
        cutoff_dt   = now - timedelta(days=_MAX_LOOKBACK_DAYS)   # must be older than this
        deep_cutoff = now - timedelta(days=_DEEP_ORPHAN_DAYS)    # must be newer than this

        # Build set of order_ids that already have a CLOSE row (idempotency guard)
        closed_in_csv: set = set()
        try:
            with open(PAPER_TRADE_LOG, newline="", encoding="utf-8") as _fh:
                for _row in csv.DictReader(_fh):
                    _ev = _row.get("event", "").strip().upper()
                    if _ev in ("CLOSE", "CANCELLED"):
                        _oid = _row.get("order_id", "").strip()
                        if _oid:
                            closed_in_csv.add(_oid)
        except Exception as _scan_exc:
            log.debug("[ORJ001] CSV scan error: %s", _scan_exc)
            return 0

        # Identify eligible SIM_ orphans
        eligible: list = []
        try:
            with open(PAPER_TRADE_LOG, newline="", encoding="utf-8") as _fh:
                for _row in csv.DictReader(_fh):
                    _oid = _row.get("order_id", "").strip()
                    _ev  = _row.get("event", "").strip().upper()

                    if not _oid or not _oid.startswith("SIM_"):   # 1
                        continue
                    if _ev not in ("OPEN", "REENTRY_OPEN"):        # 2
                        continue
                    if _oid in closed_in_csv:                      # 2 (no CLOSE)
                        continue
                    if _oid in self._orders:                       # 5
                        continue

                    _ts = _row.get("timestamp", "")
                    try:
                        _rdt = datetime.strptime(_ts[:19], "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        continue
                    if _rdt >= cutoff_dt:    # 3: must be older than restore window
                        continue
                    if _rdt < deep_cutoff:   # 4: within extended scan horizon
                        continue

                    eligible.append((_oid, _row, _rdt))
        except Exception as _elig_exc:
            log.debug("[ORJ001] Eligibility scan error: %s", _elig_exc)
            return 0

        if not eligible:
            return 0

        # Append CLOSE rows — append-only, never rewrites existing rows
        count = 0
        try:
            with self._journal_lock:
                with open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8") as _fh:
                    _w = csv.DictWriter(_fh, fieldnames=_JOURNAL_HEADER)
                    for _oid, _row, _rdt in eligible:
                        _ep    = float(_row.get("entry_price", 0) or 0)
                        _age_d = (now - _rdt).days
                        _w.writerow({
                            "timestamp":   now.strftime("%Y-%m-%d %H:%M:%S"),
                            "order_id":    _oid,
                            "symbol":      _row.get("symbol", ""),
                            "direction":   _row.get("direction", ""),
                            "quantity":    _row.get("quantity", 0),
                            "entry_price": _ep,
                            "stop_loss":   _row.get("stop_loss", ""),
                            "target":      _row.get("target", ""),
                            "strategy":    _row.get("strategy", ""),
                            "confidence":  "",
                            "rr":          "",
                            "event":       "CLOSE",
                            "exit_price":  _ep,
                            "pnl":         0.0,
                            "reason":      "PAPER_MODE_ARTIFACT",
                        })
                        log.info(
                            "[ORJ001] PAPER_MODE_ARTIFACT: %s %s  age=%dd  "
                            "(SIM record — original OPEN preserved, CLOSE appended).",
                            _row.get("symbol", ""), _oid, _age_d,
                        )
                        count += 1
                    _fh.flush()
                    os.fsync(_fh.fileno())
        except Exception as _write_exc:
            log.warning("[ORJ001] Failed to write reconciliation rows: %s", _write_exc)
            return 0

        log.info(
            "[ORJ001] Journal reconciliation complete: %d SIM paper artifact(s) reconciled. "
            "Original OPEN rows preserved. No live positions created.",
            count,
        )
        return count

    # ── Live execution journal (JSONL) ────────────────────────────────────────
    # Written in live mode so container restarts can recover in-flight positions
    # without depending on the broker API being reachable.

    def _append_live_journal(self, event: str, rec: "OrderRecord",
                             extra: Optional[dict] = None) -> None:
        """Append one OPEN/CLOSE event line to LIVE_ORDER_LOG."""
        try:
            os.makedirs(_LIVE_DIR, exist_ok=True)
            entry: dict = {
                "event":             event,
                "timestamp":         datetime.now(timezone.utc).isoformat(),
                "order_id":          rec.order_id,
                "broker_order_id":   rec.broker_order_id,
                "symbol":            rec.symbol,
                "direction":         rec.direction,
                "quantity":          rec.quantity,
                "entry_price":       rec.entry_price,
                "stop_loss":         rec.stop_loss,
                "target_price":      rec.target,
                "strategy":          rec.strategy,
                "opportunity_id":    getattr(rec, "opportunity_id", ""),
                "fill_status":       rec.fill_status,
                "actual_fill_price": rec.actual_fill_price,
            }
            if extra:
                entry.update(extra)
            with open(LIVE_ORDER_LOG, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, default=str) + "\n")
        except Exception as exc:
            log.warning("[LiveJournal] Write failed (non-critical): %s", exc)

    def _restore_from_live_journal(self) -> None:
        """
        H-001: On live-mode startup, replay LIVE_ORDER_LOG to re-hydrate any
        open positions that were active when the container was last killed.

        Restored positions get fill_status='JOURNAL_RESTORED' so
        reconcile_startup_fills() will then fetch actual broker state.
        """
        if self._paper_mode:
            return

        opened: dict = {}
        closed: set  = set()
        closed_rows: dict = {}  # D-003: oid → CLOSE row for cooldown restore
        today  = datetime.now()
        cutoff = today - timedelta(days=7)

        if not os.path.exists(LIVE_ORDER_LOG):
            log.info("[LiveJournal] No live order journal found — starting with empty state.")
            return

        try:
            with open(LIVE_ORDER_LOG, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    oid   = row.get("order_id", "")
                    event = row.get("event", "")
                    if not oid:
                        continue
                    ts_str = row.get("timestamp", "")
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts.replace(tzinfo=None) < cutoff:
                            continue
                    except Exception:
                        pass
                    if event == "OPEN":
                        opened[oid] = row
                    elif event in ("CLOSE", "SESSION_EXPIRED", "REJECTED"):
                        closed.add(oid)
                        closed_rows[oid] = row  # D-003: keep for cooldown restore
        except Exception as exc:
            log.warning("[LiveJournal] Could not read journal at startup: %s", exc)
            return

        # D-003: Restore EARLY_LOSS cooldown state from today's CLOSE events.
        # Without this, a 24h EARLY_LOSS cooldown would be silently lost on restart,
        # allowing immediate re-entry into a losing setup.
        for oid, row in closed_rows.items():
            try:
                reason = row.get("reason", "")
                symbol = row.get("symbol", "")
                if not symbol or not reason:
                    continue
                ts_str = row.get("timestamp", "")
                close_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                close_dt = close_dt.replace(tzinfo=None)  # normalize to naive local
                direction = row.get("direction", "")
                _r = 0.0
                try:
                    entry_p = float(row.get("entry_price") or 0)
                    stop_p  = float(row.get("stop_loss") or 0)
                    pnl_v   = float(row.get("pnl") or 0)
                    qty_v   = int(row.get("quantity") or 1)
                    risk    = abs(entry_p - stop_p) * qty_v
                    _r = round(pnl_v / risk, 3) if risk > 0 else 0.0
                except Exception:
                    pass
                _RECENT_CLOSE_TIMES[symbol.strip()] = {
                    "time":      close_dt,
                    "r":         _r,
                    "direction": direction,
                    "reason":    reason,
                }
            except Exception as _ct_exc:
                log.debug("[LiveJournal] Cooldown restore error for %s: %s", oid, _ct_exc)

        if _RECENT_CLOSE_TIMES:
            log.info(
                "[LiveJournal] Restored %d close-time entries for cooldown tracking.",
                len(_RECENT_CLOSE_TIMES),
            )

        to_restore = {oid: row for oid, row in opened.items() if oid not in closed}
        if not to_restore:
            log.info("[LiveJournal] Startup: no open positions to restore.")
            return

        log.warning(
            "[LiveJournal] \u26a0\ufe0f  Restoring %d open position(s) from live journal. "
            "Verify against broker dashboard before the next cycle.",
            len(to_restore),
        )
        for oid, row in to_restore.items():
            try:
                rec = OrderRecord(
                    order_id          = oid,
                    broker_order_id   = row.get("broker_order_id") or "",
                    symbol            = row.get("symbol", "UNKNOWN"),
                    direction         = row.get("direction", "BUY"),
                    quantity          = int(row.get("quantity") or 0),
                    entry_price       = float(row.get("entry_price") or 0),
                    stop_loss         = float(row.get("stop_loss") or 0),
                    target            = float(row.get("target_price") or 0),
                    strategy          = row.get("strategy", ""),
                    fill_status       = "JOURNAL_RESTORED",
                    actual_fill_price = float(row.get("actual_fill_price") or
                                              row.get("entry_price") or 0),
                    opportunity_id    = row.get("opportunity_id") or "",
                )
                self._orders[oid] = rec
                # D-008: use Position object, not plain dict — downstream code
                # accesses pos.ltp, pos.has_live_ltp, etc. as attributes.
                _fill_price = rec.actual_fill_price or rec.entry_price
                self._portfolio.positions[rec.symbol] = Position(
                    symbol          = rec.symbol,
                    quantity        = rec.quantity if rec.direction == "BUY" else -rec.quantity,
                    avg_entry_price = _fill_price,
                    ltp             = _fill_price,
                    stop_loss       = rec.stop_loss,
                    target_price    = rec.target,
                    strategy_name   = rec.strategy,
                    has_live_ltp    = False,
                    restore_time    = datetime.now(),
                )
                log.warning(
                    "[LiveJournal] Restored: %s %s qty=%d fill=%.2f order_id=%s",
                    rec.direction, rec.symbol, rec.quantity,
                    rec.actual_fill_price, oid,
                )
            except Exception as _rec_exc:
                log.error("[LiveJournal] Could not restore order_id=%s: %s", oid, _rec_exc)

        self._restore_stats["restored_today"] = len(to_restore)

    def reconcile_startup_fills(self) -> int:
        """
        On startup: query Dhan for any restored live order whose fill_status
        is blank (not yet reconciled from a prior run).

        Safe to call at startup after _restore_from_journal().
        Never raises.  Returns count of orders reconciled.
        """
        if self._paper_mode or not self._broker:
            return 0
        if not hasattr(self._broker, "get_fill_details"):
            log.debug("[StartupReconcile] broker has no get_fill_details — skipped.")
            return 0
        reconciled = 0
        for oid, rec in list(self._orders.items()):
            if rec.fill_status not in ("", "PENDING", "UNRESOLVED", "JOURNAL_RESTORED"):
                continue  # already resolved
            if oid.startswith("SIM_"):
                continue  # paper / sim — not a live order
            self._reconcile_fill(rec)
            reconciled += 1
            log.info(
                "[StartupReconcile] order_id=%s symbol=%s fill_status=%s "
                "fill_price=%.2f filled_qty=%d",
                oid, rec.symbol, rec.fill_status,
                rec.actual_fill_price, rec.filled_quantity,
            )
            # If broker says REJECTED or CANCELLED: deregister to avoid phantom position
            if rec.fill_status in ("REJECTED", "CANCELLED"):
                self._orders.pop(oid, None)
                self._portfolio.positions.pop(rec.symbol, None)
                log.warning(
                    "[StartupReconcile] %s order %s has broker status %s — "
                    "removed phantom position.",
                    rec.symbol, oid, rec.fill_status,
                )
        if reconciled:
            log.info(
                "[StartupReconcile] Reconciled %d order(s) at startup. "
                "Broker is the source of truth for live fill status.",
                reconciled,
            )
        return reconciled

