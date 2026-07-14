"""iios/investment/decision/explainability/explainability_quality.py
ExplainabilityQualityEvaluator — aggregates transparency + traceability into
an overall explainability score.
"""
from __future__ import annotations

from iios.investment.decision.explainability.decision_explanation import DecisionExplanation
from iios.investment.decision.explainability.decision_trace import DecisionTrace
from iios.investment.decision.explainability.traceability_score import TraceabilityScorer


class ExplainabilityQualityEvaluator:
    """Combines transparency and traceability into a 0–100 quality score."""

    def __init__(self) -> None:
        self._trace_scorer = TraceabilityScorer()

    def evaluate(
        self,
        explanation:       DecisionExplanation,
        trace:             DecisionTrace,
        transparency_score: float,
    ) -> float:
        traceability_score = self._trace_scorer.score(trace)

        # Human readability proxy: factor count + narrative length
        factor_count = len(explanation.supporting_factors) + len(explanation.opposing_factors)
        readability  = min(100.0, factor_count * 10.0 + len(explanation.assumptions) * 5.0)

        # Weighted combination
        quality = (
            transparency_score  * 0.40
            + traceability_score * 0.35
            + readability        * 0.25
        )
        return round(min(100.0, max(0.0, quality)), 4)
