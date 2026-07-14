"""iios/investment/decision/explainability/explanation_snapshot.py
ExplanationSnapshot — canonical, immutable, versioned explainability output.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.decision.explainability.decision_explanation import DecisionExplanation
from iios.investment.decision.explainability.explainability_constants import (
    DecisionOutcome,
    ExplainabilityGrade,
    TraceabilityLevel,
)


@dataclass(frozen=True)
class ExplanationSnapshot:
    """
    Canonical, immutable, versioned explanation for one decision assessment.
    This is the output type of the Decision Explainability Engine.
    """
    snapshot_id:            str
    decision_id:            str
    subject_id:             str
    subject_type:           str
    version:                int

    # ── Input snapshot lineage ──────────────────────────────────────────────
    evidence_snapshot_id:   str
    reasoning_snapshot_id:  str
    confidence_snapshot_id: str
    risk_snapshot_id:       str

    # ── Core explanation ────────────────────────────────────────────────────
    explanation:            DecisionExplanation

    # ── Derived outcome (deterministic) ────────────────────────────────────
    outcome:                DecisionOutcome

    # ── Explainability quality ──────────────────────────────────────────────
    explainability_score:   float                 # 0–100
    explainability_grade:   ExplainabilityGrade
    transparency_score:     float                 # 0–100
    traceability_level:     TraceabilityLevel

    # ── Performance ─────────────────────────────────────────────────────────
    generation_duration_ms: float

    created_at:             datetime

    @property
    def is_high_quality(self) -> bool:
        return self.explainability_grade in {ExplainabilityGrade.A, ExplainabilityGrade.B}

    @property
    def is_auditable(self) -> bool:
        return self.traceability_level in {TraceabilityLevel.FULL, TraceabilityLevel.PARTIAL}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":            self.snapshot_id,
            "decision_id":            self.decision_id,
            "subject_id":             self.subject_id,
            "subject_type":           self.subject_type,
            "version":                self.version,
            "evidence_snapshot_id":   self.evidence_snapshot_id,
            "reasoning_snapshot_id":  self.reasoning_snapshot_id,
            "confidence_snapshot_id": self.confidence_snapshot_id,
            "risk_snapshot_id":       self.risk_snapshot_id,
            "outcome":                self.outcome.value,
            "explainability_score":   round(self.explainability_score, 2),
            "explainability_grade":   self.explainability_grade.value,
            "transparency_score":     round(self.transparency_score, 2),
            "traceability_level":     self.traceability_level.value,
            "generation_duration_ms": round(self.generation_duration_ms, 2),
            "created_at":             self.created_at.isoformat(),
            "is_high_quality":        self.is_high_quality,
            "is_auditable":           self.is_auditable,
            "explanation":            self.explanation.to_dict(),
        }


def build_explanation_snapshot(
    decision_id:            str,
    subject_id:             str,
    subject_type:           str,
    evidence_snapshot_id:   str,
    reasoning_snapshot_id:  str,
    confidence_snapshot_id: str,
    risk_snapshot_id:       str,
    explanation:            DecisionExplanation,
    outcome:                DecisionOutcome,
    explainability_score:   float,
    transparency_score:     float,
    traceability_level:     TraceabilityLevel,
    generation_duration_ms: float,
    version:                int = 1,
) -> ExplanationSnapshot:
    grade = ExplainabilityGrade.from_score(explainability_score)
    return ExplanationSnapshot(
        snapshot_id=str(uuid.uuid4()),
        decision_id=decision_id,
        subject_id=subject_id,
        subject_type=subject_type,
        version=version,
        evidence_snapshot_id=evidence_snapshot_id,
        reasoning_snapshot_id=reasoning_snapshot_id,
        confidence_snapshot_id=confidence_snapshot_id,
        risk_snapshot_id=risk_snapshot_id,
        explanation=explanation,
        outcome=outcome,
        explainability_score=round(explainability_score, 4),
        explainability_grade=grade,
        transparency_score=round(transparency_score, 4),
        traceability_level=traceability_level,
        generation_duration_ms=round(generation_duration_ms, 2),
        created_at=datetime.now(timezone.utc),
    )
