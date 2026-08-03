"""
evidence_validator_models.py — Typed models for the ARS EvidenceValidator.

ARS Phase 2C.

Pure data.  No business logic.  All fields JSON-serialisable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── enumerations ─────────────────────────────────────────────────────────────

class ValidationOutcome(str, Enum):
    """Overall verdict for one evidence validation."""
    PASSED                  = "PASSED"
    PASSED_WITH_OBSERVATIONS = "PASSED_WITH_OBSERVATIONS"
    FAILED                  = "FAILED"


class GateStatus(str, Enum):
    """Result of applying a single quality gate."""
    PASSED      = "PASSED"       # gate evaluated; condition met
    FAILED      = "FAILED"       # gate evaluated; condition not met
    SKIPPED     = "SKIPPED"      # gate applicable but data unavailable
    INAPPLICABLE = "INAPPLICABLE"  # gate not relevant for this subject type


# ─── gate result ──────────────────────────────────────────────────────────────

@dataclass
class GateResult:
    """
    Result of applying one quality gate to a body of evidence.

    Quality score contribution:
        PASSED       → full gate weight
        SKIPPED      → half gate weight (neutral / unknown)
        FAILED       → zero weight
        INAPPLICABLE → excluded from total weight
    """
    gate_id:      str               # e.g. "G-EV-01"
    name:         str               # human-readable gate name
    status:       GateStatus
    actual_value: Optional[Any]     # what was measured (None if SKIPPED/INAPPLICABLE)
    threshold:    Optional[Any]     # what was required  (None if INAPPLICABLE)
    explanation:  str               # full human-readable reasoning
    is_critical:  bool              # True → one FAILED on this gate forces FAILED outcome
    weight:       float             # relative contribution to quality score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id":      self.gate_id,
            "name":         self.name,
            "status":       self.status.value,
            "actual_value": self.actual_value,
            "threshold":    self.threshold,
            "explanation":  self.explanation,
            "is_critical":  self.is_critical,
            "weight":       self.weight,
        }


# ─── quality score ────────────────────────────────────────────────────────────

@dataclass
class EvidenceQualityScore:
    """
    Composite evidence quality score computed from all gate results.

    Formula (INAPPLICABLE gates excluded):
        earned  = sum(weight for PASSED) + sum(weight * 0.5 for SKIPPED)
        total   = sum(weight for PASSED + FAILED + SKIPPED)
        score   = earned / total   (0.0 if total == 0)
    """
    total:            float             # 0.0–1.0 composite score
    gate_scores:      Dict[str, float]  # gate_id → individual contribution
    applicable_gates: int               # gates with status != INAPPLICABLE
    passed_gates:     int
    failed_gates:     int
    skipped_gates:    int
    breakdown:        Dict[str, Any]    # formula components documented

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total":            self.total,
            "gate_scores":      self.gate_scores,
            "applicable_gates": self.applicable_gates,
            "passed_gates":     self.passed_gates,
            "failed_gates":     self.failed_gates,
            "skipped_gates":    self.skipped_gates,
            "breakdown":        self.breakdown,
        }


# ─── evidence validation ──────────────────────────────────────────────────────

@dataclass
class EvidenceValidation:
    """
    Complete validation record for one piece of evidence.

    Every field required for full Scientific Director traceability:
        input         → subject_type + subject_id + subject_summary
        rules         → rules_evaluated (gate_ids)
        evidence      → evidence_used (IDs of studies/findings/edges used)
        gate results  → gate_results (one GateResult per gate)
        score         → quality_score
        decision      → outcome + outcome_explanation
        observations  → observations (PASSED_WITH_OBSERVATIONS only)
        timestamp     → validated_at
    """
    validation_id:       str                    # EV-{F|H|R}-{sha256[:8]}
    subject_type:        str                    # "finding" | "hypothesis" | "roadmap_entry"
    subject_id:          str                    # finding_id / hypothesis_id / entry_id
    subject_summary:     str                    # one-line description of what was validated
    validated_at:        datetime
    gate_results:        List[GateResult]       # one per gate; always 10 entries
    quality_score:       EvidenceQualityScore
    outcome:             ValidationOutcome
    outcome_explanation: str                    # full explanation of decision
    observations:        List[str]              # PASSED_WITH_OBSERVATIONS messages
    evidence_used:       List[str]              # IDs that were consulted
    rules_evaluated:     List[str]              # gate_ids that were evaluated (non-INAPPLICABLE)
    validator_version:   str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id":       self.validation_id,
            "subject_type":        self.subject_type,
            "subject_id":          self.subject_id,
            "subject_summary":     self.subject_summary,
            "validated_at":        self.validated_at.isoformat(),
            "gate_results":        [g.to_dict() for g in self.gate_results],
            "quality_score":       self.quality_score.to_dict(),
            "outcome":             self.outcome.value,
            "outcome_explanation": self.outcome_explanation,
            "observations":        self.observations,
            "evidence_used":       self.evidence_used,
            "rules_evaluated":     self.rules_evaluated,
            "validator_version":   self.validator_version,
        }


# ─── validation summary ───────────────────────────────────────────────────────

@dataclass
class ValidationSummary:
    """Aggregate summary of multiple validation results."""
    summary_id:          str
    generated_at:        datetime
    validations:         List[EvidenceValidation]
    total_validated:     int
    passed_count:        int
    passed_with_obs_count: int
    failed_count:        int
    avg_quality_score:   float
    by_subject_type:     Dict[str, int]   # subject_type → count
    common_failures:     List[str]        # gate names most frequently FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id":           self.summary_id,
            "generated_at":         self.generated_at.isoformat(),
            "total_validated":      self.total_validated,
            "passed_count":         self.passed_count,
            "passed_with_obs_count": self.passed_with_obs_count,
            "failed_count":         self.failed_count,
            "avg_quality_score":    self.avg_quality_score,
            "by_subject_type":      self.by_subject_type,
            "common_failures":      self.common_failures,
        }


# ─── validation statistics ────────────────────────────────────────────────────

@dataclass
class ValidationStatistics:
    """Running statistics across all validations performed in this session."""
    total_validations_run: int
    by_outcome:            Dict[str, int]  # ValidationOutcome.value → count
    by_subject_type:       Dict[str, int]  # subject_type → count
    avg_quality_score:     float
    most_failed_gate:      Optional[str]   # gate_id most frequently FAILED
    most_passed_gate:      Optional[str]   # gate_id most frequently PASSED
    built_at:              datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_validations_run": self.total_validations_run,
            "by_outcome":            self.by_outcome,
            "by_subject_type":       self.by_subject_type,
            "avg_quality_score":     self.avg_quality_score,
            "most_failed_gate":      self.most_failed_gate,
            "most_passed_gate":      self.most_passed_gate,
            "built_at":              self.built_at.isoformat(),
        }


# ─── configuration ────────────────────────────────────────────────────────────

@dataclass
class EvidenceValidatorConfig:
    """
    All EvidenceValidator quality gate thresholds in one place.

    No thresholds are hardcoded in the validator — every threshold lives here.
    Override any field to customise the scientific standards for your context.

    ┌──────────────────────────────────────────────────────────────────┐
    │ Quality score → outcome mapping                                  │
    │                                                                  │
    │   score ≥ passed_threshold        AND  no critical failures      │
    │   → PASSED                                                       │
    │                                                                  │
    │   score ≥ passed_with_obs_threshold  (or critical failure skips  │
    │   this tier entirely)               → PASSED_WITH_OBSERVATIONS  │
    │                                                                  │
    │   score < passed_with_obs_threshold  OR  critical failure        │
    │   → FAILED                                                       │
    └──────────────────────────────────────────────────────────────────┘
    """
    # G-EV-01: minimum observations for statistical significance
    min_observations: int = 100

    # G-EV-02: minimum independent corroborating studies
    min_corroborating_studies: int = 2

    # G-EV-03: minimum temporal span of evidence (days)
    min_temporal_coverage_days: int = 90

    # G-EV-04: minimum number of distinct market regimes covered
    min_regime_count: int = 2

    # G-EV-05: minimum distinct sectors represented
    min_sector_diversity: int = 2

    # G-EV-06: minimum walk-forward consistency (0.0–1.0)
    min_walk_forward_pass_rate: float = 0.60

    # G-EV-07: minimum out-of-sample win rate (0.0–1.0)
    min_oos_win_rate: float = 0.55

    # G-EV-08: maximum fraction of contradicting studies (CRITICAL gate)
    max_contradiction_ratio: float = 0.30

    # G-EV-09: minimum count of passed certifications
    min_certification_count: int = 1

    # G-EV-10: maximum evidence staleness (days since most recent study)
    max_evidence_staleness_days: int = 180

    # Outcome score thresholds
    passed_threshold:          float = 0.80
    passed_with_obs_threshold: float = 0.60

    # Gate weights (normalized internally; relative importance only)
    gate_weights: Dict[str, float] = field(default_factory=lambda: {
        "G-EV-01": 1.0,   # Sample Size
        "G-EV-02": 1.5,   # Replication
        "G-EV-03": 1.0,   # Temporal Coverage
        "G-EV-04": 1.0,   # Regime Coverage
        "G-EV-05": 0.5,   # Sector Coverage
        "G-EV-06": 1.5,   # Walk-Forward Consistency
        "G-EV-07": 1.0,   # Out-of-Sample Validation
        "G-EV-08": 2.0,   # Contradiction Check
        "G-EV-09": 1.0,   # Certification Status
        "G-EV-10": 1.0,   # Evidence Freshness
    })

    # Critical gates — one FAILED gate forces FAILED outcome regardless of score
    critical_gates: List[str] = field(default_factory=lambda: ["G-EV-08"])


# ─── exceptions ───────────────────────────────────────────────────────────────

class EvidenceValidatorError(Exception):
    """Base exception for EvidenceValidator."""


class ValidationSubjectNotFoundError(EvidenceValidatorError):
    """Raised when the requested subject (finding / hypothesis) is not found."""
