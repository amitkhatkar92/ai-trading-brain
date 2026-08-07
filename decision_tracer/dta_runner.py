"""
decision_tracer/dta_runner.py
================================
DTA-001 — Decision Traceability Audit — Runner

Usage:
    python -m decision_tracer.dta_runner --symbol RELIANCE
    python -m decision_tracer.dta_runner --symbol RELIANCE --date 2026-04-02

Output: data/dta/YYYY-MM-DD/RELIANCE_DECISION_TRACE.md
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from typing import Optional

from .dta_collector import collect_trace
from .dta_analyzer  import analyze
from .dta_reporter  import write_report

log = logging.getLogger(__name__)


def run_dta(symbol: str, target_date: Optional[str] = None,
            report_date: Optional[str] = None) -> dict:
    """
    Run DTA-001 for a symbol.
    symbol:      e.g. 'RELIANCE'
    target_date: trace the decision on this specific date (YYYY-MM-DD)
    report_date: where to write the report (default: today)
    Returns summary dict with report path and audit verdict.
    """
    if report_date is None:
        report_date = date.today().isoformat()

    log.info("[DTA-001] Tracing decision for %s (target_date=%s)", symbol, target_date)

    # Collect all evidence layers
    bundle = collect_trace(symbol, target_date)
    log.info("[DTA-001] Collected: decision=%s  features=%s  dna=%d  edges=%d  alts=%d",
             bundle.decision.decision if bundle.decision else "N/A",
             bool(bundle.features and bundle.features.features),
             len(bundle.dna_matches),
             len(bundle.edge_matches),
             len(bundle.alternative_candidates))

    # Answer the 8 audit questions
    audit = analyze(bundle)
    log.info("[DTA-001] Audit: %s", audit.overall_verdict)

    # Write report
    path = write_report(bundle, audit, report_date)
    log.info("[DTA-001] Report: %s", path)

    # Build summary
    d = bundle.decision
    return {
        "symbol":       symbol,
        "target_date":  target_date or "most_recent",
        "report_date":  report_date,
        "decision":     d.decision if d else "NOT_FOUND",
        "confidence":   round(d.confidence, 4) if d else None,
        "strategy":     d.strategy if d else None,
        "cycle_id":     d.cycle_id if d else None,
        "cycle_time":   d.ts[:19] if d else None,
        "answered":     sum(1 for a in audit.answers if a.verdict == "ANSWERED"),
        "total_questions": len(audit.answers),
        "dna_matches":  sum(1 for m in bundle.dna_matches if m.matched),
        "edge_matches": sum(1 for e in bundle.edge_matches if e.all_satisfied),
        "alternatives": len(bundle.alternative_candidates),
        "report_path":  str(path),
    }


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [DTA] %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="DTA-001: Decision Traceability Audit"
    )
    parser.add_argument("--symbol", required=True,
                        help="Symbol to trace (e.g. RELIANCE)")
    parser.add_argument("--date", default=None,
                        help="Trace decision on this date YYYY-MM-DD (default: most recent)")
    parser.add_argument("--report-date", default=None,
                        help="Date folder for output (default: today)")
    args = parser.parse_args()

    result = run_dta(
        symbol=args.symbol.upper(),
        target_date=args.date,
        report_date=args.report_date,
    )
    print(json.dumps(result, default=str, indent=2))


if __name__ == "__main__":
    main()
