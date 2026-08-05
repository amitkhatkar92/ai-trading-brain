#!/usr/bin/env python3
"""
HKAP-001: Historical Knowledge Acquisition Program
Reconstructs institutional market knowledge from historical NSE data.

Usage:
    python run_hkap.py                           # all configured years + synthesis
    python run_hkap.py --year 2023               # single year
    python run_hkap.py --years 2020,2021,2022    # specific years
    python run_hkap.py --synthesis               # synthesis only (needs 2+ completed years)
    python run_hkap.py --status                  # print current status
    python run_hkap.py --dry-run                 # dry run (no disk writes, no downloads)
    python run_hkap.py --force                   # re-run even completed years
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt = "%H:%M:%S",
)
log = logging.getLogger("hkap")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="HKAP-001: Historical Knowledge Acquisition Program",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--year",      type=int,    help="Run a single year")
    g.add_argument("--years",     type=str,    help="Comma-separated list of years, e.g. 2020,2021")
    g.add_argument("--synthesis", action="store_true", help="Run synthesis only")
    g.add_argument("--status",    action="store_true", help="Print status and exit")
    p.add_argument("--dry-run",   action="store_true", help="No disk writes or data downloads")
    p.add_argument("--force",     action="store_true", help="Re-run completed years")
    p.add_argument(
        "--universe", default="NIFTY500",
        choices=["NIFTY500", "NIFTY100", "NIFTY50"],
        help="Universe to use (default: NIFTY500)",
    )
    p.add_argument("--max-symbols", type=int, default=150,
                   help="Max symbols per year (default: 150)")
    p.add_argument(
        "--year-range", type=str, default=None,
        help="Year range e.g. 2015-2025 (inclusive)",
    )
    return p


def main() -> int:
    from hkap import HKAPConfig, HKAPEngine

    args = _build_parser().parse_args()

    # ── build years list ──────────────────────────────────────────────────
    years = None
    if args.year:
        years = [args.year]
    elif args.years:
        try:
            years = [int(y.strip()) for y in args.years.split(",")]
        except ValueError:
            log.error("--years must be comma-separated integers, e.g. 2020,2021")
            return 1
    elif args.year_range:
        try:
            start, end = [int(x) for x in args.year_range.split("-")]
            years = list(range(start, end + 1))
        except ValueError:
            log.error("--year-range must be START-END e.g. 2015-2025")
            return 1

    # ── build config ──────────────────────────────────────────────────────
    config_years = years if years else list(range(2015, 2027))
    config = HKAPConfig(
        years        = config_years,
        dry_run      = args.dry_run,
        universe_name = args.universe,
        max_symbols   = args.max_symbols,
    )

    log.info("HKAP-001 starting | years=%s dry_run=%s", config.sorted_years, config.dry_run)

    # ── build engine ──────────────────────────────────────────────────────
    engine = HKAPEngine(config=config)

    # ── dispatch ──────────────────────────────────────────────────────────
    if args.status:
        st = engine.status()
        print(json.dumps(st.to_dict(), indent=2))
        return 0

    if args.synthesis:
        try:
            reports = engine.run_synthesis()
            log.info("Synthesis complete. Reports: %s", reports)
        except Exception as exc:
            log.error("Synthesis failed: %s", exc)
            return 1
        return 0

    if args.year:
        try:
            pkg = engine.run_year(args.year)
            print(json.dumps(pkg.to_dict(), indent=2, default=str))
        except Exception as exc:
            log.error("Year %d failed: %s", args.year, exc)
            return 1
        return 0

    # ── full run (all years + synthesis) ──────────────────────────────────
    summary = engine.run(years=years, force=args.force)
    print("\n" + "=" * 60)
    print("HKAP-001 COMPLETE")
    print("=" * 60)
    print(json.dumps(summary.to_dict(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
