"""
Replay Engine
=============
Non-invasive replay harness.  Subclasses MasterOrchestrator and overrides
two injection points to supply historical data instead of live feeds:

  1. market_data_ai.fetch()      — patched with the day's historical dict
  2. global_intelligence.run()   — patched with a mock premarket_bias so no
                                   live global API calls are made

All production logic (strategy lab, risk, debate, execution) runs exactly as
in production, in paper mode.
"""

from __future__ import annotations

import hashlib
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestrator.master_orchestrator import MasterOrchestrator
from simulation_replay.historical_loader import DayData
from simulation_replay.trace_logger import TraceCollector
from utils import get_logger

log = get_logger(__name__)

TRACE_DIR = Path(__file__).resolve().parent.parent / "simulation_logs" / "decision_trace"


# ── Mock objects ──────────────────────────────────────────────────────────────

class _MockPremarketBias:
    """Minimal premarket bias duck-typed to what the orchestrator reads."""
    def __init__(self, vix: float = 15.0):
        # regime_nudge: "bullish" / "bearish" / "neutral"
        self.regime_nudge       = "bullish" if vix < 14 else ("bearish" if vix > 20 else "neutral")
        self.bias_score         = 3.0 if self.regime_nudge == "bullish" else (-3.0 if self.regime_nudge == "bearish" else 0.0)
        # GlobalDataAI expects a distortion object too
        self.distortion         = _MockDistortion()

class _MockDistortion:
    risk_level             = "LOW"
    stress_score           = 0
    any_distortion         = False
    active_flags: List     = field(default_factory=list) if False else []
    sector_watches: List   = field(default_factory=list) if False else []

    class _overrides:
        trading_allowed              = True
        position_size_multiplier     = 1.0
        max_new_trades               = 10
        hedge_preferred              = False

    behavior_overrides = _overrides()


# ── Per-day result ────────────────────────────────────────────────────────────

@dataclass
class DayCycleResult:
    day_num:        int
    trading_date:   date
    raw_data:       Dict[str, Any]
    executed_trades: List[Dict[str, Any]] = field(default_factory=list)
    signals_found:  int   = 0
    errors:         List[str] = field(default_factory=list)
    trace_path:     Optional[Path] = None
    cycle_ok:       bool  = True
    regime:         str   = "UNKNOWN"
    vix:            float = 0.0
    nifty_close:    float = 0.0
    nifty_change:   float = 0.0
    rejection_funnel: Dict[str, int] = field(default_factory=dict)


# ── Replay Orchestrator ───────────────────────────────────────────────────────

