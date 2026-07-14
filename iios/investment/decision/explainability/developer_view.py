"""iios/investment/decision/explainability/developer_view.py
DeveloperView — internal scores, timings, and diagnostic data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot


@dataclass(frozen=True)
class DeveloperView:
    snapshot_id:            str
    decision_id:            str
    subject_id:             str
    version:                int

    # Input lineage
    evidence_snapshot_id:   str
    reasoning_snapshot_id:  str
    confidence_snapshot_id: str
    risk_snapshot_id:       str

    # Scores
    overall_confidence:     float
    overall_risk:           float
    evidence_quality:       float
    reasoning_quality:      float
    logic_consistency:      float
    explainability_score:   float
    transparency_score:     float

    # Counts
    evidence_item_count:    int
    reasoning_step_count:   int
    supporting_count:       int
    opposing_count:         int

    # Outcome + quality
    outcome:                str
    traceability_level:     str
    explainability_grade:   str

    # Performance
    generation_duration_ms: float
    created_at:             str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "view_type":              "developer",
            "snapshot_id":            self.snapshot_id,
            "decision_id":            self.decision_id,
            "subject_id":             self.subject_id,
            "version":                self.version,
            "evidence_snapshot_id":   self.evidence_snapshot_id,
            "reasoning_snapshot_id":  self.reasoning_snapshot_id,
            "confidence_snapshot_id": self.confidence_snapshot_id,
            "risk_snapshot_id":       self.risk_snapshot_id,
            "overall_confidence":     round(self.overall_confidence, 4),
            "overall_risk":           round(self.overall_risk, 4),
            "evidence_quality":       round(self.evidence_quality, 4),
            "reasoning_quality":      round(self.reasoning_quality, 4),
            "logic_consistency":      round(self.logic_consistency, 4),
            "explainability_score":   round(self.explainability_score, 4),
            "transparency_score":     round(self.transparency_score, 4),
            "evidence_item_count":    self.evidence_item_count,
            "reasoning_step_count":   self.reasoning_step_count,
            "supporting_count":       self.supporting_count,
            "opposing_count":         self.opposing_count,
            "outcome":                self.outcome,
            "traceability_level":     self.traceability_level,
            "explainability_grade":   self.explainability_grade,
            "generation_duration_ms": round(self.generation_duration_ms, 2),
            "created_at":             self.created_at,
        }


def build_developer_view(snapshot: ExplanationSnapshot) -> DeveloperView:
    exp = snapshot.explanation
    return DeveloperView(
        snapshot_id            = snapshot.snapshot_id,
        decision_id            = snapshot.decision_id,
        subject_id             = exp.subject_id,
        version                = snapshot.version,
        evidence_snapshot_id   = snapshot.evidence_snapshot_id,
        reasoning_snapshot_id  = snapshot.reasoning_snapshot_id,
        confidence_snapshot_id = snapshot.confidence_snapshot_id,
        risk_snapshot_id       = snapshot.risk_snapshot_id,
        overall_confidence     = exp.overall_confidence,
        overall_risk           = exp.overall_risk,
        evidence_quality       = exp.evidence_quality,
        reasoning_quality      = exp.reasoning_quality,
        logic_consistency      = exp.logic_consistency,
        explainability_score   = snapshot.explainability_score,
        transparency_score     = snapshot.transparency_score,
        evidence_item_count    = exp.evidence_item_count,
        reasoning_step_count   = exp.reasoning_step_count,
        supporting_count       = len(exp.supporting_factors),
        opposing_count         = len(exp.opposing_factors),
        outcome                = snapshot.outcome.value,
        traceability_level     = snapshot.traceability_level.value,
        explainability_grade   = snapshot.explainability_grade.value,
        generation_duration_ms = snapshot.generation_duration_ms,
        created_at             = snapshot.created_at.isoformat(),
    )
