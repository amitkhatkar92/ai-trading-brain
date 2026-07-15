"""iios/investment/portfolio/risk/credit_risk.py

Credit risk analysis: quality scores, default probability proxies, spread risk.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    CREDIT_HIGH_THRESHOLD, CREDIT_LOW_THRESHOLD,
    RiskLevel, bucket_weights, weighted_average, RiskPosition,
    risk_score_to_level,
)


@dataclass(frozen=True)
class CreditRiskResult:
    """Credit risk metrics for a portfolio."""

    result_id:             str       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:          str       = ""

    # Quality measures
    avg_credit_quality:    float     = 0.0   # 0=junk, 1=AAA
    min_credit_quality:    float     = 0.0
    weighted_quality_score:float     = 0.0

    # Default probability proxy (1 - credit_quality, scaled)
    default_prob_proxy:    float     = 0.0    # expected loss proxy
    credit_spread_proxy:   float     = 0.0    # bps-equivalent spread

    # Sub-investment-grade exposure (quality < 0.50)
    junk_weight:           float     = 0.0
    investment_grade_weight: float   = 1.0

    # Sector credit risk (highest sector default risk)
    highest_risk_sector:   str       = ""
    highest_risk_sector_weight: float = 0.0

    risk_level:            RiskLevel = RiskLevel.LOW
    warnings:              tuple     = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_credit_quality":      round(self.avg_credit_quality, 4),
            "min_credit_quality":      round(self.min_credit_quality, 4),
            "default_prob_proxy":      round(self.default_prob_proxy, 4),
            "credit_spread_proxy":     round(self.credit_spread_proxy, 2),
            "junk_weight":             round(self.junk_weight, 4),
            "investment_grade_weight": round(self.investment_grade_weight, 4),
            "highest_risk_sector":     self.highest_risk_sector,
            "risk_level":              self.risk_level.value,
            "warnings":                list(self.warnings),
        }


def analyze_credit_risk(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
) -> CreditRiskResult:
    if not positions:
        return CreditRiskResult(portfolio_id=portfolio_id)

    avg_quality = weighted_average(positions, "credit_quality")
    min_quality = min(p.credit_quality for p in positions)

    # Default probability: (1 - credit_quality)^2 * weight  (convex — penalises junk)
    default_prob = sum(
        p.weight * (1.0 - p.credit_quality) ** 2 for p in positions
    )

    # Credit spread proxy: map default_prob to basis points
    # 0 → 0 bps, 0.25 → 300 bps (rough institutional proxy)
    spread_bps = default_prob * 1200.0

    # Junk weight: positions with credit_quality < 0.50
    junk_w  = sum(p.weight for p in positions if p.credit_quality < 0.50)
    ig_w    = 1.0 - junk_w

    # Highest default-risk sector
    sector_default: Dict[str, float] = {}
    sector_w: Dict[str, float] = {}
    for p in positions:
        s = p.sector or "unknown"
        sector_default[s] = sector_default.get(s, 0.0) + p.weight * (1.0 - p.credit_quality)
        sector_w[s]       = sector_w.get(s, 0.0) + p.weight
    worst_sector = max(sector_default, key=lambda s: sector_default[s], default="")
    worst_sector_w = sector_w.get(worst_sector, 0.0)

    # Risk level driven by avg quality and junk weight
    raw_risk = (1.0 - avg_quality) * 0.6 + junk_w * 0.4
    risk_level = risk_score_to_level(raw_risk)

    warnings = []
    if avg_quality < CREDIT_LOW_THRESHOLD:
        warnings.append(f"Very low average credit quality {avg_quality:.2f}")
    elif avg_quality < CREDIT_HIGH_THRESHOLD * 0.75:
        warnings.append(f"Below-average credit quality {avg_quality:.2f}")
    if junk_w >= 0.20:
        warnings.append(f"Significant sub-investment-grade exposure {junk_w:.1%}")
    if min_quality < 0.20:
        warnings.append(f"Position with near-default credit quality {min_quality:.2f}")

    return CreditRiskResult(
        portfolio_id            = portfolio_id,
        avg_credit_quality      = round(avg_quality, 4),
        min_credit_quality      = round(min_quality, 4),
        weighted_quality_score  = round(avg_quality, 4),
        default_prob_proxy      = round(default_prob, 6),
        credit_spread_proxy     = round(spread_bps, 2),
        junk_weight             = round(junk_w, 4),
        investment_grade_weight = round(ig_w, 4),
        highest_risk_sector     = worst_sector,
        highest_risk_sector_weight = round(worst_sector_w, 4),
        risk_level              = risk_level,
        warnings                = tuple(warnings),
    )
