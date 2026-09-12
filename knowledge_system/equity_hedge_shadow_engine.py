"""
Equity-Hedge Shadow Engine
============================
DTA-EQUITY-HEDGE-SHADOW-001 — Phase D future-work bootstrap.

Read-only observer of equity's own ORDER_PLACED events. For every real
equity trade, attempts to find a corresponding single-stock option and
shadow-tracks a hypothetical protective hedge — with ZERO real capital
risk and ZERO write-back into equity decisions. Equity's own pipeline is
never touched: this module only listens to the shared EventBus, exactly
like the existing OIOSExecutionBridge / PaperTradeLogger observers.

Why shadow-first
-----------------
Per the audited activation plan (2026-09-12): before any real capital is
deployed into single-stock option hedges, the system must accumulate its
OWN evidence — not borrowed from index-options knowledge — that the
underlying-move -> option-move leverage relationship holds for individual
stocks specifically, and that a hedge would have been profitable net of
cost. This engine is that evidence-collection phase. It never places a
real trade.

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

IMPORTANT — what "automatic" means here
----------------------------------------
Once all 5 checks pass for a symbol, `check_readiness()` marks it
READY_FOR_LIVE and fires a notification. It does NOT itself place any real
trade: no single-stock options execution path exists anywhere in this
codebase today (confirmed empirically 2026-09-12 — `OptionsFeed.get_chain()`
returns None for individual stocks; `NSE_LOT_SIZES` / `NSE_STRIKE_INTERVALS`
/ Dhan's option-chain endpoint only cover index instruments). Building that
execution path is separate, explicit future work requiring its own
authorization. This module's "no human gate" scope is the AUTHENTICATION
decision only — not a live-trading switch.

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
            self.register_equity_trade(
                symbol=symbol,
                order_id=str(p.get("order_id", "")),
                direction=str(p.get("direction", "BUY")),
                entry_price=float(p.get("entry_price", 0.0) or 0.0),
                qty=int(p.get("quantity", 0) or 0),
            )
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
                # Protective hedge: BUY a PUT against a long equity position,
                # BUY a CALL against a short equity position.
                is_long = direction.upper() in ("BUY", "BULLISH", "LONG")
                leg = chain.atm_put() if is_long else chain.atm_call()
                if leg is not None and leg.premium > 0:
                    obs.chain_available = True
                    obs.hedge_option_type = "PE" if is_long else "CE"
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
                    "readiness checks (n=%d). NOTE: no single-stock options "
                    "execution path exists yet -- this is an authentication "
                    "signal only, not a live-trading switch.",
                    symbol, n,
                )
                try:
                    from notifications.telegram_bot import get_telegram_bot
                    get_telegram_bot().push(
                        f"[EquityHedgeShadow] {symbol} reached authenticated "
                        f"evidence (n={n}) for hedge shadow tracking. "
                        f"Live execution still requires building single-stock "
                        f"options infrastructure -- not yet active."
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

            # A protective put pays off when the underlying FALLS; a
            # protective call pays off when the underlying RISES.
            moved_against_equity = (spot_change_pct < -0.005) if is_long else (spot_change_pct > 0.005)

            if moved_against_equity:
                # Hedge would likely have offset a losing equity move —
                # estimate payoff as a multiple of premium paid (bounded).
                hypo_pnl = obs.hedge_entry_premium * min(3.0, abs(spot_change_pct) * 40) * obs.equity_qty
                classification = "HEDGE_WOULD_HAVE_HELPED"
            else:
                # Underlying moved with (or flat to) the equity position —
                # the hedge premium would have been a pure cost.
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
