"""
production_readiness/ph5_daily_pipeline.py — Phase 5: Daily Automatic ILC Pipeline.

run_daily_pipeline() runs the complete post-market learning pipeline
(PGA -> ILC -> GVA -> SD Review -> Verification -> Reports) as one
standalone, failure-isolated sequence. It is NOT called from
orchestrator._do_eod_learning() -- that method already calls PGA and ILC
directly as its own individual try/except blocks (confirmed via grep), so
calling run_daily_pipeline() there too would duplicate execution of both.
Kept as a standalone/manual utility (e.g. CLI, future out-of-band use).

build_pipeline_result_from_live_stages() (below) is the safe integration
point actually used by the live orchestrator: it wraps the orchestrator's
OWN already-executed PGA/ILC result dicts into a DailyPipelineResult
without re-running anything, so production_readiness/ph9_certification.py's
Daily_ILC_Operational check can see a real signal instead of always None.
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


def build_pipeline_result_from_live_stages(
    pga_result: Optional[Dict[str, Any]] = None,
    ilc_result: Optional[Dict[str, Any]] = None,
    report_date: Optional[str] = None,
) -> DailyPipelineResult:
    """
    Build a DailyPipelineResult from the orchestrator's OWN already-executed
    PGA/ILC results (predictive_gap.pga_runner.run_pga() /
    institutional_learning.ilc_runner.run_ilc() output dicts) -- never
    re-runs anything.

    GVA/SD_review/verification/reports stages are left None: confirmed via
    grep that master_orchestrator.py never calls them today, so
    representing them as "ran" would be dishonest. None accurately means
    "not attempted this cycle" (matches DailyPipelineResult's own
    Optional[...] = None fields).

    A stage dict is considered successful if it exists and its "status"
    field (if present) is "OK" -- both run_pga()/run_ilc()'s real return
    shape. Absence of the stage dict (None) means that stage either wasn't
    reached this cycle or raised inside its own try/except upstream.
    """
    today = report_date or datetime.now().date().isoformat()

    def _stage(name: str, result: Optional[Dict[str, Any]]) -> Optional[PipelineStageResult]:
        if result is None:
            return None
        ok = str(result.get("status", "OK")).upper() == "OK"
        return PipelineStageResult(
            stage=name,
            success=ok,
            elapsed_seconds=0.0,
            output=result if isinstance(result, dict) else {},
            error="" if ok else str(result.get("status", "UNKNOWN")),
        )

    pga_stage = _stage("PGA", pga_result)
    ilc_stage = _stage("ILC", ilc_result)
    attempted = [s for s in (pga_stage, ilc_stage) if s is not None]

    return DailyPipelineResult(
        date=today,
        total_elapsed_seconds=0.0,
        stages_completed=sum(1 for s in attempted if s.success),
        stages_failed=sum(1 for s in attempted if not s.success),
        pga=pga_stage,
        ilc=ilc_stage,
    )

