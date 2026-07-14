"""iios/investment/decision/explainability/analyst_view.py
AnalystView — full factor breakdown for investment analysts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.explainability.decision_explanation import ExplanationFactor


@dataclass(frozen=True)
class AnalystView:
    decision_id:         str
    subject_id:          str
    outcome:             str
    executive_summary:   str
    technical_summary:   str

    # Evidence breakdown
    evidence_count:      int
    source_count:        int
    evidence_quality:    float
    evidence_coverage:   float
    evidence_freshness:  float

    # Reasoning breakdown
    reasoning_steps:     int
    logic_consistency:   float
    reasoning_quality:   float

    # Confidence breakdown
    overall_confidence:  float
    confidence_label:    str    # from one_line_summary

    # Risk breakdown by dimension (from technical_summary)
    overall_risk:        float
    risk_label:          str

    # Factors (full list)
    supporting_factors:  Tuple[Dict[str, Any], ...]
    opposing_factors:    Tuple[Dict[str, Any], ...]
    assumptions:         Tuple[str, ...]
    key_risks:           Tuple[str, ...]

    # Explainability quality
    explainability_score: float
    transparency_score:   float
    traceability_level:   str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "view_type":            "analyst",
            "decision_id":          self.decision_id,
            "subject_id":           self.subject_id,
            "outcome":              self.outcome,
            "executive_summary":    self.executive_summary,
            "technical_summary":    self.technical_summary,
            "evidence_count":       self.evidence_count,
            "source_count":         self.source_count,
            "evidence_quality":     round(self.evidence_quality, 2),
            "evidence_coverage":    round(self.evidence_coverage, 4),
            "evidence_freshness":   round(self.evidence_freshness, 4),
            "reasoning_steps":      self.reasoning_steps,
            "logic_consistency":    round(self.logic_consistency, 2),
            "reasoning_quality":    round(self.reasoning_quality, 2),
            "overall_confidence":   round(self.overall_confidence, 2),
            "overall_risk":         round(self.overall_risk, 2),
            "supporting_factors":   list(self.supporting_factors),
            "opposing_factors":     list(self.opposing_factors),
            "assumptions":          list(self.assumptions),
            "key_risks":            list(self.key_risks),
            "explainability_score": round(self.explainability_score, 2),
            "transparency_score":   round(self.transparency_score, 2),
            "traceability_level":   self.traceability_level,
        }


def build_analyst_view(snapshot: ExplanationSnapshot) -> AnalystView:
    exp = snapshot.explanation
    return AnalystView(
        decision_id          = snapshot.decision_id,
        subject_id           = exp.subject_id,
        outcome              = snapshot.outcome.value,
        executive_summary    = exp.executive_summary,
        technical_summary    = exp.technical_summary,
        evidence_count       = exp.evidence_item_count,
        source_count         = exp.source_count,
        evidence_quality     = exp.evidence_quality,
        evidence_coverage    = exp.evidence_coverage,
        evidence_freshness   = exp.evidence_freshness,
        reasoning_steps      = exp.reasoning_step_count,
        logic_consistency    = exp.logic_consistency,
        reasoning_quality    = exp.reasoning_quality,
        overall_confidence   = exp.overall_confidence,
        confidence_label     = "n/a",
        overall_risk         = exp.overall_risk,
        risk_label           = "n/a",
        supporting_factors   = tuple(f.to_dict() for f in exp.supporting_factors),
        opposing_factors     = tuple(f.to_dict() for f in exp.opposing_factors),
        assumptions          = exp.assumptions,
        key_risks            = exp.key_risks,
        explainability_score = snapshot.explainability_score,
        transparency_score   = snapshot.transparency_score,
        traceability_level   = snapshot.traceability_level.value,
    )
