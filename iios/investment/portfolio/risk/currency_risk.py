"""iios/investment/portfolio/risk/currency_risk.py

Currency risk analysis: foreign exposure, FX concentration, currency shock impact.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    FOREIGN_CURRENCY_CRITICAL, FOREIGN_CURRENCY_WARNING,
    RiskLevel, bucket_weights, hhi, risk_score_to_level, RiskPosition,
)


@dataclass(frozen=True)
class CurrencyRiskResult:
    """Currency and FX risk metrics."""

    result_id:               str            = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:            str            = ""

    # Currency breakdown
    currency_weights:        Dict[str, float] = field(default_factory=dict)
    n_currencies:            int            = 1
    currency_hhi:            float          = 1.0   # concentration

    # Foreign exposure
    domestic_currency:       str            = "INR"
    domestic_weight:         float          = 1.0
    foreign_weight:          float          = 0.0

    # FX shock impact proxy: assumes -15% adverse move on all foreign positions
    fx_shock_impact_15pct:   float          = 0.0
    fx_shock_impact_30pct:   float          = 0.0

    # Largest foreign currency exposure
    largest_foreign_currency: str           = ""
    largest_foreign_weight:   float         = 0.0

    risk_level:              RiskLevel      = RiskLevel.VERY_LOW
    warnings:                tuple          = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "currency_weights":          {k: round(v, 4) for k, v in self.currency_weights.items()},
            "n_currencies":              self.n_currencies,
            "currency_hhi":              round(self.currency_hhi, 4),
            "domestic_weight":           round(self.domestic_weight, 4),
            "foreign_weight":            round(self.foreign_weight, 4),
            "fx_shock_impact_15pct":     round(self.fx_shock_impact_15pct, 4),
            "fx_shock_impact_30pct":     round(self.fx_shock_impact_30pct, 4),
            "largest_foreign_currency":  self.largest_foreign_currency,
            "largest_foreign_weight":    round(self.largest_foreign_weight, 4),
            "risk_level":                self.risk_level.value,
            "warnings":                  list(self.warnings),
        }


def analyze_currency_risk(
    positions:        List[RiskPosition],
    domestic_currency: str = "INR",
    portfolio_id:     str  = "",
) -> CurrencyRiskResult:
    if not positions:
        return CurrencyRiskResult(portfolio_id=portfolio_id)

    ccy_weights = bucket_weights(positions, "currency")
    n_ccy       = len(ccy_weights)
    ccy_hhi     = hhi(list(ccy_weights.values()))

    domestic_w  = ccy_weights.get(domestic_currency, 0.0)
    foreign_w   = sum(v for k, v in ccy_weights.items() if k != domestic_currency)

    # Largest single foreign currency
    foreign_ccys = {k: v for k, v in ccy_weights.items() if k != domestic_currency}
    if foreign_ccys:
        largest_ccy = max(foreign_ccys, key=foreign_ccys.__getitem__)
        largest_ccy_w = foreign_ccys[largest_ccy]
    else:
        largest_ccy   = ""
        largest_ccy_w = 0.0

    # FX shock impact (loss if all foreign currencies depreciate by X%)
    fx_impact_15 = foreign_w * 0.15
    fx_impact_30 = foreign_w * 0.30

    # Risk level: driven by foreign exposure
    raw_risk = foreign_w * 0.8 + (1.0 - ccy_hhi) * 0.2
    risk_level = risk_score_to_level(raw_risk)

    warnings = []
    if foreign_w >= FOREIGN_CURRENCY_CRITICAL:
        warnings.append(f"Critical foreign currency exposure {foreign_w:.1%}")
    elif foreign_w >= FOREIGN_CURRENCY_WARNING:
        warnings.append(f"Elevated foreign currency exposure {foreign_w:.1%}")
    if largest_ccy_w >= 0.40:
        warnings.append(f"High concentration in {largest_ccy} at {largest_ccy_w:.1%}")

    return CurrencyRiskResult(
        portfolio_id             = portfolio_id,
        currency_weights         = {k: round(v, 4) for k, v in ccy_weights.items()},
        n_currencies             = n_ccy,
        currency_hhi             = round(ccy_hhi, 4),
        domestic_currency        = domestic_currency,
        domestic_weight          = round(domestic_w, 4),
        foreign_weight           = round(foreign_w, 4),
        fx_shock_impact_15pct    = round(fx_impact_15, 4),
        fx_shock_impact_30pct    = round(fx_impact_30, 4),
        largest_foreign_currency = largest_ccy,
        largest_foreign_weight   = round(largest_ccy_w, 4),
        risk_level               = risk_level,
        warnings                 = tuple(warnings),
    )
