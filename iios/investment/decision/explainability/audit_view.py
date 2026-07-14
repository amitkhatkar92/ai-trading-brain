"""iios/investment/decision/explainability/audit_view.py
AuditView — complete, immutable, compliance-grade record.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.explainability.decision_trace import DecisionTrace
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot


@dataclass(frozen=True)
class AuditView:
    """
    Complete, immutable audit record for one decision assessment.
    Designed for regulatory submission and compliance review.
    All fields are deterministic and reproducible.
    """
    snapshot_id:            str
    decision_id:            str
    subject_id:             str
    subject_type:           str
    version:                int
    created_at:             str

    # Lineage — can be used to reproduce the explanation exactly
    evidence_snapshot_id:   str
    reasoning_snapshot_id:  str
    confidence_snapshot_id: str
    risk_snapshot_id:       str

    # Outcome
    outcome:                str

    # Scores
    overall_confidence:     float
    overall_risk:           float
    explainability_score:   float
    transparency_score:     float
    traceability_level:     str
    explainability_grade:   str
    policy_compliance:      str     # "compliant" | "warning" | "violation"

    # Full explanation text
    one_line_summary:       str
    executive_summary:      str
    technical_summary:      str
    assumptions:            Tuple[str, ...]
    key_risks:              Tuple[str, ...]

    # Factor count (full factor lists are in developer/analyst views)
    supporting_factor_count: int
    opposing_factor_count:  int

    # Trace summary
    evidence_node_count:    int
    reasoning_node_count:   int
    traced_evidence_fraction: float

    # Performance
    generation_duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "view_type":              "audit",
            "snapshot_id":            self.snapshot_id,
            "decision_id":            self.decision_id,
            "subject_id":             self.subject_id,
            "subject_type":           self.subject_type,
            "version":                self.version,
            "created_at":             self.created_at,
            "evidence_snapshot_id":   self.evidence_snapshot_id,
            "reasoning_snapshot_id":  self.reasoning_snapshot_id,
            "confidence_snapshot_id": self.confidence_snapshot_id,
            "risk_snapshot_id":       self.risk_snapshot_id,
            "outcome":                self.outcome,
            "overall_confidence":     round(self.overall_confidence, 4),
            "overall_risk":           round(self.overall_risk, 4),
            "explainability_score":   round(self.explainability_score, 4),
            "transparency_score":     round(self.transparency_score, 4),
            "traceability_level":     self.traceability_level,
            "explainability_grade":   self.explainability_grade,
            "policy_compliance":      self.policy_compliance,
            "one_line_summary":       self.one_line_summary,
            "executive_summary":      self.executive_summary,
            "technical_summary":      self.technical_summary,
            "assumptions":            list(self.assumptions),
            "key_risks":              list(self.key_risks),
            "supporting_factor_count": self.supporting_factor_count,
            "opposing_factor_count":  self.opposing_factor_count,
            "evidence_node_count":    self.evidence_node_count,
            "reasoning_node_count":   self.reasoning_node_count,
            "traced_evidence_fraction": round(self.traced_evidence_fraction, 4),
            "generation_duration_ms": round(self.generation_duration_ms, 2),
        }


def build_audit_view(
    snapshot: ExplanationSnapshot,
    trace: DecisionTrace,
    policy_compliance: str = "compliant",
) -> AuditView:
    exp = snapshot.explanation
    return AuditView(
        snapshot_id             = snapshot.snapshot_id,
        decision_id             = snapshot.decision_id,
        subject_id              = exp.subject_id,
        subject_type            = exp.subject_type,
        version                 = snapshot.version,
        created_at              = snapshot.created_at.isoformat(),
        evidence_snapshot_id    = snapshot.evidence_snapshot_id,
        reasoning_snapshot_id   = snapshot.reasoning_snapshot_id,
        confidence_snapshot_id  = snapshot.confidence_snapshot_id,
        risk_snapshot_id        = snapshot.risk_snapshot_id,
        outcome                 = snapshot.outcome.value,
        overall_confidence      = exp.overall_confidence,
        overall_risk            = exp.overall_risk,
        explainability_score    = snapshot.explainability_score,
        transparency_score      = snapshot.transparency_score,
        traceability_level      = snapshot.traceability_level.value,
        explainability_grade    = snapshot.explainability_grade.value,
        policy_compliance       = policy_compliance,
        one_line_summary        = exp.one_line_summary,
        executive_summary       = exp.executive_summary,
        technical_summary       = exp.technical_summary,
        assumptions             = exp.assumptions,
        key_risks               = exp.key_risks,
        supporting_factor_count = len(exp.supporting_factors),
        opposing_factor_count   = len(exp.opposing_factors),
        evidence_node_count     = trace.evidence_node_count,
        reasoning_node_count    = trace.reasoning_node_count,
        traced_evidence_fraction = trace.traced_evidence_fraction,
        generation_duration_ms  = snapshot.generation_duration_ms,
    )
