"""
iios/intelligence/forecast/probability/probability_engine.py
=============================================================
ProbabilityEngine — Bayesian updating, ensemble estimation, Monte Carlo.
"""
from __future__ import annotations

import math
import random
import threading
from dataclasses import dataclass, field
from typing import Any

from .confidence_distribution import NormalDistribution, bayesian_update, fit_normal
from .risk_distribution import RiskDistribution
from ..hypothesis_constants import (
    ProbabilityMethod,
    DEFAULT_PRIOR_PROBABILITY,
    DEFAULT_CONFIDENCE_INTERVAL,
)
from ..hypothesis_exceptions import (
    ProbabilityOutOfRangeError,
    DistributionError,
)
from ..forecast.forecast_statistics import clamp_probability, mean


@dataclass
class ProbabilityEstimate:
    """Result of a probability calculation."""

    method:      ProbabilityMethod     = ProbabilityMethod.BAYESIAN
    probability: float                 = 0.5
    lower:       float                 = 0.0
    upper:       float                 = 1.0
    confidence:  float                 = 0.5
    metadata:    dict[str, Any]        = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method":      self.method.value,
            "probability": round(self.probability, 4),
            "lower":       round(self.lower, 4),
            "upper":       round(self.upper, 4),
            "confidence":  round(self.confidence, 4),
            "metadata":    self.metadata,
        }


class ProbabilityEngine:
    """
    Estimates and updates probabilities using multiple methods.

    All methods return ProbabilityEstimate.
    """

    def __init__(self) -> None:
        self._lock:   threading.RLock     = threading.RLock()
        self._priors: dict[str, float]    = {}   # hypothesis_id → prior probability

    # -- Priors ────────────────────────────────────────────────────────────────

    def set_prior(self, hypothesis_id: str, probability: float) -> None:
        if not 0.0 <= probability <= 1.0:
            raise ProbabilityOutOfRangeError(probability)
        with self._lock:
            self._priors[hypothesis_id] = probability

    def get_prior(self, hypothesis_id: str) -> float:
        with self._lock:
            return self._priors.get(hypothesis_id, DEFAULT_PRIOR_PROBABILITY)

    # -- Bayesian update ───────────────────────────────────────────────────────

    def bayesian_update(
        self,
        hypothesis_id:    str,
        likelihood_given_true:  float,  # P(evidence | H is true)
        likelihood_given_false: float,  # P(evidence | H is false)
    ) -> ProbabilityEstimate:
        """
        Update P(H) via Bayes' theorem:
          P(H|E) = P(E|H)·P(H) / P(E)
        """
        if not 0.0 <= likelihood_given_true <= 1.0:
            raise ProbabilityOutOfRangeError(likelihood_given_true)
        if not 0.0 <= likelihood_given_false <= 1.0:
            raise ProbabilityOutOfRangeError(likelihood_given_false)

        prior   = self.get_prior(hypothesis_id)
        p_e     = (likelihood_given_true  * prior
                   + likelihood_given_false * (1.0 - prior))
        if p_e == 0.0:
            raise DistributionError("P(evidence) = 0; cannot update")
        posterior = likelihood_given_true * prior / p_e
        posterior = clamp_probability(posterior)

        with self._lock:
            self._priors[hypothesis_id] = posterior

        return ProbabilityEstimate(
            method      = ProbabilityMethod.BAYESIAN,
            probability = posterior,
            lower       = max(0.0, posterior - 0.1),
            upper       = min(1.0, posterior + 0.1),
            confidence  = abs(posterior - 0.5) * 2.0,
            metadata    = {
                "prior": prior,
                "likelihood_given_true":  likelihood_given_true,
                "likelihood_given_false": likelihood_given_false,
            },
        )

    # -- Ensemble ──────────────────────────────────────────────────────────────

    def ensemble_estimate(
        self,
        probabilities: list[float],
        weights:       list[float] | None = None,
    ) -> ProbabilityEstimate:
        """Weighted average of multiple probability estimates."""
        if not probabilities:
            raise DistributionError("No probabilities provided for ensemble")
        for p in probabilities:
            if not 0.0 <= p <= 1.0:
                raise ProbabilityOutOfRangeError(p)
        n = len(probabilities)
        w = weights if weights and len(weights) == n else [1.0 / n] * n
        total_w = sum(w) or 1.0
        w_norm  = [x / total_w for x in w]
        prob    = sum(p * wt for p, wt in zip(probabilities, w_norm))
        spread  = max(probabilities) - min(probabilities)
        conf    = 1.0 - spread
        return ProbabilityEstimate(
            method      = ProbabilityMethod.ENSEMBLE,
            probability = clamp_probability(prob),
            lower       = clamp_probability(prob - spread / 2),
            upper       = clamp_probability(prob + spread / 2),
            confidence  = max(0.0, conf),
        )

    # -- Monte Carlo ───────────────────────────────────────────────────────────

    def monte_carlo(
        self,
        base_probability:  float,
        volatility:        float        = 0.1,
        n_simulations:     int          = 1_000,
        ci_level:          float        = DEFAULT_CONFIDENCE_INTERVAL,
        seed:              int | None   = None,
    ) -> ProbabilityEstimate:
        """Simulate a distribution of probabilities around the base estimate."""
        if not 0.0 <= base_probability <= 1.0:
            raise ProbabilityOutOfRangeError(base_probability)

        rng     = random.Random(seed)
        samples: list[float] = []
        for _ in range(n_simulations):
            p = rng.gauss(base_probability, volatility)
            samples.append(clamp_probability(p))

        from ..forecast.forecast_statistics import confidence_interval as calc_ci
        lo, hi = calc_ci(samples, ci_level)
        avg    = mean(samples)

        return ProbabilityEstimate(
            method      = ProbabilityMethod.MONTE_CARLO,
            probability = clamp_probability(avg),
            lower       = clamp_probability(lo),
            upper       = clamp_probability(hi),
            confidence  = 1.0 - (hi - lo),
            metadata    = {"n_simulations": n_simulations, "volatility": volatility},
        )

    # -- Frequentist ───────────────────────────────────────────────────────────

    def frequentist(
        self,
        successes: int,
        trials:    int,
        ci_level:  float = DEFAULT_CONFIDENCE_INTERVAL,
    ) -> ProbabilityEstimate:
        """Maximum-likelihood frequentist estimate with Wilson CI."""
        if trials <= 0:
            raise DistributionError("trials must be > 0")
        if successes < 0 or successes > trials:
            raise DistributionError(f"successes {successes} must be in [0, {trials}]")
        from ..forecast.forecast_statistics import z_score_ci
        p = successes / trials
        z = z_score_ci(ci_level)
        # Wilson score interval
        denom = 1 + z ** 2 / trials
        centre = (p + z ** 2 / (2 * trials)) / denom
        half   = (z * math.sqrt(p * (1 - p) / trials + z ** 2 / (4 * trials ** 2))) / denom
        return ProbabilityEstimate(
            method      = ProbabilityMethod.FREQUENTIST,
            probability = clamp_probability(p),
            lower       = clamp_probability(centre - half),
            upper       = clamp_probability(centre + half),
            confidence  = 1.0 - abs(0.5 - p),
            metadata    = {"successes": successes, "trials": trials},
        )

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {"tracked_hypotheses": len(self._priors)}


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock              = threading.Lock()
_ENGINE: ProbabilityEngine | None   = None


def get_probability_engine() -> ProbabilityEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = ProbabilityEngine()
    return _ENGINE


def reset_probability_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
