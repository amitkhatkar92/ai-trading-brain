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
from simulation_replay.integrity_validator import (
    IntegrityValidator, ReplayIntegritySummary, ReplayIntegrityError,
)
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

    def __init__(self, strict_validation: bool = False) -> None:
        log.info("[ReplayOrchestrator] Initialising (paper mode) …")
        super().__init__()
        self._replay_raw_data: Optional[Dict[str, Any]] = None
        self.collector = TraceCollector(self.bus)
        # Closed trades for the current replay day — set by _close_replay_positions_with_outcomes()
        self._current_day_trades: list = []
        # Per-day learning measurements read by the integrity validator after _do_eod_learning()
        self._last_feature_rows_before: int = 0
        self._last_labels_updated:      int = 0
        self._last_ede_completed:       bool = False
        self._last_ede_report:          str  = ""
        self._current_replay_date:      Optional[str] = None
        self._validator = IntegrityValidator(strict=strict_validation)
        self._validator.snapshot_start()

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

    # ── Replay-specific EOD helpers ───────────────────────────────────────────

    def _close_replay_positions_with_outcomes(self, day_data: DayData) -> int:
        """
        Close all open positions using real historical OHLC price resolution.
        Resets portfolio heat.  Must be called BEFORE _do_eod_learning() so
        _current_day_trades is populated with evidence-based outcomes.
        """
        self._current_day_trades = []
        self._current_replay_date = str(day_data.date)
        open_orders = self.order_manager.get_open_orders()
        if not open_orders:
            log.info("[ReplayOrchestrator] EOD close: no open positions this day.")
            self.risk_manager.update_portfolio_heat(0.0)
            return 0

        # Per-symbol OHLC from today's historical data
        _ohlc: Dict[str, tuple] = {
            item.get("symbol", ""): (
                float(item.get("day_high", item.get("ltp", 0.0)) or 0.0),
                float(item.get("day_low",  item.get("ltp", 0.0)) or 0.0),
                float(item.get("ltp", 0.0) or 0.0),
            )
            for item in day_data.stock_watchlist
            if item.get("symbol")
        }

        for rec in list(open_orders):
            entry  = rec.entry_price
            sl     = rec.initial_stop_loss if rec.initial_stop_loss > 0 else rec.stop_loss
            target = rec.target
            qty    = rec.quantity
            symbol = rec.symbol

            if entry <= 0 or sl <= 0 or target <= 0:
                # Incomplete signal — close at entry, exclude from learning
                self.order_manager.close_position(rec.order_id, entry, reason="ORPHAN_CLOSE")
                continue

            day_high, day_low, eod_close = _ohlc.get(symbol, (0.0, 0.0, 0.0))
            exit_price, reason = _resolve_historical_outcome(
                entry, sl, target, rec.direction, day_high, day_low, eod_close
            )
            self.order_manager.close_position(rec.order_id, exit_price, reason=reason)

            if reason == "ORPHAN_CLOSE":
                # No historical OHLC for this symbol — exclude from learning
                continue

            # close_position() does not set r_multiple; compute it here for learning.
            # OrderRecord is a plain @dataclass (no __slots__) so dynamic attr works at runtime.
            risk = abs(entry - sl) * max(qty, 1)
            rec.r_multiple = round(rec.pnl / risk, 3) if risk > 0 else 0.0  # type: ignore[attr-defined]

            self._current_day_trades.append(rec)

        n = len(self._current_day_trades)
        log.info("[ReplayOrchestrator] EOD close: %d position(s) with historical outcomes.", n)
        self.risk_manager.update_portfolio_heat(0.0)
        return n

    def _do_eod_learning(self) -> None:
        """
        Replay-specific EOD learning override.

        Uses _current_day_trades (set by _close_replay_positions_with_outcomes)
        instead of the production CSV-recovery path.  The CSV path is bypassed
        because all replay days share datetime.now() as their write timestamp,
        causing cross-day label contamination when more than one day has run.
        All production learning APIs are called with unchanged signatures.
        """
        self._last_feature_rows_before = 0
        self._last_labels_updated      = 0
        self._last_ede_completed       = False
        self._last_ede_report          = ""

        trades = list(self._current_day_trades)
        if not trades:
            log.info("[ReplayOrchestrator] EOD learning: no closed trades — skipped.")
            return

        log.info("[ReplayOrchestrator] EOD learning: %d trade(s).", len(trades))

        # Core learning engine
        self.learning_engine.learn(trades)

        # Per-trade performance tracking
        for trade in trades:
            strategy   = (getattr(trade, "strategy",      None)
                          or getattr(trade, "strategy_name", "unknown"))
            regime     = (getattr(trade, "signal_regime", None)
                          or getattr(trade, "regime",       "unknown"))
            pnl        = getattr(trade, "pnl",        0.0)
            r_multiple = getattr(trade, "r_multiple",  0.0)
            won        = pnl > 0
            self.performance_evaluator.record_trade(
                strategy=strategy, regime=regime,
                pnl=pnl, r_multiple=r_multiple, won=won,
            )
            self.perf_tracker.record_trade(
                strategy, pnl_r=r_multiple,
                order_id=getattr(trade, "order_id", ""),
            )
            if regime and regime != "unknown":
                self.regime_strategy_map.record(regime, strategy, pnl_r=r_multiple)

        # Meta-Learning feedback — accumulates verified historical outcomes into k-NN model
        for trade in trades:
            strategy   = (getattr(trade, "strategy",      None)
                          or getattr(trade, "strategy_name", "unknown"))
            pnl        = getattr(trade, "pnl",        0.0)
            r_multiple = getattr(trade, "r_multiple",  0.0)
            self.meta_learning.record_result(
                strategy   = strategy,
                snapshot   = None,   # uses MetaLearningEngine._last_snapshot from run_full_cycle
                r_multiple = r_multiple,
                return_pct = pnl / 1_000_000 * 100,
                won        = pnl > 0,
                trade_date = self._current_replay_date,
            )
        self.meta_learning.retrain_if_due()

        # Edge Discovery: back-fill labels then mine patterns
        ede_snapshot = self._last_snapshot
        if ede_snapshot is not None:
            _traded_syms = {getattr(t, "symbol", "") for t in trades if getattr(t, "symbol", "")}
            _zero_before = _count_zero_labels(_traded_syms)
            self._last_feature_rows_before = _zero_before

            for trade in trades:
                sym     = getattr(trade, "symbol",       "?")
                pnl     = getattr(trade, "pnl",          0.0)
                entry   = getattr(trade, "entry_price",  1.0) or 1.0
                ret_pct = pnl / entry if entry else 0.0
                strat   = (getattr(trade, "strategy",      "")
                           or getattr(trade, "strategy_name", ""))
                self.edge_discovery.enrich_with_outcomes(sym, ret_pct)
                self.edge_discovery.record_outcome(strat, pnl > 0)

            self._last_labels_updated = max(0, _zero_before - _count_zero_labels(_traded_syms))

            ede_report = self.edge_discovery.run_discovery_cycle(
                ede_snapshot, publish_event=True)
            self._last_ede_completed = True
            self._last_ede_report    = ede_report
            log.info("[ReplayOrchestrator] EDE: %s", ede_report)
        else:
            log.info("[ReplayOrchestrator] No snapshot cached — EDE skipped this day.")

        try:
            from communication import EventType, LearningEvent
            self.bus.publish(LearningEvent(
                event_type=EventType.LEARNING_CYCLE_COMPLETE,
                source_agent="LearningEngine",
                payload={"trades_processed": len(trades)},
            ))
        except Exception:
            pass

    # ── Public API ────────────────────────────────────────────────────────────

    def get_integrity_summary(self) -> ReplayIntegritySummary:
        """Generate and log the Replay Learning Integrity Report."""
        return self._validator.generate_summary()

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

            # Build intraday H/L/close lookup from today's watchlist
            hl_lookup: Dict[str, tuple] = {}
            for wl_item in day_data.stock_watchlist:
                s_sym   = wl_item.get("symbol", "")
                s_high  = float(wl_item.get("day_high", wl_item.get("ltp", 0.0)) or 0.0)
                s_low   = float(wl_item.get("day_low",  wl_item.get("ltp", 0.0)) or 0.0)
                s_close = float(wl_item.get("ltp", 0.0) or 0.0)
                if s_sym:
                    hl_lookup[s_sym] = (s_high, s_low, s_close)

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
                        day_high, day_low, eod_close = hl_lookup.get(sym, (0.0, 0.0, 0.0))
                        _exit_p, _ = _resolve_historical_outcome(
                            entry, sl, target, dirn, day_high, day_low, eod_close)
                        if dirn.upper() in ("BUY", "LONG"):
                            pnl = round((_exit_p - entry) * qty, 2)
                        else:
                            pnl = round((entry - _exit_p) * qty, 2)
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

            # ── EOD close with historical outcomes (MUST precede EOD learning) ──
            # Resolves each position's exit using real OHLC: SL hit, target hit, or EOD close.
            _n_closed = 0
            try:
                _n_closed = self._close_replay_positions_with_outcomes(day_data)
            except Exception as eod_close_exc:
                log.warning("[ReplayOrchestrator] EOD close error: %s", eod_close_exc)
                result.errors.append(f"eod_close: {eod_close_exc}")

            # ── EOD learning — positions are closed, labels are non-zero ──
            try:
                self._do_eod_learning()
            except Exception as eod_exc:
                log.warning("[ReplayOrchestrator] EOD learning error: %s", eod_exc)
                result.errors.append(f"eod_learning: {eod_exc}")

            # ── Integrity validation (read-only, does not affect learning) ──
            try:
                _int_result = self._validator.check_day(
                    day_num=day_data.day_num,
                    trading_date=day_data.date,
                    n_closed=_n_closed,
                    n_fed=len(self._current_day_trades),
                    feature_rows_available=self._last_feature_rows_before,
                    n_labels_updated=self._last_labels_updated,
                    ede_completed=self._last_ede_completed,
                    ede_report=self._last_ede_report,
                )
                if not _int_result.passed:
                    result.errors.extend(_int_result.failures)
            except ReplayIntegrityError:
                raise   # strict mode — propagate to abort the replay
            except Exception as _val_exc:
                log.warning("[ReplayIntegrity] Validation error day %d: %s",
                            day_data.day_num, _val_exc)

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


