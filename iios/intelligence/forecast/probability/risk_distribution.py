"""
iios/intelligence/forecast/probability/risk_distribution.py
============================================================
Risk-adjusted distribution with configurable fat tails.
No external dependencies.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class RiskDistribution:
    """
    A heavier-tailed distribution built on a base normal distribution.

    The tail-weight parameter ``tail_factor`` scales the standard deviation
    for tail probability estimates.  tail_factor = 1.0 → pure normal.
    Values > 1 add fat-tails.
    """

    mu:          float = 0.0
    sigma:       float = 1.0
    tail_factor: float = 1.5    # >1 ⟹ heavier tails than normal

    def __post_init__(self) -> None:
        if self.sigma <= 0:
            raise ValueError(f"sigma must be > 0, got {self.sigma}")
        if self.tail_factor < 1.0:
            raise ValueError(
                f"tail_factor must be ≥ 1.0, got {self.tail_factor}"
            )

    @property
    def effective_sigma(self) -> float:
        return self.sigma * self.tail_factor

    def ci(self, level: float = 0.90) -> tuple[float, float]:
        from ..forecast.forecast_statistics import z_score_ci
        z  = z_score_ci(level)
        lo = self.mu - z * self.effective_sigma
        hi = self.mu + z * self.effective_sigma
        return lo, hi

    def var(self, confidence: float = 0.95) -> float:
        """
        Value at Risk: the loss not exceeded with probability ``confidence``.
        Returns a positive number for a downside loss.
        """
        from ..forecast.forecast_statistics import z_score_ci
        c_two_tail = round(1.0 - 2 * (1.0 - confidence), 2)
        z  = z_score_ci(c_two_tail if c_two_tail > 0 else 0.90)
        return self.mu - z * self.effective_sigma

    def cvar(self, confidence: float = 0.95, n_tail: int = 1_000) -> float:
        """
        Conditional Value at Risk (Expected Shortfall) — Monte Carlo approximation.
        """
        import random
        var_threshold = self.var(confidence)
        tail_samples  = []
        rng = random.Random(42)
        for _ in range(n_tail):
            u   = rng.gauss(self.mu, self.effective_sigma)
            if u < var_threshold:
                tail_samples.append(u)
        if not tail_samples:
            return var_threshold
        return sum(tail_samples) / len(tail_samples)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mu":           self.mu,
            "sigma":        self.sigma,
            "tail_factor":  self.tail_factor,
            "effective_sigma": round(self.effective_sigma, 6),
        }
