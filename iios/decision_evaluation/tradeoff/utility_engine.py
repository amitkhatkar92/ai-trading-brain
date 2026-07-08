"""iios/decision_evaluation/tradeoff/utility_engine.py"""
from __future__ import annotations

import copy
import math
from abc import ABC, abstractmethod

from ..scoring.score_calculator import AlternativeScore


class UtilityFunction(ABC):
    @abstractmethod
    def apply(self, score: float) -> float: ...

    def apply_all(self, scores: list[float]) -> list[float]:
        return [self.apply(s) for s in scores]


class LinearUtility(UtilityFunction):
    def __init__(self, slope: float = 1.0, intercept: float = 0.0) -> None:
        self._slope     = slope
        self._intercept = intercept

    def apply(self, score: float) -> float:
        return self._slope * score + self._intercept


class SigmoidUtility(UtilityFunction):
    def __init__(self, k: float = 10.0, midpoint: float = 0.5) -> None:
        self._k        = k
        self._midpoint = midpoint

    def apply(self, score: float) -> float:
        return 1.0 / (1.0 + math.exp(-self._k * (score - self._midpoint)))


class StepUtility(UtilityFunction):
    def __init__(self, thresholds: list[tuple[float, float]]) -> None:
        # [(threshold, utility), ...] sorted ascending by threshold
        self._thresholds = sorted(thresholds, key=lambda t: t[0])

    def apply(self, score: float) -> float:
        utility = 0.0
        for threshold, u in self._thresholds:
            if score >= threshold:
                utility = u
        return utility


class PowerUtility(UtilityFunction):
    def __init__(self, power: float = 0.5) -> None:
        # < 1 = risk averse, > 1 = risk seeking
        self._power = power

    def apply(self, score: float) -> float:
        return max(score, 0.0) ** self._power


class UtilityEngine:
    """Applies a utility function to a list of AlternativeScores."""

    def apply_utility(
        self,
        alternatives: list[AlternativeScore],
        utility_fn:   UtilityFunction,
    ) -> list[AlternativeScore]:
        result: list[AlternativeScore] = []
        for alt in alternatives:
            a = copy.copy(alt)
            try:
                a.composite_score = utility_fn.apply(alt.composite_score)
            except Exception:  # noqa: BLE001
                a.composite_score = alt.composite_score
            result.append(a)
        return result
