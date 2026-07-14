"""iios/investment/decision/explainability/executive_view.py
ExecutiveView — single-page, business-language view of an ExplanationSnapshot.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot


@dataclass(frozen=True)
class ExecutiveView:
    decision_id:       str
    subject_id:        str
    subject_type:      str
    outcome:           str
    confidence_pct:    float   # 0–100
    confidence_label:  str
    risk_pct:          float   # 0–100
    risk_label:        str
    one_line_summary:  str
    executive_summary: str
    top_supporting:    tuple   # top-3 factor names
    top_opposing:      tuple   # top-3 factor names
    key_risks:         tuple   # top-3 risk strings
    grade:             str     # explainability grade
    created_at:        str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "view_type":        "executive",
            "decision_id":      self.decision_id,
            "subject_id":       self.subject_id,
            "subject_type":     self.subject_type,
            "outcome":          self.outcome,
            "confidence_pct":   round(self.confidence_pct, 1),
            "confidence_label": self.confidence_label,
            "risk_pct":         round(self.risk_pct, 1),
            "risk_label":       self.risk_label,
            "one_line_summary": self.one_line_summary,
            "executive_summary": self.executive_summary,
            "top_supporting":   list(self.top_supporting),
            "top_opposing":     list(self.top_opposing),
            "key_risks":        list(self.key_risks),
            "grade":            self.grade,
            "created_at":       self.created_at,
        }


def build_executive_view(snapshot: ExplanationSnapshot) -> ExecutiveView:
    exp = snapshot.explanation
    return ExecutiveView(
        decision_id      = snapshot.decision_id,
        subject_id       = exp.subject_id,
        subject_type     = exp.subject_type,
        outcome          = snapshot.outcome.value,
        confidence_pct   = exp.overall_confidence,
        confidence_label = snapshot.explanation.one_line_summary.split("|")[1].strip() if "|" in snapshot.explanation.one_line_summary else "",
        risk_pct         = exp.overall_risk,
        risk_label       = "",
        one_line_summary = exp.one_line_summary,
        executive_summary = exp.executive_summary,
        top_supporting   = tuple(f.name for f in exp.supporting_factors[:3]),
        top_opposing     = tuple(f.name for f in exp.opposing_factors[:3]),
        key_risks        = tuple(exp.key_risks[:3]),
        grade            = snapshot.explainability_grade.value,
        created_at       = snapshot.created_at.isoformat(),
    )
