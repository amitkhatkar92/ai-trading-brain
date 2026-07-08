"""
iios/intelligence/forecast/scenario/scenario_comparator.py
===========================================================
ScenarioComparator — ranks and compares Scenario objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .scenario_generator import Scenario
from ..hypothesis_constants import (
    SCENARIO_WEIGHT_PROBABILITY,
    SCENARIO_WEIGHT_IMPACT,
    SCENARIO_WEIGHT_CONFIDENCE,
)


@dataclass
class ScenarioComparison:
    """Result of comparing multiple scenarios."""

    scenario_ids:    list[str]            = field(default_factory=list)
    scores:          dict[str, float]     = field(default_factory=dict)
    ranked:          list[str]            = field(default_factory=list)
    top_scenario_id: str                  = ""
    total_prob:      float                = 0.0
    metadata:        dict[str, Any]       = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_ids":    self.scenario_ids,
            "scores":          {k: round(v, 4) for k, v in self.scores.items()},
            "ranked":          self.ranked,
            "top_scenario_id": self.top_scenario_id,
            "total_prob":      round(self.total_prob, 4),
            "metadata":        self.metadata,
        }


class ScenarioComparator:
    """
    Scores and ranks scenarios using a weighted composite score.

    score = P(scenario) × w_prob + impact × w_impact + confidence × w_conf
    """

    def __init__(
        self,
        w_probability: float = SCENARIO_WEIGHT_PROBABILITY,
        w_impact:      float = SCENARIO_WEIGHT_IMPACT,
        w_confidence:  float = SCENARIO_WEIGHT_CONFIDENCE,
    ) -> None:
        total = w_probability + w_impact + w_confidence or 1.0
        self._w_prob  = w_probability / total
        self._w_imp   = w_impact      / total
        self._w_conf  = w_confidence  / total

    def score(self, scenario: Scenario) -> float:
        return (
            scenario.probability * self._w_prob
            + scenario.impact    * self._w_imp
            + scenario.confidence * self._w_conf
        )

    def compare(self, scenarios: list[Scenario]) -> ScenarioComparison:
        if not scenarios:
            return ScenarioComparison()

        scores = {s.scenario_id: self.score(s) for s in scenarios}
        ranked = sorted(scores, key=lambda sid: scores[sid], reverse=True)
        total_prob = sum(s.probability for s in scenarios)

        return ScenarioComparison(
            scenario_ids    = [s.scenario_id for s in scenarios],
            scores          = scores,
            ranked          = ranked,
            top_scenario_id = ranked[0] if ranked else "",
            total_prob      = total_prob,
        )
