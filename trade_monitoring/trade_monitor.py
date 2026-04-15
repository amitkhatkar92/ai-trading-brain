"""
Trade Monitor — Layer 9
==========================
Watches all open positions in real time and takes autonomous action
when predefined triggers are hit.

Actions:
  • Move stop to breakeven when 1R profit is reached
  • Trail stop when 2R profit is reached
  • Close position at target
  • Emergency close on maximum adverse excursion
  • Alert when market conditions change adversely mid-trade
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from execution_engine.order_manager import OrderRecord
from utils import get_logger
from trade_monitoring.trade_analytics import TradeAnalytics

try:
    import config as _cfg
    _AE_ENABLED            = getattr(_cfg, "ENABLE_ADAPTIVE_EXIT",             True)
    _AE_TIME_MIN           = getattr(_cfg, "ADAPTIVE_TIME_STALE_MINUTES",       180)
    _AE_STALE_MAX_R        = getattr(_cfg, "ADAPTIVE_STALE_MAX_R",              0.30)
    _AE_EARLY_LOSS_R       = getattr(_cfg, "ADAPTIVE_EARLY_LOSS_R",            -0.60)
    _AE_LOSS_TRENDING_R    = getattr(_cfg, "ADAPTIVE_EARLY_LOSS_TRENDING_R",   -0.70)
    _AE_LOSS_SIDEWAYS_R    = getattr(_cfg, "ADAPTIVE_EARLY_LOSS_SIDEWAYS_R",   -0.50)
    _AE_GUARD_R            = getattr(_cfg, "ADAPTIVE_MIN_R_TO_GUARD",           2.50)
    # ── Adaptive Profit Extension ───────────────────────────────────────
    _EXT_ENABLED           = getattr(_cfg, "ENABLE_ADAPTIVE_EXTENSION",          True)
    _EXT_TRIGGER_R         = getattr(_cfg, "ADAPTIVE_EXTENSION_TRIGGER_R",        2.80)
    _EXT_LOCK_R            = getattr(_cfg, "ADAPTIVE_EXTENSION_LOCK_R",           2.50)
    _EXT_LOCK_STRONG_R     = getattr(_cfg, "ADAPTIVE_EXTENSION_LOCK_STRONG_R",    2.70)
    _EXT_STRONG_R          = getattr(_cfg, "ADAPTIVE_EXTENSION_STRONG_R",         3.10)
    _EXT_MAX_VIX           = getattr(_cfg, "ADAPTIVE_EXTENSION_MAX_VIX",         20.0)
    _EXT_TARGET_PCT        = getattr(_cfg, "ADAPTIVE_EXTENSION_TARGET_PCT",        0.10)
    _EXT_TIME_CAP_MIN      = getattr(_cfg, "ADAPTIVE_EXTENSION_TIME_CAP_MIN",     90)
except Exception:
    _AE_ENABLED            = True
    _AE_TIME_MIN           = 180
    _AE_STALE_MAX_R        = 0.30
    _AE_EARLY_LOSS_R       = -0.60
    _AE_LOSS_TRENDING_R    = -0.70
    _AE_LOSS_SIDEWAYS_R    = -0.50
    _AE_GUARD_R            = 2.50
    _EXT_ENABLED           = True
    _EXT_TRIGGER_R         = 2.80
    _EXT_LOCK_R            = 2.50
    _EXT_LOCK_STRONG_R     = 2.70
    _EXT_STRONG_R          = 3.10
    _EXT_MAX_VIX           = 20.0
    _EXT_TARGET_PCT        = 0.10
    _EXT_TIME_CAP_MIN      = 90

log = get_logger(__name__)


class TradeMonitor:
    """
    Monitors open positions tick-by-tick (or on each polling cycle)
    and manages the trade lifecycle post-entry.
    """

    R_BREAKEVEN_TRIGGER  = 1.0   # Move SL to breakeven after 1R
    R_TRAIL_TRIGGER      = 2.0   # Start trailing after 2R
    R_TARGET_TRIGGER     = 3.0   # Close at 3R (if no separate target)
    MAX_ADVERSE_EXCURSION = 0.015 # Close if LTP moves 1.5% beyond SL (gap risk)

    def __init__(self):
        self._open_orders: Dict[str, OrderRecord] = {}   # order_id → OrderRecord
        self._closed_orders: List[OrderRecord]    = []
        self._order_manager                       = None  # injected by orchestrator
        # Adaptive Exit: track peak R-multiple per order (guards against closing
        # trades that were strongly in profit before current drawback)
        self._peak_r: Dict[str, float]            = {}   # order_id → max R seen
        self._adaptive_reasons: Dict[str, str]    = {}   # order_id → reason string
        # Adaptive Profit Extension: track which orders have been extended (one-time only)
        self._extended: Dict[str, bool]           = {}   # order_id → True once SL locked
        self._extended_at: Dict[str, datetime]    = {}   # order_id → wall time of extension
        # Momentum confirmation: rolling LTP history per order (last 3 LTPs).
        # Using a 3-entry window avoids single-tick noise: extension only fires
        # when ≥2 of the last 2 consecutive moves are in the right direction.
        self._ltp_history: Dict[str, List[float]]  = {}  # order_id → [oldest…newest], max 3
        # Market context (updated each monitoring cycle by orchestrator)
        self._last_regime: str   = ""    # e.g. "bull_trend", "range_market"
        self._last_vix:    float = 0.0
        # Performance analytics: records every trade close for daily report
        self._analytics: TradeAnalytics       = TradeAnalytics()
        self._r_at_extension: Dict[str, float] = {}  # oid → R when extension fired
        log.info("[TradeMonitor] Initialised.")

    # ─────────────────────────────────────────────────────────────────
    # REGISTRATION
    # ─────────────────────────────────────────────────────────────────

    def register(self, order: OrderRecord):
        """Register a newly placed order for monitoring."""
        self._open_orders[order.order_id] = order
        self._peak_r[order.order_id]   = 0.0   # initialise peak tracker
        self._ltp_history[order.order_id] = [order.entry_price]  # seed momentum history
        log.info("[TradeMonitor] Registered: %s %s qty=%d entry=%.2f",
                 order.symbol, order.direction, order.quantity, order.entry_price)

    def inject_order_manager(self, order_manager):
        """Inject OrderManager so monitor can close positions."""
        self._order_manager = order_manager

    def update_market_context(self, regime: str, vix: float) -> None:
        """Called by orchestrator before each monitoring cycle with current regime/VIX."""
        self._last_regime = regime or ""
        self._last_vix    = vix or 0.0

    # ─────────────────────────────────────────────────────────────────
    # MONITORING CYCLE
    # ─────────────────────────────────────────────────────────────────

    def check_all(self, price_feed: Optional[Dict[str, float]] = None):
        """
        Called every N minutes.
        price_feed: dict of {symbol: ltp} — if None, simulates prices.

        For LIMIT orders in paper mode: only proceed with SL/target evaluation
        once the market price has actually reached (crossed) the zone_price.
        Until then, send no noise — a "⏳ Limit Pending" was already sent at placement.
        When fill is confirmed, send "Trade Opened" and downgrade to MARKET so
        subsequent cycles evaluate SL/target normally.
        """
        closed_ids = []
        for oid, order in self._open_orders.items():
            ltp = self._get_ltp(order.symbol, price_feed)
            if ltp is None:
                continue

            # ── Paper LIMIT fill simulation ────────────────────────────
            # A LIMIT order was placed but is not filled until LTP crosses
            # the zone_price.  Skip SL/target evaluation until then.
            if order.order_type == "LIMIT":
                zone_px = getattr(order, "zone_price", 0.0)
                if zone_px > 0.0:
                    is_long = order.direction == "BUY"
                    filled = (is_long and ltp <= zone_px) or \
                             (not is_long and ltp >= zone_px)
                    if not filled:
                        continue   # price not yet reached — skip this cycle

                    # Price has crossed the limit — confirm fill
                    order.order_type  = "MARKET"   # mark filled for future cycles
                    order.entry_price = zone_px    # PnL based on actual fill price
                    log.info(
                        "[TradeMonitor] ✅ LIMIT FILL confirmed: %s @ %.2f "
                        "(LTP=%.2f)",
                        order.symbol, zone_px, ltp,
                    )
                    try:
                        from notifications.notifier_manager import get_notifier
                        rr = (abs(order.target - zone_px) / abs(zone_px - order.stop_loss)
                              if order.stop_loss and order.stop_loss != zone_px else 0)
                        get_notifier().trade_opened(
                            symbol=order.symbol,
                            direction=order.direction,
                            entry=zone_px,
                            stop=order.stop_loss,
                            target=order.target,
                            strategy=order.strategy,
                            mode="paper",
                        )
                    except Exception:
                        pass
                    continue   # evaluate SL/target from next cycle onward

            action = self._evaluate(order, ltp)
            if not action and _AE_ENABLED:
                action = self._adaptive_check(oid, order, ltp)
            if action:
                self._act(oid, order, ltp, action)
                if action in ("close_target", "close_emergency", "close_eod",
                              "close_sl", "adaptive_exit"):
                    closed_ids.append(oid)

        for oid in closed_ids:
            self._closed_orders.append(self._open_orders.pop(oid))
            self._peak_r.pop(oid, None)           # clean up peak tracker
            self._adaptive_reasons.pop(oid, None) # clean up reason store
            self._extended.pop(oid, None)          # clean up extension flag
            self._extended_at.pop(oid, None)       # clean up extension timestamp
            self._ltp_history.pop(oid, None)        # clean up momentum history
            self._r_at_extension.pop(oid, None)    # clean up extension baseline
        # Append current LTP to rolling history for all still-open orders.
        # Keep only the last 3 entries (enough for 2-step direction check).
        for oid, order in self._open_orders.items():
            _cur = self._get_ltp(order.symbol, price_feed)
            if _cur is not None:
                hist = self._ltp_history.setdefault(oid, [_cur])
                hist.append(_cur)
                if len(hist) > 3:
                    del hist[0]

    # ─────────────────────────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────────────────────────

    def _evaluate(self, order: OrderRecord, ltp: float) -> Optional[str]:
        entry  = order.entry_price
        sl     = order.stop_loss
        target = order.target

        is_long = order.direction == "BUY"
        risk    = abs(entry - sl) if sl else 0.0

        if risk == 0:
            return None

        unrealised  = (ltp - entry) if is_long else (entry - ltp)
        r_multiple  = unrealised / risk

        # ── Check: target hit (or near-target extension intercept) ───────────────
        if target and ((is_long and ltp >= target) or (not is_long and ltp <= target)):
            # Adaptive Profit Extension: intercept the exit if conditions are strong.
            # Only fires once per trade; never modifies order.target.
            oid = order.order_id
            if _EXT_ENABLED and self._can_extend(oid, r_multiple, order):
                # Dynamic lock: strong move gets higher protection
                lock_r  = _EXT_LOCK_STRONG_R if r_multiple >= _EXT_STRONG_R else _EXT_LOCK_R
                locked_sl = (entry + risk * lock_r) if is_long \
                             else (entry - risk * lock_r)
                order.stop_loss = round(locked_sl, 2)
                self._extended[oid]        = True
                self._extended_at[oid]     = datetime.now()
                self._r_at_extension[oid]  = r_multiple   # baseline for impact calc
                self._analytics.mark_extension(oid, r_multiple)
                log.info(
                    "[AdaptiveExtension] HOLD → near target  %s  "
                    "r=%.2fR  sl_locked=%.2f (%.1fR)  regime=%s  vix=%.1f",
                    order.symbol, r_multiple, order.stop_loss,
                    lock_r, self._last_regime, self._last_vix,
                )
                return None   # do NOT exit — trailing takes over from next cycle
            return "close_target"

        # ── Check: stop loss hit ──────────────────────────────────────
        if (is_long and ltp <= sl) or (not is_long and ltp >= sl):
            return "close_sl"

        # ── Update peak R tracker for adaptive guardrails ─────────────
        if _AE_ENABLED:
            prev_peak = self._peak_r.get(order.order_id, 0.0)
            if r_multiple > prev_peak:
                self._peak_r[order.order_id] = r_multiple

        # ── Check: 2R → trail stop ────────────────────────────────────
        if r_multiple >= self.R_TRAIL_TRIGGER:
            new_sl = ltp - risk if is_long else ltp + risk
            if (is_long and new_sl > sl) or (not is_long and new_sl < sl):
                order.stop_loss = round(new_sl, 2)
                log.info("[TradeMonitor] 🔄 Trail SL %s → %.2f (R=%.1f)",
                         order.symbol, order.stop_loss, r_multiple)

        # ── Check: 1R → move to breakeven ─────────────────────────────
        elif r_multiple >= self.R_BREAKEVEN_TRIGGER:
            if (is_long and sl < entry) or (not is_long and sl > entry):
                order.stop_loss = entry
                log.info("[TradeMonitor] 🔒 Breakeven SL %s → %.2f",
                         order.symbol, entry)

        return None

    def _can_extend(self, oid: str, r_multiple: float,
                    order: OrderRecord) -> bool:
        """
        Adaptive Profit Extension gate — 4-condition check:

        1. Not already extended (one-time only)
        2. Regime = bull_trend AND VIX ≤ EXT_MAX_VIX
        3. Distance to target: within last EXT_TARGET_PCT% of target distance
           (ensures we only extend genuine breakouts, not weak/noisy approaches)
        4. Momentum: LTP is still moving in the right direction vs previous cycle
           (avoids extending an exhausted/reversing trend)
        """
        if self._extended.get(oid):
            return False                          # already extended once — hands off
        if not self._last_regime or "bull" not in self._last_regime:
            return False                          # only in trending markets
        if self._last_vix > _EXT_MAX_VIX:
            return False                          # VIX too high — reversal risk
        if r_multiple < _EXT_TRIGGER_R:
            return False                          # not close enough to target yet

        # ── Improvement 1: Distance to target check ────────────────────────
        # Only extend if within the last EXT_TARGET_PCT of the full target distance.
        # This filters out weak moves that drifted to 3R over days.
        entry   = order.entry_price
        sl      = order.stop_loss
        target  = order.target
        is_long = order.direction == "BUY"
        risk    = abs(entry - sl) if sl else 0.0
        if target and risk > 0:
            full_target_dist = abs(target - entry)
            remaining_dist   = abs(target - (entry + (r_multiple * risk if is_long
                                              else -(r_multiple * risk))))
            if full_target_dist > 0:
                proximity_pct = remaining_dist / full_target_dist
                if proximity_pct > _EXT_TARGET_PCT:
                    return False   # not close enough — still >10% away from target

        # ── Improvement 2: Multi-cycle momentum confirmation ────────────────
        # Check the last 2 consecutive LTP moves (from the 3-entry rolling
        # history).  Extension fires only if ≥2 of those moves are in the
        # right direction.  A single-tick reversals is ignored as noise.
        hist = self._ltp_history.get(oid, [])
        if len(hist) >= 3:
            # We have [oldest, mid, newest] — check both steps.
            steps_up   = sum(1 for a, b in zip(hist, hist[1:]) if b > a)
            steps_down = sum(1 for a, b in zip(hist, hist[1:]) if b < a)
            momentum_ok = (steps_up >= 2) if is_long else (steps_down >= 2)
        elif len(hist) >= 2:
            # Only one step available — fall back to single-tick check.
            momentum_ok = (hist[-1] > hist[-2]) if is_long else (hist[-1] < hist[-2])
        else:
            # No history yet (first cycle after registration) — allow extension.
            momentum_ok = True
        if not momentum_ok:
            return False   # price reversing ≥2 cycles — exhaustion signal, do NOT extend

        return True

    def _adaptive_check(self, oid: str, order: OrderRecord,
                         ltp: float) -> Optional[str]:
        """
        Phase 1 Adaptive Exit Engine.

        Priorities (TIME FIRST — never rely on price movement alone):

        1. TIME_STALE  — trade open ≥ TIME_STALE_MINUTES AND
                         current R in [−STALE_MAX_R, +STALE_MAX_R]
                         AND peak R never exceeded GUARD_R (not a runner).
        2. EARLY_LOSS  — R ≤ EARLY_LOSS_R (e.g. −0.6R) AND
                         peak R never exceeded GUARD_R.

        Guardrails (never fire if):
         • SL or target already hit (caller checks those first)
         • Trade is ≥ GUARD_R in profit at any point (strong runner — let it run)
         • Trade is within 10% of its fixed target (already managed by trail)
        """
        entry   = order.entry_price
        sl      = order.stop_loss
        target  = order.target
        is_long = order.direction == "BUY"
        risk    = abs(entry - sl) if sl else 0.0

        if risk == 0:
            return None

        unrealised = (ltp - entry) if is_long else (entry - ltp)
        r_multiple = unrealised / risk
        peak_r     = self._peak_r.get(oid, 0.0)

        # Guardrail: trade was ever a strong runner → hands off
        if peak_r >= _AE_GUARD_R:
            return None

        # Guardrail: near fixed target (within 10% of target distance) → let it land
        if target and risk > 0:
            target_r = abs(target - entry) / risk
            if r_multiple >= target_r * 0.90:
                return None

        # ── Gate 1: TIME_STALE ─────────────────────────────────────────
        # TIME FIRST — only check price movement after time gate passes.
        created = getattr(order, "created_at", None)
        if created:
            age_minutes = (datetime.now() - created).total_seconds() / 60

            # ── Improvement 4: Time cap on EXTENDED trades ────────────────────
            # If this trade was extended AND has been running too long since extension,
            # tighten trailing to 0.5R step to force gradual closure. NOT a hard exit.
            if self._extended.get(oid) and oid in self._extended_at:
                extended_mins = (datetime.now() - self._extended_at[oid]).total_seconds() / 60
                if extended_mins >= _EXT_TIME_CAP_MIN:
                    entry   = order.entry_price
                    sl_raw  = order.stop_loss
                    is_long = order.direction == "BUY"
                    risk    = abs(entry - (sl_raw or entry))
                    if risk > 0:
                        tight_sl = (peak_r - 0.5) * risk
                        new_sl   = round(entry + tight_sl, 2) if is_long \
                                   else round(entry - tight_sl, 2)
                        if (is_long and new_sl > sl_raw) or (not is_long and new_sl < sl_raw):
                            order.stop_loss = new_sl
                            log.info(
                                "[AdaptiveExtension] TIGHTEN_SL %s → extended_age=%.0fmin  "
                                "sl=%.2f  reason=TIME_CAP",
                                order.symbol, extended_mins, new_sl,
                            )

            if age_minutes >= _AE_TIME_MIN:
                if abs(r_multiple) <= _AE_STALE_MAX_R:
                    log.info(
                        "[AdaptiveExit] EXIT %s → reason=TIME_STALE  "
                        "age=%.0fmin  r=%.2fR  peak=%.2fR",
                        order.symbol, age_minutes, r_multiple, peak_r,
                    )
                    self._adaptive_reasons[oid] = "TIME_STALE"
                    return "adaptive_exit"

        # ── Gate 2: EARLY_LOSS (regime-aware threshold) ───────────────────────
        # bull_trend → -0.7R (momentum needs breathing room)
        # sideways/bear → -0.5R (cut dead weight quickly)
        # default → -0.6R
        if "bull" in self._last_regime:
            loss_threshold = _AE_LOSS_TRENDING_R
        elif self._last_regime in ("range_market", "bear_market"):
            loss_threshold = _AE_LOSS_SIDEWAYS_R
        else:
            loss_threshold = _AE_EARLY_LOSS_R

        if r_multiple <= loss_threshold:
            log.info(
                "[AdaptiveExit] EXIT %s → reason=EARLY_LOSS  "
                "r=%.2fR  threshold=%.2fR  regime=%s  peak=%.2fR",
                order.symbol, r_multiple, loss_threshold,
                self._last_regime or "unknown", peak_r,
            )
            self._adaptive_reasons[oid] = "EARLY_LOSS"
            return "adaptive_exit"

        return None

    def _act(self, oid: str, order: OrderRecord, ltp: float, action: str):
        reason_map = {
            "close_target":    f"Target hit at {ltp:.2f}",
            "close_sl":        f"Stop loss hit at {ltp:.2f}",
            "close_emergency": f"Emergency MAE at {ltp:.2f}",
            "close_eod":       "End of day close",
            "adaptive_exit":   f"Adaptive exit: {self._adaptive_reasons.get(oid, 'UNKNOWN')} at {ltp:.2f}",
        }
        reason = reason_map.get(action, action)
        log.info("[TradeMonitor] %s %s — %s", action.upper(), order.symbol, reason)

        # Record in performance analytics layer
        try:
            was_extended     = bool(self._extended.get(oid, False))
            adaptive_reason  = self._adaptive_reasons.get(oid)
            r_at_ext         = self._r_at_extension.get(oid, 0.0)
            self._analytics.record_closed_trade(
                order, ltp, action, adaptive_reason, was_extended
            )
        except Exception as _ae:
            log.debug("[TradeAnalytics] record failed (non-fatal): %s", _ae)

        if self._order_manager:
            self._order_manager.close_position(oid, ltp, reason=action)

    def _get_ltp(self, symbol: str,
                  price_feed: Optional[Dict[str, float]]) -> Optional[float]:
        if price_feed and symbol in price_feed:
            return price_feed[symbol]
        # Simulation fallback
        import random
        order = next((o for o in self._open_orders.values()
                      if o.symbol == symbol), None)
        if order:
            return round(order.entry_price * (1 + random.uniform(-0.03, 0.03)), 2)
        return None

    # ─────────────────────────────────────────────────────────────────
    # ACCESS
    # ─────────────────────────────────────────────────────────────────

    def get_closed_trades(self) -> List[OrderRecord]:
        return list(self._closed_orders)

    def get_open_trades(self) -> List[OrderRecord]:
        return list(self._open_orders.values())

    def get_analytics(self) -> TradeAnalytics:
        """Return the live analytics engine. Use for EOD reporting."""
        return self._analytics

    def check_open_positions(self):
        """Alias for check_all() — used by MasterOrchestrator."""
        return self.check_all()

    def summary(self) -> str:
        open_ct   = len(self._open_orders)
        closed_ct = len(self._closed_orders)
        realised  = sum(o.pnl for o in self._closed_orders)
        return (f"[TradeMonitor] Open:{open_ct} | Closed:{closed_ct} | "
                f"Realised PnL: ₹{realised:+,.0f}")
