"""
analysis/live_observation_audit.py
=========================================
LIVE_OBSERVATION_FRAMEWORK_001 — CLI orchestrator.

Ingests paper_trades.csv into live_observations.db with full enrichment,
then prints a dashboard summary.

Usage
-----
    python analysis/live_observation_audit.py

    # Re-process even if rows already exist (idempotent — skips duplicates)
    python analysis/live_observation_audit.py --reingest

    # Custom CSV path
    python analysis/live_observation_audit.py --csv data/paper_trades.csv

    # Watch mode: poll every 60s for new trades (for VPS deployment)
    python analysis/live_observation_audit.py --watch --interval 60
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from analysis.live_observation_collector import ingest_from_csv, PAPER_TRADES_CSV
from analysis.live_observation_tracker   import get_live_tracker


def _print_dashboard(tracker) -> None:
    s = tracker.summary()
    print("\n" + "="*55)
    print("  LIVE_OBSERVATION_FRAMEWORK_001 — Status")
    print("="*55)
    print(f"  Total observations    : {s['total']}")
    print(f"  Open                  : {s['open']}")
    print(f"  Closed → WIN          : {s['wins']}")
    print(f"  Closed → LOSS         : {s['losses']}")
    closed = s['wins'] + s['losses']
    print(f"  Win rate (closed)     : {s['win_rate']:.1f}%  (n={closed})")

    if s.get("tiers"):
        print("\n  Quality Tier Breakdown:")
        for tier in ["PREMIUM", "HIGH", "MEDIUM", "LOW"]:
            n = s["tiers"].get(tier, 0)
            print(f"    {tier:<10} : {n} trades")

    if s.get("regimes"):
        print("\n  Regime Breakdown:")
        for regime, n in sorted(s["regimes"].items()):
            print(f"    {regime:<12} : {n} trades")

    twr = tracker.tier_win_rates()
    if twr:
        print("\n  Tier Win Rates (live evidence):")
        for tier in ["PREMIUM", "HIGH", "MEDIUM", "LOW"]:
            if tier in twr:
                r = twr[tier]
                bar = "█" * int(r["win_rate"] / 10)
                print(f"    {tier:<10} : {r['win_rate']:>5.1f}%  {bar}  (n={r['n']})")

    if s["total"] < 30:
        remaining = 30 - s["total"]
        print(f"\n  ⏳ Need {remaining} more closed trades before recommendation")
        print(f"     validation becomes statistically meaningful.")
    else:
        print(f"\n  ✅ Sufficient data for initial recommendation validation.")

    print("="*55)


def run_once(csv_path: str) -> None:
    tracker = get_live_tracker()
    result  = ingest_from_csv(csv_path, tracker)
    print(f"\n  CSV rows processed : {result['processed']}")
    print(f"  New observations   : {result['new']}")
    print(f"  Already in DB      : {result['skipped']}")
    if result["errors"]:
        print(f"  Errors             : {result['errors']}")
        for d in result["error_details"][:5]:
            print(f"    {d}")
    _print_dashboard(tracker)


def main() -> None:
    p = argparse.ArgumentParser(
        description="LIVE_OBSERVATION_FRAMEWORK_001 — ingest and report live trades"
    )
    p.add_argument("--csv",      default=PAPER_TRADES_CSV, help="Path to paper_trades.csv")
    p.add_argument("--watch",    action="store_true",      help="Poll for new trades continuously")
    p.add_argument("--interval", default=60, type=int,     help="Poll interval in seconds (watch mode)")
    args = p.parse_args()

    if args.watch:
        print(f"Watching {args.csv} every {args.interval}s. Ctrl+C to stop.")
        while True:
            run_once(args.csv)
            time.sleep(args.interval)
    else:
        run_once(args.csv)


if __name__ == "__main__":
    main()
