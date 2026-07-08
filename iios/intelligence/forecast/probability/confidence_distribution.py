"""
iios/intelligence/forecast/probability/confidence_distribution.py
==================================================================
Normal distribution utilities for confidence interval estimation.
No external dependencies.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from ..forecast.forecast_statistics import (
    mean,
    std_dev,
    normal_ci,
    z_score_ci,
    clamp_probability,
)


@dataclass
class NormalDistribution:
    """Parameterised normal distribution."""

    mu:    float = 0.0     # mean
    sigma: float = 1.0     # std deviation (must be > 0)

    def __post_init__(self) -> None:
        if self.sigma <= 0:
            raise ValueError(f"sigma must be > 0, got {self.sigma}")

    def pdf(self, x: float) -> float:
        exponent = -0.5 * ((x - self.mu) / self.sigma) ** 2
        return math.exp(exponent) / (self.sigma * math.sqrt(2 * math.pi))

    def ci(self, level: float = 0.90) -> tuple[float, float]:
        return normal_ci(self.mu, self.sigma, level)

    def probability_above(self, threshold: float) -> float:
        """P(X > threshold) using erfc approximation."""
        z = (threshold - self.mu) / (self.sigma * math.sqrt(2))
        return 0.5 * math.erfc(z)

    def probability_below(self, threshold: float) -> float:
        return 1.0 - self.probability_above(threshold)

    def to_dict(self) -> dict[str, Any]:
        return {"mu": self.mu, "sigma": self.sigma}


def fit_normal(values: list[float]) -> NormalDistribution:
    """Fit a normal distribution to a sample of values."""
    if len(values) < 2:
        mu    = values[0] if values else 0.0
        sigma = 1.0
    else:
        mu    = mean(values)
        sigma = std_dev(values, sample=True) or 1.0
    return NormalDistribution(mu=mu, sigma=sigma)


def bayesian_update(
    prior_mu:    float,
    prior_sigma: float,
    obs_mu:      float,
    obs_sigma:   float,
) -> NormalDistribution:
    """
    Conjugate normal-normal Bayesian update.
    Returns the posterior distribution.
    """
    prior_tau  = 1.0 / (prior_sigma ** 2)
    obs_tau    = 1.0 / (obs_sigma   ** 2)
    post_tau   = prior_tau + obs_tau
    post_mu    = (prior_tau * prior_mu + obs_tau * obs_mu) / post_tau
    post_sigma = math.sqrt(1.0 / post_tau)
    return NormalDistribution(mu=post_mu, sigma=post_sigma)
