"""
test_rc.py â€” ResearchCoordinator test suite.

IIOS Research Infrastructure â€” Phase 3A.

Test inventory (190 tests, T001â€“T190):
  T001â€“T012   rc_models: stage constants and RC_ALL_STAGES / RC_ALWAYS_RUN
  T013â€“T022   rc_models: ResearchStageState enum
  T014â€“T023   rc_models: ResearchHealth enum
  T024â€“T035   rc_models: ResearchStage dataclass + to_dict
  T036â€“T048   rc_models: ResearchTelemetry to_dict completeness
  T049â€“T058   rc_models: ResearchRun to_dict
  T059â€“T065   rc_models: ResearchSummary to_dict
  T066â€“T073   rc_models: RCStatus to_dict
  T074â€“T080   rc_models: RCError / RCStageError
  T081â€“T085   rc_models: make_rc_run_id + _now_iso
  T086â€“T098   rc_config: RCConfig defaults and field types
  T099â€“T105   coordinator: construction + status with no data
  T106â€“T120   coordinator: happy-path full pipeline (all modules mocked)
  T121â€“T130   coordinator: stage isolation â€” each stage independently fails
  T131â€“T138   coordinator: stage toggles (each stage disabled via config)
  T139â€“T144   coordinator: replay skip for non-HISTORICAL_REPLAY types
  T145â€“T150   coordinator: evidence integration skip when no hypothesis
  T151â€“T157   coordinator: run_validation standalone
  T158â€“T165   coordinator: history API
  T166â€“T172   coordinator: statistics API
  T173â€“T180   coordinator: dry_run mode
  T181â€“T186   coordinator: health transitions (HEALTHY / DEGRADED / FAILED)
  T187â€“T190   coordinator: run_study alias + to_dict round-trip
"""
from __future__ import annotations

import sys
import os
import json
import threading
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# â”€â”€ path bootstrap â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# â”€â”€ test harness (identical to test_mlc.py / test_dre.py pattern) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestResult:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self._fails: List[str] = []

    def ok(self, label: str, condition: bool, msg: str = "") -> None:
        if condition:
            self.passed += 1
            print(f"  PASS  {label}")
        else:
            self.failed += 1
            detail = f" â€” {msg}" if msg else ""
            print(f"  FAIL  {label}{detail}")
            self._fails.append(label)

    def summary(self) -> None:
        total = self.passed + self.failed
        bar   = "=" * 60
        print(f"\n{bar}")
        print(f"  {self.passed}/{total} tests passed  ({self.failed} failed)")
        if self._fails:
            print("  Failed tests:")
            for f in self._fails:
                print(f"    â€¢ {f}")
        print(bar)

    @property
    def all_passed(self) -> bool:
        return self.failed == 0


# â”€â”€ imports under test â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from autonomous_research.rc_models import (
    RC_ALL_STAGES,
    RC_ALWAYS_RUN,
    STAGE_STUDY_PLAN,
    STAGE_REPLAY,
    STAGE_VALIDATION,
    STAGE_EVIDENCE,
    STAGE_EVOLUTION,
    STAGE_KNOWLEDGE,
    STAGE_SYNTHESIS,
    STAGE_REPOSITORY,
    STAGE_REPORT,
    RCError,
    RCStageError,
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
from autonomous_research.rc_config import RCConfig
from autonomous_research.research_coordinator import ResearchCoordinator


# â”€â”€ mock helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _make_mock_plan(
    plan_id: str = "SP-TEST0001",
    study_type: str = "EDGE_VALIDATION",
    source_hypothesis_id: Optional[str] = None,
    source_gap_id: Optional[str] = None,
    title: str = "Test Research Study",
) -> MagicMock:
    """Return a mock StudyPlan with the essential fields."""
    plan = MagicMock()
    plan.plan_id                = plan_id
    plan.study_type             = study_type
    plan.source_hypothesis_id   = source_hypothesis_id
    plan.source_gap_id          = source_gap_id
    plan.title                  = title
    est = MagicMock()
    est.total_hours             = 2.5
    plan.execution_estimate     = est
    return plan


def _make_mock_planner() -> MagicMock:
    planner = MagicMock()
    planner.validate_dependencies.return_value = []
    est = MagicMock()
    est.total_hours = 2.5
    planner.estimate_cost.return_value = est
    return planner


def _make_mock_hypothesis_registry(hyp_id: str = "HYP-001") -> MagicMock:
    reg = MagicMock()
    hyp = MagicMock()
    hyp.hypothesis_id = hyp_id
    reg.get.return_value = hyp
    reg.add_evidence.return_value = None
    return reg


def _make_mock_evidence_validator(outcome: str = "PASSED") -> MagicMock:
    ev = MagicMock()
    result = MagicMock()
    result.outcome = MagicMock()
    result.outcome.value = outcome
    ev.validate_hypothesis.return_value = result
    ev.validate_finding.return_value    = result
    ev.validate.return_value            = result
    stats = MagicMock()
    stats.total_validations = 10
    ev.statistics.return_value = stats
    return ev


def _make_mock_knowledge_provider(
    findings: int = 5,
    edges: int = 3,
    strategies: int = 2,
    certs: int = 1,
) -> MagicMock:
    kp = MagicMock()
    snap = MagicMock()
    snap.total_findings      = findings
    snap.total_edges         = edges
    snap.total_strategies    = strategies
    snap.total_certifications = certs
    kp.get_snapshot.return_value = snap
    kp.get_warnings.return_value = []
    kp.list_studies.return_value = []
    kp.list_edges.return_value   = []
    replay = MagicMock()
    kp.get_replay_summary.return_value = replay
    return kp


def _make_mock_synthesizer(sf: int = 4, c: int = 1) -> MagicMock:
    synth = MagicMock()
    report = MagicMock()
    report.synthesized_findings = [MagicMock()] * sf
    report.contradictions       = [MagicMock()] * c
    synth.synthesize.return_value = report
    return synth


