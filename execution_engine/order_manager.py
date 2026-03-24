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
import time
from dataclasses import dataclass, field
from datetime import datetime
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
AET_VIX_CONFIRM_THRESHOLD = 18.0  # VIX must be below this to confirm entry
AET_PULLBACK_DIP_PCT      = 0.10  # extra % deeper into zone for PULLBACK mode
AET_MAX_WAIT_CANDLES      = 1     # max candles a CONFIRMATION slot may wait [REDUCED 2→1]

# ── Paper trade journal ───────────────────────────────────────────────────
_DATA_DIR        = os.path.join(os.path.dirname(__file__), "..", "data")
PAPER_TRADE_LOG  = os.path.join(_DATA_DIR, "paper_trades.csv")
_JOURNAL_HEADER  = [
    "timestamp", "order_id", "symbol", "direction", "quantity",
    "entry_price", "stop_loss", "target", "strategy",
    "confidence", "rr", "event",
]

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
        if self._paper_mode:
            os.makedirs(_DATA_DIR, exist_ok=True)
            log.info("[OrderManager] PAPER TRADING mode — no live orders will be sent.")
            log.info("[OrderManager] Trade journal: %s", os.path.abspath(PAPER_TRADE_LOG))
        else:
            log.info("[OrderManager] Active broker: %s", ACTIVE_BROKER.upper())

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────────────────────────

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
        if self._symbol_has_open_position(signal.symbol):
            log.warning(
                "[OrderManager] ❌ DUP GUARD: %s already has open position. "
                "Rejecting new entry to prevent duplicate trades.",
                signal.symbol
            )
            return None

        # ── FIX 2: Guard against position explosion ────────────────────
        open_count = len(self.get_open_orders())
        if open_count >= MAX_OPEN_POSITIONS:
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

        log.info("[OrderManager] ➡  Executing LIMIT %s %s qty=%d  signal=%.2f  "
                 "zone=%.2f  SL=%.2f  TGT=%.2f",
                 signal.direction.value, signal.symbol,
                 qty, signal.entry_price,
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

        log.info("[OrderManager] Position closed: %s | PnL=₹%+,.0f | Reason=%s",
                 rec.symbol, pnl, reason)
        if self._paper_mode:
            self._journal_write_close(rec, exit_price, reason)
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

    def _symbol_has_open_position(self, symbol: str) -> bool:
        """Check if the symbol already has an open position (symbol deduplication)."""
        for rec in self._orders.values():
            if rec.symbol == symbol and rec.status == "open":
                return True
        return False
