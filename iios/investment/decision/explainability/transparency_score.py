"""iios/investment/decision/explainability/transparency_score.py
TransparencyScorer — computes how transparent the explanation is.
"""
from __future__ import annotations

from iios.investment.decision.explainability.decision_explanation import DecisionExplanation
from iios.investment.decision.explainability.decision_trace import DecisionTrace
from iios.investment.decision.explainability.explainability_constants import (
    MIN_FACTORS_FOR_FULL_TRANSPARENCY,
)


class TransparencyScorer:
    """
    Scores transparency of an explanation on a 0–100 scale.

    Transparency = how well the explanation surfaces ALL factors, assumptions,
    reasoning steps, and uncertainties that a regulator or auditor might require.
    """

    def score(
        self, explanation: DecisionExplanation, trace: DecisionTrace,
    ) -> float:
        score = 0.0

        # 1. Factor completeness (30 pts)
        total_factors = len(explanation.supporting_factors) + len(explanation.opposing_factors)
        if total_factors >= MIN_FACTORS_FOR_FULL_TRANSPARENCY * 2:
            score += 30.0
        elif total_factors >= MIN_FACTORS_FOR_FULL_TRANSPARENCY:
            score += 20.0
        elif total_factors >= 1:
            score += 10.0

        # 2. Assumptions disclosed (20 pts)
        if len(explanation.assumptions) >= 2:
            score += 20.0
        elif len(explanation.assumptions) >= 1:
            score += 12.0

        # 3. Key risks disclosed (15 pts)
        if len(explanation.key_risks) >= 3:
            score += 15.0
        elif len(explanation.key_risks) >= 1:
            score += 8.0

        # 4. Narrative quality (15 pts) — measured by length and content
        if len(explanation.executive_summary) >= 100:
            score += 10.0
        if len(explanation.technical_summary) >= 200:
            score += 5.0

        # 5. Traceability completeness (20 pts)
        if trace.evidence_node_count >= 5:
            score += 10.0
        elif trace.evidence_node_count >= 2:
            score += 5.0

        if trace.reasoning_node_count >= 3:
            score += 10.0
        elif trace.reasoning_node_count >= 1:
            score += 5.0

        return round(min(100.0, max(0.0, score)), 4)
