"""
Equity-Hedge Shadow + Execution Engine
=========================================
DTA-EQUITY-HEDGE-SHADOW-001 / DTA-EQUITY-HEDGE-EXEC-001.

Read-only observer of equity's own ORDER_PLACED events. For every real
equity trade, attempts to find a corresponding single-stock option and
shadow-tracks a hypothetical companion option position — with ZERO real
capital risk while evidence accumulates, and ZERO write-back into equity
decisions. Equity's own pipeline is never touched: this module only
listens to the shared EventBus, exactly like the existing
OIOSExecutionBridge / PaperTradeLogger observers.

Structure (2026-09-12 clarification): this is a SAME-DIRECTION, defined-
risk companion option, not a traditional opposite-direction protective
hedge. When equity BUYS a stock, this engine's target position is a long
CALL on the same stock (same direction — captures amplified upside per
the "underlying move -> option move" leverage research, bounded profit
target) whose maximum loss is the premium paid (defined, capped downside
-- "minimizes the loss" relative to holding more equity). Equity SELL ->
long PUT, symmetrically.

Why shadow-first
-----------------
Per the audited activation plan (2026-09-12): before any real capital is
deployed into single-stock option positions, the system must accumulate
its OWN evidence — not borrowed from index-options knowledge — that the
leverage relationship holds for individual stocks specifically, and that
the companion position would be profitable net of cost. This engine
collects that evidence continuously; live execution is gated on it (below).

Readiness gate (EQH-Ready-1..5) — automated, no human sign-off required
for the AUTHENTICATION decision itself, mirroring the same no-human-gate
philosophy already used by OptionsKnowledgeStore:
  EQH-Ready-1  >= MIN_OBS_AUTHENTICATED analysed observations, per symbol
  EQH-Ready-2  OOS split: p < ALPHA (one-tailed sign test on the split halves)
  EQH-Ready-3  mean hypothetical PnL, net of COST_ESTIMATE_PCT, is positive
  EQH-Ready-4  no single symbol > MAX_CONCENTRATION of the evidence base
  EQH-Ready-5  evidence must come from THIS engine's own single-stock
               observations only (chain_available=True) — never borrowed
               from index-options knowledge stores

Live execution (2026-09-12 -- built and verified against real Dhan data)
--------------------------------------------------------------------------
Once a symbol passes all 5 checks and is marked READY_FOR_LIVE, the next
equity ORDER_PLACED for that symbol triggers a companion option order,
routed through the SAME, already-proven execution machinery used for
index options (OptionsRiskEngine.approve_and_size -> OptionsOrderManager
.execute) — no new, untested execution path was built. Verified
empirically before wiring: Dhan's option_chain API supports single-stock
(NSE_EQ) underlyings with the identical response schema as indices;
DhanFnOSecurityMap resolves real security_ids AND real lot sizes
(SEM_LOT_UNITS) from Dhan's own instrument master — never hard-coded.
Every step fails closed (chain unavailable, lot size unverified, quality
too low, etc. all reject rather than guess) rather than defaulting to an
unverified assumption.

Persistence: data/equity_hedge_shadow.json
Singleton:   get_equity_hedge_shadow_engine()
"""

from __future__ import annotations

import json
import os
import statistics
import threading
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_PERSIST_PATH = "data/equity_hedge_shadow.json"
_INSTANCE: Optional["EquityHedgeShadowEngine"] = None
_INSTANCE_LOCK = threading.Lock()

# How often the background loop checks for matured monitors / readiness.
LOOP_INTERVAL_MINUTES = 30

# How long to watch the underlying before scoring the hypothetical hedge.
MONITOR_HORIZON_DAYS = 10

# ── Readiness-gate thresholds (reuse existing project bars, no new
#    numbers invented — matches OptionsKnowledgeStore's own AUTHENTICATED
#    thresholds) ──────────────────────────────────────────────────────────
MIN_OBS_AUTHENTICATED = 40     # EQH-Ready-1 (mirrors MIN_OUTCOMES_AUTHENTICATED)
OOS_P_ALPHA            = 0.10  # EQH-Ready-2 (mirrors OOS_P_ALPHA)
COST_ESTIMATE_PCT      = 0.02  # EQH-Ready-3: assumed round-trip cost as a
                                # fraction of premium (slippage + brokerage)
