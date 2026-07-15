"""iios/investment/portfolio/risk/interest_rate_risk.py

Interest rate risk analysis: duration proxy, rate sensitivity, bond-like
income assets exposure.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    RiskLevel, bucket_weights, weighted_average, risk_score_to_level,
    RiskPosition,
)


# Rate-sensitive asset classes
RATE_SENSITIVE_CLASSES = frozenset(
    {"bond", "fixed_income", "debt", "reit", "infrastructure", "utility"}
)

# Duration proxy by asset class (in years)
DURATION_PROXY = {
    "bond":           7.0,
    "fixed_income":   7.0,
    "debt":           5.0,
    "reit":           4.0,
    "infrastructure": 4.0,
    "utility":        3.0,
    "equity":         0.0,
    "cash":           0.1,
}


@dataclass(frozen=True)
class InterestRateRiskResult:
    """Interest rate (duration) risk metrics for a portfolio."""

    result_id:                  str       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:               str       = ""

    # Duration
    portfolio_duration_proxy:   float     = 0.0   # years
    rate_sensitive_weight:      float     = 0.0   # weight in rate-sensitive assets

    # Rate sensitivity: portfolio impact for +100bps parallel shift
    impact_100bps:              float     = 0.0   # portfolio loss fraction
    impact_200bps:              float     = 0.0
    impact_minus_100bps:        float     = 0.0   # gain for -100bps (rate fall)

    # Asset class breakdown
    asset_class_weights:        Dict[str, float] = field(default_factory=dict)

    risk_level:                 RiskLevel = RiskLevel.VERY_LOW
    warnings:                   tuple     = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_duration_proxy": round(self.portfolio_duration_proxy, 4),
            "rate_sensitive_weight":    round(self.rate_sensitive_weight, 4),
            "impact_100bps":            round(self.impact_100bps, 4),
            "impact_200bps":            round(self.impact_200bps, 4),
            "asset_class_weights":      {k: round(v, 4) for k, v in self.asset_class_weights.items()},
            "risk_level":               self.risk_level.value,
            "warnings":                 list(self.warnings),
        }


def analyze_interest_rate_risk(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
) -> InterestRateRiskResult:
    if not positions:
        return InterestRateRiskResult(portfolio_id=portfolio_id)

    ac_weights = bucket_weights(positions, "asset_class")

    # Portfolio duration = Σ w_i × duration_i
    port_duration = sum(
        p.weight * DURATION_PROXY.get(p.asset_class.lower(), 0.0)
        for p in positions
    )

    rate_sensitive_w = sum(
        p.weight for p in positions
        if p.asset_class.lower() in RATE_SENSITIVE_CLASSES
    )

    # Price impact ≈ -Duration × ΔRate (Modified Duration approximation)
    impact_100bps     = port_duration * 0.01
    impact_200bps     = port_duration * 0.02
    impact_minus_100  = -port_duration * 0.01  # gain when rates fall

    # Risk level: driven by duration and rate-sensitive weight
    raw_risk = min(1.0, port_duration / 10.0) * 0.7 + rate_sensitive_w * 0.3
    risk_level = risk_score_to_level(raw_risk)

    warnings = []
    if port_duration >= 6.0:
        warnings.append(f"High portfolio duration {port_duration:.1f}y — elevated rate sensitivity")
    elif port_duration >= 3.0:
        warnings.append(f"Moderate portfolio duration {port_duration:.1f}y")
    if rate_sensitive_w >= 0.40:
        warnings.append(f"High rate-sensitive exposure {rate_sensitive_w:.1%}")

    return InterestRateRiskResult(
        portfolio_id              = portfolio_id,
        portfolio_duration_proxy  = round(port_duration, 4),
        rate_sensitive_weight     = round(rate_sensitive_w, 4),
        impact_100bps             = round(impact_100bps, 4),
        impact_200bps             = round(impact_200bps, 4),
        impact_minus_100bps       = round(impact_minus_100, 4),
        asset_class_weights       = {k: round(v, 4) for k, v in ac_weights.items()},
        risk_level                = risk_level,
        warnings                  = tuple(warnings),
    )
