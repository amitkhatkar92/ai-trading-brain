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
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
_JOURNAL_HEADER  = [
    "timestamp", "order_id", "symbol", "direction", "quantity",
    "entry_price", "stop_loss", "target", "strategy",
    "confidence", "rr", "event",
]

# Closed-order registry: one order_id per line, new file each calendar day.
# Used by _restore_from_journal to filter ghost OPEN rows whose CLOSE event
# was written but the CSV write failed (e.g. process killed mid-write).
def _closed_registry_path() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(_DATA_DIR, f"closed_orders_{today}.txt")

# ── Strategy-aware carry restore window ──────────────────────────────────
# Controls how many calendar days a position is allowed to carry before it
# is treated as a genuine orphan and excluded from journal restore.
# Matching is prefix-based and case/underscore-insensitive.
CARRY_RESTORE_DAYS = 7   # rolling window — must match or exceed max carry

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
    """Return the max carry days for a given strategy name."""
    key = strategy.lower().replace("_", "").replace("-", "").replace(" ", "")
    for prefix, days in _CARRY_DAYS_BY_TYPE.items():
        if key.startswith(prefix):
            return days
    return _CARRY_DAYS_DEFAULT

# ── Duplicate-guard LTP freshness thresholds ─────────────────────────────
_DUP_GUARD_STALE_AFTER_S    = 120  # LTP age (s) above which we mark stale
_DUP_GUARD_FRESH_COOLDOWN_S =  30  # after going stale, wait this long before fresh again
_DUP_GUARD_LTP_CONF_TICKS   =   2  # minimum consecutive fresh ticks for full R confidence

