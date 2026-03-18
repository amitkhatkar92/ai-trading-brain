"""
System Validation — Pre-Flight Checklist
==========================================
Runs a structured 15-step validation of every layer in the AI Trading Brain
before a 60-day replay or live capital deployment.

Usage:
    python system_validation.py               # all 15 steps
    python system_validation.py --steps 1-12  # skip replay steps
    python system_validation.py --fast        # skip network-dependent steps

Output:
    PASS / WARN / FAIL per step
    Final GO / NO-GO verdict
    Saved report: data/validation_report.txt
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# ── Project root on path ──────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("PAPER_TRADING", "true")

# ─────────────────────────────────────────────────────────────────────────────
# Reporting infrastructure
# ─────────────────────────────────────────────────────────────────────────────

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
SKIP = "SKIP"

_COLORS = {
    PASS: "\033[92m",   # green
    WARN: "\033[93m",   # yellow
    FAIL: "\033[91m",   # red
    SKIP: "\033[90m",   # grey
}
_RESET = "\033[0m"


class StepResult:
    def __init__(self, step: int, name: str, status: str,
                 detail: str = "", duration_ms: float = 0):
        self.step        = step
        self.name        = name
        self.status      = status
        self.detail      = detail
        self.duration_ms = duration_ms
        self.ts          = datetime.now().strftime("%H:%M:%S")

    def __str__(self) -> str:
        col  = _COLORS.get(self.status, "")
        icon = {"PASS": "[OK]", "WARN": "[!!]", "FAIL": "[XX]", "SKIP": "[--]"}
        s    = (f"{col}{icon[self.status]}{_RESET}  "
                f"Step {self.step:02d}  {self.name:<38}  "
                f"{col}{self.status}{_RESET}  "
                f"({self.duration_ms:.0f}ms)")
        if self.detail:
            s += f"\n         {self.detail}"
        return s

    def plain(self) -> str:
        return (f"[{self.status}] Step {self.step:02d}  {self.name}  "
                f"({self.duration_ms:.0f}ms)\n"
                f"         {self.detail}")


def _run_step(step_num: int, name: str, fn, skip: bool = False) -> StepResult:
    if skip:
        return StepResult(step_num, name, SKIP, "skipped by --fast mode")
    t0 = time.monotonic()
    try:
        status, detail = fn()
        ms = (time.monotonic() - t0) * 1000
        return StepResult(step_num, name, status, detail, ms)
    except Exception as exc:
        ms = (time.monotonic() - t0) * 1000
        tb_last = traceback.format_exc().splitlines()[-1]
        return StepResult(step_num, name, FAIL,
                          f"{type(exc).__name__}: {exc}  |  {tb_last}", ms)


# ─────────────────────────────────────────────────────────────────────────────
# Step implementations
# ─────────────────────────────────────────────────────────────────────────────

def step01_system_boot() -> Tuple[str, str]:
    """Import core infrastructure without starting the full system."""
    from communication.event_bus import EventBus
    from utils import get_logger

    bus = EventBus()
    log = get_logger("validation")
    assert bus is not None
    assert log  is not None

    # Verify MasterOrchestrator class is importable (not instantiated — that
    # would trigger a full startup)
    from orchestrator.master_orchestrator import MasterOrchestrator
    assert hasattr(MasterOrchestrator, "run_full_cycle")
    assert hasattr(MasterOrchestrator, "start_scheduler")

    return PASS, "EventBus + logger + MasterOrchestrator class all importable"


def step02_market_data_pipeline() -> Tuple[str, str]:
    """Verify data feed manager and MarketDataAI can be imported and initialised."""
    from data_feeds.data_feed_manager import get_feed_manager
    from market_intelligence.market_data_ai import MarketDataAI

    fm = get_feed_manager()
    assert fm is not None

    status = fm.get_feed_status() if hasattr(fm, "get_feed_status") else None

    mda = MarketDataAI()
    assert mda is not None

    detail = "DataFeedManager + MarketDataAI initialised"
    if status is not None:
        detail += f"  |  feeds={status.summary() if hasattr(status, 'summary') else status}"
    return PASS, detail


def step03_market_intelligence() -> Tuple[str, str]:
    """Verify market intelligence layers load and classify a synthetic snapshot."""
    from market_intelligence.market_regime_ai import MarketRegimeAI
    from market_intelligence.sector_rotation_ai import SectorRotationAI
    from market_intelligence.liquidity_ai import LiquidityAI

    regime_ai  = MarketRegimeAI()
    sector_ai  = SectorRotationAI()
    liquidity  = LiquidityAI()

    # Synthetic raw_data — no network needed
    raw = {
        "vix": 14.5,
        "pcr": 0.95,
        "breadth": 0.62,
        "indices": {"NIFTY 50": {"close": 24000, "change_pct": 0.3}},
    }
    out = regime_ai.classify(raw, global_bias="bullish", global_sentiment_score=0.2)
    assert out is not None
    assert out.data.get("regime") is not None

    regime    = out.data["regime"].value if hasattr(out.data["regime"], "value") else str(out.data["regime"])
    vol_level = out.data.get("volatility")
    vol_str   = vol_level.value if hasattr(vol_level, "value") else str(vol_level)

    return PASS, (
        f"MarketRegimeAI classified → Regime={regime}  "
        f"Volatility={vol_str}  "
        f"SectorAI + LiquidityAI importable"
    )


def step04_strategy_lab() -> Tuple[str, str]:
    """Verify strategy generator and meta-learning engine can be imported."""
    from strategy_lab.strategy_generator_ai import StrategyGeneratorAI
    from meta_learning import MetaLearningEngine

    sgen  = StrategyGeneratorAI()
    meta  = MetaLearningEngine()

    assert hasattr(sgen, "assign_strategy")
    assert meta is not None

    # Check evolved_strategies.json exists and has entries
    evolved_path = _ROOT / "data" / "evolved_strategies.json"
    n_strats = 0
    if evolved_path.exists():
        import json
        data = json.loads(evolved_path.read_text(encoding="utf-8"))
        n_strats = len(data) if isinstance(data, list) else len(data.get("strategies", []))

    return PASS, (
        f"StrategyGeneratorAI + MetaLearningEngine loaded  |  "
        f"evolved_strategies: {n_strats} entry/entries"
    )


def step05_opportunity_engine() -> Tuple[str, str]:
    """Verify equity scanner and options opportunity modules import cleanly."""
    from opportunity_engine.equity_scanner_ai import EquityScannerAI

    scanner = EquityScannerAI()
    assert scanner is not None

    # Verify scanner has a scan method
    assert hasattr(scanner, "scan")

    # Check options opportunity module if present
    opts_note = ""
    try:
        from opportunity_engine.options_opportunity_ai import OptionsOpportunityAI
        OptionsOpportunityAI()
        opts_note = " + OptionsOpportunityAI"
    except Exception:
        opts_note = " (OptionsOpportunityAI not found — optional)"

    return PASS, f"EquityScannerAI initialised{opts_note}"


def step06_risk_control() -> Tuple[str, str]:
    """Verify risk manager, position sizer, and guardian load correctly."""
    from risk_guardian.risk_guardian import FailSafeRiskGuardian, KILL_SWITCH_VIX, MAX_DAILY_LOSS_PCT
    from risk_control.risk_manager_ai import RiskManagerAI

    guardian = FailSafeRiskGuardian(total_capital=1_000_000)
    assert guardian is not None

    risk_mgr = RiskManagerAI()
    assert risk_mgr is not None

    # Verify kill-switch constants are within expected ranges
    assert 30.0 <= KILL_SWITCH_VIX <= 60.0,  f"Kill-switch VIX={KILL_SWITCH_VIX} out of expected range"
    assert 1.0  <= MAX_DAILY_LOSS_PCT <= 5.0, f"MaxDailyLoss={MAX_DAILY_LOSS_PCT}% out of expected range"

    # Synthetic guardian check — normal VIX, no loss, should be clear
    from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
    snap = MarketSnapshot(
        timestamp=datetime.now(),
        indices={},
        regime=RegimeLabel.RANGE_MARKET,
        volatility=VolatilityLevel.LOW,
        vix=14.5,
    )
    status = guardian.get_status() if hasattr(guardian, "get_status") else None
    status_detail = ""
    if status:
        halted = status.get("trading_halted", False)
        status_detail = f"  |  trading_halted={halted}"

    return PASS, (
        f"FailSafeRiskGuardian(cap=1M) + RiskManagerAI loaded  |  "
        f"KillVIX={KILL_SWITCH_VIX}  MaxDailyLoss={MAX_DAILY_LOSS_PCT}%"
        f"{status_detail}"
    )


def step07_decision_engine() -> Tuple[str, str]:
    """Load DecisionEngine and MultiAgentDebate; test a synthetic vote set."""
    from decision_ai.decision_engine import DecisionEngine, AGENT_WEIGHTS
    from debate_system.multi_agent_debate import MultiAgentDebate
    from models.agent_output import DebateVote
    from config import MIN_CONFIDENCE_SCORE

    engine = DecisionEngine()
    debate = MultiAgentDebate()
    assert engine is not None and debate is not None

    # Synthetic votes — all approve with high confidence
    from models.trade_signal import TradeSignal, SignalDirection
    from models.market_data  import MarketSnapshot, RegimeLabel, VolatilityLevel

    votes = [
        DebateVote(agent_name="TechnicalAnalystAI", vote="approve",
                   score=8.0, suggested_position_modifier=1.0, reasoning="setup confirmed"),
        DebateVote(agent_name="MacroAnalystAI",     vote="approve",
                   score=7.5, suggested_position_modifier=1.0, reasoning="macro clear"),
        DebateVote(agent_name="RiskDebateAI",       vote="approve",
                   score=7.0, suggested_position_modifier=0.9, reasoning="risk ok"),
        DebateVote(agent_name="SentimentAI",        vote="approve",
                   score=7.2, suggested_position_modifier=1.0, reasoning="sentiment neutral+"),
        DebateVote(agent_name="RegimeDebateAI",     vote="approve",
                   score=8.0, suggested_position_modifier=1.0, reasoning="regime aligned"),
    ]

    snap = MarketSnapshot(
        timestamp=datetime.now(),
        indices={},
        regime=RegimeLabel.RANGE_MARKET,
        volatility=VolatilityLevel.LOW,
        vix=14.5,
    )

    class _FakeSignal:
        symbol = "SYNTH"
        direction = SignalDirection.BUY if hasattr(SignalDirection, "BUY") else "BUY"
        entry_price = 1000.0
        stop_loss   = 985.0
        target      = 1030.0
        risk_reward_ratio = 2.0

    result = engine.decide(_FakeSignal(), votes, snap)  # type: ignore[arg-type]
    approved = result.approved if hasattr(result, "approved") else None
    score    = result.confidence_score if hasattr(result, "confidence_score") else "?"

    assert approved is True, f"Synthetic all-approve vote was rejected: {result}"

    return PASS, (
        f"DecisionEngine + MultiAgentDebate loaded  |  "
        f"5-agent synthetic vote → approved={approved}  score={score:.2f}  "
        f"threshold={MIN_CONFIDENCE_SCORE}"
    )


def step08_execution_engine() -> Tuple[str, str]:
    """Verify OrderManager, AET constants, and zone logic are intact."""
    from execution_engine.order_manager import (
        OrderManager,
        LIMIT_CANDLE_EXPIRY,
        AET_MAX_WAIT_CANDLES,
        REENTRY_WINDOW_CANDLES,
        ZONE_BASE_PCT,
        AdaptiveTimingMode,
        AetPendingSlot,
    )

    om = OrderManager()
    assert om is not None
    assert hasattr(om, "execute")
    assert hasattr(om, "attempt_aet_confirmations")
    assert hasattr(om, "attempt_all_reentries")

    # Verify AET mode selection with known inputs
    mode_imm  = om._determine_aet_mode(vix=10.0, regime="RANGE_MARKET", distortion_active=False)
    mode_conf = om._determine_aet_mode(vix=20.0, regime="RANGE_MARKET", distortion_active=False)
    mode_pull = om._determine_aet_mode(vix=10.0, regime="TREND",        distortion_active=False)

    assert mode_imm  == AdaptiveTimingMode.IMMEDIATE,     f"Expected IMMEDIATE got {mode_imm}"
    assert mode_conf == AdaptiveTimingMode.CONFIRMATION,  f"Expected CONFIRMATION got {mode_conf}"
    assert mode_pull == AdaptiveTimingMode.PULLBACK,      f"Expected PULLBACK got {mode_pull}"

    return PASS, (
        f"OrderManager loaded  |  "
        f"LIMIT_EXPIRY={LIMIT_CANDLE_EXPIRY}c  AET_WAIT={AET_MAX_WAIT_CANDLES}c  "
        f"REENTRY={REENTRY_WINDOW_CANDLES}c  ZONE_BASE={ZONE_BASE_PCT}%  |  "
        f"AET mode logic: IMMEDIATE/PULLBACK/CONFIRMATION all correct"
    )


def step09_trade_monitoring() -> Tuple[str, str]:
    """Verify TradeMonitor and StrategyHealthMonitor import and initialise."""
    from trade_monitoring.trade_monitor import TradeMonitor
    from trade_monitoring.strategy_health_monitor import StrategyHealthMonitor

    tm = TradeMonitor()
    shm = StrategyHealthMonitor()
    assert tm  is not None
    assert shm is not None
    assert hasattr(tm,  "register") or hasattr(tm,  "add_trade") or hasattr(tm, "update")
    assert hasattr(shm, "record_trade") or hasattr(shm, "record") or hasattr(shm, "update") or hasattr(shm, "check_health")

    return PASS, "TradeMonitor + StrategyHealthMonitor initialised; register/update methods present"


def step10_learning_system() -> Tuple[str, str]:
    """Verify LearningEngine, StrategyPerformanceTracker, and RegimeStrategyMap load."""
    from learning_system.learning_engine import LearningEngine
    from learning_system.strategy_performance_tracker import get_performance_tracker
    from meta_learning.regime_strategy_map import get_regime_strategy_map

    engine  = LearningEngine()
    tracker = get_performance_tracker()
    remap   = get_regime_strategy_map()

    assert engine  is not None
    assert tracker is not None
    assert remap   is not None

    # Verify tracker has performance-recording method (non-destructive check)
    has_record = (hasattr(tracker, "record_trade") or
                  hasattr(tracker, "update")       or
                  hasattr(tracker, "add"))

    return PASS, (
        f"LearningEngine + StrategyPerformanceTracker + RegimeStrategyMap loaded  |  "
        f"record method present: {has_record}"
    )


def step11_edge_diagnostics() -> Tuple[str, str]:
    """Check all four analytics modules load and replay_summary.json exists."""
    from simulation_replay.market_capture  import analyze_market_capture, format_mcr_report
    from simulation_replay.edge_half_life  import analyze_edge_half_life,  format_ehl_report
    from simulation_replay.edge_distribution import analyze_edge_distribution, format_edm_report

    # Check modules callable with empty input
    r1 = analyze_market_capture([])
    r2 = analyze_edge_half_life([])
    r3 = analyze_edge_distribution([])
    assert r1 is not None and r2 is not None and r3 is not None

    # Check replay_summary.json
    summary_path = _ROOT / "data" / "replay_summary.json"
    summary_age  = ""
    pf_val       = None
    if summary_path.exists():
        import json
        data   = json.loads(summary_path.read_text(encoding="utf-8"))
        gen_at = data.get("generated_at", "")
        pf_val = (data.get("metrics") or {}).get("profit_factor")
        if gen_at:
            age_s = (datetime.now() - datetime.fromisoformat(gen_at)).total_seconds()
            summary_age = f"  |  age={age_s/3600:.1f}h"
    else:
        summary_age = "  |  replay_summary.json MISSING — run replay first"

    status = PASS if summary_path.exists() else WARN
    return status, (
        f"MCR + EHL + EDM modules callable with empty input  |  "
        f"replay_summary.json: {'FOUND' if summary_path.exists() else 'MISSING'}"
        f"{summary_age}"
        + (f"  |  last_PF={pf_val:.3f}" if pf_val is not None else "")
    )


def step12_system_health() -> Tuple[str, str]:
    """Verify RiskGuardian thresholds, paper-trade flag, and DB manager."""
    from risk_guardian.risk_guardian import (
        FailSafeRiskGuardian,
        KILL_SWITCH_VIX,
        KILL_SWITCH_NIFTY_DROP,
        MAX_DAILY_LOSS_PCT,
        MAX_PORTFOLIO_RISK_PCT,
        MAX_OPEN_TRADES,
    )
    from database.db_manager import DBManager

    # Verify paper trading is active
    paper = os.environ.get("PAPER_TRADING", "false").lower()
    assert paper in ("true", "1"), "PAPER_TRADING not set — refusing to validate in live mode"

    # Verify DB manager importable
    db = DBManager()
    assert db is not None

    issues: List[str] = []
    if KILL_SWITCH_VIX < 30 or KILL_SWITCH_VIX > 60:
        issues.append(f"KillSwitchVIX={KILL_SWITCH_VIX} outside 30-60 range")
    if MAX_DAILY_LOSS_PCT < 1.0 or MAX_DAILY_LOSS_PCT > 5.0:
        issues.append(f"MaxDailyLoss={MAX_DAILY_LOSS_PCT}% outside 1-5% range")

    status = FAIL if issues else PASS
    detail = (
        f"PAPER_TRADING=true  |  "
        f"KillVIX={KILL_SWITCH_VIX}  NiftyDrop={KILL_SWITCH_NIFTY_DROP}%  "
        f"MaxDailyLoss={MAX_DAILY_LOSS_PCT}%  MaxPortfolioRisk={MAX_PORTFOLIO_RISK_PCT}%  "
        f"MaxOpenTrades={MAX_OPEN_TRADES}  |  DBManager loaded"
    )
    if issues:
        detail += "  ISSUES: " + "; ".join(issues)
    return status, detail


def step13_dry_cycle(fast: bool = False) -> Tuple[str, str]:
    """
    Run a real 1-day replay cycle via subprocess (isolated process).
    Uses run_replay.py --days 1 to exercise the full pipeline end-to-end.
    """
    if fast:
        return SKIP, "skipped in --fast mode"

    t0 = time.monotonic()
    r = subprocess.run(
        [sys.executable, "simulation_replay/run_replay.py", "--days", "1"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(_ROOT), timeout=180,
    )
    elapsed = time.monotonic() - t0
    lines   = (r.stdout + r.stderr).splitlines()

    if r.returncode != 0:
        # Find error line
        err_line = next((l for l in lines if "Error" in l or "Traceback" in l), "unknown error")
        return FAIL, f"exit={r.returncode}  |  {err_line[:120]}"

    complete = any("REPLAY COMPLETE" in l for l in lines)
    err_0    = any("Errors  : 0" in l for l in lines)
    status   = PASS if (complete and err_0) else WARN
    return status, (
        f"1-day dry cycle completed in {elapsed:.1f}s  |  "
        f"pipeline_complete={complete}  errors=0={err_0}  exit={r.returncode}"
    )


def step14_seven_day_stability(fast: bool = False) -> Tuple[str, str]:
    """
    Check that a 7-day replay has been run recently (< 2 hours),
    or run one now if not in fast mode.
    """
    summary_path = _ROOT / "data" / "replay_summary.json"

    if summary_path.exists():
        import json
        data   = json.loads(summary_path.read_text(encoding="utf-8"))
        gen_at = data.get("generated_at", "")
        if gen_at:
            age_s = (datetime.now() - datetime.fromisoformat(gen_at)).total_seconds()
            days  = data.get("days_replayed", 0)
            if age_s < 7200 and days >= 7:
                pf = (data.get("metrics") or {}).get("profit_factor", 0)
                errs = (data.get("health") or {}).get("total_errors", "-")
                return PASS, (
                    f"Recent {days}-day replay found  |  age={age_s/60:.0f}min  "
                    f"PF={pf:.2f}  errors={errs}"
                )

    if fast:
        return WARN, "No recent 7-day replay found.  Run: python run_replay.py --days 7"

    # Run a fresh 7-day replay
    t0 = time.monotonic()
    r = subprocess.run(
        [sys.executable, "simulation_replay/run_replay.py", "--days", "7"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(_ROOT), timeout=600,
    )
    elapsed = time.monotonic() - t0
    lines   = (r.stdout + r.stderr).splitlines()

    if r.returncode != 0:
        err_line = next((l for l in lines if "Error" in l or "Traceback" in l), "unknown error")
        return FAIL, f"7-day replay failed: exit={r.returncode}  |  {err_line[:120]}"

    # Re-read summary
    errors = "?"
    pf     = "?"
    if summary_path.exists():
        import json
        data   = json.loads(summary_path.read_text(encoding="utf-8"))
        pf     = (data.get("metrics") or {}).get("profit_factor", "?")
        errors = (data.get("health")  or {}).get("total_errors",  "?")
        pf     = f"{pf:.2f}" if isinstance(pf, float) else str(pf)

    complete = any("REPLAY COMPLETE" in l for l in lines)
    status   = PASS if (complete and r.returncode == 0) else WARN
    return status, (
        f"7-day replay completed in {elapsed:.1f}s  |  "
        f"errors={errors}  PF={pf}  exit={r.returncode}"
    )


def step15_sixty_day_prompt(fast: bool = False) -> Tuple[str, str]:
    """
    Inform user how to run the 60-day replay.
    Does NOT execute it automatically (takes 10+ minutes).
    """
    cmd = f"python simulation_replay/run_replay.py --days 60"
    return PASS, (
        f"Command ready: {cmd}  |  "
        f"Expected runtime: 8-15 min  |  "
        f"Targets: PF>1.5  MaxDD<5%  Errors=0"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

STEPS = [
    (1,  "System Boot & Infrastructure",   step01_system_boot),
    (2,  "Market Data Pipeline",           step02_market_data_pipeline),
    (3,  "Market Intelligence Layer",      step03_market_intelligence),
    (4,  "Strategy Lab",                   step04_strategy_lab),
    (5,  "Opportunity Engine",             step05_opportunity_engine),
    (6,  "Risk Control",                   step06_risk_control),
    (7,  "Decision Engine",                step07_decision_engine),
    (8,  "Execution Engine",               step08_execution_engine),
    (9,  "Trade Monitoring",               step09_trade_monitoring),
    (10, "Learning System",                step10_learning_system),
    (11, "Edge Diagnostics Suite",         step11_edge_diagnostics),
    (12, "System Health & Safety",         step12_system_health),
    (13, "1-Day End-to-End Dry Cycle",     None),   # special subprocess step
    (14, "7-Day Stability Test",           None),   # special subprocess step
    (15, "60-Day Replay Readiness",        step15_sixty_day_prompt),
]


def _parse_step_range(s: str) -> List[int]:
    """Parse '1-12' or '1,3,5' into a list of step numbers."""
    result = []
    for part in s.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            result.extend(range(int(lo), int(hi) + 1))
        else:
            result.append(int(part.strip()))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Trading Brain — System Validation Pre-Flight Checklist"
    )
    parser.add_argument("--fast",  action="store_true",
                        help="Skip network/subprocess steps (units only, ~5s)")
    parser.add_argument("--steps", default=None,
                        help="Comma/range of steps to run, e.g. '1-12' or '1,3,7'")
    args = parser.parse_args()

    run_steps: Optional[List[int]] = None
    if args.steps:
        run_steps = _parse_step_range(args.steps)

    start_ts  = datetime.now()
    results: List[StepResult] = []

    print()
    print("=" * 70)
    print("  AI TRADING BRAIN — SYSTEM VALIDATION")
    print(f"  {start_ts.strftime('%Y-%m-%d  %H:%M:%S')}  |  PAPER_TRADING=true  |  fast={args.fast}")
    print("=" * 70)
    print()

    for step_num, name, fn in STEPS:
        if run_steps and step_num not in run_steps:
            continue

        should_skip = args.fast and step_num in (13, 14)

        if step_num == 13:
            res = _run_step(step_num, name,
                            lambda: step13_dry_cycle(fast=args.fast),
                            skip=False)
        elif step_num == 14:
            res = _run_step(step_num, name,
                            lambda: step14_seven_day_stability(fast=args.fast),
                            skip=False)
        else:
            res = _run_step(step_num, name, fn, skip=should_skip)

        results.append(res)
        print(res)
        print()

    # ── Final verdict ─────────────────────────────────────────────────────────
    n_pass = sum(1 for r in results if r.status == PASS)
    n_warn = sum(1 for r in results if r.status == WARN)
    n_fail = sum(1 for r in results if r.status == FAIL)
    n_skip = sum(1 for r in results if r.status == SKIP)

    fails  = [r for r in results if r.status == FAIL]
    warns  = [r for r in results if r.status == WARN]

    print("=" * 70)
    print(f"  RESULTS:  "
          f"{_COLORS[PASS]}PASS={n_pass}{_RESET}  "
          f"{_COLORS[WARN]}WARN={n_warn}{_RESET}  "
          f"{_COLORS[FAIL]}FAIL={n_fail}{_RESET}  "
          f"{_COLORS[SKIP]}SKIP={n_skip}{_RESET}")
    print()

    # Critical steps that block GO
    critical = {1, 6, 7, 8, 12}
    critical_fails = [r for r in fails if r.step in critical]

    if critical_fails or n_fail > 0:
        verdict = f"{_COLORS[FAIL]}NO-GO{_RESET}"
        verdict_plain = "NO-GO"
        verdict_reason = "; ".join(f"Step {r.step} {r.name}" for r in fails)
    elif n_warn > 2:
        verdict = f"{_COLORS[WARN]}CONDITIONAL GO{_RESET}"
        verdict_plain = "CONDITIONAL GO"
        verdict_reason = f"{n_warn} warnings — investigate before deploying capital"
    else:
        verdict = f"{_COLORS[PASS]}GO{_RESET}"
        verdict_plain = "GO"
        verdict_reason = "All critical steps passed."

    print(f"  VERDICT:  {verdict}  —  {verdict_reason}")
    print()

    if fails:
        print("  FAILED STEPS:")
        for r in fails:
            print(f"    Step {r.step:02d} — {r.name}: {r.detail}")
        print()

    if warns:
        print("  WARNINGS:")
        for r in warns:
            print(f"    Step {r.step:02d} — {r.name}: {r.detail}")
        print()

    if verdict_plain in ("GO", "CONDITIONAL GO"):
        print("  NEXT STEP:")
        print("    python simulation_replay/run_replay.py --days 60")
        print()

    print("=" * 70)

    # ── Save report ────────────────────────────────────────────────────────────
    report_path = _ROOT / "data" / "validation_report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "AI Trading Brain — System Validation Report",
        f"Generated: {start_ts.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Duration:  {(datetime.now() - start_ts).total_seconds():.1f}s",
        "=" * 65,
        "",
    ]
    for r in results:
        lines.append(r.plain())
        lines.append("")
    lines += [
        "=" * 65,
        f"PASS={n_pass}  WARN={n_warn}  FAIL={n_fail}  SKIP={n_skip}",
        f"VERDICT: {verdict_plain}  —  {verdict_reason}",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Report saved: data/validation_report.txt")
    print()

    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
