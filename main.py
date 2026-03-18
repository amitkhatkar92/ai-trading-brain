"""
AI Trading Brain — Main Entry Point
======================================
Usage:
  python main.py                 # Run one immediate analysis cycle
  python main.py --schedule      # Run on intraday schedule (daemon mode)
  python main.py --backtest      # Re-run all strategy backtests
  python main.py --evolve        # Trigger strategy evolution pass
  python main.py --report        # Print learning engine report
  python main.py --dashboard     # Launch Control Tower Streamlit dashboard
  python main.py --discover      # Run Edge Discovery Engine manually
  python main.py --readiness     # Run system readiness checklist
  python main.py --paper         # Run in paper trading mode (no live orders)
  python main.py --pilot         # Run with pilot capital rules (₹20k, max 2 trades)
  python main.py --telegram      # Start Telegram command bot (@Amitkhatkarbot)
"""

import argparse
import sys
import os
import threading
from datetime import datetime as _dt

# Ensure console output handles Unicode/emoji characters (box-drawing, ₹, ✅, etc.)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path so all imports resolve correctly
sys.path.insert(0, os.path.dirname(__file__))

from orchestrator import MasterOrchestrator
from utils import get_logger

log = get_logger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Trading Brain — Hierarchical Multi-Agent System"
    )
    parser.add_argument("--schedule",  action="store_true",
                        help="Run on intraday schedule (daemon)")
    parser.add_argument("--backtest",  action="store_true",
                        help="Re-run all strategy backtests")
    parser.add_argument("--evolve",    action="store_true",
                        help="Run genetic algorithm evolution pass")
    parser.add_argument("--report",    action="store_true",
                        help="Print learning report and exit")
    parser.add_argument("--dashboard", action="store_true",
                        help="Launch Control Tower Streamlit dashboard")
    parser.add_argument("--discover",  action="store_true",
                        help="Run Edge Discovery Engine manually and print report")
    parser.add_argument("--readiness", action="store_true",
                        help="Run system readiness pre-flight checklist")
    parser.add_argument("--paper",     action="store_true",
                        help="Force paper trading mode (no live orders sent)")
    parser.add_argument("--pilot",     action="store_true",
                        help="Run with pilot capital rules (₹20k, max 2 trades)")
    parser.add_argument("--telegram",  action="store_true",
                        help="Start Telegram command bot (@Amitkhatkarbot) and block")
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Override env with CLI flags ─────────────────────────────────────
    if args.paper:
        import config as _cfg
        _cfg.PAPER_TRADING = True
        os.environ["PAPER_TRADING"] = "true"

    log.info("=" * 65)
    log.info("  AI TRADING BRAIN  |  HIERARCHICAL MULTI-AGENT SYSTEM")
    log.info("  Layers: 17  |  Agents: ~62  |  Date: %s",
             _dt.now().strftime("%Y-%m-%d"))
    log.info("=" * 65)

    # ── Mode: System readiness check ─────────────────────────────────────
    if args.readiness:
        import runpy
        readiness_path = os.path.join(os.path.dirname(__file__),
                                      "system_readiness_test.py")
        runpy.run_path(readiness_path, run_name="__main__")
        return

    # ── Mode: Telegram command bot ────────────────────────────────────────
    if args.telegram:
        from notifications.telegram_bot import run_bot
        run_bot()
        return

    # ── Mode: Control Tower dashboard (no brain needed) ──────────────────
    if args.dashboard:
        log.info("Launching Control Tower dashboard…")
        dashboard_script = os.path.join(
            os.path.dirname(__file__), "control_tower", "dashboard_app.py")
        os.execv(
            sys.executable,
            [sys.executable, "-m", "streamlit", "run", dashboard_script],
        )
        return   # unreachable but keeps linters happy
    brain = MasterOrchestrator()

    # ── Mode: Edge Discovery (manual run) ─────────────────────────
    if args.discover:
        log.info("Running Edge Discovery Engine…")
        from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
        dummy = MarketSnapshot(
            timestamp=_dt.now(), indices={},
            regime=RegimeLabel.RANGE_MARKET,
            volatility=VolatilityLevel.MEDIUM,
            vix=15.0,
        )
        report = brain.edge_discovery.run_discovery_cycle(dummy, publish_event=False)
        print(report)
        print(brain.edge_discovery.get_ranking_report())
        return

    # ── Mode: Learning report ──────────────────────────────────────
    if args.report:
        brain.learning_engine._print_report()
        return

    # ── Mode: Strategy backtests ───────────────────────────────────
    if args.backtest:
        from strategy_lab.strategy_generator_ai import STRATEGY_PARAMS
        from strategy_lab.backtesting_ai import _BACKTEST_CACHE

        base_strategies = [
            "Breakout_Volume", "Momentum_Retest", "Mean_Reversion", "Trend_Pullback",
            "Bull_Call_Spread", "Iron_Condor_Range", "Hedging_Model",
            "Short_Straddle_IV_Spike", "Long_Straddle_Pre_Event",
            "Futures_Basis_Arb", "ETF_NAV_Arb",
        ]

        # Run backtests for all base strategies (evolved variants auto-loaded)
        for s in base_strategies:
            brain.backtesting_ai.run_full_backtest(s)

        # Collect all results (base + evolved variants populated by _populate_cache)
        results = dict(_BACKTEST_CACHE)

        # ── Print rich BACKTEST REPORT table ──────────────────────────
        from datetime import datetime
        width = 82
        date_str = datetime.now().strftime("%Y-%m-%d")
        passing  = [r for r in results.values() if r.passes_gate]
        failing  = [r for r in results.values() if not r.passes_gate]
        evolved_names = {n for n, p in STRATEGY_PARAMS.items()
                         if p.get("base_strategy")}

        print()
        print("═" * width)
        print(f"  BACKTEST REPORT  |  {date_str}  |  {len(results)} strategies tested")
        print("═" * width)
        header = (
            f"  {'Strategy':<34} {'WinRate':>7} {'Sharpe':>7} "
            f"{'WF%':>5} {'XMkt%':>6} {'OvFit':>6}  Status"
        )
        print(header)
        print("  " + "─" * (width - 2))

        for name, r in sorted(results.items(),
                               key=lambda x: (not x[1].passes_gate, x[0])):
            tag      = " *" if name in evolved_names else "  "
            status   = "✅ PASS" if r.passes_gate else "❌ FAIL"
            reasons  = ""
            if not r.passes_gate and r.failure_reasons:
                reasons = f"  [{'; '.join(r.failure_reasons[:2])}]"
            print(
                f"  {name+tag:<34} "
                f"{r.win_rate:>6.0%} "
                f"{r.sharpe:>7.2f} "
                f"{r.wf_consistency:>5.0%} "
                f"{r.cross_market_pass_rate:>5.0%} "
                f"{r.overfitting_ratio:>6.2f}  "
                f"{status}{reasons}"
            )

        print("  " + "─" * (width - 2))
        disabled = [r.strategy_name for r in failing]
        disabled_str = ", ".join(disabled) if disabled else "None"
        print(f"  ✅ Passing: {len(passing)}   ❌ Failing: {len(failing)}")
        print(f"  Disabled this cycle: {disabled_str}")
        print(f"  (* = evolved variant)")
        print("═" * width)

        # Show SHM live health status (carry-over from previous runs)
        print()
        print("  Strategy Health Monitor — Live Performance Status:")
        brain.strategy_health.print_health_report()

        # Show MetaController regime view for a simulated snapshot
        print()
        from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
        dummy_snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            indices={},
            regime=RegimeLabel.BULL_TREND,
            volatility=VolatilityLevel.MEDIUM,
            vix=14.0,
        )
        passing_set = {r.strategy_name for r in passing}
        all_strats  = list(STRATEGY_PARAMS.keys())
        print("  Simulated activation (Bull Trend / Normal Vol):")
        brain.meta_strategy.print_activation_report(dummy_snapshot, passing_set, all_strats)

        return

    # ── Mode: Strategy evolution ───────────────────────────────────
    if args.evolve:
        log.info("Running strategy GA evolution pass…")
        strategies = ["Breakout_Volume", "Momentum_Retest", "Mean_Reversion", "Trend_Pullback"]
        all_approved = []
        for s in strategies:
            approved = brain.strategy_evolution.run_evolution(s)
            all_approved.extend(approved)

        # Final summary
        w = 80
        print("\n" + "═" * w)
        print("  EVOLUTION SUMMARY")
        print("═" * w)
        if all_approved:
            for v in all_approved:
                print(f"  ✅  {v.variant_name:<40} "
                      f"Cross-market = {v.cross_market_rate:.0%}  "
                      f"Status = APPROVED")
            print()
            print(f"  {len(all_approved)} new variant(s) saved to data/evolved_strategies.json")
            print(f"  They will be used automatically in the next trading cycle.")
        else:
            print("  No variants passed all quality gates this run.")
            print("  Try again later — evolution outcomes vary with market conditions.")
        print("═" * w + "\n")
        return

    # ── Mode: Scheduled daemon ─────────────────────────────────────
    if args.schedule:
        import signal

        log.info("Starting in scheduled daemon mode.")
        log.info("System will initialize at 08:00 and follow the intraday schedule.")
        log.info("Press Ctrl+C or send SIGTERM to stop.")

        brain.start_scheduler()

        # Register clean shutdown on SIGTERM (sent by Windows Task Scheduler
        # and Windows Services when stopping the process)
        _stop = threading.Event()

        def _handle_stop(signum, frame):
            log.info("Stop signal received — shutting down scheduler…")
            brain.shutdown()
            _stop.set()

        signal.signal(signal.SIGTERM, _handle_stop)
        if hasattr(signal, "SIGBREAK"):          # Windows Ctrl+Break
            signal.signal(signal.SIGBREAK, _handle_stop)

        try:
            while not _stop.is_set():
                _stop.wait(timeout=60)
        except KeyboardInterrupt:
            log.info("KeyboardInterrupt — shutting down scheduler…")
            brain.shutdown()
        return

    # ── Mode: Pilot run ───────────────────────────────────────────────
    if args.pilot:
        from pilot import get_pilot_controller, get_paper_broker
        pilot = get_pilot_controller()
        paper = get_paper_broker(capital=pilot._capital)
        log.info("Running PILOT cycle with ₹%.0f capital…", pilot._capital)
        brain.run_full_cycle()
        pilot.log_status()
        paper.print_portfolio()
        return

    # ── Default: Single cycle ──────────────────────────────────────
    brain.run_full_cycle()


if __name__ == "__main__":
    main()
