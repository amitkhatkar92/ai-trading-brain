"""predictive_gap/pga_runner.py — PGA-001 orchestrator + CLI entry point."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any

log = logging.getLogger(__name__)


def run_pga(
    report_date: str | None = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Run the complete PGA-001 pipeline for a given date.

    Steps:
      1. Collect — price data, decisions, signals, executed trades
      2. Analyze — classify each gainer/loser as predicted/predictable
      3. Root Cause — identify why each miss occurred (13 categories)
      4. Learning — plan A–G actions, execute C/B automatically
      5. Report — write 9 Markdown reports to data/pga/YYYY-MM-DD/

    Returns a summary dict suitable for orchestrator logging.
    """
    from .pga_config import PGAConfig, PGA_DIR
    from .pga_collector import collect_daily
    from .pga_analyzer import analyze_universe
    from .pga_root_cause import analyze_misses
    from .pga_learning import plan_actions, execute_actions
    from .pga_reporter import write_all_reports

    # ── Resolve date ────────────────────────────────────────────────
    if report_date is None:
        report_date = date.today().isoformat()

    cfg = PGAConfig(dry_run=dry_run)
    report_dir = PGA_DIR / report_date

    log.info("[PGA-001] Starting pipeline for %s (dry_run=%s)", report_date, dry_run)
    t0 = datetime.now()

    # ── Step 1: Collect ─────────────────────────────────────────────
    daily_data = collect_daily(report_date, cfg)

    if not daily_data.all_moves:
        log.warning("[PGA-001] No price data available for %s — aborting", report_date)
        return {
            "date": report_date,
            "status": "NO_PRICE_DATA",
            "n_gainers": 0,
            "n_losers": 0,
            "n_missed_winners": 0,
            "n_missed_losers": 0,
            "n_learning_actions": 0,
            "report_dir": str(report_dir),
            "elapsed_seconds": (datetime.now() - t0).total_seconds(),
        }

    # ── Step 2: Analyze ─────────────────────────────────────────────
    analyses = analyze_universe(daily_data, cfg)

    # ── Step 3: Root Cause ───────────────────────────────────────────
    causes = analyze_misses(analyses, daily_data, cfg)

    # ── Step 4: Learning ─────────────────────────────────────────────
    actions = plan_actions(causes, analyses, daily_data, cfg, report_date)

    if not cfg.dry_run:
        report_dir.mkdir(parents=True, exist_ok=True)

    actions = execute_actions(actions, cfg, report_dir)

    # ── Step 5: Report ───────────────────────────────────────────────
    if not cfg.dry_run:
        write_all_reports(daily_data, analyses, causes, actions, report_dir)

    from .pga_analyzer import MISS_MISSED_WINNER, MISS_MISSED_LOSER
    elapsed = (datetime.now() - t0).total_seconds()

    result = {
        "date": report_date,
        "status": "OK",
        "n_gainers": len(daily_data.gainers),
        "n_losers": len(daily_data.losers),
        "n_analyses": len(analyses),
        "n_missed_winners": sum(1 for a in analyses if a.miss_type == MISS_MISSED_WINNER),
        "n_missed_losers": sum(1 for a in analyses if a.miss_type == MISS_MISSED_LOSER),
        "n_learning_actions": len(actions),
        "n_hypotheses": sum(1 for a in actions if a.category == "C" and a.scheduled),
        "report_dir": str(report_dir),
        "elapsed_seconds": round(elapsed, 1),
    }
    log.info(
        "[PGA-001] Pipeline complete in %.1fs: "
        "gainers=%d losers=%d missed_winners=%d missed_losers=%d actions=%d",
        elapsed,
        result["n_gainers"],
        result["n_losers"],
        result["n_missed_winners"],
        result["n_missed_losers"],
        result["n_learning_actions"],
    )
    return result


# ── CLI ─────────────────────────────────────────────────────────────

def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="PGA-001 — Predictive Gap Analysis (run for one trading date)",
        prog="python -m predictive_gap.pga_runner",
    )
    parser.add_argument(
        "--date", "-d",
        default=None,
        help="Date to analyse (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run analysis but do not write reports or execute learning actions.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print result as JSON to stdout.",
    )
    args = parser.parse_args()

    result = run_pga(report_date=args.date, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    sep = "=" * 60
    print(f"\n{sep}")
    print("  PGA-001 RESULT")
    print(sep)
    for k, v in result.items():
        print(f"  {k:<25} {v}")
    print(sep)

    if result.get("report_dir") and not args.dry_run:
        report_path = Path(result["report_dir"]) / "PGA_DAILY_REPORT.md"
        if report_path.exists():
            print(f"\n  Main report: {report_path}")


if __name__ == "__main__":
    _main()
