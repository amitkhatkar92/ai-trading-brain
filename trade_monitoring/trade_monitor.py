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
from typing import Any, Dict, List, Optional, Set

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
        # LTPGuard: last known-good price per order to detect bad API values
        self._last_good_ltp: Dict[str, float]  = {}  # order_id → last valid LTP
        # StaleCarry alert: track last date alerted per order to fire once per day
        self._stale_alerted: Dict[str, str]    = {}  # order_id → last alerted date (YYYY-MM-DD)
        # DataGuard: unchanged-price stale detection across monitoring cycles
        # Tracks consecutive cycles where the resolved LTP was identical to the
        # previous cycle.  After _DATAGAURD_STALE_CYCLES identical values a
        # [DataGuard] warning is logged.  Counter resets on any price change.
        self._dg_last_price: Dict[str, float]  = {}  # order_id → last resolved LTP
        self._dg_stale_count: Dict[str, int]   = {}  # order_id → consecutive unchanged cycles
        # LTP resolution — per-cycle state exposed to master_orchestrator.
        # Populated by _get_ltp during each check_all call so the orchestrator
        # can sync portfolio position LTPs with LTPGuard-validated values instead
        # of the raw feed values (which may be garbage at market close).
        self._resolved_prices: Dict[str, float] = {}  # symbol → validated LTP this cycle
        self._corrected_symbols: set            = set()  # symbols corrected by LTPGuard
        # Feed-degraded tracking: count consecutive cycles a symbol has no live feed.
        # SL monitoring and adaptive exits are suppressed while degraded.
        self._feed_degraded_cycles: Dict[str, int] = {}   # order_id → cycle count
        log.info("[TradeMonitor] Initialised.")

    # ─────────────────────────────────────────────────────────────────
    # REGISTRATION
    # ─────────────────────────────────────────────────────────────────

    def register(self, order: OrderRecord):
        """Register a newly placed order for monitoring."""
        self._open_orders[order.order_id] = order
        self._peak_r[order.order_id]   = 0.0   # initialise peak tracker
        self._ltp_history[order.order_id] = [order.entry_price]  # seed momentum history
        self._last_good_ltp[order.order_id] = order.entry_price  # seed LTPGuard baseline
        # Restore extended flag for cross-day carry positions that had extension
        # fire before a container restart.  OrderManager.journal_write_extend()
        # writes EXTEND events; _restore_from_journal() collects the oids into
        # _restored_extended_oids so we can re-arm the flag here without
        # re-running _can_extend() logic that may not match stale conditions.
        if (self._order_manager is not None
                and hasattr(self._order_manager, "_restored_extended_oids")
                and order.order_id in self._order_manager._restored_extended_oids):
            self._extended[order.order_id]    = True
            self._extended_at[order.order_id] = datetime.now()
            log.info("[TradeMonitor] Restored extended state for %s %s  (SL=%.2f locked)",
                     order.symbol, order.order_id, order.stop_loss)
        log.info("[TradeMonitor] Registered: %s %s qty=%d entry=%.2f",
                 order.symbol, order.direction, order.quantity, order.entry_price)

    def deregister(self, order_id: str) -> None:
        """Remove a position from monitoring — called when smart-swap closes it.
        Prevents phantom SL/target monitoring on already-replaced positions."""
        if order_id in self._open_orders:
            rec = self._open_orders.pop(order_id)
            self._peak_r.pop(order_id, None)
            self._ltp_history.pop(order_id, None)
            self._r_at_extension.pop(order_id, None)
            self._extended.pop(order_id, None)
            self._extended_at.pop(order_id, None)
            self._adaptive_reasons.pop(order_id, None)
            self._last_good_ltp.pop(order_id, None)
            self._dg_last_price.pop(order_id, None)
            self._dg_stale_count.pop(order_id, None)
            self._stale_alerted.pop(order_id, None)
            log.info("[TradeMonitor] Deregistered (swap-replaced): %s %s",
                     rec.symbol, order_id)

    def inject_order_manager(self, order_manager):
        """Inject OrderManager so monitor can close positions."""
        self._order_manager = order_manager

    def seed_ltp(self, order_id: str, price: float) -> None:
        """Slide the LTPGuard baseline to *price* for *order_id*.

        Call this before check_all() whenever a trusted model price (e.g. a
        Black-Scholes synthetic premium or a freshly-fetched live premium) is
        available.  Without this, LTPGuard compares every incoming price to the
        original *entry* price — for options positions that legitimately move
        40-60 % from entry, LTPGuard would permanently reject correct data.

        This does NOT bypass LTPGuard; it simply advances the baseline so the
        deviation check measures tick-to-tick movement rather than entry-to-now.
        """
        if price > 0 and order_id in self._open_orders:
            self._last_good_ltp[order_id] = price

    def update_market_context(self, regime: str, vix: float) -> None:
        """Called by orchestrator before each monitoring cycle with current regime/VIX."""
        self._last_regime = regime or ""
        self._last_vix    = vix or 0.0

    # ─────────────────────────────────────────────────────────────────
    # MONITORING CYCLE
    # ─────────────────────────────────────────────────────────────────

    def check_all(
        self,
        price_feed: Optional[Dict[str, float]] = None,
        degraded_symbols: Optional[Set[str]] = None,
    ):
        """
        Called every N minutes.
        price_feed: dict of {symbol: ltp} — if None, simulates prices.
        degraded_symbols: bare symbol names that have no live feed this cycle
          (excluded from price_feed by MarketDataRouter).  SL evaluation and
          adaptive exits are suppressed for these symbols to prevent false
          triggers from stale/synthetic prices.

        For LIMIT orders in paper mode: only proceed with SL/target evaluation
        once the market price has actually reached (crossed) the zone_price.
        Until then, send no noise — a "⏳ Limit Pending" was already sent at placement.
        When fill is confirmed, send "Trade Opened" and downgrade to MARKET so
        subsequent cycles evaluate SL/target normally.
        """
        # Reset per-cycle resolution state so get_resolved_prices() and
        # get_guard_correction_count() always reflect the CURRENT cycle only.
        self._resolved_prices    = {}
        self._corrected_symbols  = set()
        _degraded = degraded_symbols or set()

        closed_ids = []
        for oid, order in self._open_orders.items():
            # ── FEED_DEGRADED guard ────────────────────────────────────────
            # When MarketDataRouter has no live or cached price for this symbol,
            # suppress SL and adaptive-exit evaluation entirely.  A degraded
            # price is stale/synthetic — acting on it risks false SL hits or
            # premature adaptive exits.
            _sym_degraded = order.symbol in _degraded
            if _sym_degraded:
                _dcycles = self._feed_degraded_cycles.get(oid, 0) + 1
                self._feed_degraded_cycles[oid] = _dcycles
                log.warning(
                    "[TradeMonitor] FEED_DEGRADED %s -- cycle=%d  "
                    "SL/adaptive SUPPRESSED this cycle",
                    order.symbol, _dcycles,
                )
                continue   # skip all evaluation for this order this cycle
            else:
                # Symbol has live feed — reset degraded counter
                if oid in self._feed_degraded_cycles:
                    self._feed_degraded_cycles.pop(oid)

            ltp = self._get_ltp(order.symbol, price_feed)
            if ltp is None:
                continue

            # ── SL Integrity Gate ──────────────────────────────────────
            # Before acting on any price for SL/target/adaptive-exit:
            # validate it against the sanity band, cross-source agreement,
            # and intra-cycle plausibility.  A failure suppresses execution
            # for this cycle and fires a Telegram alert.
            _prev_ltp_for_gate = self._last_good_ltp.get(oid)
            try:
                from data_integrity.price_integrity_validator import get_price_validator
                _gate_result = get_price_validator().validate(
                    symbol=order.symbol,
                    candidate_price=ltp,
                    yahoo_price=None,       # cross-source check done at router level
                    feed_degraded=False,    # already handled by FEED_DEGRADED guard above
                    previous_ltp=_prev_ltp_for_gate,
                )
                if not _gate_result.ok:
                    log.warning(
                        "[ExecutionIntegrity] SL_SUPPRESSED  symbol=%s  "
                        "classification=%s  ltp=%.2f  prev=%.2f  reason=%s",
                        order.symbol, _gate_result.classification, ltp,
                        _prev_ltp_for_gate or 0.0, _gate_result.reason,
                    )
                    continue   # do NOT fire SL/target/adaptive exit this cycle
            except Exception as _gate_exc:
                log.debug("[ExecutionIntegrity] gate check error %s: %s",
                          order.symbol, _gate_exc)
            # Gate passed — update confirmed-LTP baseline
            self._last_good_ltp[oid] = ltp

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
            if not action and _AE_ENABLED and not _sym_degraded:
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
            self._dg_last_price.pop(oid, None)    # clean up DataGuard state
            self._dg_stale_count.pop(oid, None)   # clean up DataGuard state
        # Append current LTP to rolling history for all still-open orders.
        # Keep only the last 3 entries (enough for 2-step direction check).
        for oid, order in self._open_orders.items():
            _cur = self._get_ltp(order.symbol, price_feed)
            if _cur is not None:
                hist = self._ltp_history.setdefault(oid, [_cur])
                hist.append(_cur)
                if len(hist) > 3:
                    del hist[0]

        # ── StaleCarry check: alert on positions open too long with minimal movement.
        # Fires once per calendar day per order. Does NOT auto-close. Alert only.
        #
        # Strategy-aware thresholds:
        #   Mean-reversion strategies are time-sensitive — alpha decays quickly.
        #   Trend strategies expect multi-day drift — more patience is correct.
        _STALE_BY_TYPE: Dict[str, int] = {
            # Mean-reversion: short-duration thesis — alert after 2 days
            "mean_reversion": 2,
            "meanreversion":  2,
            "reversion":      2,
            "range":          2,
            "hedging":        2,
            # Trend / momentum: longer-duration thesis — alert after 5 days
            "trend":          5,
            "momentum":       5,
            "breakout":       5,
            "edg_moment":     5,
            # Default for any unclassified strategy
        }
        _STALE_DEFAULT  = 3     # fallback for unclassified strategies
        _STALE_BAND_R   = 0.3   # flag if position hasn't moved beyond ±0.3R
        _today_str      = datetime.now().strftime("%Y-%m-%d")
        for oid, order in self._open_orders.items():
            if not order.placed_at:
                continue
            age_days = (datetime.now() - order.placed_at).days
            # Determine strategy-aware session threshold
            _strat_key = (order.strategy or "").lower().replace("_", "").replace("-", "")
            _stale_days = _STALE_DEFAULT
            for _prefix, _days in _STALE_BY_TYPE.items():
                if _strat_key.startswith(_prefix.replace("_", "")):
                    _stale_days = _days
                    break
            if age_days < _stale_days:
                continue
            # Already alerted today?
            if self._stale_alerted.get(oid) == _today_str:
                continue
            # Check movement band
            risk = abs(order.entry_price - order.stop_loss) if order.stop_loss else 0.0
            if risk <= 0:
                continue
            _cur_ltp = self._get_ltp(order.symbol, price_feed)
            if _cur_ltp is None:
                continue
            if order.direction == "BUY":
                r_now = (_cur_ltp - order.entry_price) / risk
            else:
                r_now = (order.entry_price - _cur_ltp) / risk
            if abs(r_now) <= _STALE_BAND_R:
                self._stale_alerted[oid] = _today_str
                log.warning(
                    "[StaleCarry] ⚠️ %s %s open for %d day(s), minimal movement "
                    "(current_r=%.2fR, entry=%.2f, sl=%.2f, strategy=%s, threshold=%dd). "
                    "Review manually — NO auto-close.",
                    order.symbol, oid, age_days, r_now,
                    order.entry_price, order.stop_loss,
                    order.strategy, _stale_days,
                )
                try:
                    from notifications.notifier_manager import get_notifier
                    # Wrap strategy in backticks so underscores (e.g. Mean_Reversion)
                    # are not mis-parsed as Markdown italic delimiters by Telegram.
                    get_notifier().market_alert(
                        "⚠️ Stale Carry Alert",
                        f"{order.symbol} ({order.direction}) has been open "
                        f"{age_days} day(s) with minimal movement "
                        f"(R={r_now:+.2f}).\n"
                        f"Entry: ₹{order.entry_price:.2f}  "
                        f"SL: ₹{order.stop_loss:.2f}  "
                        f"Target: ₹{order.target:.2f}\n"
                        f"Strategy: `{order.strategy}` (threshold: {_stale_days}d)\n"
                        f"Manual review recommended. No auto-close.",
                    )
                except Exception:
                    pass

        # ── ConcentrationAudit + ExposureAudit: observe-only telemetry ──
        self._emit_concentration_telemetry(price_feed)
        # ── StalePositionAudit: log all positions open >24 h with full context ──
        self._emit_stale_position_audit(price_feed)

    # ─────────────────────────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────────────────────────

    def _emit_concentration_telemetry(self, price_feed: Optional[dict]) -> None:
        """
        Emit [ConcentrationAudit] and [ExposureAudit] for currently open positions.

        OBSERVE ONLY — no execution blocking.  Runs once per monitoring cycle so
        that log analysis can track exposure concentration trends over time.
        """
        if not self._open_orders:
            return
        n = len(self._open_orders)
        sym_exposure: Dict[str, float]   = {}
        strat_exposure: Dict[str, float] = {}
        long_n = short_n = 0
        total_gross = 0.0

        for _oid, order in self._open_orders.items():
            gross = abs((order.entry_price or 0.0) * (order.quantity or 0))
            total_gross += gross
            sym_exposure[order.symbol]     = sym_exposure.get(order.symbol,     0.0) + gross
            strat_exposure[order.strategy] = strat_exposure.get(order.strategy, 0.0) + gross
            _dir = (getattr(order, "direction", "") or "").upper()
            if _dir in ("BUY", "LONG"):
                long_n += 1
            else:
                short_n += 1

        _denom       = total_gross if total_gross > 0 else 1.0
        _max_sym_w   = max(sym_exposure.values())   / _denom * 100 if sym_exposure   else 0.0
        _max_strat_w = max(strat_exposure.values()) / _denom * 100 if strat_exposure else 0.0
        _bias = "LONG" if long_n > short_n else "SHORT" if short_n > long_n else "NEUTRAL"

        log.info(
            "[ConcentrationAudit] open_positions=%d  symbols=%d  strategies=%d"
            "  directional_bias=%s  largest_symbol_weight=%.0f%%"
            "  largest_strategy_weight=%.0f%%",
            n, len(sym_exposure), len(strat_exposure),
            _bias, _max_sym_w, _max_strat_w,
        )
        for _oid, order in self._open_orders.items():
            _gross = abs((order.entry_price or 0.0) * (order.quantity or 0))
            _pct   = _gross / _denom * 100
            log.info(
                "[ExposureAudit] symbol=%s  strategy=%s  gross_exposure=\u20b9%.0f"
                "  portfolio_pct=%.1f%%  direction=%s",
                order.symbol, order.strategy, _gross, _pct,
                (getattr(order, "direction", "") or "").upper(),
            )

    def _emit_stale_position_audit(self, price_feed: Optional[dict]) -> None:
        """
        Emit [StalePositionAudit] log lines for every open position that has
        been open for more than 24 hours.  This is an observation log — never
        takes autonomous action.

        Logged fields:
          symbol, direction, age_h, entry, ltp, sl_active,
          feed_degraded_cycles, feed_state, governance_state
        """
        now = datetime.now()
        for oid, order in self._open_orders.items():
            if not order.placed_at:
                continue
            # Skip positions already closed — governance_state tracks lifecycle.
            # CarryExpiry marks CLOSED before removing from _open_orders; avoid
            # logging 50+ redundant StalePositionAudit lines for finished trades.
            if getattr(order, "governance_state", "ACTIVE") == "CLOSED":
                continue
            age_h = (now - order.placed_at).total_seconds() / 3600
            if age_h < 24:
                continue   # only audit positions open more than one day
            ltp = self._get_ltp(order.symbol, price_feed)
            risk = abs(order.entry_price - (order.stop_loss or order.entry_price))
            if risk > 0 and ltp is not None:
                unreal_r = ((ltp - order.entry_price) / risk
                            if order.direction == "BUY"
                            else (order.entry_price - ltp) / risk)
            else:
                unreal_r = None
            feed_deg_cycles = self._feed_degraded_cycles.get(oid, 0)
            feed_state = "DEGRADED" if feed_deg_cycles > 0 else "LIVE"
            sl_active = order.stop_loss is not None and order.stop_loss > 0
            governance_state = getattr(order, "governance_state", "ACTIVE")
            log.info(
                "[StalePositionAudit] symbol=%s  dir=%s  age=%.1fh  "
                "entry=%.2f  ltp=%s  sl_active=%s  unreal_r=%s  "
                "feed_state=%s  feed_degraded_cycles=%d  governance_state=%s  "
                "oid=%s",
                order.symbol, order.direction, age_h,
                order.entry_price, f"{ltp:.2f}" if ltp else "N/A",
                sl_active,
                f"{unreal_r:+.2f}R" if unreal_r is not None else "N/A",
                feed_state, feed_deg_cycles,
                governance_state, oid,
            )

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
                # Persist locked SL to journal so it survives container restarts.
                # _restore_from_journal reads EXTEND rows to restore locked_sl
                # and suppress double-extension via _restored_extended_oids.
                if self._order_manager is not None:
                    self._order_manager.journal_write_extend(oid, locked_sl)
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

    # Map internal action tokens → canonical lifecycle reasons stored in the journal.
    # These strings are the ground truth consumed by EOD learning, Phase D shadow
    # reports, and lifecycle analysis.  Human-readable log descriptions are kept
    # separate (see _LOG_REASON_MAP below).
    _CANONICAL_REASON: dict = {
        "close_target":    "TARGET_HIT",
        "close_sl":        "STOP_HIT",
        "close_emergency": "close_emergency",   # system intervention — preserved as-is
        "close_eod":       "EOD_CLOSE",
        # adaptive_exit sub-reason is resolved at call time from _adaptive_reasons
    }

    def _act(self, oid: str, order: OrderRecord, ltp: float, action: str):
        # ── Human-readable log description (never written to journal) ─────────
        _log_reason_map = {
            "close_target":    f"Target hit at {ltp:.2f}",
            "close_sl":        f"Stop loss hit at {ltp:.2f}",
            "close_emergency": f"Emergency MAE at {ltp:.2f}",
            "close_eod":       "End of day close",
            "adaptive_exit":   f"Adaptive exit: {self._adaptive_reasons.get(oid, 'UNKNOWN')} at {ltp:.2f}",
        }
        log.info("[TradeMonitor] %s %s — %s",
                 action.upper(), order.symbol,
                 _log_reason_map.get(action, action))

        # ── Canonical journal reason (machine-readable, persisted to CSV) ─────
        # adaptive_exit carries a sub-reason ("TIME_STALE" or "EARLY_LOSS")
        # already stored in _adaptive_reasons.  Use it directly as the canonical
        # label so EOD learning and Phase D reports can group by exit type.
        if action == "adaptive_exit":
            canonical_reason = self._adaptive_reasons.get(oid, "adaptive_exit")
        else:
            canonical_reason = self._CANONICAL_REASON.get(action, action)

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
            self._order_manager.close_position(oid, ltp, reason=canonical_reason)

    # ── LTPGuard threshold ────────────────────────────────────────────
    _LTP_GUARD_MAX_DEVIATION   = 0.20  # flag prices that deviate >20% from last known
    # ── DataGuard stale-price detection ──────────────────────────────
    _DATAGAURD_STALE_CYCLES    = 6     # consecutive identical prices before warning
    _DATAGAURD_REPEAT_CYCLES   = 12    # repeat the warning every N more identical cycles

    def _dg_update_stale(self, order_id: str, symbol: str, resolved: float) -> None:
        """DataGuard: track consecutive identical prices and log stale warnings."""
        last = self._dg_last_price.get(order_id)
        if last is not None and resolved == last:
            count = self._dg_stale_count.get(order_id, 0) + 1
            self._dg_stale_count[order_id] = count
            # Log at first threshold, then every _DATAGAURD_REPEAT_CYCLES more
            if count == self._DATAGAURD_STALE_CYCLES or (
                count > self._DATAGAURD_STALE_CYCLES
                and (count - self._DATAGAURD_STALE_CYCLES) % self._DATAGAURD_REPEAT_CYCLES == 0
            ):
                log.warning(
                    "[DataGuard] Stale price detected for %s — "
                    "price unchanged at %.2f for %d consecutive monitoring cycles.",
                    symbol, resolved, count,
                )
        else:
            # Price changed — reset counter
            self._dg_stale_count[order_id] = 0
        self._dg_last_price[order_id] = resolved

    @staticmethod
    def _fetch_from_scanner_cache(symbol: str) -> Optional[float]:
        """Pull symbol price from the equity-scanner cache (no network call)."""
        try:
            from opportunity_engine.equity_scanner_ai import (
                _PRICE_CACHE, _PRICE_CACHE_LOCK,
            )
            with _PRICE_CACHE_LOCK:
                return _PRICE_CACHE.get(symbol)
        except Exception:
            return None

    def _get_ltp(self, symbol: str,
                  price_feed: Optional[Dict[str, float]]) -> Optional[float]:
        order = next((o for o in self._open_orders.values()
                      if o.symbol == symbol), None)

        if price_feed and symbol in price_feed:
            candidate = price_feed[symbol]
            # ── LTPGuard: two-step validation ──────────────────────────
            if order:
                baseline = self._last_good_ltp.get(order.order_id, order.entry_price)
                if baseline > 0:
                    deviation = abs(candidate - baseline) / baseline
                    if deviation > self._LTP_GUARD_MAX_DEVIATION:
                        # Step 1 — try equity-scanner cache as independent source
                        cached = self._fetch_from_scanner_cache(symbol)
                        if cached and cached > 0:
                            cached_dev = abs(cached - baseline) / baseline
                            if cached_dev <= self._LTP_GUARD_MAX_DEVIATION:
                                # Cache confirms a genuine move — accept cached price
                                log.info(
                                    "[LTPGuard] %s feed=%.2f flagged (%.0f%% vs baseline=%.2f) "
                                    "— cache confirms %.2f as genuine move.",
                                    symbol, candidate, deviation * 100, baseline, cached,
                                )
                                self._last_good_ltp[order.order_id] = cached
                                # Record validated price for portfolio sync
                                self._resolved_prices[symbol] = cached
                                self._corrected_symbols.add(symbol)
                                return cached
                        # Step 2 — no independent confirmation; freeze at last good
                        log.warning(
                            "[LTPGuard] Corrected abnormal price for %s: "
                            "feed=%.2f vs last_known=%.2f (%.0f%% deviation) "
                            "— using last known good.",
                            symbol, candidate, baseline, deviation * 100,
                        )
                        log.warning(
                            "[DataGuard] Using fallback price for %s — live data unavailable "
                            "(feed=%.2f flagged; fallback=%.2f).",
                            symbol, candidate, baseline,
                        )
                        self._dg_update_stale(order.order_id, symbol, baseline)
                        # Record validated (frozen) price for portfolio sync
                        self._resolved_prices[symbol] = baseline
                        self._corrected_symbols.add(symbol)
                        return baseline
                # Price is sane — update the last-known-good baseline
                self._last_good_ltp[order.order_id] = candidate
            self._dg_update_stale(order.order_id if order else "__anon__", symbol, candidate)
            # Record sane feed price for portfolio sync (don't overwrite a correction
            # that was already recorded for this symbol in an earlier call this cycle).
            if symbol not in self._corrected_symbols:
                self._resolved_prices[symbol] = candidate
            return candidate

        # Simulation fallback ONLY when no price_feed at all (dev/no-feed mode).
        # When price_feed is provided but symbol is absent, the feed was attempted
        # but excluded (no live data, no cache).  Return None so this cycle is
        # skipped; MarketDataRouter already put the symbol in degraded_symbols.
        if price_feed is not None:
            return None
        import random
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

    def get_resolved_prices(self) -> Dict[str, float]:
        """Return {symbol: validated_ltp} from the last check_all cycle.

        Prices have been through LTPGuard — corrupt feed values are replaced
        with cached or last-known-good values.  Use this for portfolio sync
        instead of the raw price feed to prevent false drawdown calculations.
        Only populated after check_all() has run; returns {} before first call.
        """
        return dict(self._resolved_prices)

    def get_guard_correction_count(self) -> int:
        """Number of distinct symbols that had LTPGuard corrections in the last cycle.

        Used by the orchestrator's P0.5 batch-corruption freeze: if this count
        exceeds 50% of the total symbols, the drawdown halt-check is skipped.
        """
        return len(self._corrected_symbols)

    def summary(self) -> str:
        open_ct   = len(self._open_orders)
        closed_ct = len(self._closed_orders)
        realised  = sum(o.pnl for o in self._closed_orders)
        return (f"[TradeMonitor] Open:{open_ct} | Closed:{closed_ct} | "
                f"Realised PnL: ₹{realised:+,.0f}")
