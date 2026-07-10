"""iios/investment/market/regime/transition_probability.py
Markov-style transition probability model with Laplace smoothing.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Tuple

from iios.investment.market.regime.models import RegimeType

_N_REGIMES = len(RegimeType)


class TransitionProbabilityModel:
    """Markov transition probability model with Laplace smoothing (+1)."""

    def __init__(self) -> None:
        self._counts: Dict[RegimeType, Dict[RegimeType, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._total: Dict[RegimeType, int] = defaultdict(int)

    def update(self, from_regime: RegimeType, to_regime: RegimeType) -> None:
        """Record an observed transition."""
        self._counts[from_regime][to_regime] += 1
        self._total[from_regime] += 1

    def probability(self, from_regime: RegimeType, to_regime: RegimeType) -> float:
        """P(to_regime | from_regime) using Laplace smoothing."""
        observed = self._counts[from_regime][to_regime]
        total    = self._total[from_regime]
        # Laplace: add 1 to each cell, add N to total
        return (observed + 1) / (total + _N_REGIMES)

    def transition_probability(self, from_regime: RegimeType) -> float:
        """P(regime changes to any other regime) = 1 - P(stay)."""
        return max(0.0, min(1.0, 1.0 - self.probability(from_regime, from_regime)))

    def most_likely_next(self, from_regime: RegimeType) -> Tuple[RegimeType, float]:
        """Return (most_likely_next_regime, probability)."""
        best_regime = RegimeType.UNKNOWN
        best_prob   = -1.0
        for r in RegimeType:
            p = self.probability(from_regime, r)
            if p > best_prob:
                best_prob   = p
                best_regime = r
        return best_regime, best_prob

    def transition_matrix(self) -> Dict[str, Dict[str, float]]:
        """Full normalized transition matrix as nested dicts."""
        return {
            fr.value: {
                tr.value: self.probability(fr, tr)
                for tr in RegimeType
            }
            for fr in RegimeType
        }

    def total_transitions(self) -> int:
        """Total number of transitions recorded across all from-regimes."""
        return sum(self._total.values())

    def reset(self) -> None:
        self._counts.clear()
        self._total.clear()
