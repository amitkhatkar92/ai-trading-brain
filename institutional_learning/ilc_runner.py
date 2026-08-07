"""
institutional_learning/ilc_runner.py — ILC-001 Main Orchestrator + CLI.

Usage:
    python -m institutional_learning.ilc_runner [--date YYYY-MM-DD] [--dry-run] [--json]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)


def run_ilc(
    report_date: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Run the full Institutional Learning Cycle.

    Phase 1  : audit_market_opportunities (top-20 gainers + losers)
    Phase 2-4: run_pga(top_n=20)  — collector, analyzer, root cause
    Phase 5  : score_all_actions   — confidence scoring
    Phase 6  : prioritize_actions  — EIG priority ranking
    Phase 7  : execute_actions     — reuse pga_learning (auto-execute B/C)
    Phase 8  : register + verify   — persistent learning registry
    Phase 9  : compute ROI
    Phase 10 : update lifecycle
    Phase 11 : ILS score
    Phase 12 : write 12 reports

    Returns a dict with all key metrics (suitable for orchestrator logging).
    """
    t0    = time.monotonic()
    today = report_date or date.today().isoformat()

    # ── Phase 0: Directories ────────────────────────────────────────────────
    from .ilc_config import ILC_DIR
    report_dir = ILC_DIR / today
    report_dir.mkdir(parents=True, exist_ok=True)

    log.info("[ILC-001] Starting cycle for %s (dry_run=%s)", today, dry_run)

    # ── Phase 1: Audit top-20 gainers + losers ──────────────────────────────
    log.info("[ILC] Phase 1: Market opportunity audit")
    from .ilc_market_audit import audit_market_opportunities

    # We'll populate gainers/losers moves after PGA runs; start with empty
    # and pass actual moves after Phase 2 (PGA collector)
    opportunities_pre: list = []   # filled in after PGA

    # ── Phase 2-4: PGA pipeline with ILC_TOP_N=20 ──────────────────────────
    log.info("[ILC] Phase 2-4: PGA pipeline (top_n=20)")
    from predictive_gap.pga_collector import collect_daily
    from predictive_gap.pga_analyzer  import analyze_universe
    from predictive_gap.pga_root_cause import analyze_misses
    from predictive_gap.pga_learning  import plan_actions, execute_actions
    from predictive_gap.pga_config    import PGAConfig

    cfg = PGAConfig(
        top_n=20,   # ILC uses top 20 vs PGA's default 5
        dry_run=dry_run,
        max_symbols_for_price_fetch=100,
    )

    try:
        data     = collect_daily(today, cfg)
        analyses = analyze_universe(data, cfg)
        causes   = analyze_misses(analyses, data, cfg)
        actions  = plan_actions(causes, analyses, data, cfg, today)
        if not dry_run:
            actions = execute_actions(actions, cfg, report_dir)
    except Exception as exc:
        log.error("[ILC] PGA pipeline failed: %s", exc, exc_info=True)
        data, analyses, causes, actions = None, [], [], []

    # Phase 1 (continued) — now we have price data for the audit
    log.info("[ILC] Phase 1 (continued): classifying universe status")
    if data is not None:
        pga_syms = {a.symbol for a in analyses}
        try:
            opportunities_pre = audit_market_opportunities(
                today, data.gainers, data.losers, pga_syms,
            )
        except Exception as exc:
            log.warning("[ILC] Market audit failed: %s", exc)
            opportunities_pre = []

    opportunities = opportunities_pre

    # ── Phase 5: Confidence scoring ─────────────────────────────────────────
    log.info("[ILC] Phase 5: Confidence scoring")
    from .ilc_confidence import score_all_actions
    confidences = score_all_actions(actions, analyses, causes)

    # ── Phase 6: EIG priority ───────────────────────────────────────────────
    log.info("[ILC] Phase 6: EIG priority ranking")
    from .ilc_priority import prioritize_actions
    eig_results = prioritize_actions(actions, confidences, analyses, causes)

    # ── Phase 7: already done inside plan/execute above ─────────────────────

    # ── Phase 8: Register new actions + run verification pass ───────────────
    log.info("[ILC] Phase 8: Learning registry + verification")
    from .ilc_verification import (
        register_learning_actions,
        run_verification_pass,
        get_all_records,
    )
    new_records    = register_learning_actions(actions, confidences, eig_results, today, dry_run)
    verified_today = run_verification_pass(today, dry_run)
    all_records    = get_all_records()

    n_improved  = sum(1 for v in verified_today if v.verdict == "IMPROVED")
    n_no_change = sum(1 for v in verified_today if v.verdict == "NO_CHANGE")
    n_declined  = sum(1 for v in verified_today if v.verdict == "DECLINED")

    # ── Phase 9: ROI ─────────────────────────────────────────────────────────
    log.info("[ILC] Phase 9: ROI calculation")
    from .ilc_roi import compute_all_roi
    roi_records = compute_all_roi(all_records)

    # ── Phase 10: Lifecycle ──────────────────────────────────────────────────
    log.info("[ILC] Phase 10: Knowledge lifecycle update")
    from .ilc_lifecycle import update_lifecycle
    lifecycle_records = update_lifecycle(verified_today, today, dry_run)

    # ── Phase 11: ILS score ──────────────────────────────────────────────────
    log.info("[ILC] Phase 11: ILS score")
    from .ilc_score import compute_ils_score

    # Try to get GVA score for research productivity component
    gva_score = 50.0
    try:
        from growth_validator.gva_runner import run_gva
        _gva = run_gva(report_date=today)
        gva_score = float(_gva.get("overall_score", 50.0))
    except Exception as gva_exc:
        log.debug("[ILC] GVA unavailable: %s", gva_exc)

    ils = compute_ils_score(
        learning_records=all_records,
        verified_results=verified_today,
        lifecycle_records=lifecycle_records,
        roi_records=roi_records,
        gva_score=gva_score,
    )

    # ── Phase 12: Write 12 reports ───────────────────────────────────────────
    log.info("[ILC] Phase 12: Writing 12 reports → %s", report_dir)
    from .ilc_reporter import write_all_reports
    write_all_reports(
        opportunities=opportunities,
        analyses=analyses,
        causes=causes,
        actions=actions,
        confidences=confidences,
        eig_results=eig_results,
        new_records=new_records,
        verified_today=verified_today,
        all_records=all_records,
        lifecycle_records=lifecycle_records,
        roi_records=roi_records,
        ils=ils,
        report_dir=report_dir,
        today=today,
    )

    elapsed = time.monotonic() - t0

    # ── Assemble result dict ─────────────────────────────────────────────────
    n_inside   = sum(1 for o in opportunities if o.universe_status == "INSIDE")
    n_by_design= sum(1 for o in opportunities if o.universe_status == "OUTSIDE_BY_DESIGN")
    n_unexp    = sum(1 for o in opportunities if o.universe_status == "OUTSIDE_UNEXPECTED")
    n_missed_w = sum(1 for a in analyses if getattr(a, "miss_type", "") == "MISSED_WINNER")
    n_missed_l = sum(1 for a in analyses if getattr(a, "miss_type", "") == "MISSED_LOSER")
    n_exec     = sum(1 for a in actions if getattr(a, "scheduled", False))
    top_eig    = eig_results[0].description if eig_results else ""
    roi_pos_pct= (
        100 * sum(1 for r in roi_records if r.roi_score > 0) / max(len(roi_records), 1)
    )
    conf_high  = confidences.count("HIGH")
    conf_med   = confidences.count("MEDIUM")
    conf_low   = confidences.count("LOW")
    conf_exp   = confidences.count("EXPERIMENTAL")

    result = {
        "date":                     today,
        "status":                   "OK",
        "n_opportunities":          len(opportunities),
        "n_inside_universe":        n_inside,
        "n_outside_by_design":      n_by_design,
        "n_outside_unexpected":     n_unexp,
        "n_analyses":               len(analyses),
        "n_missed_winners":         n_missed_w,
        "n_missed_losers":          n_missed_l,
        "n_root_causes":            len(causes),
        "n_actions":                len(actions),
        "n_actions_executed":       n_exec,
        "n_verified_today":         len(verified_today),
        "n_improved":               n_improved,
        "n_no_change":              n_no_change,
        "n_declined":               n_declined,
        "learning_score":           ils.overall_score,
        "grade":                    ils.grade,
        "report_dir":               str(report_dir),
        "elapsed_seconds":          round(elapsed, 1),
        "high_confidence_actions":  conf_high,
        "medium_confidence_actions":conf_med,
        "low_confidence_actions":   conf_low,
        "experimental_actions":     conf_exp,
        "top_eig_action":           top_eig,
        "verification_records_total": len(all_records),
        "roi_positive_pct":         round(roi_pos_pct, 1),
    }

    log.info(
        "[ILC-001] Cycle complete in %.1fs: score=%.1f/100 (%s) "
        "actions=%d verified=%d improved=%d",
        elapsed, ils.overall_score, ils.grade,
        len(actions), len(verified_today), n_improved,
    )
    return result


