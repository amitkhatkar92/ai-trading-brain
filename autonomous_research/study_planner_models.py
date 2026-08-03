"""
study_planner_models.py — Typed models for the ARS StudyPlanner.

ARS Phase 2D.

Pure data.  No business logic.  All fields JSON-serialisable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── enumerations ─────────────────────────────────────────────────────────────

class StudyType(str, Enum):
    """Ten supported study types."""
    HISTORICAL_REPLAY  = "HISTORICAL_REPLAY"
    DNA_DISCOVERY      = "DNA_DISCOVERY"
    REGIME_ANALYSIS    = "REGIME_ANALYSIS"
    SECTOR_RESEARCH    = "SECTOR_RESEARCH"
    EDGE_VALIDATION    = "EDGE_VALIDATION"
    CROSS_VALIDATION   = "CROSS_VALIDATION"
    FEATURE_IMPORTANCE = "FEATURE_IMPORTANCE"
    PATTERN_MINING     = "PATTERN_MINING"
    META_LEARNING      = "META_LEARNING"
    CUSTOM             = "CUSTOM"


class ApprovalClass(str, Enum):
    """Scientific Director approval requirement."""
    CLASS_A = "CLASS_A"  # routine review is sufficient
    CLASS_B = "CLASS_B"  # explicit Scientific Director approval required


class PlanStatus(str, Enum):
    DRAFT      = "DRAFT"       # created; not yet dependency-validated
    READY      = "READY"       # dependencies resolved; execution-ready
    APPROVED   = "APPROVED"    # Scientific Director approved
    SUPERSEDED = "SUPERSEDED"  # a newer plan covers this work


class RiskClass(str, Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


# ─── dataset requirement ──────────────────────────────────────────────────────

@dataclass
class DatasetRequirement:
    """One required dataset for a study."""
    name:             str
    symbols:          List[str]      # tickers required
    date_start:       Optional[str]  # ISO date
    date_end:         Optional[str]  # ISO date
    regimes:          List[str]      # market regimes required
    sectors:          List[str]      # market sectors required
    feature_groups:   List[str]      # feature sets required
    min_observations: int            # minimum rows required
    notes:            str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":             self.name,
            "symbols":          self.symbols,
            "date_start":       self.date_start,
            "date_end":         self.date_end,
            "regimes":          self.regimes,
            "sectors":          self.sectors,
            "feature_groups":   self.feature_groups,
            "min_observations": self.min_observations,
            "notes":            self.notes,
        }


# ─── validation plan ──────────────────────────────────────────────────────────

@dataclass
class ValidationPlan:
    """Scientific validation protocol for a study."""
    methodology:            str          # human description
    walk_forward_windows:   int          # number of WF windows
    oos_split:              float        # 0.0–1.0 holdout fraction
    cross_validation_folds: int
    success_criteria:       List[str]    # measurable targets
    acceptance_criteria:    List[str]    # gates that must pass to promote
    metrics:                List[str]    # metrics to track
    min_win_rate:           float        # 0.0–1.0
    min_sharpe:             float
    max_drawdown:           float        # 0.0–1.0 maximum acceptable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "methodology":            self.methodology,
            "walk_forward_windows":   self.walk_forward_windows,
            "oos_split":              self.oos_split,
            "cross_validation_folds": self.cross_validation_folds,
            "success_criteria":       self.success_criteria,
            "acceptance_criteria":    self.acceptance_criteria,
            "metrics":                self.metrics,
            "min_win_rate":           self.min_win_rate,
            "min_sharpe":             self.min_sharpe,
            "max_drawdown":           self.max_drawdown,
        }


# ─── execution estimate ───────────────────────────────────────────────────────

@dataclass
class ExecutionEstimate:
    """Estimated resource usage for executing a study."""
    data_fetch_hours:  float
    compute_hours:     float
    analysis_hours:    float
    total_hours:       float            # sum of above three components
    compute_cost_usd:  float            # rough cloud cost estimate
    storage_mb:        float
    parallelizable:    bool
    compute_intensity: str              # "LOW" | "MEDIUM" | "HIGH"
    breakdown:         Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_fetch_hours":  self.data_fetch_hours,
            "compute_hours":     self.compute_hours,
            "analysis_hours":    self.analysis_hours,
            "total_hours":       self.total_hours,
            "compute_cost_usd":  self.compute_cost_usd,
            "storage_mb":        self.storage_mb,
            "parallelizable":    self.parallelizable,
            "compute_intensity": self.compute_intensity,
            "breakdown":         self.breakdown,
        }


# ─── study dependency ─────────────────────────────────────────────────────────

@dataclass
class StudyDependency:
    """A dependency that must be resolved before a study can begin."""
    depends_on_plan_id:       Optional[str]  # another StudyPlan
    depends_on_gap_id:        Optional[str]  # a KnowledgeGap to close first
    depends_on_hypothesis_id: Optional[str]  # a Hypothesis to validate first
    reason:                   str
    is_blocking:              bool           # True → plan cannot start until resolved

    def to_dict(self) -> Dict[str, Any]:
        return {
            "depends_on_plan_id":       self.depends_on_plan_id,
            "depends_on_gap_id":        self.depends_on_gap_id,
            "depends_on_hypothesis_id": self.depends_on_hypothesis_id,
            "reason":                   self.reason,
            "is_blocking":              self.is_blocking,
        }


# ─── study task ───────────────────────────────────────────────────────────────

@dataclass
class StudyTask:
    """One atomic task within a study plan."""
    task_id:         str
    title:           str
    description:     str
    inputs:          List[str]   # dataset names / artifact IDs needed
    outputs:         List[str]   # artifacts produced
    estimated_hours: float
    order:           int         # 1-based sequential order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id":         self.task_id,
            "title":           self.title,
            "description":     self.description,
            "inputs":          self.inputs,
            "outputs":         self.outputs,
            "estimated_hours": self.estimated_hours,
            "order":           self.order,
        }


# ─── study plan ───────────────────────────────────────────────────────────────

@dataclass
class StudyPlan:
    """
    Complete specification of a scientific study.

    Every field required for full traceability and reproducibility:
        identity     → plan_id (SP-{sha256[:8]}), title, study_type
        scientific   → scientific_question, background, objective
        evidence     → supporting_evidence, related_hypotheses, related_gaps
        data         → dataset_requirements
        validation   → validation_plan
        execution    → tasks, execution_estimate, dependencies
        governance   → risk_class, approval_class, status
        outcomes     → expected_outputs, success_criteria, acceptance_criteria
        provenance   → source_gap_id, source_hypothesis_id, source_entry_id
        metadata     → created_at, estimated_knowledge_gain

    plan_id is deterministic:
        SP-{sha256(f"{study_type}:{title}:{source_key}")[:8].upper()}
    """
    plan_id:                  str
    study_type:               StudyType
    title:                    str
    objective:                str
    scientific_question:      str
    background:               str
    supporting_evidence:      List[str]
    related_hypotheses:       List[str]
    related_gaps:             List[str]
    dataset_requirements:     List[DatasetRequirement]
    validation_plan:          ValidationPlan
    tasks:                    List[StudyTask]
    execution_estimate:       ExecutionEstimate
    dependencies:             List[StudyDependency]
    risk_class:               RiskClass
    approval_class:           ApprovalClass
    status:                   PlanStatus
    expected_outputs:         List[str]
    success_criteria:         List[str]
    acceptance_criteria:      List[str]
    estimated_knowledge_gain: float              # 0.0–1.0
    source_gap_id:            Optional[str]
    source_hypothesis_id:     Optional[str]
    source_entry_id:          Optional[str]
    created_at:               datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id":                  self.plan_id,
            "study_type":               self.study_type.value,
            "title":                    self.title,
            "objective":                self.objective,
            "scientific_question":      self.scientific_question,
            "background":               self.background,
            "supporting_evidence":      self.supporting_evidence,
            "related_hypotheses":       self.related_hypotheses,
            "related_gaps":             self.related_gaps,
            "dataset_requirements":     [d.to_dict() for d in self.dataset_requirements],
            "validation_plan":          self.validation_plan.to_dict(),
            "tasks":                    [t.to_dict() for t in self.tasks],
            "execution_estimate":       self.execution_estimate.to_dict(),
            "dependencies":             [d.to_dict() for d in self.dependencies],
            "risk_class":               self.risk_class.value,
            "approval_class":           self.approval_class.value,
            "status":                   self.status.value,
            "expected_outputs":         self.expected_outputs,
            "success_criteria":         self.success_criteria,
            "acceptance_criteria":      self.acceptance_criteria,
            "estimated_knowledge_gain": self.estimated_knowledge_gain,
            "source_gap_id":            self.source_gap_id,
            "source_hypothesis_id":     self.source_hypothesis_id,
            "source_entry_id":          self.source_entry_id,
            "created_at":               self.created_at.isoformat(),
        }


# ─── study portfolio ──────────────────────────────────────────────────────────

@dataclass
class StudyPortfolio:
    """Aggregate view of all plans in a session."""
    plans:                List[StudyPlan]
    total_plans:          int
    by_study_type:        Dict[str, int]   # StudyType.value → count
    by_approval_class:    Dict[str, int]   # ApprovalClass.value → count
    by_risk_class:        Dict[str, int]   # RiskClass.value → count
    by_status:            Dict[str, int]   # PlanStatus.value → count
    total_compute_hours:  float
    total_knowledge_gain: float
    class_b_plans:        List[str]        # plan_ids requiring explicit approval
    built_at:             datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_plans":          self.total_plans,
            "by_study_type":        self.by_study_type,
            "by_approval_class":    self.by_approval_class,
            "by_risk_class":        self.by_risk_class,
            "by_status":            self.by_status,
            "total_compute_hours":  self.total_compute_hours,
            "total_knowledge_gain": self.total_knowledge_gain,
            "class_b_plans":        self.class_b_plans,
            "built_at":             self.built_at.isoformat(),
        }


# ─── planning statistics ──────────────────────────────────────────────────────

@dataclass
class PlanningStatistics:
    """Session aggregate statistics for the StudyPlanner."""
    total_plans_created: int
    by_study_type:       Dict[str, int]
    by_approval_class:   Dict[str, int]
    by_risk_class:       Dict[str, int]
    avg_knowledge_gain:  float
    avg_compute_hours:   float
    class_b_fraction:    float           # fraction of plans that are CLASS_B
    built_at:            datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_plans_created": self.total_plans_created,
            "by_study_type":       self.by_study_type,
            "by_approval_class":   self.by_approval_class,
            "by_risk_class":       self.by_risk_class,
            "avg_knowledge_gain":  self.avg_knowledge_gain,
            "avg_compute_hours":   self.avg_compute_hours,
            "class_b_fraction":    self.class_b_fraction,
            "built_at":            self.built_at.isoformat(),
        }


# ─── configuration ────────────────────────────────────────────────────────────

@dataclass
class StudyPlannerConfig:
    """All planning defaults and thresholds. No value is hardcoded in the engine."""
    default_date_lookback_days:   int       = 504    # ~2 trading years
    default_oos_split:            float     = 0.20
    default_walk_forward_windows: int       = 5
    default_cv_folds:             int       = 5
    default_min_win_rate:         float     = 0.50
    default_min_sharpe:           float     = 0.80
    default_max_drawdown:         float     = 0.15
    default_min_observations:     int       = 100
    max_symbols_per_plan:         int       = 50
    cost_per_compute_hour_usd:    float     = 0.50   # rough cloud cost
    storage_mb_per_symbol_year:   float     = 10.0
    # study types that always require CLASS_B approval
    class_b_study_types:          List[StudyType] = field(default_factory=lambda: [
        StudyType.META_LEARNING,
        StudyType.CUSTOM,
    ])
    # risk level at which any study escalates to CLASS_B
    class_b_risk_threshold:       RiskClass = RiskClass.HIGH


# ─── exceptions ───────────────────────────────────────────────────────────────

class StudyPlannerError(Exception):
    """Base exception for StudyPlanner errors."""


class StudyPlanNotFoundError(StudyPlannerError):
    """Raised when a referenced plan_id does not exist in the planner."""
