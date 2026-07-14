"""iios/investment/decision/committee/committee_context.py
CommitteeContext — immutable, read-only wrapper of all upstream snapshots.
Passed into each specialist's review() and into every engine sub-component.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot


@dataclass(frozen=True)
class CommitteeContext:
    """
    Read-only container of all upstream decision intelligence snapshots.
    Never contains recommendations or trading instructions.
    """
    decision_id:  str
    subject_id:   str
    subject_type: str
    evidence:     EvidenceSnapshot
    reasoning:    ReasoningSnapshot
    confidence:   ConfidenceSnapshot
    risk:         RiskSnapshot
    explanation:  ExplanationSnapshot

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":  self.decision_id,
            "subject_id":   self.subject_id,
            "subject_type": self.subject_type,
            "evidence_snapshot_id":     self.evidence.snapshot_id,
            "reasoning_snapshot_id":    self.reasoning.snapshot_id,
            "confidence_snapshot_id":   self.confidence.snapshot_id,
            "risk_snapshot_id":         self.risk.snapshot_id,
            "explanation_snapshot_id":  self.explanation.snapshot_id,
            "overall_confidence":       round(self.confidence.overall_confidence, 2),
            "overall_risk":             round(self.risk.overall_risk, 2),
            "explainability_score":     round(self.explanation.explainability_score, 2),
            "evidence_item_count":      self.evidence.item_count,
            "evidence_quality":         round(self.evidence.quality_score, 2),
        }
