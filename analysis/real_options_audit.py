"""
analysis/real_options_audit.py
====================================
REAL_OPTIONS_AUDIT_002 — Master orchestrator.

Downloads real NIFTY + BANKNIFTY + VIX data, runs the options payoff
backtester across all strategies × regimes, stores results, and writes
a dated comparison report vs OPTIONS_AUDIT_001 synthetic findings.

Usage
-----
    python analysis/real_options_audit.py

    # Force re-download (skip cache)
    python analysis/real_options_audit.py --no-cache

    # 1-year lookback instead of 2
    python analysis/real_options_audit.py --period 1y

    # Re-run today's backtest even if run_id already exists
    python analysis/real_options_audit.py --force

    # Custom output dir
    python analysis/real_options_audit.py --out reports/real_options/

    # 10-day holding period (default: 5-day)
    python analysis/real_options_audit.py --hold 10

CLI options
-----------
    --period PERIOD   yfinance period string: 1y / 2y / 3y / 5y  (default: 2y)
    --no-cache        Skip reading/writing CSV cache
    --force           Re-run backtest even if today's run_id exists
    --hold {5,10}     Holding period in days (default: 5)
    --db PATH         Override DB path
    --out PATH        Override report output directory
    --summary         Print one-line result to stdout
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from analysis.nse_data_loader import load_market_history, regime_distribution
from analysis.options_backtester import backtest_all_strategies, aggregate_stats, compare_to_synthetic
from analysis.real_options_tracker import get_real_options_tracker, DB_PATH as DEFAULT_DB
from analysis.real_options_reporter import generate_real_options_report


UNDERLYINGS = ["NIFTY", "BANKNIFTY"]


def run_audit(
    period:    str  = "2y",
    use_cache: bool = True,
    use_10d:   bool = False,
    force:     bool = False,
    db_path:   str  = DEFAULT_DB,
    out_dir:   str  = os.path.join(ROOT, "reports", "real_options"),
    summary:   bool = False,
) -> str:
    """
    Full REAL_OPTIONS_AUDIT_002 pipeline.

    1. Download real NIFTY + BANKNIFTY + VIX data
    2. Run payoff simulation for all strategies
    3. Persist to SQLite
    4. Write markdown report

    Returns path to the written report.
    """
    now     = datetime.now(timezone.utc)
    run_id  = now.strftime("%Y%m%d")
    tracker = get_real_options_tracker(db_path)

    if tracker.run_exists(run_id) and not force:
        print(f"[REAL_OPTIONS_AUDIT_002] Run {run_id} already exists. "
              f"Use --force to re-run.")
        # Still regenerate report from existing data
        return generate_real_options_report(tracker, run_id, period, out_dir)

    if force and tracker.run_exists(run_id):
        removed = tracker.clear_run(run_id)
        print(f"[REAL_OPTIONS_AUDIT_002] Cleared {removed} records for run {run_id}.")

    all_records = []
    all_days_total = 0

    for underlying in UNDERLYINGS:
        print(f"  Loading {underlying} ({period})...", end=" ", flush=True)
        days = load_market_history(
            underlying = underlying,
            period     = period,
            use_cache  = use_cache,
        )
        all_days_total += len(days)
        dist  = regime_distribution(days)
        print(
            f"{len(days)} days | "
            + " | ".join(f"{k}:{v}" for k, v in sorted(dist.items()))
        )

        records = backtest_all_strategies(days, use_10d=use_10d)
        all_records.extend(records)

    stored = tracker.store_batch(all_records, run_id=run_id)
    print(f"  Stored {stored:,} backtest records (run_id={run_id})")

    # ── Aggregate and print quick summary ─────────────────────────────────────
    overall  = aggregate_stats(all_records, group_by="strategy")
    verdicts = compare_to_synthetic(overall)

    if summary:
        print(f"\n{'Strategy':<20} {'Real WR':>8} {'PF':>6}  Verdict")
        print("-" * 65)
        for strat, st in sorted(overall.items()):
            v = verdicts.get(strat, "")[:30]
            print(f"  {st.strategy:<18} {st.win_rate:>7.1f}% {st.profit_factor:>6.2f}  {v}")

    # ── Write report ──────────────────────────────────────────────────────────
    report_path = generate_real_options_report(tracker, run_id, period, out_dir)
    return report_path


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="REAL_OPTIONS_AUDIT_002 — Validate option strategies with real data"
    )
    p.add_argument("--period",   default="2y",         help="yfinance period: 1y/2y/3y/5y")
    p.add_argument("--no-cache", action="store_true",  help="Skip CSV cache")
    p.add_argument("--force",    action="store_true",  help="Re-run even if run_id exists today")
    p.add_argument("--hold",     default=5, type=int,  choices=[5, 10], help="Holding period")
    p.add_argument("--db",       default=DEFAULT_DB,   help="Override DB path")
    p.add_argument("--out",      default=os.path.join(ROOT, "reports", "real_options"),
                                                       help="Output directory")
    p.add_argument("--summary",  action="store_true",  help="Print table to stdout")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    print(f"\nREAL_OPTIONS_AUDIT_002 — period={args.period} hold={args.hold}d\n")

    report = run_audit(
        period    = args.period,
        use_cache = not args.no_cache,
        use_10d   = (args.hold == 10),
        force     = args.force,
        db_path   = args.db,
        out_dir   = args.out,
        summary   = args.summary,
    )
    print(f"\nReport: {report}")


if __name__ == "__main__":
    main()
