"""
analysis/options_risk_audit.py
====================================
OPTIONS_RISK_AUDIT_001 — Master orchestrator.

Reads from the real_options_audit.db (populated by real_options_audit.py),
computes risk metrics and drawdown analytics for every strategy,
and writes a dated risk-first report.

This module does NOT re-download data. It operates purely on what
real_options_audit.py already stored. Run that first.

Usage
-----
    python analysis/options_risk_audit.py

    # Force overwrite today's report
    python analysis/options_risk_audit.py --force

    # Custom DB and output
    python analysis/options_risk_audit.py --db data/real_options_audit.db --out reports/options_risk/

    # Quick stdout table
    python analysis/options_risk_audit.py --summary
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from analysis.tail_risk_analyzer   import compute_risk_metrics, compute_regime_risk, RiskMetrics
from analysis.drawdown_analyzer    import compute_all_drawdowns
from analysis.options_risk_reporter import generate_risk_report
from analysis.real_options_tracker  import DB_PATH as DEFAULT_DB
from analysis.options_backtester    import ALL_STRATEGIES


OUT_DIR = os.path.join(ROOT, "reports", "options_risk")


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_records(db_path: str, run_id: str = "") -> List[dict]:
    """Load all backtest records from real_options_audit.db."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"{db_path} not found. Run real_options_audit.py first."
        )
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        if run_id:
            rows = conn.execute(
                "SELECT * FROM real_options_backtest WHERE run_id=? ORDER BY date",
                (run_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM real_options_backtest ORDER BY date"
            ).fetchall()
    return [dict(r) for r in rows]


def _latest_run_id(db_path: str) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT run_id FROM real_options_backtest ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
    return row[0] if row else ""


def _date_range(records: List[dict]) -> tuple:
    dates = [r["date"] for r in records if r.get("date")]
    return (min(dates, default=""), max(dates, default=""))


# ── Core pipeline ─────────────────────────────────────────────────────────────

def run_risk_audit(
    db_path:  str  = DEFAULT_DB,
    run_id:   str  = "",
    out_dir:  str  = OUT_DIR,
    force:    bool = False,
    summary:  bool = False,
) -> str:
    """
    1. Load real backtest records
    2. Compute tail risk metrics per strategy (overall + per regime)
    3. Compute drawdown metrics per strategy (overall + per regime)
    4. Write risk report

    Returns path to written report.
    """
    date_str   = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path   = os.path.join(out_dir, f"OPTIONS_RISK_AUDIT_001_{date_str}.md")

    if not force and os.path.exists(out_path):
        print(f"Report already exists: {out_path}\nUse --force to overwrite.")
        return out_path

    # Load
    run_id = run_id or _latest_run_id(db_path)
    if not run_id:
        raise RuntimeError("No records found in DB. Run real_options_audit.py first.")
    print(f"  Loading records for run_id={run_id}...", end=" ", flush=True)
    records = _load_records(db_path, run_id)
    print(f"{len(records):,} records")

    date_r  = _date_range(records)

    # ── Risk metrics per strategy ─────────────────────────────────────────────
    risk_by_strategy: Dict[str, Dict[str, RiskMetrics]] = {}

    for strat in ALL_STRATEGIES:
        strat_recs = [r for r in records if r["strategy"] == strat]
        if not strat_recs:
            continue
        risk_by_strategy[strat] = compute_regime_risk(strat, strat_recs)

    # ── Drawdown per strategy ─────────────────────────────────────────────────
    dd_by_strategy = compute_all_drawdowns(records)

    # ── Quick summary ─────────────────────────────────────────────────────────
    if summary:
        print(f"\n{'Strategy':<20} {'WR':>6} {'PF':>6} {'EV':>8}  {'Sharpe':>7}  "
              f"{'MaxDD':>8}  {'WrstMo':>8}  Verdict")
        print("-" * 90)
        for strat in ALL_STRATEGIES:
            rm = risk_by_strategy.get(strat, {}).get("ALL")
            dd = dd_by_strategy.get(strat, {}).get("ALL")
            if rm is None:
                print(f"  {strat:<18} {'NO DATA':>40}")
                continue
            mdd   = f"{dd.max_drawdown_r:+.2f}R" if dd else "—"
            worst = f"{dd.worst_month_r:+.2f}R"  if dd else "—"
            print(
                f"  {strat:<18} {rm.win_rate:>5.1f}% {rm.profit_factor:>6.2f} "
                f"{rm.expected_value:>+8.3f}R {rm.sharpe:>7.2f}  "
                f"{mdd:>8}  {worst:>8}  {rm.verdict}"
            )

    # ── Write report ──────────────────────────────────────────────────────────
    report_path = generate_risk_report(
        risk_by_strategy = risk_by_strategy,
        dd_by_strategy   = dd_by_strategy,
        total_records    = len(records),
        date_range       = date_r,
        out_dir          = out_dir,
    )
    return report_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="OPTIONS_RISK_AUDIT_001 — risk-first options strategy evaluation"
    )
    p.add_argument("--db",      default=DEFAULT_DB, help="real_options_audit.db path")
    p.add_argument("--run-id",  default="",         help="Specific run_id (default: latest)")
    p.add_argument("--out",     default=OUT_DIR,    help="Output directory")
    p.add_argument("--force",   action="store_true",help="Overwrite today's report")
    p.add_argument("--summary", action="store_true",help="Print table to stdout")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    print("\nOPTIONS_RISK_AUDIT_001\n")
    report = run_risk_audit(
        db_path = args.db,
        run_id  = args.run_id,
        out_dir = args.out,
        force   = args.force,
        summary = args.summary,
    )
    print(f"\nReport: {report}")


if __name__ == "__main__":
    main()
