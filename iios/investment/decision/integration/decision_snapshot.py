"""iios/investment/decision/integration/decision_snapshot.py
DecisionIntelligenceSnapshot — the single canonical output of the integration engine.
Every downstream component consumes ONLY this object.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.integration.decision_state import IntegrationDecisionState
from iios.investment.decision.integration.decision_summary import (
    CommitteeSummary,
    ConfidenceSummary,
    EvidenceSummary,
    ExplanationSummary,
    ReasoningSummary,
    RecommendationSummary,
    RiskSummary,
)
from iios.investment.decision.integration.integration_constants import (
    QualityGrade,
    SnapshotStatus,
    ValidationStatus,
)


@dataclass(frozen=True)
class DecisionIntelligenceSnapshot:
    """
    Canonical, immutable, versioned integration snapshot.
    Produced once per integration cycle.
    Downstream engines consume ONLY this object — never individual engine outputs.
    """
    snapshot_id:           str
    decision_id:           str
    subject_id:            str
    subject_type:          str
    version:               int

    # Integration state
    decision_state:        IntegrationDecisionState
    snapshot_status:       SnapshotStatus
    validation_status:     ValidationStatus

    # Per-engine summaries (None if engine has not yet produced output)
    evidence_summary:      Optional[EvidenceSummary]
    reasoning_summary:     Optional[ReasoningSummary]
    confidence_summary:    Optional[ConfidenceSummary]
    risk_summary:          Optional[RiskSummary]
    explanation_summary:   Optional[ExplanationSummary]
    committee_summary:     Optional[CommitteeSummary]
    recommendation_summary: Optional[RecommendationSummary]

    # Integration scores (computed by integration layer)
    overall_intelligence_score: float   # 0–100 composite
    overall_confidence:         float   # 0–100 integration-level confidence
    quality_score:              float   # 0–100
    quality_grade:              QualityGrade
    completeness:               float   # 0–1

    # Conflict + validation
    total_conflicts:            int
    unresolved_conflicts:       int
    blocking_conflicts:         int
    validation_check_count:     int
    validation_warning_count:   int
    validation_invalid_count:   int

    # Audit
    integration_duration_ms:   float
    created_at:                datetime

    @property
    def is_complete(self) -> bool:
        return self.snapshot_status == SnapshotStatus.COMPLETE

    @property
    def is_publishable(self) -> bool:
        return self.decision_state.is_publishable

    @property
    def has_conflicts(self) -> bool:
        return self.total_conflicts > 0

    @property
    def is_high_quality(self) -> bool:
        return self.quality_grade in {QualityGrade.A, QualityGrade.B}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":    self.snapshot_id,
            "decision_id":    self.decision_id,
            "subject_id":     self.subject_id,
            "subject_type":   self.subject_type,
            "version":        self.version,
            "snapshot_status":   self.snapshot_status.value,
            "validation_status": self.validation_status.value,
            "is_publishable": self.is_publishable,
            "is_complete":    self.is_complete,
            "completeness":   round(self.completeness, 3),
            # scores
            "overall_intelligence_score": round(self.overall_intelligence_score, 2),
            "overall_confidence":         round(self.overall_confidence, 2),
            "quality_score":              round(self.quality_score, 2),
            "quality_grade":              self.quality_grade.value,
            # conflicts
            "total_conflicts":      self.total_conflicts,
            "unresolved_conflicts": self.unresolved_conflicts,
            "blocking_conflicts":   self.blocking_conflicts,
            # validation
            "validation_checks":  self.validation_check_count,
            "validation_warnings":self.validation_warning_count,
            "validation_invalid": self.validation_invalid_count,
            # summaries
            "evidence":      self.evidence_summary.to_dict()      if self.evidence_summary      else None,
            "reasoning":     self.reasoning_summary.to_dict()     if self.reasoning_summary     else None,
            "confidence":    self.confidence_summary.to_dict()    if self.confidence_summary    else None,
            "risk":          self.risk_summary.to_dict()          if self.risk_summary          else None,
            "explanation":   self.explanation_summary.to_dict()   if self.explanation_summary   else None,
            "committee":     self.committee_summary.to_dict()     if self.committee_summary     else None,
            "recommendation":self.recommendation_summary.to_dict() if self.recommendation_summary else None,
            # audit
            "integration_duration_ms": round(self.integration_duration_ms, 1),
            "created_at":              self.created_at.isoformat(),
        }


def build_decision_snapshot(
    decision_id:           str,
    subject_id:            str,
    subject_type:          str,
    version:               int,
    decision_state:        IntegrationDecisionState,
    snapshot_status:       SnapshotStatus,
    validation_status:     ValidationStatus,
    evidence_summary:      Optional[EvidenceSummary],
    reasoning_summary:     Optional[ReasoningSummary],
    confidence_summary:    Optional[ConfidenceSummary],
    risk_summary:          Optional[RiskSummary],
    explanation_summary:   Optional[ExplanationSummary],
    committee_summary:     Optional[CommitteeSummary],
    recommendation_summary: Optional[RecommendationSummary],
    overall_intelligence_score: float,
    overall_confidence:         float,
    quality_score:              float,
    completeness:               float,
    total_conflicts:            int,
    unresolved_conflicts:       int,
    blocking_conflicts:         int,
    validation_check_count:     int,
    validation_warning_count:   int,
    validation_invalid_count:   int,
    integration_duration_ms:    float,
) -> DecisionIntelligenceSnapshot:
    return DecisionIntelligenceSnapshot(
        snapshot_id            = str(uuid.uuid4()),
        decision_id            = decision_id,
        subject_id             = subject_id,
        subject_type           = subject_type,
        version                = version,
        decision_state         = decision_state,
        snapshot_status        = snapshot_status,
        validation_status      = validation_status,
        evidence_summary       = evidence_summary,
        reasoning_summary      = reasoning_summary,
        confidence_summary     = confidence_summary,
        risk_summary           = risk_summary,
        explanation_summary    = explanation_summary,
        committee_summary      = committee_summary,
        recommendation_summary = recommendation_summary,
        overall_intelligence_score = overall_intelligence_score,
        overall_confidence         = overall_confidence,
        quality_score              = quality_score,
        quality_grade              = QualityGrade.from_score(quality_score),
        completeness               = completeness,
        total_conflicts            = total_conflicts,
        unresolved_conflicts       = unresolved_conflicts,
        blocking_conflicts         = blocking_conflicts,
        validation_check_count     = validation_check_count,
        validation_warning_count   = validation_warning_count,
        validation_invalid_count   = validation_invalid_count,
        integration_duration_ms    = integration_duration_ms,
        created_at                 = datetime.now(timezone.utc),
    )
