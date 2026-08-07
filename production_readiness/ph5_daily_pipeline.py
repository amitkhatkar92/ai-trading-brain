"""
production_readiness/ph5_daily_pipeline.py — Phase 5: Daily Automatic ILC Pipeline.

Runs the complete post-market learning pipeline after each market close.
Each stage is failure-isolated: one stage failing never stops the rest.
Pipeline: PGA → ILC → GVA → SD Review → Verification → Reports

Called from orchestrator._do_eod_learning() — replaces the individual
try/except wrappers that exist there today.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from .prr_config import PIPELINE_CONTINUE_ON_FAILURE, PIPELINE_TIMEOUT_EACH_S
from .prr_models import DailyPipelineResult, PipelineStageResult

log = logging.getLogger(__name__)


def _run_stage(
    name: str,
    fn,
    timeout_s: float = PIPELINE_TIMEOUT_EACH_S,
) -> PipelineStageResult:
    """Run a pipeline stage function with timing and exception isolation."""
    t0 = time.monotonic()
    try:
        output = fn()
        elapsed = time.monotonic() - t0
        log.info("[DailyPipeline] Stage %-16s COMPLETE in %.1fs", name, elapsed)
        return PipelineStageResult(
            stage=name,
            success=True,
            elapsed_seconds=round(elapsed, 2),
            output=output if isinstance(output, dict) else {"result": str(output)},
        )
    except Exception as e:
        elapsed = time.monotonic() - t0
        log.warning("[DailyPipeline] Stage %-16s FAILED in %.1fs: %s", name, elapsed, e)
        return PipelineStageResult(
            stage=name,
            success=False,
            elapsed_seconds=round(elapsed, 2),
            error=str(e),
        )


def run_daily_pipeline(
    report_date: Optional[str] = None,
    dry_run: bool = False,
) -> DailyPipelineResult:
    """
    Execute the full post-market learning pipeline.
    Returns DailyPipelineResult with per-stage outcomes.
    Failure of any stage is logged as WARNING but never raises.
    """
    today = report_date or datetime.now().date().isoformat()
    t_total = time.monotonic()
    log.info("[DailyPipeline] ── Starting daily pipeline for %s (dry_run=%s) ──", today, dry_run)

    # ── Stage 1: PGA (Predictive Gap Analysis) ────────────────────────────────
    def _pga():
        from predictive_gap.pga_collector import run_pga
        result = run_pga(report_date=today, dry_run=dry_run)
        return result if isinstance(result, dict) else {"status": "ok", "result": str(result)}

    pga_result = _run_stage("PGA", _pga)

    # ── Stage 2: ILC (Institutional Learning Cycle) ────────────────────────────
    def _ilc():
        from institutional_learning.ilc_runner import run_ilc
        return run_ilc(report_date=today, dry_run=dry_run)

    ilc_result = _run_stage("ILC", _ilc)

    # ── Stage 3: GVA (Growth Validator AI) ────────────────────────────────────
    def _gva():
        try:
            from growth_validator.gva_runner import run_gva
            return run_gva(report_date=today, dry_run=dry_run)
        except ImportError:
            # If gva_runner doesn't have a standalone run function, call directly
            from growth_validator.growth_validator_ai import GrowthValidatorAI
            gva = GrowthValidatorAI()
            result = gva.run_daily_validation()
            return {"status": "ok", "result": str(result)}

    gva_result = _run_stage("GVA", _gva)

    # ── Stage 4: Scientific Director daily review ─────────────────────────────
    def _sd():
        from autonomous_research.scientific_director import ScientificDirector
        sd = ScientificDirector()
        review = sd.daily_review()
        return {
            "review_id":       getattr(review, "review_id", "?"),
            "research_health": str(getattr(review, "research_health", "?")),
            "active_studies":  getattr(review, "active_studies", 0),
            "status":          "ok",
        }

    sd_result = _run_stage("SD_Review", _sd)

    # ── Stage 5: ILC Verification pass ────────────────────────────────────────
    def _verify():
        from institutional_learning.ilc_verification import run_verification_pass
        results = run_verification_pass(today=today, dry_run=dry_run)
        improved = sum(1 for r in results if getattr(r, "verdict", "") == "IMPROVED")
        declined = sum(1 for r in results if getattr(r, "verdict", "") == "DECLINED")
        return {"total_verified": len(results), "improved": improved, "declined": declined}

    verify_result = _run_stage("ILC_Verify", _verify)

    # ── Stage 6: PRR reports ───────────────────────────────────────────────────
    def _reports():
        from .prr_reporter import write_all_reports as _write
        from .prr_runner import _collect_prr_data
        data = _collect_prr_data(today)
        _write(data, today=today)
        return {"status": "written", "date": today}

    reports_result = _run_stage("PRR_Reports", _reports)

    # ── Summary ───────────────────────────────────────────────────────────────
    total_elapsed = time.monotonic() - t_total
    stages_done   = sum(1 for s in [pga_result, ilc_result, gva_result, sd_result, verify_result, reports_result] if s.success)
    stages_failed = 6 - stages_done

    result = DailyPipelineResult(
        date=today,
        total_elapsed_seconds=round(total_elapsed, 2),
        stages_completed=stages_done,
        stages_failed=stages_failed,
        pga=pga_result,
        ilc=ilc_result,
        gva=gva_result,
        sd_review=sd_result,
        verification=verify_result,
        reports=reports_result,
    )

    log.info(
        "[DailyPipeline] ── Complete: %d/%d stages OK in %.1fs ──",
        stages_done, 6, total_elapsed,
    )
    if stages_failed > 0:
        failed_names = [s.stage for s in [pga_result, ilc_result, gva_result, sd_result, verify_result, reports_result] if not s.success]
        log.warning("[DailyPipeline] Failed stages: %s", ", ".join(failed_names))

    return result
