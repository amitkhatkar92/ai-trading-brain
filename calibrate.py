# -*- coding: utf-8 -*-
"""
AI Trading Brain - System Calibration Runner
=============================================
Integration test that traces signals through every layer and prints a
detailed funnel report.  Does NOT affect production — runs everything
in dry-run mode with a forced BULL_TREND snapshot so trade execution
can be verified end-to-end.

Usage:
    python calibrate.py
"""

from __future__ import annotations
import sys, os, time
from datetime import datetime
from typing import List

# Force UTF-8 output so Unicode box chars work on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── project root on path ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from models import MarketSnapshot, TradeSignal
from models.market_data import RegimeLabel, VolatilityLevel
from models.portfolio   import Portfolio
from utils import get_logger

log = get_logger("calibrate")

# ─────────────────────────────────────────────────────────────────────────────
# FORCED BULL-TREND SNAPSHOT
# Forces every regime-conditional check into its best-case branch so we can
# verify the happy path all the way to execution.
# ─────────────────────────────────────────────────────────────────────────────

def _bull_snapshot() -> MarketSnapshot:
    from models.market_data import IndexData
    base_prices = {
        "NIFTY 50": 22500, "NIFTY BANK": 48500, "NIFTY 500": 20200,
        "NIFTY MIDCAP 150": 15200, "NIFTY SMALLCAP 250": 8700,
        "NIFTY IT": 35500, "NIFTY PSU BANK": 6600,
        "NIFTY PHARMA": 19200, "NIFTY AUTO": 23500, "NIFTY FMCG": 21300,
    }
    indices = {}
    for sym, base in base_prices.items():
        indices[sym] = IndexData(
            symbol=sym, ltp=base, open=base*0.99, high=base*1.01,
            low=base*0.99, close=base, volume=2_000_000, change_pct=1.2,
        )
    return MarketSnapshot(
        timestamp       = datetime.now(),
        indices         = indices,
        regime          = RegimeLabel.BULL_TREND,
        volatility      = VolatilityLevel.MEDIUM,
        vix             = 14.5,
        sector_flows    = [],
        sector_leaders  = ["RELIANCE", "ICICIBANK", "HDFCBANK"],
        events_today    = [],
        market_breadth  = 0.72,
        pcr             = 0.85,
        global_bias     = "bullish",
        global_sentiment_score = 0.45,
    )


# ─────────────────────────────────────────────────────────────────────────────
# LAYER RUNNERS WITH COUNT TRACKING
# ─────────────────────────────────────────────────────────────────────────────

class SignalFunnel:
    """Tracks signal counts and rejection reasons at each layer."""

    def __init__(self):
        self.stages: list[dict] = []

    def record(self, name: str, before: int, after: int, detail: str = ""):
        dropped = before - after
        self.stages.append({
            "layer":   name,
            "in":      before,
            "out":     after,
            "dropped": dropped,
            "detail":  detail,
        })

    def print_report(self):
        W = 92
        print("\n" + "═" * W)
        print(f"{'CALIBRATION SIGNAL FUNNEL':^{W}}")
        print("═" * W)
        print(f"  {'Layer':<34}  {'In':>4}  {'Out':>4}  {'Dropped':>7}  Status")
        print("  " + "─" * (W - 4))
        for s in self.stages:
            status = "✅" if s["dropped"] == 0 else (
                "⚠️ " if s["out"] > 0 else "❌")
            print(
                f"  {s['layer']:<34}  {s['in']:>4}  {s['out']:>4}  "
                f"{s['dropped']:>7}  {status}  {s['detail']}"
            )
        print("  " + "─" * (W - 4))
        final_out = self.stages[-1]["out"] if self.stages else 0
        final_in  = self.stages[0]["in"]   if self.stages else 0
        pct       = 100.0 * final_out / final_in if final_in else 0
        print(f"  {'TOTAL PIPELINE':<34}  {final_in:>4}  {final_out:>4}  "
              f"{final_in - final_out:>7}  {pct:.0f}% pass rate")
        print("═" * W)