# ── CLI ──────────────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main() -> None:
    _setup_logging()

    parser = argparse.ArgumentParser(description="ILC-001 Institutional Learning Cycle")
    parser.add_argument("--date",    metavar="YYYY-MM-DD", help="Report date (default: today)")
    parser.add_argument("--dry-run", action="store_true",  help="Run without writing to registry")
    parser.add_argument("--json",    action="store_true",  help="Output result as JSON")
    args = parser.parse_args()

    result = run_ilc(report_date=args.date, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  ILC-001 Institutional Learning Cycle — {result['date']}")
    print(sep)
    print(f"  ILS Score  : {result['learning_score']:.1f}/100  [{result['grade']}]")
    print(f"  Elapsed    : {result['elapsed_seconds']}s")
    print(f"  Stocks     : {result['n_opportunities']} audited  "
          f"({result['n_inside_universe']} inside  {result['n_outside_unexpected']} unexpected gaps)")
    print(f"  PGA        : {result['n_analyses']} analyses  "
          f"{result['n_missed_winners']} missed winners  {result['n_missed_losers']} missed losers")
    print(f"  Actions    : {result['n_actions']} total  "
          f"(H={result['high_confidence_actions']} M={result['medium_confidence_actions']} "
          f"L={result['low_confidence_actions']} E={result['experimental_actions']})")
    print(f"  Verified   : {result['n_verified_today']} today  "
          f"IMPROVED={result['n_improved']}  DECLINED={result['n_declined']}")
    print(f"  ROI+       : {result['roi_positive_pct']:.0f}%  "
          f"Registry={result['verification_records_total']} total records")
    print(f"  Reports    : {result['report_dir']}")
    if result.get("top_eig_action"):
        print(f"  Top Action : {result['top_eig_action'][:70]}")
    print(sep)


if __name__ == "__main__":
    main()
