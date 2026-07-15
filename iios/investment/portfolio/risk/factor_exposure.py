"""iios/investment/portfolio/risk/factor_exposure.py

Factor exposure analysis: quality, value, growth, momentum, size, low-vol.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    weighted_average, RiskPosition,
)


@dataclass(frozen=True)
class FactorExposureResult:
    """Systematic factor exposure for institutional risk attribution."""

    result_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str   = ""

    # Factor tilts [-1, +1]; positive = tilted toward factor
    quality_tilt:    float = 0.0    # high conviction → quality
    value_tilt:      float = 0.0    # low risk_score + high credit → value
    growth_tilt:     float = 0.0    # high risk_score + high conviction → growth
    momentum_tilt:   float = 0.0    # high confidence → momentum
    low_vol_tilt:    float = 0.0    # low risk_score → low-vol factor
    size_tilt:       float = 0.0    # proxy via concentration

    # Factor concentrations [0, 1]; higher = more concentrated in factor
    quality_concentration:  float = 0.0
    growth_concentration:   float = 0.0
    momentum_concentration: float = 0.0

    # Dominant factor
    dominant_factor:        str   = ""
    dominant_factor_score:  float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality_tilt":    round(self.quality_tilt, 4),
            "value_tilt":      round(self.value_tilt, 4),
            "growth_tilt":     round(self.growth_tilt, 4),
            "momentum_tilt":   round(self.momentum_tilt, 4),
            "low_vol_tilt":    round(self.low_vol_tilt, 4),
            "size_tilt":       round(self.size_tilt, 4),
            "dominant_factor": self.dominant_factor,
            "dominant_factor_score": round(self.dominant_factor_score, 4),
        }


def analyze_factor_exposure(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
) -> FactorExposureResult:
    if not positions:
        return FactorExposureResult(
            portfolio_id=portfolio_id,
            dominant_factor="none",
        )

    avg_risk     = weighted_average(positions, "risk_score")
    avg_conv     = weighted_average(positions, "conviction")
    avg_conf     = weighted_average(positions, "confidence")
    avg_credit   = weighted_average(positions, "credit_quality")
    avg_liq      = weighted_average(positions, "liquidity")

    # Quality tilt: high conviction + high credit quality → quality factor
    quality = avg_conv * 0.6 + avg_credit * 0.4

    # Value tilt: low risk (defensive) + high credit (financials) → value proxy
    value = (1.0 - avg_risk) * 0.5 + avg_credit * 0.3 + avg_liq * 0.2

    # Growth tilt: high risk_score + high conviction (growth/momentum stocks)
    growth = avg_risk * 0.5 + avg_conv * 0.5

    # Momentum tilt: high confidence signal
    momentum = avg_conf

    # Low-vol tilt: lower risk_score → low-vol factor
    low_vol = 1.0 - avg_risk

    # Size tilt: proxy using position count (more positions → large cap diversified)
    n = len(positions)
    size = min(1.0, n / 20.0)  # 20 positions → full large-cap tilt

    # Concentrations (std dev of attribute across positions — high = concentrated)
    if n > 1:
        mean_q = sum(p.conviction for p in positions) / n
        quality_conc = 1.0 - min(
            1.0,
            sum((p.conviction - mean_q) ** 2 for p in positions) / n / 0.04
        )
        mean_rs = sum(p.risk_score for p in positions) / n
        growth_conc = 1.0 - min(
            1.0,
            sum((p.risk_score - mean_rs) ** 2 for p in positions) / n / 0.04
        )
        mean_cf = sum(p.confidence for p in positions) / n
        momentum_conc = 1.0 - min(
            1.0,
            sum((p.confidence - mean_cf) ** 2 for p in positions) / n / 0.04
        )
    else:
        quality_conc = momentum_conc = growth_conc = 0.5

    # Dominant factor
    factors = {
        "quality":  quality,
        "growth":   growth,
        "momentum": momentum,
        "value":    value,
        "low_vol":  low_vol,
    }
    dom_factor = max(factors, key=factors.__getitem__)

    return FactorExposureResult(
        portfolio_id           = portfolio_id,
        quality_tilt           = round(quality, 4),
        value_tilt             = round(value, 4),
        growth_tilt            = round(growth, 4),
        momentum_tilt          = round(momentum, 4),
        low_vol_tilt           = round(low_vol, 4),
        size_tilt              = round(size, 4),
        quality_concentration  = round(max(0.0, quality_conc), 4),
        growth_concentration   = round(max(0.0, growth_conc), 4),
        momentum_concentration = round(max(0.0, momentum_conc), 4),
        dominant_factor        = dom_factor,
        dominant_factor_score  = round(factors[dom_factor], 4),
    )
