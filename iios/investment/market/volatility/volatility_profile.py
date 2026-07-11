"""iios/investment/market/volatility/volatility_profile.py
Stateless analyzer that builds a VolatilityProfile from raw estimator
outputs and the current VolatilityState.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.market.volatility.models import (
    VolatilityEstimate,
    VolatilityProfile,
    VolatilityState,
)


class VolatilityProfileAnalyzer:
    """Combines multiple estimator outputs into a single VolatilityProfile."""

    # ── Public API ─────────────────────────────────────────────────────────

    def analyze(
        self,
        state: VolatilityState,
        estimates: "Dict[str, VolatilityEstimate]",
    ) -> VolatilityProfile:
        valid = [e for e in estimates.values() if e.confidence > 0]

        primary = self._select_primary(valid)
        agreement = self._compute_agreement(valid)
        spread = self._compute_spread(valid)

        return VolatilityProfile(
            state=state,
            estimates=dict(estimates),
            primary_estimate=primary,
            estimate_agreement=agreement,
            estimate_spread=spread,
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _select_primary(
        self, estimates: "List[VolatilityEstimate]"
    ) -> "Optional[VolatilityEstimate]":
        """Select the estimate with the highest confidence as the primary."""
        if not estimates:
            return None
        return max(estimates, key=lambda e: e.confidence)

    def _compute_agreement(
        self, estimates: "List[VolatilityEstimate]"
    ) -> float:
        """
        Agreement score 0-1:  1.0 = all estimators produce identical result,
        0.0 = spread equals the mean (coefficient of variation = 1).
        """
        if len(estimates) < 2:
            return 1.0
        vals = [e.annualized_pct for e in estimates]
        mu = sum(vals) / len(vals)
        if mu < 1e-10:
            return 1.0
        spread = max(vals) - min(vals)
        cv = spread / mu
        return max(0.0, min(1.0, 1.0 - cv))

    def _compute_spread(
        self, estimates: "List[VolatilityEstimate]"
    ) -> float:
        """Range of annualised % among all estimators."""
        if len(estimates) < 2:
            return 0.0
        vals = [e.annualized_pct for e in estimates]
        return max(vals) - min(vals)