# ── Risk Guards (prevent trade volume explosion & duplicates) ──────────────
MAX_OPEN_POSITIONS = 15       # maximum concurrent positions (INCREASED 5→15 for capital deployment)
MAX_CAPITAL_PER_TRADE_PCT = 25.0  # max % of capital per single trade (pilot: ₹20k → ₹5k)
MAX_TOTAL_OPEN_EXPOSURE_PCT = 85.0  # max % of total capital in open positions (INCREASED 65→85)


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
    # Governance state — explicitly tracks position lifecycle for risk oversight.
    # ACTIVE           : normal in-carry monitored position
    # ACTIVE_CARRY     : restored multi-day carry, fully governed
    # ORPHAN_WATCH     : past carry_limit, monitoring continues until SESSION_EXPIRED closes it
    # EXPIRED_PENDING  : SESSION_EXPIRED written to CSV, awaiting final deregister
    governance_state:  str  = "ACTIVE"   # see constants above
    orphan_watch:      bool = False       # True if past carry_limit; monitoring still active


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
        # Restore diagnostics: populated by _restore_from_journal() each startup.
        # Persisted for the lifetime of the process so health monitors and
        # daily reports can always surface restore integrity.
        self._restore_stats: Dict[str, Any] = {
            "restored_today":         0,
            "restored_carry":         0,
            "skipped_closed":         0,
            "skipped_expired":        0,   # always 0 now — orphans are monitored, not dropped
            "orphan_watch":           0,   # positions restored past carry_limit (monitored)
            "orphan_monitored_count": 0,
            "monitoring_gap_seconds": 0,
        }
        if self._paper_mode:
            os.makedirs(_DATA_DIR, exist_ok=True)
            log.info("[OrderManager] PAPER TRADING mode — no live orders will be sent.")
            log.info("[OrderManager] Trade journal: %s", os.path.abspath(PAPER_TRADE_LOG))
            self._restore_from_journal()   # re-hydrate open positions after any restart
            self._prefetch_restored_ltps() # immediately resolve LTP for restored positions
        else:
            log.info("[OrderManager] Active broker: %s", ACTIVE_BROKER.upper())

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────────────────────────

    def inject_trade_monitor(self, trade_monitor) -> None:
        """Wire in the TradeMonitor so smart-swap can deregister replaced positions."""
        self._trade_monitor = trade_monitor

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
        # ── FIX 1: Guard against duplicate trades on same symbol ──────
        _new_score = float(getattr(decision, "confidence_score", 5.0))
        if self._symbol_has_open_position(signal.symbol):
            if not self._dup_guard_reentry_check(
                signal.symbol,
                decision_score=_new_score,
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
                    _swap_rec = self._orders[_swap_oid]
                    _swap_pos = self._portfolio.positions.get(_swap_sym)
                    _exit_px = (
                        _swap_pos.ltp
                        if _swap_pos and _swap_pos.has_live_ltp and _swap_pos.ltp > 0
                        else _swap_rec.entry_price
                    )
                    self.close_position(_swap_oid, _exit_px, reason="REPLACEMENT")
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
                _swap_rec = self._orders[_swap_oid]
                _swap_pos = self._portfolio.positions.get(_swap_sym)
                _exit_px = (
                    _swap_pos.ltp
                    if _swap_pos and _swap_pos.has_live_ltp and _swap_pos.ltp > 0
                    else _swap_rec.entry_price
                )
                self.close_position(_swap_oid, _exit_px, reason="REPLACEMENT")
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

        qty = int(signal.quantity * decision.position_size_modifier)
        if qty <= 0:
            log.warning("[OrderManager] Zero quantity after modifier for %s.", signal.symbol)
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
        )
        self._orders[order_id] = record
        self._update_portfolio(signal, qty)

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

        # Reverse direction to close — use MARKET so exits always fill immediately
        close_dir = "SELL" if rec.direction == "BUY" else "BUY"
        self._broker_place(rec.symbol, close_dir, rec.quantity, exit_price,
                           order_type="MARKET")

        pnl = (exit_price - rec.entry_price) * rec.quantity
        if rec.direction in ("SELL", "SHORT"):
            pnl = -pnl

        rec.status    = "closed"
        rec.pnl       = round(pnl, 2)
        rec.closed_at = datetime.now()
        self._portfolio.realised_pnl += pnl

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
        return True

    def close_all_positions(self):
        log.warning("[OrderManager] ⚠ Closing ALL positions.")
        for oid, rec in list(self._orders.items()):
            if rec.status == "open":
                self.close_position(oid, rec.entry_price, reason="emergency_close")

    def get_portfolio(self) -> Portfolio:
        return self._portfolio

    def get_open_orders(self) -> List[OrderRecord]:
        return [r for r in self._orders.values() if r.status == "open"]

    def get_open_order_ids(self) -> frozenset:
        """Return frozenset of all order_ids currently tracked as open in memory.
        Used by CycleHealthMonitor to distinguish legitimate carries from CSV orphans."""
        return frozenset(
            oid for oid, rec in self._orders.items() if rec.status == "open"
        )

    def get_restore_stats(self) -> Dict[str, int]:
        """Return the restore diagnostics captured at startup by _restore_from_journal().
        Keys: restored_today, restored_carry, skipped_closed, skipped_expired, orphan_watch.
        Values are 0 when PAPER_TRADING is False or before the first restore completes."""
        return dict(self._restore_stats)

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
                signal_regime = slot.signal_regime,
                signal_vix    = slot.signal_vix,
            )
            self._orders[order_id] = rec
            self._update_portfolio(slot.signal, slot.qty)

            log.info(
                "[OrderManager] ✅ AET CONFIRMED: %s %s  "
                "zone=%.2f  waited=%d candles  order=%s",
                direction, slot.signal.symbol,
                _confirmed_zone, slot.candles_waited, order_id,
            )
            if self._paper_mode:
                self._journal_write_aet_confirmed(rec, slot)

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

            # Journal the cancellation
            if self._paper_mode:
                self._journal_cancel(rec, reason=cancel_reason)

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
                signal_regime = slot.signal_regime,
                signal_vix    = slot.signal_vix,
            )
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
                    w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER + ["exit_price", "pnl", "reason"])
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

    def _journal_write_reentry(self, rec: "OrderRecord",
                               slot: "ReentrySlot") -> None:
        """Append a REENTRY_OPEN row to the paper trade CSV journal."""
        try:
            write_header = not os.path.exists(PAPER_TRADE_LOG)
            with open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8") as fh:
                extra = ["exit_price", "pnl", "reason", "retry_attempt"]
                w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER + extra)
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
                w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER + ["exit_price", "pnl", "reason"])
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
        return None

    def _broker_place(self, symbol: str, direction: str,
                       qty: int, price: float,
                       order_type: str = "LIMIT") -> Optional[str]:
        if not self._broker:
            log.info("[OrderManager] [SIM-%s] %s %s qty=%d @ %.2f",
                     order_type, direction, symbol, qty, price)
            return f"SIM_{symbol}_{direction}_{qty}"
        return self._broker.place_order(
            symbol=symbol, exchange="NSE",
            transaction_type=direction, quantity=qty, price=price,
            order_type=order_type,
        )

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
        """
        symbols = [
            sym for sym, pos in self._portfolio.positions.items()
            if not pos.has_live_ltp
        ]
        if not symbols:
            return
        try:
            from data_feeds import get_feed_manager
            quotes = get_feed_manager().get_multiple_quotes(symbols)
            fetched = 0
            now_dt = datetime.now()
            for sym, quote in (quotes or {}).items():
                if quote and quote.ltp and quote.ltp > 0:
                    pos = self._portfolio.positions.get(sym)
                    if pos is not None:
                        pos.ltp           = quote.ltp
                        pos.has_live_ltp  = True
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
        """Check if the symbol already has an open position (symbol deduplication)."""
        for rec in self._orders.values():
            if rec.symbol == symbol and rec.status == "open":
                return True
        return False

    # ── Smart-Swap constants ───────────────────────────────────────────────
    _SWAP_MIN_AGE_MIN    = 20.0   # never evict a position younger than this
    _SWAP_SAFE_R         = 1.5    # never evict a position running at +1.5R or better
    _SWAP_SCORE_DELTA    = 0.5    # new signal must beat weakest entry score by this margin
    _SWAP_MIN_NEW_RR     = 1.5    # new signal must have target/risk >= this (expected R)

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
                                   decision_score: float = 0.0) -> bool:
        """
        Re-entry unlock logic for the duplicate guard.

        Returns True  → allow the new trade (logs DupGuardOverride)
        Returns False → block the new trade (logs DupGuardBlock)

        Rules
        -----
        Block unconditionally if:
          • Already 2+ open positions for this symbol (hard cap)
          • The existing trade is < 15 minutes old
          • The existing trade R < -0.5 (already in loss — do not add)

        Allow if ANY of:
          • Condition A: existing trade R >= +1.0 (running well)
          • Condition B: trade age >= 180 minutes (stale / overnight)
        """
        now = datetime.now()

        # Expire missed-opportunity records older than 30 minutes.
        _expired = [
            s for s, ts in self._ltp_blocked_symbols.items()
            if (now - ts).total_seconds() > 1800
        ]
        for s in _expired:
            self._ltp_blocked_symbols.pop(s, None)

        open_recs = [
            rec for rec in self._orders.values()
            if rec.symbol == symbol and rec.status == "open"
        ]

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
                    "[DupGuard] %s low-confidence LTP bypassed — strong signal score=%.1f (tick=%d/%d).",
                    symbol, decision_score, pos.ltp_tick_count, _DUP_GUARD_LTP_CONF_TICKS,
                )
            else:
                log.info(
                    "[DupGuard] %s low-confidence LTP (tick=%d/%d) → using age-only.",
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

        # Condition B: position is stale / has been open 90+ minutes
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
        """
        On startup, scan the paper-trade CSV over a rolling CARRY_RESTORE_DAYS
        window and restore all positions that are genuinely open (OPEN event
        with no subsequent CLOSE / CANCELLED / SESSION_EXPIRED / SYSTEM_CLEANUP).

        Multi-day carry positions survive Docker restarts and remain fully
        governed by:
          - SL / target monitoring  (TradeMonitor)
          - DupGuard                (duplicate-signal block)
          - Portfolio heat          (exposure guard)
          - Carry expiry            (age > strategy limit -> SESSION_EXPIRED)
          - Adaptive exits

        Restore diagnostics logged at INFO level:
          restored_today=N    -- same-day positions re-hydrated
          restored_carry=N    -- multi-day carry positions re-hydrated
          skipped_closed=N    -- already closed within window (correct lifecycle)
          skipped_expired=N   -- age exceeds strategy carry limit (not restored)
          orphan_watch=N      -- same as skipped_expired (CycleHealthMonitor bucket)
        """
        if not os.path.exists(PAPER_TRADE_LOG):
            return

        now        = datetime.now()
        today      = now.date()
        today_str  = today.strftime("%Y-%m-%d")
        cutoff_str = (today - timedelta(days=CARRY_RESTORE_DAYS)).strftime("%Y-%m-%d")

        # Load closed-order registries for every day in the carry window.
        # Each daily registry lists order_ids that were explicitly closed
        # (CLOSE event written + fsync'd) even if the CSV row was lost mid-write.
        closed_registry: set = set()
        for offset in range(CARRY_RESTORE_DAYS + 1):
            day_str  = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
            reg_path = os.path.join(_DATA_DIR, f"closed_orders_{day_str}.txt")
            try:
                if os.path.exists(reg_path):
                    with open(reg_path, encoding="utf-8") as rf:
                        for line in rf:
                            oid_r = line.strip()
                            if oid_r:
                                closed_registry.add(oid_r)
            except Exception as reg_exc:
                log.debug("[OrderManager] Could not read closed registry %s: %s",
                          reg_path, reg_exc)

        # Valid close events -- any of these means the position is no longer open
        _CLOSE_EVENTS = frozenset({
            "CLOSE", "CANCELLED", "SESSION_EXPIRED",
            "SESSION_EXPIRED_EXTENDED", "SYSTEM_CLEANUP",
        })

        try:
            # open_rows: order_id -> (row dict, date_str of the OPEN row)
            open_rows: dict[str, tuple] = {}
            skipped_closed = 0

            with open(PAPER_TRADE_LOG, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    ts = row.get("timestamp", "")
                    if not ts:
                        continue
                    row_date_str = ts[:10]          # "YYYY-MM-DD"
                    if row_date_str < cutoff_str:   # outside restore window
                        continue

                    oid   = row.get("order_id", "").strip()
                    event = row.get("event", "").strip().upper()
                    if not oid:
                        continue

                    if event in ("OPEN", "REENTRY_OPEN"):
                        open_rows[oid] = (row, row_date_str)
                    elif event in _CLOSE_EVENTS:
                        if open_rows.pop(oid, None) is not None:
                            skipped_closed += 1   # had OPEN then CLOSE -- properly closed

            # Belt-and-suspenders: remove registry ghosts even if the CSV CLOSE
            # row was lost due to a crash mid-write.
            ghost_count = 0
            for oid_c in list(open_rows.keys()):
                if oid_c in closed_registry:
                    open_rows.pop(oid_c)
                    ghost_count += 1
                    skipped_closed += 1
            if ghost_count:
                log.info(
                    "[OrderManager] Filtered %d ghost OPEN row(s) via closed registry.",
                    ghost_count,
                )

            # Classify and restore net-open positions
            restored_today    = 0
            restored_carry    = 0
            skipped_expired   = 0   # always stays 0 — orphans are monitored now
            orphan_monitored  = 0   # positions past carry_limit restored under governance

            for oid, (row, row_date_str) in open_rows.items():
                try:
                    ts_str = row.get("timestamp", "")
                    try:
                        original_placed_at = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        original_placed_at = now

                    age_days  = (now - original_placed_at).total_seconds() / 86_400
                    strategy  = row.get("strategy", "")
                    max_carry = _carry_days_for(strategy)

                    # ── GOVERNANCE RULE: no position may leave monitoring coverage ──
                    # Even when age > carry_limit, the position retains FULL governance:
                    #   SL monitoring, adaptive exits, portfolio heat, MTM updates.
                    # Execution is restricted (no new entries on the symbol) but all
                    # risk controls remain ACTIVE until SESSION_EXPIRED closes it cleanly.
                    is_orphan = age_days > max_carry
                    if is_orphan:
                        log.warning(
                            "[OrderManager] ORPHAN_WATCH %s [%s]  "
                            "age=%.1fd > carry_limit=%dd  strategy=%s "
                            "— governance monitoring continues until SESSION_EXPIRED.",
                            row.get("symbol", "?"), oid,
                            age_days, max_carry, strategy or "unknown",
                        )
                        # Do NOT continue — fall through to restore with governance active

                    rec = OrderRecord(
                        order_id     = oid,
                        symbol       = row["symbol"],
                        direction    = row["direction"],
                        quantity     = int(float(row.get("quantity", 1))),
                        entry_price  = float(row.get("entry_price", 0) or 0),
                        stop_loss    = float(row.get("stop_loss",   0) or 0),
                        target       = float(row.get("target",      0) or 0),
                        strategy     = strategy,
                        status       = "open",
                        # MARKET type: TradeMonitor skips LIMIT fill simulation
                        # and goes straight to SL/target evaluation.
                        order_type   = "MARKET",
                        placed_at    = original_placed_at,
                        # Preserve stored confidence so smart-swap cannot evict
                        # a restored position just because confidence 0.0 < 0.5+delta.
                        confidence_score = float(row.get("confidence", 0) or 0),
                        # Governance state — explicit lifecycle visibility
                        orphan_watch     = is_orphan,
                        governance_state = "ORPHAN_WATCH" if is_orphan else "ACTIVE_CARRY",
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
                        has_live_ltp    = False,   # no live feed yet
                        restore_time    = now,     # decision latency baseline
                    )
                    self._portfolio.positions[rec.symbol] = pos
                    age_min = int(age_days * 1_440)

                    if is_orphan:
                        orphan_monitored += 1
                        log.info(
                            "[OrderManager] Restored (orphan_watch)  %s  age=%.1fd > carry=%dd  "
                            "strategy=%s  SL=%.2f  — SL/adaptive/heat active until SESSION_EXPIRED.",
                            rec.symbol, age_days, max_carry, strategy, rec.stop_loss,
                        )
                    elif row_date_str == today_str:
                        restored_today += 1
                        log.info(
                            "[OrderManager] Restored (today)  %s  age=%d min  strategy=%s",
                            rec.symbol, age_min, strategy,
                        )
                    else:
                        restored_carry += 1
                        log.info(
                            "[OrderManager] Restored (carry)  %s  age=%.1fd  "
                            "carry_limit=%dd  strategy=%s",
                            rec.symbol, age_days, max_carry, strategy,
                        )

                except Exception as row_exc:
                    log.debug(
                        "[OrderManager] Skipping malformed journal row '%s': %s",
                        oid, row_exc,
                    )

            orphan_watch   = orphan_monitored   # CHM ORPHAN_WATCH bucket alias
            total_restored = restored_today + restored_carry + orphan_monitored
            log.info(
                "[OrderManager] Journal restore complete -- window=%dd  "
                "restored_today=%d  restored_carry=%d  orphan_monitored=%d  "
                "skipped_closed=%d  skipped_expired=%d",
                CARRY_RESTORE_DAYS,
                restored_today, restored_carry, orphan_monitored,
                skipped_closed, skipped_expired,
            )
            if total_restored:
                log.info(
                    "[OrderManager] %d position(s) active: "
                    "SL/target/DupGuard/portfolio-heat all governed  "
                    "(%d in orphan_watch state).",
                    total_restored, orphan_monitored,
                )
            else:
                log.info("[OrderManager] No open positions found in journal -- clean start.")

            # Persist stats for health monitors and daily reports.
            self._restore_stats = {
                "restored_today":         restored_today,
                "restored_carry":         restored_carry,
                "skipped_closed":         skipped_closed,
                "skipped_expired":        skipped_expired,
                "orphan_watch":           orphan_watch,
                "orphan_monitored_count": orphan_monitored,
                "monitoring_gap_seconds": 0,   # populated by orchestrator post-restore pass
            }

        except Exception as exc:
            log.warning("[OrderManager] Could not restore from journal: %s", exc)
