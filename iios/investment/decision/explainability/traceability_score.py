"""iios/investment/decision/explainability/traceability_score.py
TraceabilityScorer — computes how well evidence is traced to outcome.
"""
from __future__ import annotations

from iios.investment.decision.explainability.decision_trace import DecisionTrace
from iios.investment.decision.explainability.explainability_constants import (
    FULL_TRACEABILITY_ITEM_MIN,
    MIN_STEPS_FOR_FULL_TRACEABILITY,
)


class TraceabilityScorer:
    """Scores evidence→outcome traceability on a 0–100 scale."""

    def score(self, trace: DecisionTrace) -> float:
        s = 0.0

        # Evidence coverage (40 pts)
        if trace.evidence_node_count >= FULL_TRACEABILITY_ITEM_MIN:
            s += 20.0
        elif trace.evidence_node_count >= 2:
            s += 10.0
        elif trace.evidence_node_count >= 1:
            s += 5.0

        s += min(20.0, trace.evidence_node_count * 2.0)

        # Reasoning coverage (30 pts)
        if trace.reasoning_node_count >= MIN_STEPS_FOR_FULL_TRACEABILITY:
            s += 20.0
        elif trace.reasoning_node_count >= 1:
            s += 10.0

        s += min(10.0, trace.reasoning_node_count * 3.0)

        # Cross-layer linkage (30 pts) — fraction of evidence referenced in reasoning
        frac = trace.traced_evidence_fraction
        if frac >= 0.70:
            s += 30.0
        elif frac >= 0.40:
            s += 20.0
        elif frac >= 0.10:
            s += 10.0

        return round(min(100.0, max(0.0, s)), 4)