class ReplayOrchestrator(MasterOrchestrator):
    """
    Extends MasterOrchestrator with historical data injection.
    Paper-trading mode is always enforced.

    Usage:
        orch = ReplayOrchestrator()
        orch.setup_replay()
        result = orch.run_replay_day(day_data)
    """

    def __init__(self) -> None:
        log.info("[ReplayOrchestrator] Initialising (paper mode) …")
        super().__init__()
        self._replay_raw_data: Optional[Dict[str, Any]] = None
        self.collector = TraceCollector(self.bus)

    # ── Data injection helpers ────────────────────────────────────────────────

    def _inject_day(self, day_data: DayData) -> None:
        """Monkey-patch market_data_ai.fetch and global_intelligence.run for one day."""
        self._replay_raw_data = day_data.raw_data
        vix = day_data.raw_data.get("vix", 15.0)

        # 1. Patch market_data_ai.fetch
        self.market_data_ai.fetch = lambda: dict(self._replay_raw_data)

        # 2. Patch global_intelligence.run  (avoid live API calls)
        mock_bias = _MockPremarketBias(vix=vix)
        self.global_intelligence.run            = lambda: mock_bias
        # Also patch the last_distortion attribute so distortion log doesn't crash
        self.global_intelligence.last_distortion = mock_bias.distortion

        # 3. Patch EquityScannerAI._live_watchlist so the scanner sees real
        #    historical stock data instead of its built-in random noise.
        if day_data.stock_watchlist:
            import opportunity_engine.equity_scanner_ai as _scanner_mod
            self._original_live_watchlist = _scanner_mod._live_watchlist
            watchlist_snapshot = list(day_data.stock_watchlist)
            _scanner_mod._live_watchlist = lambda extended=False: watchlist_snapshot
        else:
            self._original_live_watchlist = None

        log.info("[ReplayOrchestrator] Injected day %d / %s  (VIX=%.1f  stocks=%d)",
                 day_data.day_num, day_data.date, vix, len(day_data.stock_watchlist))

    def _restore(self) -> None:
        """Remove monkey-patches (graceful, exceptions suppressed)."""
        for attr in ("fetch",):
            try:
                delattr(self.market_data_ai, attr)
            except AttributeError:
                pass
        for attr in ("run", "last_distortion"):
            try:
                delattr(self.global_intelligence, attr)
            except AttributeError:
                pass
        # Restore original _live_watchlist
        if getattr(self, "_original_live_watchlist", None) is not None:
            try:
                import opportunity_engine.equity_scanner_ai as _scanner_mod
                _scanner_mod._live_watchlist = self._original_live_watchlist
            except Exception:
                pass
            self._original_live_watchlist = None

    # ── Public API ────────────────────────────────────────────────────────────

    def run_replay_day(self, day_data: DayData) -> DayCycleResult:
        """
        Run one complete trading cycle with the given day's historical data.
        Returns a DayCycleResult with all captured information.
        """
        result = DayCycleResult(
            day_num      = day_data.day_num,
            trading_date = day_data.date,
            raw_data     = day_data.raw_data,
            vix          = day_data.raw_data.get("vix", 0.0),
            nifty_close  = day_data.raw_data.get("indices", {}).get("NIFTY 50", {}).get("close", 0.0),
            nifty_change = day_data.raw_data.get("indices", {}).get("NIFTY 50", {}).get("change_pct", 0.0),
        )

        try:
            self._inject_day(day_data)
            self.collector.clear()
            self.collector.start()

            # ── Run the full production cycle ─────────────────────────
            self.run_full_cycle()

            # ── Capture results ───────────────────────────────────────
            trace = self.collector.get_trace()
            result.rejection_funnel = _extract_rejection_funnel(trace)
            # Build symbol → strategy map from TRADE_APPROVED events
            approved_strategy: Dict[str, str] = {}
            approved_score: Dict[str, float] = {}
            for e in trace:
                if str(e.get("event_type", "")) in (
                    "EventType.TRADE_APPROVED", "decision.trade.approved"
                ):
                    p = e.get("payload", {})
                    sym = p.get("symbol", "")
                    if sym and sym not in approved_strategy:
                        approved_strategy[sym]  = p.get("strategy", "")
                        approved_score[sym]     = p.get("confidence_score", 0.0)

            # Build intraday H/L lookup from today's watchlist (populated by historical loader)
            hl_lookup: Dict[str, tuple] = {}
            for wl_item in day_data.stock_watchlist:
                s_sym  = wl_item.get("symbol", "")
                s_high = float(wl_item.get("day_high", wl_item.get("ltp", 0.0)) or 0.0)
                s_low  = float(wl_item.get("day_low",  wl_item.get("ltp", 0.0)) or 0.0)
                if s_sym:
                    hl_lookup[s_sym] = (s_high, s_low)

            # Deduplicate ORDER_PLACED events by symbol (subscription leak)
            seen_symbols: set = set()
            executed_rows = []
            for e in trace:
                if str(e.get("event_type", "")) in (
                    "EventType.ORDER_PLACED", "execution.order.placed"
                ):
                    payload = e.get("payload", {})
                    sym = payload.get("symbol", "")
                    if sym and sym not in seen_symbols:
                        seen_symbols.add(sym)
                        entry  = float(payload.get("entry_price", 0.0) or 0.0)
                        sl     = float(payload.get("stop_loss",   0.0) or 0.0)
                        target = float(payload.get("target_price", 0.0) or 0.0)
                        qty    = int(payload.get("quantity", 1) or 1)
                        dirn   = str(payload.get("direction", "BUY"))
                        strat  = payload.get("strategy", "") or approved_strategy.get(sym, "")
                        score  = float(payload.get("confidence", 0.0) or approved_score.get(sym, 0.0))
                        pnl    = _sim_pnl(entry, sl, target, qty, dirn, day_data.date, sym)
                        day_high, day_low = hl_lookup.get(sym, (0.0, 0.0))
                        executed_rows.append({
                            "symbol":   sym,
                            "strategy": strat,
                            "score":    score,
                            "entry":    entry,
                            "sl":       sl,
                            "target":   target,
                            "qty":      qty,
                            "pnl":      pnl,
                            "day_high": day_high,
                            "day_low":  day_low,
                            "direction": dirn,
                        })

            result.executed_trades = executed_rows
            result.regime = str(getattr(self._last_snapshot, "regime", "UNKNOWN"))
            result.signals_found = _count_signals_from_trace(trace)

            # ── EOD learning on this day's data ───────────────────────
            try:
                self._do_eod_learning()
            except Exception as eod_exc:
                log.warning("[ReplayOrchestrator] EOD learning error: %s", eod_exc)
                result.errors.append(f"eod_learning: {eod_exc}")

            # ── EOD position close + heat reset ───────────────────────
            # In replay each day is self-contained.  All open orders are
            # closed at EOD (realistic intraday behaviour) and portfolio
            # heat is zeroed so the next day starts with a clean slate.
            # Without this the heat accumulates permanently across 180
            # days and the portfolio heat gate rejects every signal after
            # the 5th trade ever placed.
            try:
                open_before = len(self.order_manager.get_open_orders())
                if open_before:
                    self.order_manager.close_all_positions()
                    log.info("[ReplayOrchestrator] EOD: closed %d open position(s).",
                             open_before)
                self.risk_manager.update_portfolio_heat(0.0)
            except Exception as eod_close_exc:
                log.warning("[ReplayOrchestrator] EOD close error: %s", eod_close_exc)

        except Exception as exc:
            tb = traceback.format_exc()
            log.error("[ReplayOrchestrator] Day %d cycle error:\n%s", day_data.day_num, tb)
            result.errors.append(str(exc))
            result.cycle_ok = False
            trace = self.collector.get_trace()   # capture what we have
            result.signals_found   = _count_signals_from_trace(trace)
            result.rejection_funnel = _extract_rejection_funnel(trace)
        finally:
            self.collector.stop()
            try:
                trace_path = self.collector.save(
                    day_num      = day_data.day_num,
                    trading_date = day_data.date,
                    output_dir   = TRACE_DIR,
                )
                result.trace_path = trace_path
            except Exception as trace_exc:
                log.warning("[ReplayOrchestrator] Trace save error: %s", trace_exc)
            self._restore()

        log.info(
            "[ReplayOrchestrator] Day %d done — regime=%s  vix=%.1f  "
            "signals=%d  trades=%d  errors=%d",
            day_data.day_num, result.regime, result.vix,
            result.signals_found, len(result.executed_trades), len(result.errors),
        )
        return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _positions_to_dicts(positions: Dict) -> List[Dict[str, Any]]:
    rows = []
    for sym, pos in positions.items():
        rows.append({
            "symbol":   sym,
            "entry":    getattr(pos, "entry_price",   0.0),
            "sl":       getattr(pos, "stop_loss",     0.0),
            "target":   getattr(pos, "target_price",  0.0),
            "qty":      getattr(pos, "quantity",      0),
            "strategy": getattr(pos, "strategy_name", ""),
            "pnl":      getattr(pos, "unrealised_pnl", 0.0),
        })
    return rows


