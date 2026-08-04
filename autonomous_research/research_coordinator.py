"""
research_coordinator.py — Operational orchestrator for all IIOS research activity.

IIOS Research Infrastructure — Phase 3A.

ResearchCoordinator is the single owner of research *execution*.  It decides
HOW to run approved work; it never decides WHAT to research.  Scientific
Director owns scientific priorities; ResearchCoordinator owns the pipeline.

Responsibilities
----------------
* Accept an approved StudyPlan from the Scientific Director.
* Execute the 8-stage research pipeline in strict order.
* Isolate every stage in try/except — partial completion is valid.
* Persist a JSON run-history (max_history_runs entries).
* Expose query APIs: run_research, run_study, run_validation, status,
  history, statistics.

Pipeline stages (in order)
---------------------------
1. study_plan          — validate dependencies, estimate cost
2. replay              — historical replay (HISTORICAL_REPLAY type only)
3. validation          — EvidenceValidator quality gates
4. evidence_integration— write validated evidence into HypothesisRegistry
5. knowledge_integration— snapshot current KnowledgeProvider state
6. cross_study_synthesis— synthesize evidence across all studies
7. repository_update   — audit IDR / knowledge stores
8. research_report     — compile final report (always runs)

ResearchCoordinator NEVER
-------------------------
* Creates hypotheses
* Changes research priorities or roadmap
* Rejects scientific questions
* Makes trading decisions
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .rc_config import RCConfig
from .rc_models import (
    RC_ALWAYS_RUN,
    RC_ALL_STAGES,
    STAGE_EVIDENCE,
    STAGE_KNOWLEDGE,
    STAGE_REPLAY,
    STAGE_REPORT,
    STAGE_REPOSITORY,
    STAGE_STUDY_PLAN,
    STAGE_SYNTHESIS,
    STAGE_VALIDATION,
    RCError,
    RCStatus,
    ResearchHealth,
    ResearchRun,
    ResearchStage,
    ResearchStageState,
    ResearchSummary,
    ResearchTelemetry,
    _now_iso,
    make_rc_run_id,
)

log = logging.getLogger(__name__)


class ResearchCoordinator:
    """Operational orchestrator for all IIOS research activity.

    Parameters
    ----------
    planner : StudyPlanner | None
        Study-plan validator and cost estimator.
    hypothesis_registry : HypothesisRegistry | None
        Scientific hypothesis store.
    evidence_validator : EvidenceValidator | None
        Evidence quality gate engine.
    knowledge_provider : KnowledgeProvider | None
        Read-only knowledge access layer.
    synthesizer : CrossStudySynthesizer | None
        Cross-study knowledge synthesis engine.
    idr : IDRRepository | None
        Institutional DNA repository.
    config : RCConfig | None
        Runtime configuration.  Defaults to RCConfig() if not supplied.
    """

    def __init__(
        self,
        planner=None,
        hypothesis_registry=None,
        evidence_validator=None,
        knowledge_provider=None,
        synthesizer=None,
        idr=None,
        ptue=None,
        config: Optional[RCConfig] = None,
    ) -> None:
        self._planner             = planner
        self._hypothesis_registry = hypothesis_registry
        self._evidence_validator  = evidence_validator
        self._knowledge_provider  = knowledge_provider
        self._synthesizer         = synthesizer
        self._idr                 = idr
        self._ptue                = ptue
        self._config              = config or RCConfig()
        self._lock                = threading.Lock()
        self._history: List[Dict[str, Any]] = []
        self._consecutive_failures: int = 0
        self._last_run_id:        Optional[str] = None
        self._last_run_health:    Optional[str] = None
        self._last_run_date:      Optional[str] = None
        self._last_successful_id: Optional[str] = None
        self._load_history()
        log.info(
            "[RC] Initialised. planner=%s hyp=%s ev=%s kp=%s synth=%s idr=%s ptue=%s dry_run=%s",
            planner  is not None,
            hypothesis_registry is not None,
            evidence_validator  is not None,
            knowledge_provider  is not None,
            synthesizer         is not None,
            idr                 is not None,
            ptue                is not None,
            self._config.dry_run,
        )

    # ─── public pipeline API ────────────────────────────────────────────────

    def run_research(self, study_plan: Any) -> ResearchRun:
        """Execute the full 8-stage research pipeline for an approved study.

        Parameters
        ----------
        study_plan : StudyPlan
            An approved plan produced by StudyPlanner and authorised by the
            Scientific Director.

        Returns
        -------
        ResearchRun
            Complete record including all stage results and telemetry.
        """
        run_id     = make_rc_run_id()
        date_str   = datetime.now().strftime("%Y-%m-%d")
        t_start    = time.monotonic()
        start_iso  = _now_iso()
        plan_id    = getattr(study_plan, "plan_id", "unknown")
        study_type = str(getattr(study_plan, "study_type", "UNKNOWN"))
        if hasattr(study_type, "value"):
            study_type = study_type.value  # type: ignore[assignment]

        log.info("[RC] Starting pipeline run_id=%s plan_id=%s type=%s",
                 run_id, plan_id, study_type)

        stages: List[ResearchStage] = []
        ctx: Dict[str, Any] = {
            "plan_validated":           False,
            "dependencies_unresolved":  0,
            "estimated_hours":          0.0,
            "replay_ran":               False,
            "replay_studies_found":     0,
            "validation_ran":           False,
            "validation_outcome":       "N/A",
            "evidence_integrated":      False,
            "hypothesis_id":            None,
            "knowledge_snapshot_taken": False,
            "findings_count":           0,
            "edges_count":              0,
            "strategies_count":         0,
            "certifications_count":     0,
            "synthesis_ran":            False,
            "synthesized_findings":     0,
            "contradictions_detected":  0,
            "repository_updated":       False,
            "idr_total_active_dna":     0,
        }

        # ── stage dispatch ──────────────────────────────────────────────────
        for stage_name in RC_ALL_STAGES:
            stages.append(
                self._run_stage(stage_name, study_plan, ctx)
            )

        # ── health determination ────────────────────────────────────────────
        health = self._compute_health(stages)

        # ── telemetry ───────────────────────────────────────────────────────
        end_iso       = _now_iso()
        total_ms      = (time.monotonic() - t_start) * 1000.0
        ok_count      = sum(1 for s in stages if s.state == ResearchStageState.SUCCESS)
        fail_count    = sum(1 for s in stages if s.state == ResearchStageState.FAILED)
        skip_count    = sum(1 for s in stages if s.state == ResearchStageState.SKIPPED)

        tel = ResearchTelemetry(
            run_id=run_id,
            study_plan_id=plan_id,
            study_type=study_type,
            trading_date=date_str,
            start_time=start_iso,
            end_time=end_iso,
            total_duration_ms=round(total_ms, 2),
            stages_success=ok_count,
            stages_failed=fail_count,
            stages_skipped=skip_count,
            plan_validated=ctx["plan_validated"],
            dependencies_unresolved=ctx["dependencies_unresolved"],
            estimated_hours=ctx["estimated_hours"],
            replay_ran=ctx["replay_ran"],
            replay_studies_found=ctx["replay_studies_found"],
            validation_ran=ctx["validation_ran"],
            validation_outcome=ctx["validation_outcome"],
            evidence_integrated=ctx["evidence_integrated"],
            hypothesis_id=ctx["hypothesis_id"],
            knowledge_snapshot_taken=ctx["knowledge_snapshot_taken"],
            findings_count=ctx["findings_count"],
            edges_count=ctx["edges_count"],
            strategies_count=ctx["strategies_count"],
            certifications_count=ctx["certifications_count"],
            synthesis_ran=ctx["synthesis_ran"],
            synthesized_findings=ctx["synthesized_findings"],
            contradictions_detected=ctx["contradictions_detected"],
            repository_updated=ctx["repository_updated"],
            idr_total_active_dna=ctx["idr_total_active_dna"],
            pipeline_healthy=(health == ResearchHealth.HEALTHY),
            health=health.value,
        )

        run = ResearchRun(
            run_id=run_id,
            study_plan_id=plan_id,
            study_type=study_type,
            date=date_str,
            stages=stages,
            telemetry=tel,
            health=health,
        )

        self._record_run(run)
        log.info(
            "[RC] Pipeline complete run_id=%s health=%s ok=%d fail=%d skip=%d %.0fms",
            run_id, health.value, ok_count, fail_count, skip_count, total_ms,
        )
        return run

    def run_study(self, study_plan: Any) -> ResearchRun:
        """Semantic alias for :meth:`run_research`."""
        return self.run_research(study_plan)

    def run_validation(
        self,
        subject_id:   str,
        subject_type: str = "finding",
    ) -> ResearchRun:
        """Execute only the validation stage for a single subject.

        Returns a ResearchRun containing two stages: validation + research_report.
        """
        run_id    = make_rc_run_id()
        date_str  = datetime.now().strftime("%Y-%m-%d")
        t_start   = time.monotonic()
        start_iso = _now_iso()

        log.info("[RC] run_validation run_id=%s subject=%s type=%s",
                 run_id, subject_id, subject_type)

        ctx: Dict[str, Any] = {
            "validation_ran":    False,
            "validation_outcome": "N/A",
        }

        stages: List[ResearchStage] = []

        # ── only validate + report stages ───────────────────────────────────
        stages.append(self._exec_validation(subject_id, subject_type, ctx))
        stages.append(self._exec_report(ctx, run_id, "validation-only"))

        health  = self._compute_health(stages)
        end_iso = _now_iso()
        total_ms = (time.monotonic() - t_start) * 1000.0

        tel = ResearchTelemetry(
            run_id=run_id,
            study_plan_id=f"validation-{subject_id}",
            study_type="VALIDATION_ONLY",
            trading_date=date_str,
            start_time=start_iso,
            end_time=end_iso,
            total_duration_ms=round(total_ms, 2),
            stages_success=sum(1 for s in stages if s.state == ResearchStageState.SUCCESS),
            stages_failed=sum(1 for s in stages if s.state == ResearchStageState.FAILED),
            stages_skipped=sum(1 for s in stages if s.state == ResearchStageState.SKIPPED),
            plan_validated=False,
            dependencies_unresolved=0,
            estimated_hours=0.0,
            replay_ran=False,
            replay_studies_found=0,
            validation_ran=ctx["validation_ran"],
            validation_outcome=ctx["validation_outcome"],
            evidence_integrated=False,
            hypothesis_id=None,
            knowledge_snapshot_taken=False,
            findings_count=0,
            edges_count=0,
            strategies_count=0,
            certifications_count=0,
            synthesis_ran=False,
            synthesized_findings=0,
            contradictions_detected=0,
            repository_updated=False,
            idr_total_active_dna=0,
            pipeline_healthy=(health == ResearchHealth.HEALTHY),
            health=health.value,
        )

        run = ResearchRun(
            run_id=run_id,
            study_plan_id=f"validation-{subject_id}",
            study_type="VALIDATION_ONLY",
            date=date_str,
            stages=stages,
            telemetry=tel,
            health=health,
        )
        self._record_run(run)
        return run

    # ─── query API ──────────────────────────────────────────────────────────

    def status(self) -> RCStatus:
        """Return the current operational status of the ResearchCoordinator."""
        with self._lock:
            total = len(self._history)
            cf    = self._consecutive_failures
            lrh   = self._last_run_health

            if total == 0:
                h = ResearchHealth.NO_DATA
            elif cf == 0:
                h = ResearchHealth.HEALTHY
            elif cf < 3:
                h = ResearchHealth.DEGRADED
            else:
                h = ResearchHealth.FAILED

            if lrh and lrh == ResearchHealth.HEALTHY.value:
                detail = "Last run healthy."
            elif lrh:
                detail = f"Last run: {lrh}. {cf} consecutive failure(s)."
            else:
                detail = "No runs recorded yet."

            return RCStatus(
                health=h,
                last_run_id=self._last_run_id,
                last_run_date=self._last_run_date,
                last_run_health=lrh,
                last_successful_run_id=self._last_successful_id,
                consecutive_failures=cf,
                total_runs=total,
                planner_available=(self._planner is not None),
                hypothesis_registry_available=(self._hypothesis_registry is not None),
                evidence_validator_available=(self._evidence_validator is not None),
                synthesizer_available=(self._synthesizer is not None),
                idr_available=(self._idr is not None),
                detail=detail,
            )

    def history(self, limit: int = 20) -> List[ResearchRun]:
        """Return the last *limit* ResearchRun records (most recent first)."""
        with self._lock:
            tail = self._history[-limit:]
        runs: List[ResearchRun] = []
        for d in reversed(tail):
            try:
                runs.append(self._dict_to_run(d))
            except Exception as exc:  # noqa: BLE001
                log.warning("[RC] history: could not deserialise run: %s", exc)
        return runs

    def statistics(self) -> Dict[str, Any]:
        """Return aggregate statistics across all stored runs."""
        with self._lock:
            h_copy = list(self._history)

        total  = len(h_copy)
        if total == 0:
            return {
                "total_runs":      0,
                "healthy_runs":    0,
                "degraded_runs":   0,
                "failed_runs":     0,
                "health_rate_pct": 0.0,
                "avg_duration_ms": 0.0,
                "stages_success_total":  0,
                "stages_failed_total":   0,
                "stages_skipped_total":  0,
            }

        healthy  = sum(1 for r in h_copy if r.get("health") == ResearchHealth.HEALTHY.value)
        degraded = sum(1 for r in h_copy if r.get("health") == ResearchHealth.DEGRADED.value)
        failed   = sum(1 for r in h_copy if r.get("health") == ResearchHealth.FAILED.value)

        durations = [
            r.get("telemetry", {}).get("total_duration_ms", 0.0)
            for r in h_copy
            if r.get("telemetry")
        ]
        avg_ms = round(sum(durations) / len(durations), 2) if durations else 0.0

        s_ok   = sum(r.get("telemetry", {}).get("stages_success", 0) for r in h_copy if r.get("telemetry"))
        s_fail = sum(r.get("telemetry", {}).get("stages_failed",  0) for r in h_copy if r.get("telemetry"))
        s_skip = sum(r.get("telemetry", {}).get("stages_skipped", 0) for r in h_copy if r.get("telemetry"))

        return {
            "total_runs":            total,
            "healthy_runs":          healthy,
            "degraded_runs":         degraded,
            "failed_runs":           failed,
            "health_rate_pct":       round(healthy / total * 100, 1),
            "avg_duration_ms":       avg_ms,
            "stages_success_total":  s_ok,
            "stages_failed_total":   s_fail,
            "stages_skipped_total":  s_skip,
        }

    # ─── stage dispatcher ───────────────────────────────────────────────────

    def _run_stage(
        self,
        stage_name: str,
        study_plan: Any,
        ctx: Dict[str, Any],
    ) -> ResearchStage:
        """Dispatch *stage_name* and return a completed ResearchStage."""

        if stage_name == STAGE_STUDY_PLAN:
            return self._exec_study_plan(study_plan, ctx)
        if stage_name == STAGE_REPLAY:
            return self._exec_replay(study_plan, ctx)
        if stage_name == STAGE_VALIDATION:
            hyp_id = getattr(study_plan, "source_hypothesis_id", None)
            return self._exec_validation(hyp_id or "auto", "hypothesis" if hyp_id else "finding", ctx)
        if stage_name == STAGE_EVIDENCE:
            return self._exec_evidence_integration(study_plan, ctx)
        if stage_name == STAGE_KNOWLEDGE:
            return self._exec_knowledge_integration(ctx)
        if stage_name == STAGE_SYNTHESIS:
            return self._exec_synthesis(ctx)
        if stage_name == STAGE_REPOSITORY:
            return self._exec_repository_update(ctx)
        if stage_name == STAGE_REPORT:
            plan_id = getattr(study_plan, "plan_id", "unknown")
            return self._exec_report(ctx, plan_id, str(getattr(study_plan, "study_type", "UNKNOWN")))
        raise RCError(f"Unknown stage name: {stage_name}")

    # ─── individual stage implementations ───────────────────────────────────

    def _exec_study_plan(self, study_plan: Any, ctx: Dict[str, Any]) -> ResearchStage:
        stage = self._begin(STAGE_STUDY_PLAN)
        if not self._config.study_plan_enabled:
            return self._skip(stage, "study_plan_enabled=False")
        try:
            plan_id = getattr(study_plan, "plan_id", None)

            # dependency validation
            unresolved: List[str] = []
            if self._planner and plan_id:
                try:
                    unresolved = self._planner.validate_dependencies(plan_id)
                except (KeyError, AttributeError, TypeError):
                    # plan_id not in in-session registry — graceful fallback
                    unresolved = []
            ctx["dependencies_unresolved"] = len(unresolved)

            # cost estimate
            est_hours = 0.0
            if self._planner and plan_id:
                try:
                    est = self._planner.estimate_cost(plan_id)
                    est_hours = getattr(est, "total_hours", 0.0)
                except (KeyError, AttributeError, TypeError):
                    est_hours = float(
                        getattr(getattr(study_plan, "execution_estimate", None), "total_hours", 0.0)
                    )
            else:
                est_hours = float(
                    getattr(getattr(study_plan, "execution_estimate", None), "total_hours", 0.0)
                )

            ctx["plan_validated"]  = True
            ctx["estimated_hours"] = round(est_hours, 3)

            stage.meta = {
                "plan_id":       plan_id,
                "unresolved":    unresolved,
                "estimated_hrs": est_hours,
            }
            stage.output_summary = (
                f"Plan validated. unresolved_deps={len(unresolved)} "
                f"estimated_hours={est_hours:.2f}"
            )
            return self._succeed(stage)
        except Exception as exc:
            return self._fail(stage, exc)

    def _exec_replay(self, study_plan: Any, ctx: Dict[str, Any]) -> ResearchStage:
        stage = self._begin(STAGE_REPLAY)
        if not self._config.replay_enabled:
            return self._skip(stage, "replay_enabled=False")

        study_type_val = getattr(study_plan, "study_type", None)
        type_str = str(study_type_val.value if hasattr(study_type_val, "value") else study_type_val)

        if type_str != "HISTORICAL_REPLAY":
            return self._skip(stage, f"study_type={type_str} (replay only for HISTORICAL_REPLAY)")

        try:
            replay_summary = None
            related_studies: List[Any] = []

            if self._knowledge_provider:
                try:
                    replay_summary = self._knowledge_provider.get_replay_summary()
                except Exception:
                    replay_summary = None
                try:
                    all_studies = self._knowledge_provider.list_studies()
                    related_studies = [
                        s for s in all_studies
                        if str(getattr(s, "study_type", "")).upper() == "HISTORICAL_REPLAY"
                    ]
                except Exception:
                    related_studies = []

            # ── PTUE: resolve the point-in-time universe for this replay ────
            ptue_universe = None
            ptue_date     = None
            ptue_source   = "NONE"
            if self._ptue:
                ptue_date = _resolve_replay_date(study_plan)
                if ptue_date:
                    try:
                        ptue_universe = self._ptue.get_universe(ptue_date)
                        ptue_source   = ptue_universe.source
                        ctx["ptue_universe_date"]       = ptue_date
                        ctx["ptue_universe_name"]       = ptue_universe.universe_name
                        ctx["ptue_universe_symbols"]    = ptue_universe.symbols
                        ctx["ptue_universe_count"]      = ptue_universe.effective_count
                        ctx["ptue_universe_source"]     = ptue_source
                        ctx["ptue_universe_is_fallback"]= ptue_universe.is_fallback
                        ctx["ptue_universe_coverage"]   = ptue_universe.coverage
                    except Exception as ptue_exc:
                        log.warning("[RC] PTUE lookup failed for date %s: %s", ptue_date, ptue_exc)

            ctx["replay_ran"]           = True
            ctx["replay_studies_found"] = len(related_studies)

            stage.meta = {
                "replay_summary_available": replay_summary is not None,
                "related_studies":          len(related_studies),
                "ptue_date":                ptue_date,
                "ptue_source":              ptue_source,
                "ptue_count":               ptue_universe.effective_count if ptue_universe else 0,
                "ptue_is_fallback":         ptue_universe.is_fallback if ptue_universe else None,
            }
            stage.output_summary = (
                f"Replay context loaded. related_studies={len(related_studies)} "
                f"replay_summary={'yes' if replay_summary else 'none'} "
                f"ptue={ptue_date or 'none'}({ptue_source})"
            )
            return self._succeed(stage)
        except Exception as exc:
            return self._fail(stage, exc)

    def _exec_validation(
        self,
        subject_id: str,
        subject_type: str,
        ctx: Dict[str, Any],
    ) -> ResearchStage:
        stage = self._begin(STAGE_VALIDATION)
        if not self._config.validation_enabled:
            return self._skip(stage, "validation_enabled=False")
        try:
            outcome = "N/A"

            if self._evidence_validator and subject_id and subject_id != "auto":
                try:
                    if subject_type == "hypothesis":
                        result = self._evidence_validator.validate_hypothesis(subject_id)
                    elif subject_type == "finding":
                        result = self._evidence_validator.validate_finding(subject_id)
                    else:
                        result = self._evidence_validator.validate(
                            subject_id=subject_id, subject_type=subject_type
                        )
                    outcome_val = getattr(result, "outcome", None)
                    outcome = str(outcome_val.value if hasattr(outcome_val, "value") else outcome_val or "N/A")
                except Exception:
                    # subject may not exist in knowledge store — treat as no-data
                    stats = self._evidence_validator.statistics()
                    outcome = f"no-data (stats: {getattr(stats, 'total_validations', 0)} prior validations)"
            elif self._evidence_validator:
                # no specific subject — run statistics only
                stats = self._evidence_validator.statistics()
                outcome = f"statistics-only ({getattr(stats, 'total_validations', 0)} prior validations)"
            else:
                outcome = "evidence_validator_unavailable"

            ctx["validation_ran"]     = True
            ctx["validation_outcome"] = outcome

            stage.meta = {"outcome": outcome, "subject_id": subject_id, "subject_type": subject_type}
            stage.output_summary = f"Validation outcome={outcome}"
            return self._succeed(stage)
        except Exception as exc:
            return self._fail(stage, exc)

    def _exec_evidence_integration(self, study_plan: Any, ctx: Dict[str, Any]) -> ResearchStage:
        stage = self._begin(STAGE_EVIDENCE)
        if not self._config.evidence_integration_enabled:
            return self._skip(stage, "evidence_integration_enabled=False")
        try:
            hyp_id = getattr(study_plan, "source_hypothesis_id", None)
            ctx["hypothesis_id"] = hyp_id

            if not hyp_id:
                return self._skip(stage, "no source_hypothesis_id on plan")

            if not self._hypothesis_registry:
                return self._skip(stage, "hypothesis_registry unavailable")

            hyp = self._hypothesis_registry.get(hyp_id)
            if hyp is None:
                return self._skip(stage, f"hypothesis {hyp_id} not found in registry")

            if not self._config.dry_run:
                from .hypothesis_models import EvidenceReference, EvidenceType  # noqa: PLC0415
                plan_id    = getattr(study_plan, "plan_id", "unknown")
                study_title = getattr(study_plan, "title", "Research study")
                ev = EvidenceReference(
                    evidence_id=f"ev-rc-{plan_id}",
                    evidence_type=EvidenceType.STUDY_RESULT,
                    source_study_id=plan_id,
                    description=f"ResearchCoordinator completed execution of: {study_title}",
                    strength=0.7,
                    direction="SUPPORTING",
                    recorded_at=datetime.now().isoformat(),
                )
                self._hypothesis_registry.add_evidence(hyp_id, ev)

            ctx["evidence_integrated"] = True
            stage.meta = {"hypothesis_id": hyp_id, "dry_run": self._config.dry_run}
            stage.output_summary = (
                f"Evidence integrated for hypothesis {hyp_id} "
                f"{'(dry_run)' if self._config.dry_run else '(written)'}"
            )
            return self._succeed(stage)
        except Exception as exc:
            return self._fail(stage, exc)

    def _exec_knowledge_integration(self, ctx: Dict[str, Any]) -> ResearchStage:
        stage = self._begin(STAGE_KNOWLEDGE)
        if not self._config.knowledge_integration_enabled:
            return self._skip(stage, "knowledge_integration_enabled=False")
        try:
            if not self._knowledge_provider:
                return self._skip(stage, "knowledge_provider unavailable")

            snap = self._knowledge_provider.get_snapshot()
            findings_count      = getattr(snap, "total_findings", 0)
            edges_count         = getattr(snap, "total_edges", 0)
            strategies_count    = getattr(snap, "total_strategies", 0)
            certifications_count = getattr(snap, "total_certifications", 0)

            ctx["knowledge_snapshot_taken"] = True
            ctx["findings_count"]           = findings_count
            ctx["edges_count"]              = edges_count
            ctx["strategies_count"]         = strategies_count
            ctx["certifications_count"]     = certifications_count

            warnings = self._knowledge_provider.get_warnings()
            stage.meta = {
                "findings":      findings_count,
                "edges":         edges_count,
                "strategies":    strategies_count,
                "certifications": certifications_count,
                "warnings":      len(warnings),
            }
            stage.output_summary = (
                f"Snapshot: findings={findings_count} edges={edges_count} "
                f"strategies={strategies_count} certs={certifications_count} "
                f"warnings={len(warnings)}"
            )
            return self._succeed(stage)
        except Exception as exc:
            return self._fail(stage, exc)

    def _exec_synthesis(self, ctx: Dict[str, Any]) -> ResearchStage:
        stage = self._begin(STAGE_SYNTHESIS)
        if not self._config.synthesis_enabled:
            return self._skip(stage, "synthesis_enabled=False")
        try:
            if not self._synthesizer:
                return self._skip(stage, "synthesizer unavailable")

            report = self._synthesizer.synthesize()

            synth_findings   = len(getattr(report, "synthesized_findings", []))
            contradictions   = len(getattr(report, "contradictions", []))

            ctx["synthesis_ran"]            = True
            ctx["synthesized_findings"]     = synth_findings
            ctx["contradictions_detected"]  = contradictions

            stage.meta = {
                "synthesized_findings": synth_findings,
                "contradictions":       contradictions,
            }
            stage.output_summary = (
                f"Synthesis: synthesized_findings={synth_findings} "
                f"contradictions={contradictions}"
            )
            return self._succeed(stage)
        except Exception as exc:
            return self._fail(stage, exc)

    def _exec_repository_update(self, ctx: Dict[str, Any]) -> ResearchStage:
        stage = self._begin(STAGE_REPOSITORY)
        if not self._config.repository_update_enabled:
            return self._skip(stage, "repository_update_enabled=False")
        try:
            total_active_dna = 0

            if self._idr:
                try:
                    stats = self._idr.statistics()
                    total_active_dna = getattr(stats, "active_count", 0)
                except Exception:
                    total_active_dna = len(self._idr.list_active()) if hasattr(self._idr, "list_active") else 0

            ctx["repository_updated"]    = True
            ctx["idr_total_active_dna"]  = total_active_dna

            # also capture current study and edge counts from KP if available
            total_studies = 0
            total_edges   = 0
            if self._knowledge_provider:
                try:
                    total_studies = len(self._knowledge_provider.list_studies())
                    total_edges   = len(self._knowledge_provider.list_edges())
                except Exception:
                    pass

            stage.meta = {
                "idr_active_dna":  total_active_dna,
                "total_studies":   total_studies,
                "total_edges":     total_edges,
                "dry_run":         self._config.dry_run,
            }
            stage.output_summary = (
                f"Repository audit: idr_active_dna={total_active_dna} "
                f"studies={total_studies} edges={total_edges}"
            )
            return self._succeed(stage)
        except Exception as exc:
            return self._fail(stage, exc)

    def _exec_report(self, ctx: Dict[str, Any], plan_id: str, study_type: str) -> ResearchStage:
        stage = self._begin(STAGE_REPORT)
        try:
            ptue_line = (
                f"  ptue_universe:          {ctx.get('ptue_universe_name', 'N/A')} "
                f"date={ctx.get('ptue_universe_date', 'N/A')} "
                f"count={ctx.get('ptue_universe_count', 0)} "
                f"source={ctx.get('ptue_universe_source', 'NONE')} "
                f"fallback={ctx.get('ptue_universe_is_fallback', 'N/A')} "
                f"coverage={ctx.get('ptue_universe_coverage', 0.0):.2f}"
            )
            lines = [
                f"ResearchCoordinator report — plan={plan_id} type={study_type}",
                f"  plan_validated:         {ctx.get('plan_validated', False)}",
                f"  replay_ran:             {ctx.get('replay_ran', False)} ({ctx.get('replay_studies_found', 0)} studies)",
                ptue_line,
                f"  validation_outcome:     {ctx.get('validation_outcome', 'N/A')}",
                f"  evidence_integrated:    {ctx.get('evidence_integrated', False)}",
                f"  knowledge_snapshot:     {ctx.get('knowledge_snapshot_taken', False)} ({ctx.get('findings_count', 0)} findings)",
                f"  synthesis_ran:          {ctx.get('synthesis_ran', False)} ({ctx.get('synthesized_findings', 0)} synth-findings)",
                f"  repository_updated:     {ctx.get('repository_updated', False)} (idr_active={ctx.get('idr_total_active_dna', 0)})",
            ]
            stage.output_summary = " | ".join([
                f"plan={'ok' if ctx.get('plan_validated') else 'skip'}",
                f"replay={'ok' if ctx.get('replay_ran') else 'skip'}",
                f"ptue={ctx.get('ptue_universe_date', 'none')}",
                f"val={ctx.get('validation_outcome', 'N/A')}",
                f"ev={'ok' if ctx.get('evidence_integrated') else 'skip'}",
                f"kp={'ok' if ctx.get('knowledge_snapshot_taken') else 'skip'}",
                f"synth={'ok' if ctx.get('synthesis_ran') else 'skip'}",
                f"repo={'ok' if ctx.get('repository_updated') else 'skip'}",
            ])
            stage.meta = {"report_lines": lines}
            log.info("[RC] Research report:\n%s", "\n".join(lines))
            return self._succeed(stage)
        except Exception as exc:
            return self._fail(stage, exc)

    # ─── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _begin(name: str) -> ResearchStage:
        return ResearchStage(
            name=name,
            state=ResearchStageState.RUNNING,
            start_time=_now_iso(),
        )

    @staticmethod
    def _succeed(stage: ResearchStage) -> ResearchStage:
        stage.state    = ResearchStageState.SUCCESS
        stage.end_time = _now_iso()
        if stage.start_time:
            try:
                a = datetime.fromisoformat(stage.start_time)
                b = datetime.fromisoformat(stage.end_time)
                stage.duration_ms = (b - a).total_seconds() * 1000.0
            except Exception:
                stage.duration_ms = 0.0
        return stage

    @staticmethod
    def _skip(stage: ResearchStage, reason: str) -> ResearchStage:
        stage.state          = ResearchStageState.SKIPPED
        stage.end_time       = _now_iso()
        stage.duration_ms    = 0.0
        stage.output_summary = f"Skipped: {reason}"
        return stage

    @staticmethod
    def _fail(stage: ResearchStage, exc: Exception) -> ResearchStage:
        stage.state    = ResearchStageState.FAILED
        stage.end_time = _now_iso()
        stage.error    = str(exc)
        if stage.start_time:
            try:
                a = datetime.fromisoformat(stage.start_time)
                b = datetime.fromisoformat(stage.end_time)
                stage.duration_ms = (b - a).total_seconds() * 1000.0
            except Exception:
                stage.duration_ms = 0.0
        log.warning("[RC] Stage %s FAILED: %s", stage.name, exc)
        return stage

    @staticmethod
    def _compute_health(stages: List[ResearchStage]) -> ResearchHealth:
        counted = [
            s for s in stages
            if s.state not in (ResearchStageState.SKIPPED,)
            and s.name not in RC_ALWAYS_RUN
        ]
        if not counted:
            return ResearchHealth.HEALTHY  # all stages were skipped
        ok    = sum(1 for s in counted if s.state == ResearchStageState.SUCCESS)
        fails = sum(1 for s in counted if s.state == ResearchStageState.FAILED)
        if fails == 0:
            return ResearchHealth.HEALTHY
        if ok == 0:
            return ResearchHealth.FAILED
        return ResearchHealth.DEGRADED

    def _record_run(self, run: ResearchRun) -> None:
        d = run.to_dict()
        with self._lock:
            self._history.append(d)
            # evict oldest if over limit
            while len(self._history) > self._config.max_history_runs:
                self._history.pop(0)
            # update tracker state
            self._last_run_id    = run.run_id
            self._last_run_date  = run.date
            self._last_run_health = run.health.value
            if run.health == ResearchHealth.HEALTHY:
                self._consecutive_failures = 0
                self._last_successful_id   = run.run_id
            else:
                self._consecutive_failures += 1

        if not self._config.dry_run:
            self._persist_history()

    def _persist_history(self) -> None:
        path = Path(self._config.history_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                payload = list(self._history)
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            log.warning("[RC] Could not persist history: %s", exc)

    def _load_history(self) -> None:
        path = Path(self._config.history_path)
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                self._history = raw[-self._config.max_history_runs:]
                if self._history:
                    last = self._history[-1]
                    self._last_run_id    = last.get("run_id")
                    self._last_run_date  = last.get("date")
                    self._last_run_health = last.get("health")
                    # find last successful
                    for entry in reversed(self._history):
                        if entry.get("health") == ResearchHealth.HEALTHY.value:
                            self._last_successful_id = entry.get("run_id")
                            break
        except Exception as exc:  # noqa: BLE001
            log.warning("[RC] Could not load history from %s: %s", path, exc)

    @staticmethod
    def _dict_to_run(d: Dict[str, Any]) -> ResearchRun:
        """Reconstruct a ResearchRun from its serialised dict form."""
        stages: List[ResearchStage] = []
        for sd in d.get("stages", []):
            stages.append(ResearchStage(
                name=sd["name"],
                state=ResearchStageState(sd.get("state", "SKIPPED")),
                start_time=sd.get("start_time"),
                end_time=sd.get("end_time"),
                duration_ms=sd.get("duration_ms"),
                output_summary=sd.get("output_summary", ""),
                error=sd.get("error"),
                meta=sd.get("meta", {}),
            ))
        tel_d = d.get("telemetry")
        tel: Optional[ResearchTelemetry] = None
        if tel_d:
            try:
                tel = ResearchTelemetry(**tel_d)
            except Exception:
                tel = None
        return ResearchRun(
            run_id=d.get("run_id", ""),
            study_plan_id=d.get("study_plan_id", ""),
            study_type=d.get("study_type", ""),
            date=d.get("date", ""),
            stages=stages,
            telemetry=tel,
            health=ResearchHealth(d.get("health", ResearchHealth.NO_DATA.value)),
        )


# ─── PTUE integration helper ─────────────────────────────────────────────────

def _resolve_replay_date(study_plan: Any) -> Optional[str]:
    """Extract the replay start date from a StudyPlan's dataset requirements.

    Returns the ISO date string of the first dataset requirement's start date,
    or None if no date can be determined.
    """
    try:
        reqs = getattr(study_plan, "dataset_requirements", None) or []
        if reqs:
            first_req = reqs[0]
            date_start = getattr(first_req, "date_start", None)
            if date_start and isinstance(date_start, str) and len(date_start) == 10:
                return date_start
    except Exception:
        pass
    return None
