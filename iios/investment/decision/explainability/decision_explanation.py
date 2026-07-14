"""iios/investment/decision/explainability/decision_explanation.py
DecisionExplanation — core explanation dataclass and ExplanationFactor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from iios.investment.decision.explainability.explainability_constants import (
    DecisionOutcome,
    FactorSource,
)


@dataclass(frozen=True)
class ExplanationFactor:
    """A single factor that influenced the assessment, positive or negative."""
    name:          str
    description:   str
    impact:        float        # 0–100 magnitude of influence
    source_engine: FactorSource
    is_positive:   bool         # True = supports a favourable assessment

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":          self.name,
            "description":   self.description,
            "impact":        round(self.impact, 2),
            "source_engine": self.source_engine.value,
            "is_positive":   self.is_positive,
        }


@dataclass(frozen=True)
class DecisionExplanation:
    """
    Complete human-readable explanation for one decision assessment.

    Never contains trade instructions.
    Always derived from upstream engine outputs only.
    """
    decision_id:          str
    subject_id:           str
    subject_type:         str
    outcome:              DecisionOutcome

    # ── Narrative ──────────────────────────────────────────────────────────
    one_line_summary:     str          # ≤ 120 chars
    executive_summary:    str          # ≤ 500 chars, business language
    technical_summary:    str          # detailed, analyst-grade

    # ── Factors ────────────────────────────────────────────────────────────
    supporting_factors:   Tuple[ExplanationFactor, ...]
    opposing_factors:     Tuple[ExplanationFactor, ...]
    assumptions:          Tuple[str, ...]
    key_risks:            Tuple[str, ...]

    # ── Scores (preserved for downstream use without re-computation) ────────
    overall_confidence:   float    # 0–100
    overall_risk:         float    # 0–100
    evidence_quality:     float    # 0–100
    reasoning_quality:    float    # 0–100

    # ── Evidence stats ──────────────────────────────────────────────────────
    evidence_item_count:  int
    source_count:         int
    evidence_coverage:    float    # 0–1
    evidence_freshness:   float    # 0–1

    # ── Reasoning stats ─────────────────────────────────────────────────────
    reasoning_step_count:  int
    logic_consistency:     float   # 0–100

    @property
    def factor_count(self) -> int:
        return len(self.supporting_factors) + len(self.opposing_factors)

    @property
    def net_impact_score(self) -> float:
        """Positive − negative factor impact (positive = more supporting)."""
        pos = sum(f.impact for f in self.supporting_factors)
        neg = sum(f.impact for f in self.opposing_factors)
        return round(pos - neg, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":         self.decision_id,
            "subject_id":          self.subject_id,
            "subject_type":        self.subject_type,
            "outcome":             self.outcome.value,
            "one_line_summary":    self.one_line_summary,
            "executive_summary":   self.executive_summary,
            "technical_summary":   self.technical_summary,
            "supporting_factors":  [f.to_dict() for f in self.supporting_factors],
            "opposing_factors":    [f.to_dict() for f in self.opposing_factors],
            "assumptions":         list(self.assumptions),
            "key_risks":           list(self.key_risks),
            "overall_confidence":  round(self.overall_confidence, 2),
            "overall_risk":        round(self.overall_risk, 2),
            "evidence_quality":    round(self.evidence_quality, 2),
            "reasoning_quality":   round(self.reasoning_quality, 2),
            "evidence_item_count": self.evidence_item_count,
            "source_count":        self.source_count,
            "evidence_coverage":   round(self.evidence_coverage, 4),
            "evidence_freshness":  round(self.evidence_freshness, 4),
            "reasoning_step_count": self.reasoning_step_count,
            "logic_consistency":   round(self.logic_consistency, 2),
            "factor_count":        self.factor_count,
            "net_impact_score":    self.net_impact_score,
        }
