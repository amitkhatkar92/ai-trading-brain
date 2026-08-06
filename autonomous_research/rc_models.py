"""
rc_models.py — Pure data models for the ResearchCoordinator.

IIOS Research Infrastructure — Phase 3A.

All fields are JSON-serialisable.  No business logic.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── stage name constants ────────────────────────────────────────────────────

STAGE_STUDY_PLAN    = "study_plan"            # validate plan and cost-estimate
STAGE_REPLAY        = "replay"                # historical replay (HISTORICAL_REPLAY only)
STAGE_VALIDATION    = "validation"            # evidence / hypothesis quality gates
STAGE_AUDIT         = "methodology_audit"     # IRP-002A: methodology audit before evidence
STAGE_EVIDENCE      = "evidence_integration"  # write validated evidence into registry
STAGE_KNOWLEDGE     = "knowledge_integration" # read current knowledge snapshot
STAGE_SYNTHESIS     = "cross_study_synthesis" # synthesize across completed studies
STAGE_REPOSITORY    = "repository_update"     # IDR / knowledge-store update
STAGE_REPORT        = "research_report"       # final report — always runs
STAGE_EVOLUTION     = "scientific_evolution"  # Phase 4: SFR + DQA + next program selection

RC_ALL_STAGES: List[str] = [
    STAGE_STUDY_PLAN,
    STAGE_REPLAY,
    STAGE_VALIDATION,
    STAGE_AUDIT,        # mandatory methodology audit — runs before evidence collection
    STAGE_EVIDENCE,
    STAGE_KNOWLEDGE,
    STAGE_SYNTHESIS,
    STAGE_REPOSITORY,
    STAGE_REPORT,
    STAGE_EVOLUTION,    # always runs: Scientific Findings Review + DQA + next program
]

#: These stages always run regardless of earlier failures.
RC_ALWAYS_RUN: frozenset = frozenset({STAGE_REPORT, STAGE_EVOLUTION})


# ─── enumerations ───────────────────────────────────────────────────────────

class ResearchStageState(str, Enum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED  = "FAILED"
    SKIPPED = "SKIPPED"


class ResearchHealth(str, Enum):
    HEALTHY  = "HEALTHY"   # all enabled stages completed successfully
    DEGRADED = "DEGRADED"  # at least one stage failed; at least one succeeded
    FAILED   = "FAILED"    # all non-skipped stages failed
    NO_DATA  = "NO_DATA"   # no run executed yet


# ─── stage result ───────────────────────────────────────────────────────────

@dataclass
class ResearchStage:
    """Result of one pipeline stage."""

    name:           str
    state:          ResearchStageState
    start_time:     Optional[str]    = None
    end_time:       Optional[str]    = None
    duration_ms:    Optional[float]  = None
    output_summary: str              = ""
    error:          Optional[str]    = None
    meta:           Dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":           self.name,
            "state":          self.state.value,
            "start_time":     self.start_time,
            "end_time":       self.end_time,
            "duration_ms":    self.duration_ms,
            "output_summary": self.output_summary,
            "error":          self.error,
            "meta":           self.meta,
        }


# ─── telemetry ──────────────────────────────────────────────────────────────

@dataclass
class ResearchTelemetry:
    """Machine-readable summary of one research pipeline execution."""

    run_id:                     str
    study_plan_id:              str
    study_type:                 str
    trading_date:               str
    start_time:                 str
    end_time:                   str
    total_duration_ms:          float

    # stage counters
    stages_success:             int
    stages_failed:              int
    stages_skipped:             int

    # stage 1 — study plan
    plan_validated:             bool
    dependencies_unresolved:    int
    estimated_hours:            float

    # stage 2 — replay
    replay_ran:                 bool
    replay_studies_found:       int

    # stage 3 — validation
    validation_ran:             bool
    validation_outcome:         str   # "PASSED" | "PASSED_WITH_OBSERVATIONS" | "FAILED" | "N/A"

    # stage 4 — evidence integration
    evidence_integrated:        bool
    hypothesis_id:              Optional[str]

    # stage 5 — knowledge integration
    knowledge_snapshot_taken:   bool
    findings_count:             int
    edges_count:                int
    strategies_count:           int
    certifications_count:       int

    # stage 6 — synthesis
    synthesis_ran:              bool
    synthesized_findings:       int
    contradictions_detected:    int

    # stage 7 — repository update
    repository_updated:         bool
    idr_total_active_dna:       int

    # overall
    pipeline_healthy:           bool
    health:                     str   # ResearchHealth value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":                     self.run_id,
            "study_plan_id":              self.study_plan_id,
            "study_type":                 self.study_type,
            "trading_date":               self.trading_date,
            "start_time":                 self.start_time,
            "end_time":                   self.end_time,
            "total_duration_ms":          self.total_duration_ms,
            "stages_success":             self.stages_success,
            "stages_failed":              self.stages_failed,
            "stages_skipped":             self.stages_skipped,
            "plan_validated":             self.plan_validated,
            "dependencies_unresolved":    self.dependencies_unresolved,
            "estimated_hours":            self.estimated_hours,
            "replay_ran":                 self.replay_ran,
            "replay_studies_found":       self.replay_studies_found,
            "validation_ran":             self.validation_ran,
            "validation_outcome":         self.validation_outcome,
            "evidence_integrated":        self.evidence_integrated,
            "hypothesis_id":              self.hypothesis_id,
            "knowledge_snapshot_taken":   self.knowledge_snapshot_taken,
            "findings_count":             self.findings_count,
            "edges_count":                self.edges_count,
            "strategies_count":           self.strategies_count,
            "certifications_count":       self.certifications_count,
            "synthesis_ran":              self.synthesis_ran,
            "synthesized_findings":       self.synthesized_findings,
            "contradictions_detected":    self.contradictions_detected,
            "repository_updated":         self.repository_updated,
            "idr_total_active_dna":       self.idr_total_active_dna,
            "pipeline_healthy":           self.pipeline_healthy,
            "health":                     self.health,
        }


# ─── run ────────────────────────────────────────────────────────────────────

@dataclass
class ResearchRun:
    """Complete record of one research pipeline execution."""

    run_id:        str
    study_plan_id: str
    study_type:    str
    date:          str
    stages:        List[ResearchStage]
    telemetry:     Optional[ResearchTelemetry]
    health:        ResearchHealth

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":        self.run_id,
            "study_plan_id": self.study_plan_id,
            "study_type":    self.study_type,
            "date":          self.date,
            "stages":        [s.to_dict() for s in self.stages],
            "telemetry":     self.telemetry.to_dict() if self.telemetry else None,
            "health":        self.health.value,
        }


# ─── summary ────────────────────────────────────────────────────────────────

@dataclass
class ResearchSummary:
    """Compact, report-facing summary of a completed research run."""

    run_id:            str
    study_plan_id:     str
    study_type:        str
    date:              str
    stages_total:      int
    stages_ok:         int
    stages_failed:     int
    stages_skipped:    int
    total_duration_ms: float
    pipeline_healthy:  bool
    health:            str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":            self.run_id,
            "study_plan_id":     self.study_plan_id,
            "study_type":        self.study_type,
            "date":              self.date,
            "stages_total":      self.stages_total,
            "stages_ok":         self.stages_ok,
            "stages_failed":     self.stages_failed,
            "stages_skipped":    self.stages_skipped,
            "total_duration_ms": self.total_duration_ms,
            "pipeline_healthy":  self.pipeline_healthy,
            "health":            self.health,
        }


# ─── operational status ─────────────────────────────────────────────────────

@dataclass
class RCStatus:
    """Current operational status of the ResearchCoordinator."""

    health:                         ResearchHealth
    last_run_id:                    Optional[str]
    last_run_date:                  Optional[str]
    last_run_health:                Optional[str]
    last_successful_run_id:         Optional[str]
    consecutive_failures:           int
    total_runs:                     int
    planner_available:              bool
    hypothesis_registry_available:  bool
    evidence_validator_available:   bool
    synthesizer_available:          bool
    idr_available:                  bool
    detail:                         str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "health":                        self.health.value,
            "last_run_id":                   self.last_run_id,
            "last_run_date":                 self.last_run_date,
            "last_run_health":               self.last_run_health,
            "last_successful_run_id":        self.last_successful_run_id,
            "consecutive_failures":          self.consecutive_failures,
            "total_runs":                    self.total_runs,
            "planner_available":             self.planner_available,
            "hypothesis_registry_available": self.hypothesis_registry_available,
            "evidence_validator_available":  self.evidence_validator_available,
            "synthesizer_available":         self.synthesizer_available,
            "idr_available":                 self.idr_available,
            "detail":                        self.detail,
        }


# ─── errors ─────────────────────────────────────────────────────────────────

class RCError(Exception):
    """Base error for the ResearchCoordinator."""


class RCStageError(RCError):
    """Raised when a specific pipeline stage fails unrecoverably."""

    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(f"[{stage}] {reason}")
        self.stage  = stage
        self.reason = reason


# ─── utilities ──────────────────────────────────────────────────────────────

def make_rc_run_id(date_str: Optional[str] = None) -> str:
    """Return a unique, sortable run id: ``rc-{date}-{uuid8}``."""
    d = date_str or datetime.now().strftime("%Y%m%d")
    return f"rc-{d}-{uuid.uuid4().hex[:8]}"


def _now_iso() -> str:
    """Return the current UTC-local time as an ISO-8601 string (ms precision)."""
    return datetime.now().isoformat(timespec="milliseconds")