def run_calibration():
    start = time.time()
    funnel = SignalFunnel()

    print("\n" + "═" * 92)
    print(f"{'AI TRADING BRAIN — CALIBRATION MODE':^92}")
    print(f"{'Forced snapshot: BULL_TREND | VIX=14.5 | Breadth=72%':^92}")
    print("═" * 92 + "\n")

    snapshot = _bull_snapshot()
    print(f"[Snapshot] Regime={snapshot.regime.value}  "
          f"VIX={snapshot.vix}  Breadth={snapshot.market_breadth:.0%}  "
          f"PCR={snapshot.pcr}\n")

    # ── Layer 1: Opportunity Engine ──────────────────────────────────────
    print("─" * 55 + "  Layer 3: Opportunity Engine")
    from opportunity_engine.equity_scanner_ai    import EquityScannerAI
    from opportunity_engine.options_opportunity_ai import OptionsOpportunityAI
    from opportunity_engine.arbitrage_ai          import ArbitrageAI

    eq_signals   = EquityScannerAI().scan(snapshot)
    opt_signals  = OptionsOpportunityAI().scan(snapshot)
    arb_signals  = ArbitrageAI().scan(snapshot)
    all_signals  = eq_signals + opt_signals + arb_signals
    print(f"  Equity={len(eq_signals)}  Options={len(opt_signals)}  "
          f"Arb={len(arb_signals)}  Total={len(all_signals)}")
    for s in all_signals:
        print(f"    {s.symbol:<12} {s.direction.value:<5} entry={s.entry_price:.2f}  "
              f"sl={s.stop_loss:.2f}  conf={s.confidence:.1f}  rr={s.risk_reward_ratio:.1f}")
    funnel.record("OpportunityEngine", 0, len(all_signals),
                  f"eq={len(eq_signals)} opt={len(opt_signals)} arb={len(arb_signals)}")
    # Patch so funnel.in is correct
    funnel.stages[-1]["in"] = len(all_signals)

    if not all_signals:
        print("\n❌ CALIBRATION FAIL: Opportunity Engine produced 0 signals.")
        return

    # ── Layer 2: Strategy Lab ────────────────────────────────────────────
    print("\n" + "─" * 55 + "  Layer 4: Strategy Lab")
    from strategy_lab.strategy_generator_ai  import StrategyGeneratorAI
    from strategy_lab.strategy_evolution_ai  import StrategyEvolutionAI
    from strategy_lab.backtesting_ai         import BacktestingAI
    from strategy_lab.meta_strategy_controller import MetaStrategyController

    meta   = MetaStrategyController()
    sg     = StrategyGeneratorAI(meta_controller=meta)
    se     = StrategyEvolutionAI()
    bt     = BacktestingAI()

    assigned  = sg.assign_strategy(all_signals, snapshot)
    evolved   = se.apply_evolved_params(assigned)
    bt_tested = bt.filter_by_backtest(evolved)
    funnel.record("StrategyLab", len(all_signals), len(bt_tested),
                  f"assigned={len(assigned)} post-bt={len(bt_tested)}")
    print(f"  Assigned={len(assigned)}  Post-backtest={len(bt_tested)}")
    for s in bt_tested:
        print(f"    {s.symbol:<12} strategy={s.strategy_name}  rr={s.risk_reward_ratio:.1f}")

    if not bt_tested:
        print("\n❌ CALIBRATION FAIL: Strategy Lab dropped all signals.")
        return

    # ── Layer 3: Capital Risk Engine ─────────────────────────────────────
    print("\n" + "─" * 55 + "  Layer 4.5: Capital Risk Engine")
    from risk_control.capital_risk_engine import CapitalRiskEngine
    from models.portfolio import Portfolio

    cre      = CapitalRiskEngine()
    portfolio = Portfolio(capital=1_000_000, peak_capital=1_000_000)
    cre_sigs  = cre.allocate(bt_tested, snapshot, portfolio)
    funnel.record("CapitalRiskEngine", len(bt_tested), len(cre_sigs),
                  f"deployed after CRE={len(cre_sigs)}")
    print(f"  After CRE: {len(cre_sigs)} signals with position sizes")
    for s in cre_sigs:
        print(f"    {s.symbol:<12} qty={s.quantity}  strategy={s.strategy_name}")

    if not cre_sigs:
        print("\n❌ CALIBRATION FAIL: CRE allocated 0 positions.")
        return

    # ── Layer 4: Risk Control ────────────────────────────────────────────
    print("\n" + "─" * 55 + "  Layer 5: Risk Control")
    from risk_control.risk_manager_ai     import RiskManagerAI
    from risk_control.portfolio_allocation_ai import PortfolioAllocationAI
    from risk_control.stress_test_ai      import StressTestAI

    rm   = RiskManagerAI()
    pa   = PortfolioAllocationAI()
    st   = StressTestAI()

    rm_passed = rm.filter(cre_sigs)
    pa_sized  = pa.size_positions(rm_passed, snapshot)
    st_passed = st.validate(pa_sized, snapshot)
    funnel.record("RiskControl", len(cre_sigs), len(st_passed),
                  f"rm={len(rm_passed)} pa={len(pa_sized)} stress={len(st_passed)}")
    print(f"  RiskManager={len(rm_passed)}  PortfolioAllocator={len(pa_sized)}  "
          f"StressTest={len(st_passed)}")

    if not st_passed:
        print("\n❌ CALIBRATION FAIL: Risk Control blocked all signals.")
        # Print why each was rejected
        for s in cre_sigs:
            print(f"    {s.symbol}: conf={s.confidence:.1f} rr={s.risk_reward_ratio:.1f} "
                  f"sl={s.stop_loss:.2f} entry={s.entry_price:.2f}")
        return

    # ── Layer 5: Market Simulation ───────────────────────────────────────
    print("\n" + "─" * 55 + "  Layer 5.5: Market Simulation Engine")
    from market_simulation.simulation_engine import SimulationEngine
    sim    = SimulationEngine(mc_runs=200)   # fewer runs for speed in calibration
    result = sim.run(st_passed, snapshot)
    funnel.record("MarketSimulation", len(st_passed), len(result.approved_trades),
                  f"survival={result.approval_rate:.0%}  "
                  f"approved={len(result.approved_trades)}")
    print(f"  Approved={len(result.approved_trades)}  "
          f"Rejected={len(result.rejected_trades)}  "
          f"PassRate={result.approval_rate:.0%}")
    for score in result.scores:
        status = "✅" if score.approved else "❌"
        print(f"    {status} {score.signal.symbol:<12} "
              f"survival={score.survival_rate:.1%}  "
              f"stability={score.stability_score:.2f}  "
              f"mc_prob={score.monte_carlo_profit_prob:.1%}  "
              f"reject='{score.rejection_reason}'")

    if not result.approved_trades:
        print("\n❌ CALIBRATION FAIL: Simulation Engine blocked all signals. "
              "Check survival_rate, stability_score, mc_prob thresholds.")
        return

    # ── Layer 6: Fail-Safe Risk Guardian ────────────────────────────────
    print("\n" + "─" * 55 + "  Layer 6: Fail-Safe Risk Guardian")
    from risk_guardian import FailSafeRiskGuardian
    guardian  = FailSafeRiskGuardian(total_capital=1_000_000)
    gd        = guardian.evaluate(result.approved_trades, snapshot, portfolio)
    approved_cnt = len(gd.approved_signals)
    funnel.record("RiskGuardian", len(result.approved_trades), approved_cnt,
                  gd.reason if not gd.approved else "all signals cleared")
    print(f"  {'APPROVED' if gd.approved else 'BLOCKED'}: {gd.summary()}")

    if not gd.approved:
        print(f"\n❌ CALIBRATION FAIL: RiskGuardian blocked — {gd.reason}")
        return

    # ── Layer 7: Debate + Decision ────────────────────────────────────────
    print("\n" + "─" * 55 + "  Layer 7–8: Debate + Decision Engine")
    from debate_system.multi_agent_debate import MultiAgentDebate
    from decision_ai.decision_engine      import DecisionEngine

    debate   = MultiAgentDebate()
    decision = DecisionEngine()

    approved_sigs = []
    rejected_sigs = []
    for sig in gd.approved_signals:
        votes  = debate.run(sig, snapshot)
        result_d = decision.decide(sig, votes, snapshot)
        if result_d.approved:
            approved_sigs.append((sig, result_d))
        else:
            rejected_sigs.append((sig, result_d))
            print(f"    ❌ {sig.symbol}: {result_d.reasoning}")

    funnel.record("Debate+Decision", len(gd.approved_signals), len(approved_sigs),
                  f"rejected={len(rejected_sigs)}")
    print(f"  Approved={len(approved_sigs)}  Rejected={len(rejected_sigs)}")
    for sig, dec in approved_sigs:
        print(f"    ✅ {sig.symbol:<12} score={dec.confidence_score:.2f}  "
              f"modifier={dec.position_size_modifier:.0%}")

    if not approved_sigs:
        print("\n❌ CALIBRATION FAIL: All signals rejected at Debate+Decision stage.")
        return

    # ── Layer 8: Order Manager (dry-run) ─────────────────────────────────
    print("\n" + "─" * 55 + "  Layer 8: Order Manager (Simulation Execute)")
    from execution_engine.order_manager import OrderManager
    om = OrderManager()

    executed = []
    for sig, dec in approved_sigs:
        order = om.execute(sig, dec)
        if order:
            executed.append(order)
            print(f"    ✅ {sig.symbol:<12} order_id={order.order_id}  "
                  f"qty={order.quantity}  entry={order.entry_price:.2f}  "
                  f"sl={order.stop_loss:.2f}  tgt={order.target:.2f}")
        else:
            print(f"    ❌ {sig.symbol}: OrderManager returned None")

    funnel.record("OrderManager", len(approved_sigs), len(executed),
                  f"broker={om._broker.__class__.__name__}")

    # ── Final Funnel Report ───────────────────────────────────────────────
    elapsed = time.time() - start
    funnel.print_report()

    print()
    if executed:
        print(f"  ✅ CALIBRATION PASSED — {len(executed)} trade(s) executed successfully "
              f"in {elapsed:.2f}s")
    else:
        print(f"  ❌ CALIBRATION FAILED — 0 trades executed after full pipeline "
              f"in {elapsed:.2f}s")
    print()


if __name__ == "__main__":
    run_calibration()
