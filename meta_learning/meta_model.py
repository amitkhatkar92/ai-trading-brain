"""
Meta-Learning — MetaModel (k-NN Weighted Regression)
========================================================
A pure-Python, library-free implementation of k-Nearest-Neighbour weighted
regression used to predict a strategy's expected R-multiple under a given
set of market features.

Algorithm
----------
1. Store a list of (feature_vector, strategy, r_multiple) observations.
2. Given a query feature vector for a specific strategy:
   a. Find the k most similar historical observations (Euclidean distance).
   b. Compute inverse-distance weighted average of their R-multiples.
3. Return predicted_r for every known strategy.

This is essentially a non-parametric regressor that:
  • Requires NO external libraries (pure Python + math)
  • Adapts automatically as new observations are added
  • Degrades gracefully when history is sparse (falls back to regime defaults)

Performance characteristics:
  • Fitting is O(1)  — just append
  • Prediction is O(N × K)  — N records, K strategies
  • Good enough for 100–10 000 records at trading-day frequency

k (nearest neighbours): 10 (configurable)
distance metric: normalised Euclidean over feature space [0,1]^8
distance weight: 1 / (d + 1e-6)   (inverse, never divide by zero)
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional

from utils import get_logger
from .feature_extractor import FeatureVector

log = get_logger(__name__)

K_NEIGHBOURS = 10      # top-k neighbours used for prediction
DEFAULT_PRED  = 0.0    # fallback when no history for a strategy


@dataclass
class Observation:
    features:   list[float]    # length = FeatureVector.dim (8)
    strategy:   str
    r_multiple: float


class MetaModel:
    """
    k-NN Weighted Regression: predicts expected R-multiple per strategy
    given the current market feature vector.

    Usage::
        model = MetaModel()
        model.add(observation)
        preds = model.predict(current_features, strategies=["Mean_Rev", "ORB"])
        # preds → {"Mean_Rev": 1.35, "ORB": 0.72}
    """

    def __init__(self, k: int = K_NEIGHBOURS) -> None:
        self._k:       int           = k
        self._obs:     list[Observation] = []
        self._trained: bool          = False
        log.info("[MetaModel] Initialised. k=%d, dim=8, pure-Python k-NN regressor.",
                 self._k)

    # ── Public API ────────────────────────────────────────────────────────
    def fit(self, observations: list[Observation]) -> None:
        """Replace internal observation store (called by TrainingEngine)."""
        self._obs     = list(observations)
        self._trained = len(self._obs) >= self._k
        log.info("[MetaModel] Fitted. Records: %d  |  Ready: %s",
                 len(self._obs), "✅" if self._trained else "❌ (need more data)")

    def add(self, obs: Observation) -> None:
        """Incremental append (used during live trading)."""
        self._obs.append(obs)
        if not self._trained and len(self._obs) >= self._k:
            self._trained = True
            log.info("[MetaModel] Reached %d observations — model is now active.",
                     len(self._obs))

    def predict(self, features: FeatureVector,
                strategies: list[str]) -> dict[str, float]:
        """
        Returns {strategy_name: predicted_r_multiple} for each strategy.
        Uses k-NN weighted regression per strategy.
        Falls back to DEFAULT_PRED when there is no history.
        """
        if not self._obs:
            return {s: DEFAULT_PRED for s in strategies}

        fvec = features.to_list()
        preds: dict[str, float] = {}

        for strat in strategies:
            strat_obs = [o for o in self._obs if o.strategy == strat]
            if not strat_obs:
                preds[strat] = DEFAULT_PRED
                continue
            preds[strat] = self._knn_predict(fvec, strat_obs)

        return preds

    def is_trained(self) -> bool:
        return self._trained

    def observation_count(self) -> int:
        return len(self._obs)

    # ── Private helpers ───────────────────────────────────────────────────
    def _knn_predict(self, query: list[float],
                     obs: list[Observation]) -> float:
        # Compute distances
        scored = []
        for o in obs:
            d     = _euclidean(query, o.features)
            w     = 1.0 / (d + 1e-6)
            scored.append((w, o.r_multiple))

        # Top-k
        scored.sort(key=lambda x: x[0], reverse=True)
        top_k = scored[: min(self._k, len(scored))]

        # Weighted average
        total_w  = sum(w for w, _ in top_k)
        if total_w == 0:
            return DEFAULT_PRED
        return sum(w * r for w, r in top_k) / total_w


def _euclidean(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        # Pad shorter with 0.5 (midpoint)
        n = max(len(a), len(b))
        a = a + [0.5] * (n - len(a))
        b = b + [0.5] * (n - len(b))
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