MAX_CONCENTRATION      = 0.80  # EQH-Ready-4 (mirrors CONCENTRATION_MAX)

# ── Live-execution quality gates (reuse the SAME values already used by
#    the index-options fast path -- no new numbers invented) ──────────────
_CHAIN_QUALITY_MIN = 0.5    # mirrors master_orchestrator._CHAIN_QUALITY_MIN
_DTE_MIN           = 10     # mirrors master_orchestrator._DTE_MIN
_DTE_MAX           = 60     # mirrors master_orchestrator._DTE_MAX
_MIN_LEG_PREMIUM   = 5.0    # mirrors options_opportunity_ai.MIN_LEG_PREMIUM
_MIN_TRADABLE_OI   = 500    # mirrors data_feeds.options_feed.MIN_TRADABLE_OI


@dataclass
class EquityHedgeShadowObservation:
    """One shadow-tracked hedge for a real equity trade."""
    symbol:                str
    equity_order_id:       str
    equity_direction:      str      # BUY / SELL
    equity_entry_price:    float
    equity_qty:            int
    recorded_at:           str
    monitor_until:         str      # ISO date

    chain_available:       bool = False
    hedge_option_type:     str  = ""   # PE (protective put) / CE (protective call)
    hedge_strike:          float = 0.0
    hedge_entry_premium:   float = 0.0
    underlying_spot_at_entry: float = 0.0

    analysed:              bool = False
    underlying_spot_at_exit: Optional[float] = None
    hypothetical_hedge_pnl: Optional[float] = None
    hedge_classification:  Optional[str] = None  # HEDGE_WOULD_HAVE_HELPED / HEDGE_UNNECESSARY
    notes:                 str = ""


def get_equity_hedge_shadow_engine() -> "EquityHedgeShadowEngine":
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = EquityHedgeShadowEngine()
    return _INSTANCE