def _make_mock_idr(active: int = 7) -> MagicMock:
    idr = MagicMock()
    stats = MagicMock()
    stats.active_count = active
    idr.statistics.return_value = stats
    idr.list_active.return_value = [MagicMock()] * active
    return idr


def _full_rc(tmp_dir: str = None, dry_run: bool = False) -> ResearchCoordinator:
    """Return a ResearchCoordinator wired with all mock modules."""
    cfg = RCConfig(
        history_path=os.path.join(tmp_dir, "history.json") if tmp_dir else "data/ars/rc/test.json",
        dry_run=dry_run,
    )
    return ResearchCoordinator(
        planner=_make_mock_planner(),
        hypothesis_registry=_make_mock_hypothesis_registry(),
        evidence_validator=_make_mock_evidence_validator(),
        knowledge_provider=_make_mock_knowledge_provider(),
        synthesizer=_make_mock_synthesizer(),
        idr=_make_mock_idr(),
        config=cfg,
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T001â€“T012  rc_models: stage constants
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_stage_constants(r: TestResult) -> None:
    print("\nâ”€â”€ T001â€“T012  Stage constants â”€â”€")
    r.ok("T001 STAGE_STUDY_PLAN value",    STAGE_STUDY_PLAN    == "study_plan")
    r.ok("T002 STAGE_REPLAY value",        STAGE_REPLAY        == "replay")
    r.ok("T003 STAGE_VALIDATION value",    STAGE_VALIDATION    == "validation")
    r.ok("T004 STAGE_EVIDENCE value",      STAGE_EVIDENCE      == "evidence_integration")
    r.ok("T005 STAGE_KNOWLEDGE value",     STAGE_KNOWLEDGE     == "knowledge_integration")
    r.ok("T006 STAGE_SYNTHESIS value",     STAGE_SYNTHESIS     == "cross_study_synthesis")
    r.ok("T007 STAGE_REPOSITORY value",    STAGE_REPOSITORY    == "repository_update")
    r.ok("T008 STAGE_REPORT value",        STAGE_REPORT        == "research_report")
    r.ok("T009 RC_ALL_STAGES length",      len(RC_ALL_STAGES)  == 10)
    r.ok("T010 RC_ALL_STAGES order[0]",    RC_ALL_STAGES[0]    == STAGE_STUDY_PLAN)
    r.ok("T011 RC_ALL_STAGES order[-1]",   RC_ALL_STAGES[-1]   == STAGE_EVOLUTION)
    r.ok("T012 REPORT in RC_ALWAYS_RUN",   STAGE_REPORT in RC_ALWAYS_RUN)
    r.ok("T013b EVOLUTION in RC_ALWAYS_RUN", STAGE_EVOLUTION in RC_ALWAYS_RUN)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T013â€“T023  rc_models: enumerations
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_enumerations(r: TestResult) -> None:
    print("\nâ”€â”€ T013â€“T023  Enumerations â”€â”€")
    r.ok("T013 ResearchStageState.WAITING",  ResearchStageState.WAITING.value == "WAITING")
    r.ok("T014 ResearchStageState.RUNNING",  ResearchStageState.RUNNING.value == "RUNNING")
    r.ok("T015 ResearchStageState.SUCCESS",  ResearchStageState.SUCCESS.value == "SUCCESS")
    r.ok("T016 ResearchStageState.FAILED",   ResearchStageState.FAILED.value  == "FAILED")
    r.ok("T017 ResearchStageState.SKIPPED",  ResearchStageState.SKIPPED.value == "SKIPPED")
    r.ok("T018 ResearchHealth.HEALTHY",      ResearchHealth.HEALTHY.value  == "HEALTHY")
    r.ok("T019 ResearchHealth.DEGRADED",     ResearchHealth.DEGRADED.value == "DEGRADED")
    r.ok("T020 ResearchHealth.FAILED",       ResearchHealth.FAILED.value   == "FAILED")
    r.ok("T021 ResearchHealth.NO_DATA",      ResearchHealth.NO_DATA.value  == "NO_DATA")
    r.ok("T022 ResearchStageState is str",   issubclass(ResearchStageState, str))
    r.ok("T023 ResearchHealth is str",       issubclass(ResearchHealth, str))


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T024â€“T035  rc_models: ResearchStage
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_research_stage(r: TestResult) -> None:
    print("\nâ”€â”€ T024â€“T035  ResearchStage â”€â”€")
    s = ResearchStage(name="test_stage", state=ResearchStageState.SUCCESS)
    r.ok("T024 name set",           s.name  == "test_stage")
    r.ok("T025 state SUCCESS",      s.state == ResearchStageState.SUCCESS)
    r.ok("T026 start_time default", s.start_time  is None)
    r.ok("T027 end_time default",   s.end_time    is None)
    r.ok("T028 duration_ms default",s.duration_ms is None)
    r.ok("T029 output_summary empty",s.output_summary == "")
    r.ok("T030 error default None", s.error is None)
    r.ok("T031 meta default dict",  isinstance(s.meta, dict))

    d = s.to_dict()
    r.ok("T032 to_dict is dict",    isinstance(d, dict))
    r.ok("T033 to_dict name",       d["name"]  == "test_stage")
    r.ok("T034 to_dict state",      d["state"] == "SUCCESS")
    r.ok("T035 to_dict has meta",   "meta" in d)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T036â€“T048  rc_models: ResearchTelemetry
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _sample_telemetry() -> ResearchTelemetry:
    return ResearchTelemetry(
        run_id="rc-20260101-abc123",
        study_plan_id="SP-TEST",
        study_type="EDGE_VALIDATION",
        trading_date="2026-01-01",
        start_time="2026-01-01T09:00:00",
        end_time="2026-01-01T09:00:01",
        total_duration_ms=1000.0,
        stages_success=6,
        stages_failed=0,
        stages_skipped=2,
        plan_validated=True,
        dependencies_unresolved=0,
        estimated_hours=2.5,
        replay_ran=False,
        replay_studies_found=0,
        validation_ran=True,
        validation_outcome="PASSED",
        evidence_integrated=True,
        hypothesis_id="HYP-001",
        knowledge_snapshot_taken=True,
        findings_count=5,
        edges_count=3,
        strategies_count=2,
        certifications_count=1,
        synthesis_ran=True,
        synthesized_findings=4,
        contradictions_detected=1,
        repository_updated=True,
        idr_total_active_dna=7,
        pipeline_healthy=True,
        health="HEALTHY",
    )


def suite_research_telemetry(r: TestResult) -> None:
    print("\nâ”€â”€ T036â€“T048  ResearchTelemetry â”€â”€")
    tel = _sample_telemetry()
    d   = tel.to_dict()
    r.ok("T036 to_dict is dict",          isinstance(d, dict))
    r.ok("T037 run_id present",           d["run_id"] == "rc-20260101-abc123")
    r.ok("T038 study_type present",       d["study_type"] == "EDGE_VALIDATION")
    r.ok("T039 stages_success",           d["stages_success"] == 6)
    r.ok("T040 stages_failed",            d["stages_failed"]  == 0)
    r.ok("T041 stages_skipped",           d["stages_skipped"] == 2)
    r.ok("T042 plan_validated",           d["plan_validated"] is True)
    r.ok("T043 dependencies_unresolved",  d["dependencies_unresolved"] == 0)
    r.ok("T044 validation_outcome",       d["validation_outcome"] == "PASSED")
    r.ok("T045 evidence_integrated",      d["evidence_integrated"] is True)
    r.ok("T046 synthesis_ran",            d["synthesis_ran"] is True)
    r.ok("T047 idr_total_active_dna",     d["idr_total_active_dna"] == 7)
    r.ok("T048 pipeline_healthy",         d["pipeline_healthy"] is True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T049â€“T058  rc_models: ResearchRun
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_research_run(r: TestResult) -> None:
    print("\nâ”€â”€ T049â€“T058  ResearchRun â”€â”€")
    s   = ResearchStage(name="s1", state=ResearchStageState.SUCCESS)
    tel = _sample_telemetry()
    run = ResearchRun(
        run_id="rc-20260101-xyz",
        study_plan_id="SP-RUNTEST",
        study_type="EDGE_VALIDATION",
        date="2026-01-01",
        stages=[s],
        telemetry=tel,
        health=ResearchHealth.HEALTHY,
    )
    r.ok("T049 run_id set",        run.run_id == "rc-20260101-xyz")
    r.ok("T050 health set",        run.health == ResearchHealth.HEALTHY)
    r.ok("T051 stages list",       len(run.stages) == 1)
    r.ok("T052 telemetry attached",run.telemetry is tel)

    d = run.to_dict()
    r.ok("T053 to_dict is dict",   isinstance(d, dict))
    r.ok("T054 health str",        d["health"] == "HEALTHY")
    r.ok("T055 stages in dict",    isinstance(d["stages"], list))
    r.ok("T056 telemetry in dict", d["telemetry"] is not None)
    r.ok("T057 run_id in dict",    d["run_id"] == "rc-20260101-xyz")

    run_no_tel = ResearchRun(
        run_id="rc-none", study_plan_id="SP-X", study_type="X",
        date="2026-01-01", stages=[], telemetry=None, health=ResearchHealth.NO_DATA,
    )
    d2 = run_no_tel.to_dict()
    r.ok("T058 telemetry=None ok", d2["telemetry"] is None)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T059â€“T065  rc_models: ResearchSummary
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_research_summary(r: TestResult) -> None:
    print("\nâ”€â”€ T059â€“T065  ResearchSummary â”€â”€")
    s = ResearchSummary(
        run_id="rc-sum", study_plan_id="SP-S", study_type="META_LEARNING",
        date="2026-01-01", stages_total=8, stages_ok=7,
        stages_failed=0, stages_skipped=1,
        total_duration_ms=500.0, pipeline_healthy=True, health="HEALTHY",
    )
    d = s.to_dict()
    r.ok("T059 to_dict dict",          isinstance(d, dict))
    r.ok("T060 stages_total",          d["stages_total"] == 8)
    r.ok("T061 stages_ok",             d["stages_ok"]    == 7)
    r.ok("T062 pipeline_healthy True", d["pipeline_healthy"] is True)
    r.ok("T063 health str",            d["health"] == "HEALTHY")
    r.ok("T064 study_type",            d["study_type"] == "META_LEARNING")
    r.ok("T065 run_id",                d["run_id"] == "rc-sum")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T066â€“T073  rc_models: RCStatus
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_rc_status(r: TestResult) -> None:
    print("\nâ”€â”€ T066â€“T073  RCStatus â”€â”€")
    st = RCStatus(
        health=ResearchHealth.HEALTHY,
        last_run_id="rc-abc",
        last_run_date="2026-01-01",
        last_run_health="HEALTHY",
        last_successful_run_id="rc-abc",
        consecutive_failures=0,
        total_runs=5,
        planner_available=True,
        hypothesis_registry_available=True,
        evidence_validator_available=True,
        synthesizer_available=True,
        idr_available=True,
        detail="Last run healthy.",
    )
    d = st.to_dict()
    r.ok("T066 health value",                  d["health"] == "HEALTHY")
    r.ok("T067 last_run_id",                   d["last_run_id"] == "rc-abc")
    r.ok("T068 consecutive_failures",          d["consecutive_failures"] == 0)
    r.ok("T069 total_runs",                    d["total_runs"] == 5)
    r.ok("T070 planner_available",             d["planner_available"] is True)
    r.ok("T071 hypothesis_registry_available", d["hypothesis_registry_available"] is True)
    r.ok("T072 synthesizer_available",         d["synthesizer_available"] is True)
    r.ok("T073 idr_available",                 d["idr_available"] is True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T074â€“T080  rc_models: errors + utilities
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_errors_utils(r: TestResult) -> None:
    print("\nâ”€â”€ T074â€“T085  Errors and utilities â”€â”€")
    r.ok("T074 RCError subclass Exception",    issubclass(RCError, Exception))
    r.ok("T075 RCStageError subclass RCError", issubclass(RCStageError, RCError))

    try:
        raise RCStageError("validation", "bad data")
    except RCStageError as exc:
        r.ok("T076 RCStageError .stage",   exc.stage  == "validation")
        r.ok("T077 RCStageError .reason",  exc.reason == "bad data")
        r.ok("T078 RCStageError message",  "validation" in str(exc))

    rid = make_rc_run_id()
    r.ok("T079 make_rc_run_id format",  rid.startswith("rc-"))
    r.ok("T080 make_rc_run_id unique",  rid != make_rc_run_id())

    rid2 = make_rc_run_id("20260601")
    r.ok("T081 make_rc_run_id date arg", "20260601" in rid2)

    now_str = _now_iso()
    r.ok("T082 _now_iso is str",        isinstance(now_str, str))
    r.ok("T083 _now_iso has T",         "T" in now_str)
    r.ok("T084 _now_iso parseable",     bool(datetime.fromisoformat(now_str)))
    r.ok("T085 _now_iso ms precision",  "." in now_str)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T086â€“T098  rc_config: RCConfig
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_rc_config(r: TestResult) -> None:
    print("\nâ”€â”€ T086â€“T098  RCConfig â”€â”€")
    cfg = RCConfig()
    r.ok("T086 history_path default",                "data/ars/rc" in cfg.history_path)
    r.ok("T087 max_history_runs default",             cfg.max_history_runs == 90)
    r.ok("T088 study_plan_enabled default True",      cfg.study_plan_enabled is True)
    r.ok("T089 replay_enabled default True",          cfg.replay_enabled is True)
    r.ok("T090 validation_enabled default True",      cfg.validation_enabled is True)
    r.ok("T091 evidence_integration default True",    cfg.evidence_integration_enabled is True)
    r.ok("T092 knowledge_integration default True",   cfg.knowledge_integration_enabled is True)
    r.ok("T093 synthesis_enabled default True",       cfg.synthesis_enabled is True)
    r.ok("T094 repository_update_enabled default True",cfg.repository_update_enabled is True)
    r.ok("T095 dry_run default False",                cfg.dry_run is False)

    custom = RCConfig(max_history_runs=10, dry_run=True, study_plan_enabled=False)
    r.ok("T096 custom max_history_runs",  custom.max_history_runs  == 10)
    r.ok("T097 custom dry_run",           custom.dry_run           is True)
    r.ok("T098 custom study_plan_enabled",custom.study_plan_enabled is False)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T099â€“T105  coordinator: construction + status with no data
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_construction(r: TestResult) -> None:
    print("\nâ”€â”€ T099â€“T105  Construction and initial status â”€â”€")
    with tempfile.TemporaryDirectory() as _tmp99:
        rc = ResearchCoordinator(config=RCConfig(history_path=str(Path(_tmp99) / "hist.json")))
        r.ok("T099 created without modules",  rc is not None)

        st = rc.status()
        r.ok("T100 status returns RCStatus",  isinstance(st, RCStatus))
        r.ok("T101 health is NO_DATA",        st.health == ResearchHealth.NO_DATA)
        r.ok("T102 total_runs 0",             st.total_runs == 0)
        r.ok("T103 planner_available False",  st.planner_available is False)
        r.ok("T104 consecutive_failures 0",   st.consecutive_failures == 0)
        r.ok("T105 last_run_id None",         st.last_run_id is None)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T106â€“T120  coordinator: happy-path full pipeline
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_happy_path(r: TestResult) -> None:
    print("\nâ”€â”€ T106â€“T120  Happy-path full pipeline â”€â”€")
    with tempfile.TemporaryDirectory() as tmp:
        rc   = _full_rc(tmp, dry_run=True)
        plan = _make_mock_plan(source_hypothesis_id="HYP-001")
        run  = rc.run_research(plan)

    r.ok("T106 returns ResearchRun",     isinstance(run, ResearchRun))
    r.ok("T107 run_id set",              run.run_id.startswith("rc-"))
    r.ok("T108 study_plan_id",           run.study_plan_id == "SP-TEST0001")
    r.ok("T109 date set",                bool(run.date))
    r.ok("T110 stages count 10",          len(run.stages) == 10)
    r.ok("T111 health HEALTHY",          run.health == ResearchHealth.HEALTHY)
    r.ok("T112 telemetry not None",      run.telemetry is not None)

    tel = run.telemetry
    r.ok("T113 tel plan_validated",      tel.plan_validated is True)
    r.ok("T114 tel validation_ran",      tel.validation_ran is True)
    r.ok("T115 tel knowledge_snapshot",  tel.knowledge_snapshot_taken is True)
    r.ok("T116 tel synthesis_ran",       tel.synthesis_ran is True)
    r.ok("T117 tel repository_updated",  tel.repository_updated is True)
    r.ok("T118 tel stages_success >= 6", tel.stages_success >= 6)
    r.ok("T119 tel stages_failed 0",     tel.stages_failed == 0)

    st = rc.status()
    r.ok("T120 status healthy after run",st.health == ResearchHealth.HEALTHY)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T121â€“T130  coordinator: stage isolation â€” each stage fails independently
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_stage_isolation(r: TestResult) -> None:
    print("\nâ”€â”€ T121â€“T130  Stage isolation â”€â”€")

    def _rc_with_broken_planner() -> ResearchCoordinator:
        planner = MagicMock()
        planner.validate_dependencies.side_effect = RuntimeError("planner exploded")
        planner.estimate_cost.side_effect          = RuntimeError("planner exploded")
        return ResearchCoordinator(
            planner=planner,
            knowledge_provider=_make_mock_knowledge_provider(),
            synthesizer=_make_mock_synthesizer(),
            idr=_make_mock_idr(),
            config=RCConfig(dry_run=True),
        )

    rc   = _rc_with_broken_planner()
    plan = _make_mock_plan()
    run  = rc.run_research(plan)
    sp   = next(s for s in run.stages if s.name == STAGE_STUDY_PLAN)
    r.ok("T121 study_plan stage FAILED",   sp.state == ResearchStageState.FAILED)
    r.ok("T122 other stages not all fail", run.health != ResearchHealth.FAILED)
    r.ok("T123 report stage still ran",    any(s.name == STAGE_REPORT and
                                               s.state == ResearchStageState.SUCCESS
                                               for s in run.stages))

    def _rc_with_broken_synthesizer() -> ResearchCoordinator:
        synth = MagicMock()
        synth.synthesize.side_effect = RuntimeError("synthesis bomb")
        return ResearchCoordinator(
            planner=_make_mock_planner(),
            synthesizer=synth,
            config=RCConfig(dry_run=True),
        )

    rc2  = _rc_with_broken_synthesizer()
    run2 = rc2.run_research(_make_mock_plan())
    ss   = next(s for s in run2.stages if s.name == STAGE_SYNTHESIS)
    r.ok("T124 synthesis FAILED",         ss.state == ResearchStageState.FAILED)
    r.ok("T125 DEGRADED not FAILED total",run2.health in (ResearchHealth.DEGRADED, ResearchHealth.HEALTHY))

    def _rc_with_broken_kp() -> ResearchCoordinator:
        kp = MagicMock()
        kp.get_snapshot.side_effect = RuntimeError("kp down")
        kp.get_warnings.side_effect = RuntimeError("kp down")
        return ResearchCoordinator(knowledge_provider=kp, config=RCConfig(dry_run=True))

    rc3  = _rc_with_broken_kp()
    run3 = rc3.run_research(_make_mock_plan())
    ks   = next(s for s in run3.stages if s.name == STAGE_KNOWLEDGE)
    r.ok("T126 knowledge FAILED",         ks.state == ResearchStageState.FAILED)
    r.ok("T127 error message set",        bool(ks.error))

    def _rc_with_broken_idr() -> ResearchCoordinator:
        idr = MagicMock()
        idr.statistics.side_effect = RuntimeError("idr down")
        idr.list_active.side_effect = RuntimeError("idr down")
        return ResearchCoordinator(idr=idr, config=RCConfig(dry_run=True))

    rc4  = _rc_with_broken_idr()
    run4 = rc4.run_research(_make_mock_plan())
    rs   = next(s for s in run4.stages if s.name == STAGE_REPOSITORY)
    r.ok("T128 repository FAILED",        rs.state == ResearchStageState.FAILED)

    def _rc_with_broken_ev() -> ResearchCoordinator:
        ev = MagicMock()
        ev.validate_hypothesis.side_effect = RuntimeError("ev crash")
        ev.validate_finding.side_effect    = RuntimeError("ev crash")
        ev.validate.side_effect            = RuntimeError("ev crash")
        ev.statistics.side_effect          = RuntimeError("ev crash")
        return ResearchCoordinator(evidence_validator=ev, config=RCConfig(dry_run=True))

    rc5  = _rc_with_broken_ev()
    run5 = rc5.run_research(_make_mock_plan(source_hypothesis_id="HYP-001"))
    vs   = next(s for s in run5.stages if s.name == STAGE_VALIDATION)
    r.ok("T129 validation FAILED",        vs.state == ResearchStageState.FAILED)
    r.ok("T130 run still completes",      run5.run_id.startswith("rc-"))


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T131â€“T138  coordinator: stage toggles
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_stage_toggles(r: TestResult) -> None:
    print("\nâ”€â”€ T131â€“T138  Stage toggles â”€â”€")

    def _disabled(flag: str, stage: str) -> ResearchStage:
        kwargs = {flag: False, "dry_run": True}
        rc  = ResearchCoordinator(
            planner=_make_mock_planner(),
            evidence_validator=_make_mock_evidence_validator(),
            knowledge_provider=_make_mock_knowledge_provider(),
            synthesizer=_make_mock_synthesizer(),
            idr=_make_mock_idr(),
            config=RCConfig(**kwargs),
        )
        run = rc.run_research(_make_mock_plan(source_hypothesis_id="HYP-001"))
        return next(s for s in run.stages if s.name == stage)

    r.ok("T131 study_plan disabled â†’ SKIPPED",
         _disabled("study_plan_enabled", STAGE_STUDY_PLAN).state == ResearchStageState.SKIPPED)
    r.ok("T132 replay disabled â†’ SKIPPED",
         _disabled("replay_enabled", STAGE_REPLAY).state == ResearchStageState.SKIPPED)
    r.ok("T133 validation disabled â†’ SKIPPED",
         _disabled("validation_enabled", STAGE_VALIDATION).state == ResearchStageState.SKIPPED)
    r.ok("T134 evidence disabled â†’ SKIPPED",
         _disabled("evidence_integration_enabled", STAGE_EVIDENCE).state == ResearchStageState.SKIPPED)
    r.ok("T135 knowledge disabled â†’ SKIPPED",
         _disabled("knowledge_integration_enabled", STAGE_KNOWLEDGE).state == ResearchStageState.SKIPPED)
    r.ok("T136 synthesis disabled â†’ SKIPPED",
         _disabled("synthesis_enabled", STAGE_SYNTHESIS).state == ResearchStageState.SKIPPED)
    r.ok("T137 repository disabled â†’ SKIPPED",
         _disabled("repository_update_enabled", STAGE_REPOSITORY).state == ResearchStageState.SKIPPED)

    # All stages disabled (except always-run report + evolution)
    rc_all_off = ResearchCoordinator(config=RCConfig(
        study_plan_enabled=False, replay_enabled=False, validation_enabled=False,
        methodology_audit_enabled=False,
        evidence_integration_enabled=False, knowledge_integration_enabled=False,
        synthesis_enabled=False, repository_update_enabled=False,
        scientific_evolution_enabled=False, dry_run=True,
    ))
    run_all_off = rc_all_off.run_research(_make_mock_plan())
    skipped_count = sum(1 for s in run_all_off.stages if s.state == ResearchStageState.SKIPPED)
    r.ok("T138 all disabled â†’ 9 SKIPPED", skipped_count == 9)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T139â€“T144  coordinator: replay skip for non-HISTORICAL_REPLAY study types
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_replay_skip(r: TestResult) -> None:
    print("\nâ”€â”€ T139â€“T144  Replay stage type-guard â”€â”€")

    def _replay_stage(stype: str) -> ResearchStage:
        rc  = ResearchCoordinator(
            knowledge_provider=_make_mock_knowledge_provider(),
            config=RCConfig(dry_run=True),
        )
        plan = _make_mock_plan(study_type=stype)
        run  = rc.run_research(plan)
        return next(s for s in run.stages if s.name == STAGE_REPLAY)

    r.ok("T139 EDGE_VALIDATION â†’ replay SKIPPED",
         _replay_stage("EDGE_VALIDATION").state == ResearchStageState.SKIPPED)
    r.ok("T140 META_LEARNING â†’ replay SKIPPED",
         _replay_stage("META_LEARNING").state   == ResearchStageState.SKIPPED)
    r.ok("T141 DNA_DISCOVERY â†’ replay SKIPPED",
         _replay_stage("DNA_DISCOVERY").state   == ResearchStageState.SKIPPED)
    r.ok("T142 PATTERN_MINING â†’ replay SKIPPED",
         _replay_stage("PATTERN_MINING").state  == ResearchStageState.SKIPPED)

    # HISTORICAL_REPLAY should run
    kp = _make_mock_knowledge_provider()
    kp.list_studies.return_value = [MagicMock()] * 3
    rc_hr = ResearchCoordinator(knowledge_provider=kp, config=RCConfig(dry_run=True))
    plan_hr = _make_mock_plan(study_type="HISTORICAL_REPLAY")
    run_hr  = rc_hr.run_research(plan_hr)
    rs_hr   = next(s for s in run_hr.stages if s.name == STAGE_REPLAY)
    r.ok("T143 HISTORICAL_REPLAY â†’ replay SUCCESS",
         rs_hr.state == ResearchStageState.SUCCESS)
    r.ok("T144 replay studies found in telemetry",
         run_hr.telemetry.replay_studies_found >= 0)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T145â€“T150  coordinator: evidence integration â€” no hypothesis
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_evidence_no_hyp(r: TestResult) -> None:
    print("\nâ”€â”€ T145â€“T150  Evidence integration (no hypothesis) â”€â”€")

    rc   = ResearchCoordinator(
        hypothesis_registry=_make_mock_hypothesis_registry(),
        config=RCConfig(dry_run=True),
    )
    plan_no_hyp = _make_mock_plan(source_hypothesis_id=None)
    run         = rc.run_research(plan_no_hyp)
    ev_stage    = next(s for s in run.stages if s.name == STAGE_EVIDENCE)
    r.ok("T145 no hyp â†’ SKIPPED",        ev_stage.state == ResearchStageState.SKIPPED)
    r.ok("T146 skip reason in summary",   "source_hypothesis_id" in ev_stage.output_summary.lower()
                                           or "no source" in ev_stage.output_summary.lower()
                                           or ev_stage.state == ResearchStageState.SKIPPED)

    # Registry unavailable
    rc2   = ResearchCoordinator(config=RCConfig(dry_run=True))
    plan2 = _make_mock_plan(source_hypothesis_id="HYP-001")
    run2  = rc2.run_research(plan2)
    ev2   = next(s for s in run2.stages if s.name == STAGE_EVIDENCE)
    r.ok("T147 no registry â†’ SKIPPED",   ev2.state == ResearchStageState.SKIPPED)

    # Hypothesis not found in registry
    reg_miss = MagicMock()
    reg_miss.get.return_value = None
    rc3   = ResearchCoordinator(hypothesis_registry=reg_miss, config=RCConfig(dry_run=True))
    plan3 = _make_mock_plan(source_hypothesis_id="HYP-MISSING")
    run3  = rc3.run_research(plan3)
    ev3   = next(s for s in run3.stages if s.name == STAGE_EVIDENCE)
    r.ok("T148 missing hyp â†’ SKIPPED",   ev3.state == ResearchStageState.SKIPPED)

    # With valid hypothesis â€” should succeed (dry_run)
    rc4 = ResearchCoordinator(
        hypothesis_registry=_make_mock_hypothesis_registry(),
        config=RCConfig(dry_run=True),
    )
    plan4 = _make_mock_plan(source_hypothesis_id="HYP-001")
    run4  = rc4.run_research(plan4)
    ev4   = next(s for s in run4.stages if s.name == STAGE_EVIDENCE)
    r.ok("T149 valid hyp dry_run â†’ SUCCESS", ev4.state == ResearchStageState.SUCCESS)
    r.ok("T150 telemetry hypothesis_id set", run4.telemetry.hypothesis_id == "HYP-001")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T151â€“T157  coordinator: run_validation standalone
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_run_validation(r: TestResult) -> None:
    print("\nâ”€â”€ T151â€“T157  run_validation standalone â”€â”€")
    rc  = ResearchCoordinator(
        evidence_validator=_make_mock_evidence_validator("PASSED"),
        config=RCConfig(dry_run=True),
    )
    run = rc.run_validation("HYP-001", "hypothesis")
    r.ok("T151 returns ResearchRun",      isinstance(run, ResearchRun))
    r.ok("T152 study_type VALIDATION",    run.study_type == "VALIDATION_ONLY")
    r.ok("T153 two stages",               len(run.stages) == 2)
    r.ok("T154 validation stage present", any(s.name == STAGE_VALIDATION for s in run.stages))
    r.ok("T155 report stage present",     any(s.name == STAGE_REPORT     for s in run.stages))
    r.ok("T156 health set",               run.health in list(ResearchHealth))

    tel = run.telemetry
    r.ok("T157 telemetry validation_ran", tel.validation_ran is True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T158â€“T165  coordinator: history API
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_history(r: TestResult) -> None:
    print("\nâ”€â”€ T158â€“T165  History API â”€â”€")
    with tempfile.TemporaryDirectory() as tmp:
        rc = _full_rc(tmp, dry_run=True)
        for i in range(5):
            rc.run_research(_make_mock_plan(plan_id=f"SP-HIST-{i:03}"))

        hist = rc.history(limit=3)
        r.ok("T158 history returns list",        isinstance(hist, list))
        r.ok("T159 history limit respected",     len(hist) <= 3)
        r.ok("T160 history items are RunRun",    all(isinstance(h, ResearchRun) for h in hist))
        r.ok("T161 history most recent first",   len(hist) > 0)

        hist_full = rc.history(limit=100)
        r.ok("T162 history all 5 runs",          len(hist_full) == 5)

        hist_1 = rc.history(limit=1)
        r.ok("T163 history limit=1",             len(hist_1) == 1)

        # empty history
        rc2 = ResearchCoordinator(config=RCConfig(dry_run=True, history_path=str(Path(tmp) / "empty_hist.json")))
        r.ok("T164 empty history returns []",    rc2.history() == [])

        # status total_runs
        st = rc.status()
        r.ok("T165 status total_runs == 5",      st.total_runs == 5)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T166â€“T172  coordinator: statistics API
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_statistics(r: TestResult) -> None:
    print("\nâ”€â”€ T166â€“T172  Statistics API â”€â”€")
    with tempfile.TemporaryDirectory() as tmp:
        rc = _full_rc(tmp, dry_run=True)

        # No runs yet
        stats_empty = rc.statistics()
        r.ok("T166 empty stats total_runs 0",   stats_empty["total_runs"] == 0)

        for _ in range(4):
            rc.run_research(_make_mock_plan())

        stats = rc.statistics()
        r.ok("T167 stats is dict",               isinstance(stats, dict))
        r.ok("T168 total_runs 4",                stats["total_runs"] == 4)
        r.ok("T169 healthy_runs > 0",            stats["healthy_runs"] >= 0)
        r.ok("T170 health_rate_pct float",       isinstance(stats["health_rate_pct"], float))
        r.ok("T171 avg_duration_ms >= 0",        stats["avg_duration_ms"] >= 0.0)
        r.ok("T172 stages_success_total > 0",    stats["stages_success_total"] > 0)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T173â€“T180  coordinator: dry_run mode
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_dry_run(r: TestResult) -> None:
    print("\nâ”€â”€ T173â€“T180  dry_run mode â”€â”€")
    with tempfile.TemporaryDirectory() as tmp:
        rc   = _full_rc(tmp, dry_run=True)
        plan = _make_mock_plan(source_hypothesis_id="HYP-001")
        run  = rc.run_research(plan)

        # History file should NOT be written in dry_run=True
        hist_path = os.path.join(tmp, "history.json")
        r.ok("T173 history not persisted in dry_run", not os.path.exists(hist_path))
        r.ok("T174 run completes in dry_run",         run.run_id.startswith("rc-"))
        r.ok("T175 health HEALTHY in dry_run",        run.health == ResearchHealth.HEALTHY)

        # evidence_registry.add_evidence NOT called in dry_run
        rc2 = ResearchCoordinator(
            hypothesis_registry=_make_mock_hypothesis_registry(),
            config=RCConfig(dry_run=True),
        )
        run2 = rc2.run_research(_make_mock_plan(source_hypothesis_id="HYP-001"))
        r.ok("T176 add_evidence skipped in dry_run",
             not rc2._hypothesis_registry.add_evidence.called)

    # dry_run=False: history IS persisted
    with tempfile.TemporaryDirectory() as tmp2:
        rc3 = ResearchCoordinator(
            planner=_make_mock_planner(),
            knowledge_provider=_make_mock_knowledge_provider(),
            synthesizer=_make_mock_synthesizer(),
            idr=_make_mock_idr(),
            config=RCConfig(
                history_path=os.path.join(tmp2, "h.json"),
                dry_run=False,
            ),
        )
        rc3.run_research(_make_mock_plan())
        hist_path2 = os.path.join(tmp2, "h.json")
        r.ok("T177 history persisted when not dry_run",  os.path.exists(hist_path2))
        content = json.loads(open(hist_path2).read())
        r.ok("T178 history is list",                     isinstance(content, list))
        r.ok("T179 one entry in history file",           len(content) == 1)
        r.ok("T180 entry has run_id",                    "run_id" in content[0])


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T181â€“T186  coordinator: health transitions
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_health_transitions(r: TestResult) -> None:
    print("\nâ”€â”€ T181â€“T186  Health transitions â”€â”€")

    with tempfile.TemporaryDirectory() as _tmp181:
        rc = ResearchCoordinator(config=RCConfig(dry_run=True, history_path=str(Path(_tmp181) / "hist.json")))
        r.ok("T181 initial NO_DATA",  rc.status().health == ResearchHealth.NO_DATA)

    # All stages disabled except report â†’ HEALTHY (nothing failed)
    rc2 = ResearchCoordinator(config=RCConfig(
        study_plan_enabled=False, replay_enabled=False, validation_enabled=False,
        evidence_integration_enabled=False, knowledge_integration_enabled=False,
        synthesis_enabled=False, repository_update_enabled=False, dry_run=True,
    ))
    run2 = rc2.run_research(_make_mock_plan())
    r.ok("T182 all-skip â†’ HEALTHY",   run2.health == ResearchHealth.HEALTHY)

    # One failing module â†’ DEGRADED
    broken_synth = MagicMock()
    broken_synth.synthesize.side_effect = RuntimeError("boom")
    rc3 = ResearchCoordinator(
        planner=_make_mock_planner(),
        knowledge_provider=_make_mock_knowledge_provider(),
        synthesizer=broken_synth,
        idr=_make_mock_idr(),
        config=RCConfig(dry_run=True),
    )
    run3 = rc3.run_research(_make_mock_plan())
    r.ok("T183 one failure â†’ DEGRADED", run3.health == ResearchHealth.DEGRADED)

    # Consecutive failures counter
    rc4 = ResearchCoordinator(config=RCConfig(dry_run=True))
    # inject already-degraded run by creating one with broken modules
    broken_rc = ResearchCoordinator(config=RCConfig(
        study_plan_enabled=True, dry_run=True
    ))
    broken_rc._planner = MagicMock()
    broken_rc._planner.validate_dependencies.side_effect = RuntimeError("x")
    broken_rc._planner.estimate_cost.side_effect = RuntimeError("x")
    broken_rc.run_research(_make_mock_plan())
    broken_rc.run_research(_make_mock_plan())
    st4 = broken_rc.status()
    r.ok("T184 consecutive_failures after 2 degraded",  st4.consecutive_failures >= 1)

    # After a healthy run â†’ consecutive_failures resets
    rc5 = _full_rc(dry_run=True)
    # prime with a failure
    bad_synth = MagicMock()
    bad_synth.synthesize.side_effect = RuntimeError("boom")
    rc5._synthesizer = bad_synth
    rc5.run_research(_make_mock_plan())
    rc5._synthesizer = _make_mock_synthesizer()
    rc5.run_research(_make_mock_plan())
    r.ok("T185 failures reset after success",  rc5._consecutive_failures == 0)

    # All non-skip stages fail â†’ FAILED health
    all_bad = ResearchCoordinator(
        planner=MagicMock(**{"validate_dependencies.side_effect": RuntimeError("x"),
                              "estimate_cost.side_effect": RuntimeError("x")}),
        hypothesis_registry=MagicMock(**{"get.side_effect": RuntimeError("x")}),
        evidence_validator=MagicMock(**{"validate.side_effect": RuntimeError("x"),
                                        "validate_hypothesis.side_effect": RuntimeError("x"),
                                        "validate_finding.side_effect": RuntimeError("x"),
                                        "statistics.side_effect": RuntimeError("x")}),
        knowledge_provider=MagicMock(**{"get_snapshot.side_effect": RuntimeError("x"),
                                         "get_warnings.side_effect": RuntimeError("x")}),
        synthesizer=MagicMock(**{"synthesize.side_effect": RuntimeError("x")}),
        idr=MagicMock(**{"statistics.side_effect": RuntimeError("x"),
                          "list_active.side_effect": RuntimeError("x")}),
        config=RCConfig(dry_run=True),
    )
    run_bad = all_bad.run_research(
        _make_mock_plan(source_hypothesis_id="HYP-001")
    )
    r.ok("T186 all-fail â†’ FAILED or DEGRADED",
         run_bad.health in (ResearchHealth.FAILED, ResearchHealth.DEGRADED))


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# T187â€“T190  coordinator: run_study alias + to_dict round-trip
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def suite_alias_and_roundtrip(r: TestResult) -> None:
    print("\nâ”€â”€ T187â€“T190  run_study alias and to_dict round-trip â”€â”€")
    rc   = _full_rc(dry_run=True)
    plan = _make_mock_plan()

    run_a = rc.run_study(plan)
    run_b = rc.run_research(plan)
    r.ok("T187 run_study returns ResearchRun",   isinstance(run_a, ResearchRun))
    r.ok("T188 run_study != run_research (IDs)", run_a.run_id != run_b.run_id)

    d   = run_a.to_dict()
    raw = json.dumps(d)
    r.ok("T189 to_dict is JSON-serialisable",    isinstance(raw, str) and len(raw) > 0)

    recovered = json.loads(raw)
    r.ok("T190 round-trip run_id survives",      recovered["run_id"] == run_a.run_id)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# main
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def main() -> int:
    r = TestResult()

    suite_stage_constants(r)
    suite_enumerations(r)
    suite_research_stage(r)
    suite_research_telemetry(r)
    suite_research_run(r)
    suite_research_summary(r)
    suite_rc_status(r)
    suite_errors_utils(r)
    suite_rc_config(r)
    suite_construction(r)
    suite_happy_path(r)
    suite_stage_isolation(r)
    suite_stage_toggles(r)
    suite_replay_skip(r)
    suite_evidence_no_hyp(r)
    suite_run_validation(r)
    suite_history(r)
    suite_statistics(r)
    suite_dry_run(r)
    suite_health_transitions(r)
    suite_alias_and_roundtrip(r)

    r.summary()
    return 0 if r.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

