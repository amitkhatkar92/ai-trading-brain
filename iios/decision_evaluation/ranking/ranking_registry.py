"""iios/decision_evaluation/ranking/ranking_registry.py"""
from __future__ import annotations

import threading

from ..evaluation_exceptions import RankingAlgorithmNotFoundError
from .ranking_algorithm import (
    ParetoRanking,
    RankingAlgorithm,
    ScoreBasedRanking,
    UtilityRanking,
)


class RankingRegistry:
    """Thread-safe registry for named RankingAlgorithm instances."""

    def __init__(self) -> None:
        self._algorithms: dict[str, RankingAlgorithm] = {}
        self._lock = threading.RLock()
        # Pre-register built-ins
        self._algorithms["score_based"] = ScoreBasedRanking()
        self._algorithms["pareto"]      = ParetoRanking()
        self._algorithms["utility"]     = UtilityRanking()

    def register(self, algorithm: RankingAlgorithm, *, overwrite: bool = True) -> None:
        with self._lock:
            self._algorithms[algorithm.name] = algorithm

    def get(self, name: str) -> RankingAlgorithm:
        with self._lock:
            if name not in self._algorithms:
                raise RankingAlgorithmNotFoundError(name)
            return self._algorithms[name]

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._algorithms

    def all_names(self) -> list[str]:
        with self._lock:
            return list(self._algorithms.keys())


_registry: RankingRegistry | None = None
_lock = threading.Lock()


def get_ranking_registry() -> RankingRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = RankingRegistry()
    return _registry


def reset_ranking_registry() -> None:
    global _registry
    with _lock:
        _registry = None
