"""iios/investment/portfolio/diversification/factor_concentration.py

Style / factor concentration estimated from position proxies.
No external market data is required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.diversification.diversification_types import (
    PositionData,
    compute_hhi,
)


@dataclass(frozen=True)
class FactorExposure:
    """
    Weighted factor tilts estimated from conviction, risk, and confidence proxies.

    Tilts are expressed as a weighted average of per-position proxy values.
    All scores are in [0, 1].
    """

    # Quality / momentum proxy: high-conviction positions → quality tilt
    quality_tilt:        float = 0.5   # avg(w_i * conviction_i)
    # Volatility proxy: high-risk positions → volatility tilt
    volatility_tilt:     float = 0.5   # avg(w_i * risk_score_i)
    # Momentum proxy: high-confidence positions → momentum tilt
    momentum_tilt:       float = 0.5   # avg(w_i * confidence_i)
    # Size proxy: even weight distribution → large-cap tilt; concentrated → small-cap
    size_tilt:           float = 0.5   # 1 - hhi (normalized)
    # Value / growth proxy: low conviction + high risk → value; high conviction + low risk → growth
    value_growth_tilt:   float = 0.5   # 0 = value, 1 = growth

    # Concentration of the factor exposures themselves
    quality_concentration:    float = 0.0   # HHI of quality distribution
    volatility_concentration: float = 0.0   # HHI of volatility distribution

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality_tilt":           round(self.quality_tilt, 4),
            "volatility_tilt":        round(self.volatility_tilt, 4),
            "momentum_tilt":          round(self.momentum_tilt, 4),
            "size_tilt":              round(self.size_tilt, 4),
            "value_growth_tilt":      round(self.value_growth_tilt, 4),
            "quality_concentration":  round(self.quality_concentration, 4),
            "volatility_concentration":round(self.volatility_concentration, 4),
        }


def analyze_factor_concentration(positions: List[PositionData]) -> FactorExposure:
    """Estimate factor tilts from position proxy fields."""
    if not positions:
        return FactorExposure()

    total_w = sum(p.weight for p in positions) or 1.0

    quality_tilt   = sum(p.weight * p.conviction  for p in positions) / total_w
    volatility_tilt= sum(p.weight * p.risk_score  for p in positions) / total_w
    momentum_tilt  = sum(p.weight * p.confidence  for p in positions) / total_w

    hhi = compute_hhi([p.weight for p in positions])
    size_tilt = max(0.0, 1.0 - hhi * len(positions))  # normalized spread

    # Value/growth: growth = high conviction AND low risk
    vg_scores = [max(0.0, min(1.0, p.conviction - p.risk_score + 0.5)) for p in positions]
    value_growth_tilt = sum(p.weight * s for p, s in zip(positions, vg_scores)) / total_w

    # Concentration of conviction distribution (quality HHI)
    q_weights = [p.weight * p.conviction for p in positions]
    q_total   = sum(q_weights) or 1.0
    q_norm    = [q / q_total for q in q_weights]
    quality_conc = compute_hhi(q_norm)

    # Concentration of risk distribution (volatility HHI)
    v_weights = [p.weight * p.risk_score for p in positions]
    v_total   = sum(v_weights) or 1.0
    v_norm    = [v / v_total for v in v_weights]
    vol_conc  = compute_hhi(v_norm)

    return FactorExposure(
        quality_tilt         = round(quality_tilt, 4),
        volatility_tilt      = round(volatility_tilt, 4),
        momentum_tilt        = round(momentum_tilt, 4),
        size_tilt            = round(min(1.0, max(0.0, size_tilt)), 4),
        value_growth_tilt    = round(value_growth_tilt, 4),
        quality_concentration= round(quality_conc, 4),
        volatility_concentration=round(vol_conc, 4),
    )
