"""
run_eod_reports.py

Daily end-of-day report runner. Execute after market close.

Usage:
    python run_eod_reports.py
    python run_eod_reports.py --date 2026-06-16
    python run_eod_reports.py --date 2026-06-14 --output reports/
    python run_eod_reports.py --db data/market_behavior.db

On Saturdays, the weekly report is generated automatically in addition
to the 5 EOD reports.

Shadow mode: all Phase D and Phase E outputs are OBSERVED ONLY.
No shadow output modifies opportunities, parameters, TTLs, or decisions.
"""
import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OIOS Daily EOD Report Runner"
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Report date (YYYY-MM-DD). Default: today.",
    )
    parser.add_argument(
        "--db",
        default="data/market_behavior.db",
        help="Path to SQLite database. Default: data/market_behavior.db",
    )
    parser.add_argument(
        "--output",
        default="reports",
        help="Output directory root. Default: reports/",
    )
    parser.add_argument(
        "--weekly-only",
        action="store_true",
        help="Generate only the weekly report (Saturday mode).",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        return 1

    from oios.reporting.runner import run_full_eod, run_weekly

    if args.weekly_only:
        run_weekly(db_path, args.date, args.output)
    else:
        run_full_eod(db_path, args.date, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
