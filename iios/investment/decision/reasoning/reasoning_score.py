"""iios/investment/decision/reasoning/reasoning_score.py
ReasoningScore — quality score for the reasoning output.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.decision.reasoning.reasoning_constants import ReasoningQualityDimension


@dataclass(frozen=True)
class ReasoningQualityScore:
    """Structured quality score for one reasoning snapshot."""
    overall:          float    # 0–100 weighted composite
    completeness:     float    # 0–100 were all reasoning steps present?
    consistency:      float    # 0–100 no contradictions?
    transparency:     float    # 0–100 all steps evidence-traced?
    evidence_coverage: float   # 0–100 fraction of evidence items referenced
    chain_depth:      float    # 0–100 normalised step count
    computed_at:      datetime

    @property
    def grade(self) -> str:
        if self.overall >= 85:
            return "A"
        if self.overall >= 70:
            return "B"
        if self.overall >= 55:
            return "C"
        if self.overall >= 40:
            return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":          round(self.overall, 2),
            "grade":            self.grade,
            "completeness":     round(self.completeness, 2),
            "consistency":      round(self.consistency, 2),
            "transparency":     round(self.transparency, 2),
            "evidence_coverage": round(self.evidence_coverage, 2),
            "chain_depth":      round(self.chain_depth, 2),
            "computed_at":      self.computed_at.isoformat(),
        }


def compute_reasoning_score(
    completeness:      float,
    consistency:       float,
    transparency:      float,
    evidence_coverage: float,
    chain_depth:       float,
) -> ReasoningQualityScore:
    """Compute weighted composite reasoning quality score from 5 dimensions."""
    weighted = sum([
        completeness      * ReasoningQualityDimension.COMPLETENESS.default_weight,
        consistency       * ReasoningQualityDimension.CONSISTENCY.default_weight,
        transparency      * ReasoningQualityDimension.TRANSPARENCY.default_weight,
        evidence_coverage * ReasoningQualityDimension.EVIDENCE_COVERAGE.default_weight,
        chain_depth       * ReasoningQualityDimension.CHAIN_DEPTH.default_weight,
    ])
    return ReasoningQualityScore(
        overall=round(min(100.0, max(0.0, weighted)), 2),
        completeness=round(min(100.0, max(0.0, completeness)), 2),
        consistency=round(min(100.0, max(0.0, consistency)), 2),
        transparency=round(min(100.0, max(0.0, transparency)), 2),
        evidence_coverage=round(min(100.0, max(0.0, evidence_coverage)), 2),
        chain_depth=round(min(100.0, max(0.0, chain_depth)), 2),
        computed_at=datetime.now(timezone.utc),
    )
