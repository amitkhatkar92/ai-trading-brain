"""
scripts/hkap/seed_hkap_years.py
==================================
Self-Learning Ecosystem Phase 6 — one-time/periodic manual utility to
populate real data/hkap/{year}/year_knowledge_package.json files with
genuine yfinance-derived historical data.

Not part of the live path. hkap/hkap_kde_bridge.py's run_hkap_kde_discovery()
only reads what this script (or a future scheduled re-run of it) has
already persisted -- it never downloads anything itself.

Usage:
    python scripts/hkap/seed_hkap_years.py [--years 2023 2024] [--symbols 40] [--force]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from hkap.hkap_config import HKAPConfig
from hkap.hkap_engine import HKAPEngine


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, nargs="+", default=[2023, 2024])
    parser.add_argument("--symbols", type=int, default=40)
    parser.add_argument("--force", action="store_true", help="re-run years already marked COMPLETE")
    args = parser.parse_args()

    t0 = time.monotonic()
    config = HKAPConfig(years=args.years, max_symbols=args.symbols)
    engine = HKAPEngine(config=config)
    summary = engine.run(years=args.years, force=args.force)
    elapsed = time.monotonic() - t0

    print(f"elapsed={elapsed:.1f}s")
    print(f"years_completed={summary.years_completed}")
    print(f"years_failed={summary.years_failed}")
    print(f"total_dna_discovered={summary.total_dna_discovered}")
    print(f"synthesis_reports={summary.synthesis_reports}")


if __name__ == "__main__":
    main()
