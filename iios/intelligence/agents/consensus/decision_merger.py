"""
iios/intelligence/agents/consensus/decision_merger.py
=====================================================
DecisionMerger — merges multiple agent decisions into a single
composite decision when pure voting is insufficient.

Useful for numeric decisions (price targets, position sizes)
where a blend of agent outputs is more informative than a winner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..core.base_agent import AgentDecision

__all__ = ["MergedDecision", "DecisionMerger"]


@dataclass
class MergedDecision:
    """The output of a merger operation."""
    method:      str
    value:       Any
    confidence:  float
    components:  list[dict]        # [{agent_id, decision, weight, contribution}]
    explanation: str
    metadata:    dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "method":      self.method,
            "value":       self.value,
            "confidence":  round(self.confidence, 4),
            "components":  self.components,
            "explanation": self.explanation,
        }


class DecisionMerger:
    """
    Merges agent decisions into composite outputs.

    Works best for numeric decisions (floats, dicts of floats).
    Falls back to majority selection for non-numeric types.
    """

    def merge(
        self,
        decisions:  list[AgentDecision],
        method:     str = "confidence_weighted_average",
    ) -> MergedDecision:
        """Dispatch to the named merge method."""
        if method == "confidence_weighted_average":
            return self.confidence_weighted_average(decisions)
        if method == "simple_average":
            return self.simple_average(decisions)
        if method == "best":
            return self.best(decisions)
        return self.confidence_weighted_average(decisions)

    def confidence_weighted_average(
        self,
        decisions: list[AgentDecision],
    ) -> MergedDecision:
        """Weighted average of numeric decisions (confidence × weight)."""
        if not decisions:
            return MergedDecision(
                method="confidence_weighted_average",
                value=None, confidence=0.0,
                components=[], explanation="No decisions to merge"
            )
        numeric = [d for d in decisions if isinstance(d.decision, (int, float))]
        if not numeric:
            return self.best(decisions)

        total_w = sum(d.confidence * d.weight for d in numeric)
        if total_w == 0:
            return self.simple_average(decisions)

        value       = sum(d.decision * d.confidence * d.weight for d in numeric) / total_w
        avg_conf    = sum(d.confidence for d in numeric) / len(numeric)
        components  = [
            {
                "agent_id":     d.agent_id,
                "decision":     d.decision,
                "weight":       d.weight,
                "confidence":   d.confidence,
                "contribution": round(d.decision * d.confidence * d.weight / total_w, 4),
            }
            for d in numeric
        ]
        return MergedDecision(
            method      = "confidence_weighted_average",
            value       = value,
            confidence  = avg_conf,
            components  = components,
            explanation = (
                f"Merged {len(numeric)} numeric decisions: "
                f"value={value:.4f}, avg_confidence={avg_conf:.2%}"
            ),
        )

    def simple_average(
        self,
        decisions: list[AgentDecision],
    ) -> MergedDecision:
        """Unweighted average of numeric decisions."""
        if not decisions:
            return MergedDecision(
                method="simple_average",
                value=None, confidence=0.0,
                components=[], explanation="No decisions to merge"
            )
        numeric = [d for d in decisions if isinstance(d.decision, (int, float))]
        if not numeric:
            return self.best(decisions)

        value    = sum(d.decision for d in numeric) / len(numeric)
        avg_conf = sum(d.confidence for d in numeric) / len(numeric)
        return MergedDecision(
            method      = "simple_average",
            value       = value,
            confidence  = avg_conf,
            components  = [
                {"agent_id": d.agent_id, "decision": d.decision}
                for d in numeric
            ],
            explanation = f"Simple average of {len(numeric)} decisions: {value:.4f}",
        )

    def best(
        self,
        decisions: list[AgentDecision],
    ) -> MergedDecision:
        """Select the single highest-confidence decision."""
        if not decisions:
            return MergedDecision(
                method="best",
                value=None, confidence=0.0,
                components=[], explanation="No decisions"
            )
        winner = max(decisions, key=lambda d: d.confidence * d.weight)
        return MergedDecision(
            method      = "best",
            value       = winner.decision,
            confidence  = winner.confidence,
            components  = [{"agent_id": winner.agent_id, "decision": winner.decision}],
            explanation = (
                f"Best decision from agent {winner.agent_id!r} "
                f"(confidence={winner.confidence:.2%})"
            ),
        )