def _count_signals_from_trace(trace: List[Dict]) -> int:
    """Read total signal count from SCAN_COMPLETE payload (most accurate source)."""
    # SCAN_COMPLETE payload has {equity, options, arb, total} — use the first one
    for e in trace:
        if str(e.get("event_type", "")) in (
            "EventType.SCAN_COMPLETE", "opportunity.scan.complete"
        ):
            payload = e.get("payload", {})
            total = payload.get("total", 0)
            if total:
                return int(total)   # only need first occurrence (others are duplicates)
    # Fallback: unique symbols from EQUITY_SIGNAL_FOUND
    signal_events = {
        "EventType.EQUITY_SIGNAL_FOUND",
        "opportunity.equity.found",
        "opportunity.options.found",
        "opportunity.arbitrage.found",
    }
    seen_syms: set = set()
    for e in trace:
        if str(e.get("event_type", "")) in signal_events:
            sym = e.get("payload", {}).get("symbol", "")
            if sym:
                seen_syms.add(sym)
    return len(seen_syms)


# ── Simulated outcome ─────────────────────────────────────────────────────────

def _sim_pnl(
    entry: float,
    sl: float,
    target: float,
    qty: int,
    direction: str,
    trading_date: "date | None",
    symbol: str,
    win_rate_pct: int = 55,
) -> float:
    """
    Deterministic (hash-seeded) simulated trade outcome.

    Uses MD5 of (date + symbol) to produce a stable, repeatable win/loss
    decision so the same replay run always yields the same PnL.  The default
    55 % win rate reflects a slightly-above-random NSE intraday edge.

    Returns 0.0 when entry or SL/target are missing (trade data incomplete).
    """
    if entry <= 0 or sl <= 0 or target <= 0:
        return 0.0
    qty = max(qty, 1)
    date_str = str(trading_date) if trading_date else "unknown"
    seed_hex  = hashlib.md5(f"{date_str}:{symbol}".encode()).hexdigest()[:8]
    seed_val  = int(seed_hex, 16)          # 0 … 4_294_967_295
    win       = (seed_val % 100) < win_rate_pct

    if direction.upper() in ("BUY", "LONG"):
        reward = (target - entry) * qty
        risk   = (entry  - sl)    * qty
    else:  # SELL / SHORT
        reward = (entry  - target) * qty
        risk   = (sl     - entry)  * qty

    return round(reward if (win and reward > 0) else -abs(risk), 2)


