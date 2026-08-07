"""
growth_validator/gva_runner.py
================================
GVA-001 — Growth Validator Runner

Orchestrates all three phases: collect → compute → report.
Single entry point for CLI and programmatic use.

Usage:
    from growth_validator import run_gva
    result = run_gva()

    python -m growth_validator.gva_runner
    python -m growth_validator.gva_runner --date 2026-08-07
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Optional

from .gva_collector import collect_all, GVAEvidence
from .gva_metrics import compute_all, GrowthReport
from .gva_reporter import write_all_reports

log = logging.getLogger(__name__)


def run_gva(report_date: Optional[str] = None) -> dict:
    """
    Full GVA-001 run: collect evidence → compute metrics → write 6 reports.
    Returns summary dict with paths, scores, and SD verdict.
    Read-only with respect to all knowledge stores.
    """
    if report_date is None:
        report_date = date.today().isoformat()

    log.info("[GVA-001] Growth Validation run — %s", report_date)

    # Phase 1 — Collect evidence
    log.info("[GVA-001] Phase 1: Collecting evidence...")
    ev: GVAEvidence = collect_all()
    log.info("[GVA-001] Evidence: %d studies  %d hypotheses  %d DNA  %d edges  %d cycles",
             len(ev.studies), ev.hypothesis.total, ev.dna.total,
             ev.edges.total, ev.platform.total_cycles)

    # Phase 2 — Compute metrics
    log.info("[GVA-001] Phase 2: Computing metrics...")
    gr: GrowthReport = compute_all(ev)
    log.info("[GVA-001] Scores: K=%.0f L=%.0f D=%.0f S=%.0f P=%.0f → Overall=%.1f (%s)",
             gr.score_knowledge, gr.score_learning, gr.score_dna,
             gr.score_scientific, gr.score_platform,
             gr.overall_score, gr.overall_class)

    # Phase 3 — Write reports
    log.info("[GVA-001] Phase 3: Writing reports...")
    files = write_all_reports(ev, gr, report_date)
    log.info("[GVA-001] Reports written to data/gva/%s/", report_date)
    for fname in files:
        log.info("[GVA-001]   %s", fname)

    # Build summary
    all_metrics = (gr.knowledge + gr.learning + gr.dna +
                   gr.scientific + gr.platform)
    improving  = sum(1 for m in all_metrics if m.direction == "IMPROVING")
    declining  = sum(1 for m in all_metrics if m.direction == "DECLINING")
    stable     = sum(1 for m in all_metrics if m.direction == "STABLE")

    return {
        "report_date":     report_date,
        "overall_score":   gr.overall_score,
        "classification":  gr.overall_class,
        "dimension_scores": {
            "knowledge":   gr.score_knowledge,
            "learning":    gr.score_learning,
            "dna":         gr.score_dna,
            "scientific":  gr.score_scientific,
            "platform":    gr.score_platform,
        },
        "metrics_total":   len(all_metrics),
        "improving":       improving,
        "stable":          stable,
        "declining":       declining,
        "evidence": {
            "studies":     len(ev.studies),
            "hypotheses":  ev.hypothesis.total,
            "dna_total":   ev.dna.total,
            "features":    ev.feature_count,
            "edges_total": ev.edges.total,
            "edges_active":ev.edges.active,
            "cycles":      ev.platform.total_cycles,
        },
        "files": files,
    }


def main():
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [GVA] %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="GVA-001 Growth Validator & Assessor")
    parser.add_argument("--date", default=None, help="Report date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    result = run_gva(args.date)
    print(json.dumps(result, default=str, indent=2))


if __name__ == "__main__":
    main()
