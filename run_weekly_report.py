"""
run_weekly_report.py

Standalone weekly report runner. Intended to run every Saturday.
Can be run manually for any date.

Usage:
    python run_weekly_report.py
    python run_weekly_report.py --date 2026-06-14
    python run_weekly_report.py --date 2026-06-14 --output reports/

The weekly report covers the 7 calendar days ending on the given date.
If run on a non-Saturday, a warning is printed but the report is generated.
"""
import argparse
import sys
from datetime import date
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OIOS Weekly Report Runner"
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Week-end date (YYYY-MM-DD). Default: today.",
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
    args = parser.parse_args()

    report_date = args.date or date.today().isoformat()
    db_path = Path(args.db)

    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        return 1

    day_of_week = date.fromisoformat(report_date).weekday()
    day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][day_of_week]
    if day_of_week != 5:
        print(
            f"WARNING: {report_date} is a {day_name}, not Saturday. "
            f"Weekly report covers 7 days ending on this date."
        )

    from oios.reporting.runner import run_weekly
    run_weekly(db_path, report_date, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