def _extract_rejection_funnel(trace: List[Dict]) -> Dict[str, int]:
    """
    Read per-day EventBus trace and return a funnel dict showing how many
    signals survived each filter stage.

    Stage key          Source event
    ─────────────────  ──────────────────────────────────
    raw_signals        SCAN_COMPLETE.total
    after_strategy_lab STRATEGY_LAB_COMPLETE.after_bt
    after_risk_control RISK_CHECK_PASSED.approved
    after_simulation   SIMULATION_COMPLETE.approved
    after_guardian     RISK_GUARDIAN_COMPLETE.approved
    debate_approved    count(TRADE_APPROVED events)
    executed           unique symbols in ORDER_PLACED events
    """
    funnel: Dict[str, int] = {
        "raw_signals":        0,
        "after_strategy_lab": 0,
        "after_risk_control": 0,
        "after_simulation":   0,
        "after_guardian":     0,
        "debate_approved":    0,
        "executed":           0,
    }
    trade_approved_count = 0
    order_placed_syms: set = set()

    for e in trace:
        et = str(e.get("event_type", ""))
        p  = e.get("payload", {}) or {}

        if et in ("EventType.SCAN_COMPLETE", "opportunity.scan.complete"):
            funnel["raw_signals"] = max(funnel["raw_signals"], int(p.get("total", 0) or 0))

        elif et in ("EventType.STRATEGY_LAB_COMPLETE", "strategy.lab.complete"):
            funnel["after_strategy_lab"] = max(
                funnel["after_strategy_lab"], int(p.get("after_bt", 0) or 0))

        elif et in ("EventType.RISK_CHECK_PASSED", "risk.check.passed"):
            funnel["after_risk_control"] = max(
                funnel["after_risk_control"], int(p.get("approved", 0) or 0))

        elif et in ("EventType.SIMULATION_COMPLETE", "simulation.complete"):
            funnel["after_simulation"] = max(
                funnel["after_simulation"], int(p.get("approved", 0) or 0))

        elif et in ("EventType.RISK_GUARDIAN_COMPLETE", "risk.guardian.complete"):
            funnel["after_guardian"] = max(
                funnel["after_guardian"], int(p.get("approved", 0) or 0))

        elif et in ("EventType.TRADE_APPROVED", "decision.approved"):
            trade_approved_count += 1

        elif et in ("EventType.ORDER_PLACED", "execution.order.placed"):
            sym = (p.get("symbol") or "")
            if sym:
                order_placed_syms.add(sym)

    funnel["debate_approved"] = trade_approved_count
    funnel["executed"]        = len(order_placed_syms)

    # If guardian event was not emitted (upgrade path), infer from simulation
    if funnel["after_guardian"] == 0 and funnel["after_simulation"] > 0:
        funnel["after_guardian"] = funnel["after_simulation"]

    return funnel
