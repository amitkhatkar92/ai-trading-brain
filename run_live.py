"""
run_live.py — AI Trading Brain Live / Paper Execution Entry Point
==================================================================
Usage
-----
  Paper trading (safe, default):
      python run_live.py --mode paper

  Live trading (requires PAPER_TRADING=false in .env AND live credentials):
      python run_live.py --mode live

Description
-----------
This is the primary entry point for the continuous trading daemon.
It starts the existing MasterOrchestrator scheduler (09:05 → 15:35 IST),
wires the PaperTradeLogger into the EventBus for trade journaling, and
prints a daily terminal summary at EOD.

What this file does NOT change
-------------------------------
  * StrategyLab, BacktestingAI, Momentum_Retest XMkt override
  * RiskControl, RiskGuardian, CapitalRiskEngine
  * ATR entry zone logic
  * DecisionEngine debate threshold (6.5)
  * OrderManager internals (broker routing, position tracking)

All execution remains exactly as it does in the live production system —
the only difference in paper mode is that ``PAPER_TRADING=True`` suppresses
real broker API calls inside OrderManager.

Scheduler
---------
The intraday schedule is driven by ``config.SCHEDULE`` (unchanged):
  09:05  market_open_regime
  09:10  first_opportunity_scan
  09:20  strategy_evaluation
  09:45  trade_decision
  10:30  mid_morning_scan
  13:00  afternoon_scan
  15:00  closing_analysis
  15:35  eod_learning
"""

import argparse
import os
import signal
import sys
import threading
from datetime import datetime

# ── Ensure UTF-8 console output ────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Project root on path ───────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import get_logger

log = get_logger("run_live")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Trading Brain — live / paper trading daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_live.py --mode paper      # paper trading (safe, recommended)
  python run_live.py --mode live       # live trading   (requires .env creds)
"""
    )
    parser.add_argument(
        "--mode",
        choices=["paper", "live"],
        default="paper",
        help="'paper' = fully simulated (default). 'live' = real broker orders.",
    )
    return parser.parse_args()


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    # ── Apply mode flag BEFORE any other imports that read config ─────────────
    import config as _cfg

    if args.mode == "paper":
        _cfg.PAPER_TRADING = True
        os.environ["PAPER_TRADING"] = "true"
    elif args.mode == "live":
        # Honour whatever .env says; warn loudly if PAPER_TRADING is still True
        if _cfg.PAPER_TRADING:
            log.warning(
                "⚠  --mode live was requested but PAPER_TRADING is still True "
                "(set PAPER_TRADING=false in .env to enable live orders)."
            )
        # Don't force override — respect .env as the authoritative decision

    mode_label = "PAPER TRADING (simulated)" if _cfg.PAPER_TRADING else "LIVE TRADING"

    # ── Banner ────────────────────────────────────────────────────────────────
    log.info("=" * 65)
    log.info("  AI TRADING BRAIN  |  %s", mode_label)
    log.info("  Layers: 17  |  Agents: ~62  |  Date: %s",
             datetime.now().strftime("%Y-%m-%d"))
    log.info("=" * 65)

    if _cfg.PAPER_TRADING:
        log.info("  ✅  All orders will be SIMULATED — no real money at risk.")
        log.info("  📋  Trade journal : data/paper_trade_log.csv")
        log.info("  📋  Legacy journal: data/paper_trades.csv")
    else:
        log.warning("  ⚠   LIVE MODE — real orders will be sent to the broker!")

    # ── Initialise orchestrator ────────────────────────────────────────────────
    log.info("Initialising MasterOrchestrator…")
    from orchestrator import MasterOrchestrator
    brain = MasterOrchestrator()

    # ── Wire PaperTradeLogger ─────────────────────────────────────────────────
    if _cfg.PAPER_TRADING:
        from execution_engine.paper_trade_logger import PaperTradeLogger
        from communication import get_bus

        paper_logger = PaperTradeLogger(order_manager=brain.order_manager)
        paper_logger.subscribe(get_bus())

        log.info("[run_live] PaperTradeLogger wired to EventBus.")

        # Convenience: print a summary if the user hits Ctrl+C mid-day
        def _on_interrupt(signum, frame):
            log.info("Interrupt received — printing session summary before exit…")
            paper_logger.scan_for_closes()
            paper_logger.print_daily_summary()
            brain.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT,  _on_interrupt)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _on_interrupt)
        if hasattr(signal, "SIGBREAK"):     # Windows Ctrl+Break
            signal.signal(signal.SIGBREAK, _on_interrupt)
    else:
        # Live mode: register a clean shutdown handler without the summary
        _stop = threading.Event()

        def _on_stop(signum, frame):
            log.info("Stop signal — shutting down scheduler…")
            brain.shutdown()
            _stop.set()

        signal.signal(signal.SIGINT,  _on_stop)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _on_stop)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, _on_stop)

    # ── Start the existing intraday scheduler ─────────────────────────────────
    log.info("[run_live] Starting intraday scheduler"
             " (pre-market init 08:00 → EOD learning 15:35)…")
    log.info("[run_live] Press Ctrl+C to stop.")

    try:
        brain.start_scheduler()      # blocks until shutdown() is called
    except KeyboardInterrupt:
        log.info("KeyboardInterrupt — shutting down…")
        if _cfg.PAPER_TRADING:
            paper_logger.scan_for_closes()
            paper_logger.print_daily_summary()
        brain.shutdown()


if __name__ == "__main__":
    main()