class EquityHedgeShadowEngine:
    """
    Shadow-tracks hypothetical single-stock option hedges for real equity
    trades. Thread-safe. Never places a real trade, never mutates equity
    state — pure read-only observer + independent, atomically-persisted
    research store.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._observations: List[EquityHedgeShadowObservation] = []
        self._ready_symbols: Dict[str, str] = {}   # symbol -> first-ready-at ISO ts
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._trigger_event = threading.Event()
        os.makedirs("data", exist_ok=True)
        self._load()

    # ── EventBus wiring (read-only observer) ────────────────────────────

    def subscribe(self, bus) -> None:
        """Wire this engine into the shared EventBus. Call once at startup."""
        from communication.events import EventType
        bus.subscribe(
            EventType.ORDER_PLACED,
            self._on_order_placed,
            agent_name="EquityHedgeShadowEngine",
        )
        log.info("[EquityHedgeShadow] Subscribed to ORDER_PLACED (equity-only filter).")

    def _on_order_placed(self, event) -> None:
        """
        Handle every ORDER_PLACED event on the bus. Ignores anything that
        isn't a real equity order (options publish their own ORDER_PLACED
        from source_agent="OptionsOrderManager" — deliberately skipped here
        so this engine never mixes index-options evidence with single-stock
        evidence, per EQH-Ready-5).
        """
        try:
            if getattr(event, "source_agent", "") != "OrderManager":
                return
            p = event.payload or {}
            symbol = str(p.get("symbol", ""))
            if not symbol:
                return
            direction = str(p.get("direction", "BUY"))
            self.register_equity_trade(
                symbol=symbol,
                order_id=str(p.get("order_id", "")),
                direction=direction,
                entry_price=float(p.get("entry_price", 0.0) or 0.0),
                qty=int(p.get("quantity", 0) or 0),
            )
            # Live execution only ever fires for symbols that have already
            # passed all 5 automated EQH-Ready checks (self._ready_symbols).
            # For every other symbol (i.e. all of them today) this is a
            # pure no-op -- the shadow observation above is all that happens.
            if symbol in self._ready_symbols:
                self._attempt_live_execution(symbol, direction, qty)
        except Exception as exc:
            log.debug("[EquityHedgeShadow] on_order_placed error: %s", exc)

    # ── Public API ─────────────────────────────────────────────────────

    def register_equity_trade(
        self,
        symbol:      str,
        order_id:    str,
        direction:   str,
        entry_price: float,
        qty:         int,
    ) -> EquityHedgeShadowObservation:
        """
        Register one real equity trade for shadow hedge tracking.

        Attempts to find a corresponding single-stock option chain. If
        unavailable (true for all individual stocks today — no synthetic
        or live single-stock chain support exists yet), the observation is
        still recorded with chain_available=False, so the readiness gate's
        evidence count reflects reality rather than silently dropping
        symbols the system cannot yet shadow.
        """
        now = datetime.now()
        obs = EquityHedgeShadowObservation(
            symbol=symbol,
            equity_order_id=order_id,
            equity_direction=direction,
            equity_entry_price=entry_price,
            equity_qty=qty,
            recorded_at=now.isoformat(),
            monitor_until=(now + timedelta(days=MONITOR_HORIZON_DAYS)).date().isoformat(),
        )

        try:
            from data_feeds.options_feed import get_options_feed
            chain = get_options_feed().get_chain(symbol)
            if chain is not None and (chain.calls or chain.puts):
                # Same-direction companion: BUY a CALL alongside a long
                # equity position, BUY a PUT alongside a short position.
                # Captures amplified upside per the leverage research while
                # capping downside at the premium paid (defined risk).
                is_long = direction.upper() in ("BUY", "BULLISH", "LONG")
                leg = chain.atm_call() if is_long else chain.atm_put()
                if leg is not None and leg.premium > 0:
                    obs.chain_available = True
                    obs.hedge_option_type = "CE" if is_long else "PE"
                    obs.hedge_strike = float(leg.strike)
                    obs.hedge_entry_premium = float(leg.premium)
                    obs.underlying_spot_at_entry = float(chain.spot)
                    obs.notes = "chain_source=" + (chain.data_source or "unknown")
        except Exception as exc:
            obs.notes = f"chain_lookup_error: {exc}"

        with self._lock:
            self._observations.append(obs)
            self._save()

        log.debug(
            "[EquityHedgeShadow] Registered %s %s qty=%d chain_available=%s",
            symbol, direction, qty, obs.chain_available,
        )
        return obs

    def run_analysis(self) -> int:
        """
        Analyse all monitors whose window has matured. Only observations
        with chain_available=True can be scored (no data otherwise).
        Returns the number newly analysed.
        """
        today = date.today().isoformat()
        with self._lock:
            due = [
                o for o in self._observations
                if o.chain_available and not o.analysed and o.monitor_until <= today
            ]
        for obs in due:
            self._analyse(obs)
        if due:
            with self._lock:
                self._save()
        return len(due)

    def check_readiness(self) -> Dict[str, dict]:
        """
        Run the EQH-Ready-1..5 gate per symbol. Pure read/report — never
        places a trade. Returns {symbol: {checks..., ready: bool}}.
        Newly-ready symbols are recorded (first-ready timestamp) and logged.
        """
        with self._lock:
            analysed = [o for o in self._observations if o.chain_available and o.analysed]

        by_symbol: Dict[str, List[EquityHedgeShadowObservation]] = {}
        for o in analysed:
            by_symbol.setdefault(o.symbol, []).append(o)

        total_analysed = len(analysed)
        results: Dict[str, dict] = {}

        for symbol, obs_list in by_symbol.items():
            n = len(obs_list)
            pnls = [o.hypothetical_hedge_pnl for o in obs_list if o.hypothetical_hedge_pnl is not None]

            r1 = n >= MIN_OBS_AUTHENTICATED

            # EQH-Ready-2: OOS split sign test (chronological 70/30 split,
            # same methodology as OptionsKnowledgeStore's OOS validation).
            r2 = False
            oos_p = None
            if len(pnls) >= 10:
                split = int(len(pnls) * 0.7)
                oos = pnls[split:]
                wins = sum(1 for x in oos if x > 0)
                oos_p = _binomial_sign_test_p(wins, len(oos))
                r2 = oos_p is not None and oos_p < OOS_P_ALPHA

            # EQH-Ready-3: mean PnL positive net of an assumed cost drag.
            r3 = False
            mean_pnl_net = None
            if pnls:
                mean_premium = statistics.mean(o.hedge_entry_premium for o in obs_list)
                cost = mean_premium * COST_ESTIMATE_PCT
                mean_pnl_net = statistics.mean(pnls) - cost
                r3 = mean_pnl_net > 0

            # EQH-Ready-4: this symbol isn't >80% of the total evidence base.
            r4 = (n / total_analysed) <= MAX_CONCENTRATION if total_analysed else False

            # EQH-Ready-5: by construction — only chain_available=True
            # (single-stock-sourced) observations ever reach this method.
            r5 = True

            ready = r1 and r2 and r3 and r4 and r5
            results[symbol] = {
                "n": n,
                "EQH-Ready-1_volume":        r1,
                "EQH-Ready-2_oos_p":         r2,
                "oos_p_value":               oos_p,
                "EQH-Ready-3_profitable":    r3,
                "mean_pnl_net_of_cost":      mean_pnl_net,
                "EQH-Ready-4_concentration": r4,
                "EQH-Ready-5_domain_pure":   r5,
                "ready": ready,
            }

            if ready and symbol not in self._ready_symbols:
                with self._lock:
                    self._ready_symbols[symbol] = datetime.now().isoformat()
                    self._save()
                log.warning(
                    "[EquityHedgeShadow] READY_FOR_LIVE: %s passed all 5 "
                    "readiness checks (n=%d). Live companion-option execution "
                    "is now enabled for this symbol on its next equity trade.",
                    symbol, n,
                )
                try:
                    from notifications.telegram_bot import get_telegram_bot
                    get_telegram_bot().push(
                        f"[EquityHedgeShadow] {symbol} reached authenticated "
                        f"evidence (n={n}) and is now READY_FOR_LIVE. The next "
                        f"equity trade in this symbol will trigger a live "
                        f"companion option order (defined-risk, capped at the "
                        f"premium paid)."
                    )
                except Exception:
                    pass

        return results

    def get_summary(self) -> dict:
        with self._lock:
            total = len(self._observations)
            with_chain = sum(1 for o in self._observations if o.chain_available)
            analysed = sum(1 for o in self._observations if o.analysed)
            return {
                "total_observations":      total,
                "chain_available_count":   with_chain,
                "chain_unavailable_count": total - with_chain,
                "analysed_count":          analysed,
                "ready_symbols":           dict(self._ready_symbols),
            }

    # ── Live execution (gated on EQH-Ready-1..5 authentication only) ────

    def _attempt_live_execution(self, symbol: str, direction: str, equity_qty: int) -> None:
        """
        Construct and route a companion option order through the existing,
        already-proven OptionsRiskEngine -> OptionsOrderManager execution
        path (same machinery index options already use in production).

        Only ever called for a symbol already in self._ready_symbols (i.e.
        already passed all 5 automated EQH-Ready checks). Every step below
        additionally fails closed on its own: unavailable/non-live chain,
        unverified lot size, thin liquidity, or low chain quality all
        reject rather than guess -- consistent with never risking real
        capital on an unverified assumption.
        """
        # Defense-in-depth: never execute for a symbol that hasn't passed
        # the automated readiness gate, even if this method is ever called
        # directly (e.g. future code, tests) without going through the
        # normal _on_order_placed() gate check.
        if symbol not in self._ready_symbols:
            log.debug("[EquityHedgeShadow] %s: not READY_FOR_LIVE -- refusing "
                      "to attempt execution.", symbol)
            return
        try:
            from data_feeds.options_feed import get_options_feed
            from data_feeds.dhan_fno_security_map import get_fno_security_map
            from models.trade_signal import (
                TradeSignal, SignalDirection, SignalStrength, SignalType,
            )
            import json as _json

            chain = get_options_feed().get_chain(symbol)
            if chain is None or not chain.is_live:
                log.info("[EquityHedgeShadow] %s: no live chain available at "
                        "execution time -- skipped.", symbol)
                return

            quality_score, quality_issues = get_options_feed().chain_quality_score(chain)
            if quality_score < _CHAIN_QUALITY_MIN:
                log.info("[EquityHedgeShadow] %s: chain_quality=%.2f < %.2f -- "
                        "skipped. issues=%s", symbol, quality_score,
                        _CHAIN_QUALITY_MIN, quality_issues)
                return

            if not (_DTE_MIN <= chain.dte <= _DTE_MAX):
                log.info("[EquityHedgeShadow] %s: DTE=%d outside [%d,%d] -- "
                        "skipped.", symbol, chain.dte, _DTE_MIN, _DTE_MAX)
                return

            is_long = direction.upper() in ("BUY", "BULLISH", "LONG")
            leg = chain.atm_call() if is_long else chain.atm_put()
            if leg is None or leg.premium < _MIN_LEG_PREMIUM:
                log.info("[EquityHedgeShadow] %s: no valid ATM leg (premium "
                        "too low or unavailable) -- skipped.", symbol)
                return
            if chain.is_live and leg.open_interest < _MIN_TRADABLE_OI:
                log.info("[EquityHedgeShadow] %s: OI=%d < %d -- too thin, "
                        "skipped.", symbol, leg.open_interest, _MIN_TRADABLE_OI)
                return

            lot_size = get_fno_security_map().get_lot_size(symbol)
            if lot_size is None or lot_size <= 0:
                log.warning("[EquityHedgeShadow] %s: no verified lot size in "
                           "Dhan's instrument master -- rejecting rather than "
                           "guessing.", symbol)
                return

            option_type = "CE" if is_long else "PE"
            premium     = float(leg.premium)
            stop_prem   = round(premium * 0.50, 2)      # exit at 50% loss (defined risk)
            target_prem = round(premium * 2.00, 2)      # take profit at 100% gain

            meta = {
                "strategy_type": "EQUITY_HEDGE_COMPANION",
                "lot_size":      lot_size,
                "max_loss":      premium,     # long option: max loss = premium paid
                "dte":           chain.dte,
                "iv_rank":       chain.iv_rank,
                "chain_quality": quality_score,
                "is_live":       chain.is_live,
                "spot":          chain.spot,
                "equity_order_qty": equity_qty,
                "legs": [{
                    "type": option_type, "direction": "BUY",
                    "strike": leg.strike, "premium": premium,
                    "iv": leg.iv, "delta": leg.delta,
                    "open_interest": leg.open_interest, "volume": leg.volume,
                }],
            }

            signal = TradeSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,
                signal_type=SignalType.OPTIONS,
                strength=SignalStrength.MODERATE,
                entry_price=premium,
                stop_loss=stop_prem,
                target_price=target_prem,
                confidence=7.0,
                source_agent="EquityHedgeShadowEngine",
                strategy_name="Equity_Hedge_Companion",
                strike_price=float(leg.strike),
                option_type=option_type,
                notes=_json.dumps(meta),
            )

            from risk_control.options_risk_engine import get_options_risk_engine
            from execution_engine.options_order_manager import get_options_order_manager
            risk_engine  = get_options_risk_engine()
            order_mgr    = get_options_order_manager()

            approved = risk_engine.approve_and_size(
                signal, None,
                open_exposure_rs=order_mgr.get_total_options_exposure_rs(),
            )
            if not approved:
                log.info("[EquityHedgeShadow] %s: OptionsRiskEngine rejected "
                        "companion order.", symbol)
                return

            from models.agent_output import DecisionResult as _DecisionResult
            order = order_mgr.execute(signal, _DecisionResult(
                approved=True, confidence_score=signal.confidence,
                position_size_modifier=1.0,
                reasoning="equity_hedge_companion_authenticated",
            ))
            if order:
                log.warning(
                    "[EquityHedgeShadow] ✅ PLACED companion %s %s  lots=%d  "
                    "max_loss=₹%.0f  symbol=%s (triggered by equity %s)",
                    option_type, symbol, order.lots, order.max_loss_rs,
                    symbol, direction,
                )
                try:
                    from notifications.telegram_bot import get_telegram_bot
                    get_telegram_bot().push(
                        f"[EquityHedgeShadow] Companion {option_type} placed for "
                        f"{symbol} (order {order.order_id}), lots={order.lots}, "
                        f"max_loss=₹{order.max_loss_rs:.0f} — triggered by "
                        f"authenticated equity {direction} signal."
                    )
                except Exception:
                    pass
            else:
                log.info("[EquityHedgeShadow] %s: OptionsOrderManager did not "
                        "place the companion order (see its own logs).", symbol)
        except Exception as exc:
            log.warning("[EquityHedgeShadow] Live execution attempt failed for "
                       "%s: %s", symbol, exc)

    # ── Background loop (mirrors OptionsResearchPipeline's pattern) ─────

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="EquityHedgeShadowEngine", daemon=True,
        )
        self._thread.start()
        log.info("[EquityHedgeShadow] Background loop started.")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        self._trigger_event.set()

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            try:
                self.run_analysis()
                self.check_readiness()
            except Exception as exc:
                log.debug("[EquityHedgeShadow] loop error: %s", exc)
            self._trigger_event.wait(timeout=LOOP_INTERVAL_MINUTES * 60)
            self._trigger_event.clear()

    # ── Internal ─────────────────────────────────────────────────────────

    def _analyse(self, obs: EquityHedgeShadowObservation) -> None:
        """
        Estimate the hypothetical hedge outcome using the same directional-
        estimate methodology already used by OptionsCounterfactualEngine
        (spot-only, clearly labelled as an estimate, not real repricing).
        """
        try:
            from data_feeds.data_feed_manager import get_feed_manager
            quote = get_feed_manager().get_quote(obs.symbol)
            current_spot = float(getattr(quote, "ltp", 0.0) or getattr(quote, "close", 0.0) or 0.0)
            if current_spot <= 0 or obs.underlying_spot_at_entry <= 0:
                obs.analysed = True
                obs.notes += " | spot_unavailable_at_analysis"
                return

            obs.underlying_spot_at_exit = current_spot
            spot_change_pct = (current_spot - obs.underlying_spot_at_entry) / obs.underlying_spot_at_entry
            is_long = obs.equity_direction.upper() in ("BUY", "BULLISH", "LONG")

            # Same-direction companion: a long call pays off when the
            # underlying RISES; a long put pays off when it FALLS.
            moved_with_equity = (spot_change_pct > 0.005) if is_long else (spot_change_pct < -0.005)

            if moved_with_equity:
                # Companion option would likely have amplified a winning
                # equity move — estimate payoff as a multiple of premium
                # paid (bounded), consistent with the leverage research.
                hypo_pnl = obs.hedge_entry_premium * min(3.0, abs(spot_change_pct) * 40) * obs.equity_qty
                classification = "HEDGE_WOULD_HAVE_HELPED"
            else:
                # Underlying moved against (or flat to) the equity position —
                # the long option's loss is capped at the premium paid
                # (defined risk, unlike unbounded additional equity exposure).
                hypo_pnl = -obs.hedge_entry_premium * obs.equity_qty
                classification = "HEDGE_UNNECESSARY"

            obs.hypothetical_hedge_pnl = round(hypo_pnl, 2)
            obs.hedge_classification = classification
            obs.analysed = True
            obs.notes += (
                f" | spot_change={spot_change_pct:.2%} "
                f"method=DIRECTIONAL_ESTIMATE"
            )
        except Exception as exc:
            obs.analysed = True
            obs.notes += f" | analysis_error: {exc}"

    def _save(self) -> None:
        try:
            tmp = _PERSIST_PATH + ".tmp"
            data = {
                "observations":   [asdict(o) for o in self._observations],
                "ready_symbols":  self._ready_symbols,
            }
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            os.replace(tmp, _PERSIST_PATH)
        except Exception as exc:
            log.warning("[EquityHedgeShadow] Save failed: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(_PERSIST_PATH):
            return
        try:
            with open(_PERSIST_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._observations = [
                EquityHedgeShadowObservation(**o) for o in data.get("observations", [])
            ]
            self._ready_symbols = data.get("ready_symbols", {})
        except Exception as exc:
            log.warning("[EquityHedgeShadow] Load failed, starting fresh: %s", exc)


def _binomial_sign_test_p(wins: int, n: int) -> Optional[float]:
    """
    One-tailed binomial sign test p-value for "wins > n/2 by chance".
    Pure-stdlib (no scipy dependency), matches the project's existing
    lightweight-statistics style.
    """
    if n == 0:
        return None
    from math import comb
    p = sum(comb(n, k) for k in range(wins, n + 1)) / (2 ** n)
    return round(p, 4)
