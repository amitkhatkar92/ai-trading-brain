"""iios/decision_evaluation/weighting/weight_manager.py"""
from __future__ import annotations

import threading

from ..evaluation_constants import DEFAULT_CRITERION_WEIGHT, WeightingStrategy
from ..evaluation_exceptions import InvalidWeightError
from ..criteria.criterion import Criterion


class WeightManager:
    """Manages and normalizes criterion weights."""

    def __init__(self, strategy: WeightingStrategy = WeightingStrategy.MANUAL) -> None:
        self._strategy = strategy
        self._weights:  dict[str, float] = {}
        self._lock      = threading.Lock()

    def set_weight(self, criterion_id: str, weight: float) -> None:
        if weight < 0:
            raise InvalidWeightError(criterion_id, weight)
        with self._lock:
            self._weights[criterion_id] = weight

    def get_weight(self, criterion_id: str) -> float:
        with self._lock:
            return self._weights.get(criterion_id, DEFAULT_CRITERION_WEIGHT)

    def resolve(
        self,
        criteria: list[Criterion],
        override: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """
        Return normalized weights (sum == 1.0) for the given criteria.
        Priority: override dict > stored weights > criterion.weight > equal (1/n).
        """
        if not criteria:
            return {}

        if self._strategy == WeightingStrategy.EQUAL:
            n = len(criteria)
            return {c.criterion_id: 1.0 / n for c in criteria}

        raw: dict[str, float] = {}
        for c in criteria:
            if override and c.criterion_id in override:
                raw[c.criterion_id] = override[c.criterion_id]
            else:
                with self._lock:
                    raw[c.criterion_id] = self._weights.get(c.criterion_id, c.weight)

        return self._normalize(raw)

    def equal_weights(self, criterion_ids: list[str]) -> dict[str, float]:
        if not criterion_ids:
            return {}
        n = len(criterion_ids)
        return {cid: 1.0 / n for cid in criterion_ids}

    def normalize_weights(self, weights: dict[str, float]) -> dict[str, float]:
        return self._normalize(weights)

    def _normalize(self, weights: dict[str, float]) -> dict[str, float]:
        total = sum(max(0.0, w) for w in weights.values())
        if total == 0:
            n = len(weights)
            return {k: 1.0 / n for k in weights} if n > 0 else {}
        return {k: max(0.0, v) / total for k, v in weights.items()}