def _resolve_historical_outcome(
    entry:     float,
    sl:        float,
    target:    float,
    direction: str,
    day_high:  float,
    day_low:   float,
    eod_close: float,
) -> tuple[float, str]:
    """
    Resolve trade outcome from real historical OHLC prices.

    Priority: SL hit > target hit > EOD close.
    When both SL and target fall within the day range (ambiguous candle),
    the stop loss is conservatively assumed to have hit first.
    Returns (exit_price, close_reason).
    """
    is_long  = direction.upper() in ("BUY", "LONG")
    has_ohlc = day_high > 0 and day_low > 0

    if not has_ohlc:
        # No historical data available — caller should exclude from learning
        return entry, "ORPHAN_CLOSE"

    if is_long:
        sl_hit     = day_low  <= sl
        target_hit = day_high >= target
    else:
        sl_hit     = day_high >= sl
        target_hit = day_low  <= target

    if sl_hit:
        # SL takes priority over target on ambiguous candles (conservative)
        return sl, "close_sl"
    if target_hit:
        return target, "close_target"

    # Neither level reached — EOD exit at closing price
    close = eod_close if eod_close > 0 else entry
    return close, "eod_close"


def _count_zero_labels(symbols: set) -> int:
    """Count EDE feature DB rows with forward_return==0.0 for the given symbols."""
    try:
        from edge_discovery.pattern_miner import load_feature_db
        db = load_feature_db()
        return sum(
            1 for r in db
            if r.get("symbol") in symbols and r.get("forward_return", 0.0) == 0.0
        )
    except Exception:
        return 0


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
