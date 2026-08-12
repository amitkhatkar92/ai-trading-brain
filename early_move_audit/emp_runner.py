"""
early_move_audit/emp_runner.py — CLI entry point for EMP-001.

Usage
-----
  python -m early_move_audit.emp_runner [options]

Options
-------
  --days N          Lookback in trading days (default: 60)
  --date YYYY-MM-DD Override the run date (default: today)
  --symbol SYMBOL   Limit universe to a single symbol
  --top-n N         Top-N threshold for ranking (default: 10)
  --dry-run         Skip report writes; print summary to stdout

Public API
----------
  run_emp_audit(days, date_str, symbol, top_n, dry_run) -> EMPResult
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date as date_cls
from typing import List, Optional

from .emp_analyzer import EMPResult, run_analysis
from .emp_collector import collect_dataset
from .emp_config import DEFAULT_LOOKBACK_DAYS, DEFAULT_UNIVERSE, EmpConfig, PERSISTENCE_TOP_N
from .emp_reporter import generate_reports

log = logging.getLogger(__name__)


def run_emp_audit(
    days:     int          = DEFAULT_LOOKBACK_DAYS,
    date_str: Optional[str] = None,
    symbol:   Optional[str] = None,
    top_n:    int           = 10,
    dry_run:  bool          = False,
) -> EMPResult:
    """
    Run the full EMP-001 analysis pipeline.

    Parameters
    ----------
    days     : Number of trading days to look back (historical mode).
    date_str : Override today's date (YYYY-MM-DD).  None = today.
    symbol   : Single-symbol deep-dive.  None = full universe.
    top_n    : Primary top-N threshold for ranking and persistence.
    dry_run  : If True, skip report file writes and return result only.

    Returns
    -------
    EMPResult
    """
    run_date = date_str or date_cls.today().isoformat()

    universe = [symbol.strip().upper()] if symbol else list(DEFAULT_UNIVERSE)

    # Ensure top_n is included in persistence_top_n
    top_n_values = sorted(set(PERSISTENCE_TOP_N) | {top_n})

    config = EmpConfig(
        universe         = universe,
        lookback_days    = days,
        top_n            = top_n,
        persistence_top_n= top_n_values,
        dry_run          = dry_run,
        date_override    = date_str,
        symbol_filter    = symbol,
    )

    log.info(
        "[EmpRunner] Starting EMP-001 | date=%s days=%d universe=%d top_n=%d dry_run=%s",
        run_date, days, len(universe), top_n, dry_run,
    )

    records, quality = collect_dataset(config)

    result = run_analysis(records, quality, config, run_date)

    if dry_run:
        _print_dry_run_summary(result)
    else:
        try:
            paths = generate_reports(result)
            log.info("[EmpRunner] Reports written: %s", {k: str(v) for k, v in paths.items()})
        except Exception as exc:
            log.error("[EmpRunner] Report generation failed: %s", exc)
            result.warnings.append(f"Report generation error: {exc}")

    return result


def _print_dry_run_summary(result: EMPResult) -> None:
    """Print a brief summary to stdout for dry-run mode."""
    print(f"\n=== EMP-001 DRY RUN SUMMARY — {result.run_date} ===")
    print(f"Records:    {len(result.records)} symbol-days")
    print(f"Days:       {result.persistence.n_trading_days}")
    print(f"Symbols:    {result.persistence.n_symbols}")
    print(f"With daily:    {result.quality.with_daily}")
    print(f"With intraday: {result.quality.with_intraday}")

    lp = result.persistence.leader_persistence
    if lp:
        print("\nMorning Leader Persistence (09:30 → Close):")
        for side in ("WINNER", "LOSER"):
            d = lp.get(side, {})
            print(f"  {side}: top5={d.get(5,'N/A')}%  top10={d.get(10,'N/A')}%")

    pred = result.predictive
    print(f"\nRecommendation: {pred.recommendation}")

    if result.warnings:
        print(f"\nWarnings: {result.warnings}")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m early_move_audit.emp_runner",
        description="EMP-001: Early-Move Persistence & Previous-Day Predictive Value Audit",
    )
    parser.add_argument("--days",    type=int,   default=DEFAULT_LOOKBACK_DAYS,
                        help="Lookback in trading days (default: 60)")
    parser.add_argument("--date",    type=str,   default=None,
                        help="Run date override YYYY-MM-DD (default: today)")
    parser.add_argument("--symbol",  type=str,   default=None,
                        help="Limit to a single symbol")
    parser.add_argument("--top-n",   type=int,   default=10,
                        help="Top-N threshold (default: 10)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip report file writes; print summary only")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable DEBUG logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    result = run_emp_audit(
        days     = args.days,
        date_str = args.date,
        symbol   = args.symbol,
        top_n    = args.top_n,
        dry_run  = args.dry_run,
    )

    if result.look_ahead_violations:
        log.error("LOOK-AHEAD VIOLATIONS: %s", result.look_ahead_violations)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
