"""iios/investment/company/valuation/margin_of_safety.py
Compute MarginOfSafetyProfile from a FairValueEstimate and market price.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.valuation.fair_value_estimate import (
    FairValueEstimate, MarginOfSafetyProfile, classify_margin_of_safety,
)


class MarginOfSafetyEngine:
    """Compute margin of safety metrics given a fair value and market price."""

    def compute(
        self,
        fair_value_estimate: FairValueEstimate,
        market_price:        Optional[float],
    ) -> Optional[MarginOfSafetyProfile]:
        if market_price is None or market_price <= 0:
            return None

        fv = fair_value_estimate.intrinsic_value
        if fv is None or fv <= 0:
            return None

        mp = market_price
        mos_pct     = (fv - mp) / fv * 100.0          # positive = undervalued
        premium_pct = (mp - fv) / fv * 100.0           # positive = overvalued
        upside      = (fv - mp) / mp * 100.0            # % gain if price → FV
        downside    = (fv - mp) / mp * 100.0            # same formula, sign carries meaning

        band = classify_margin_of_safety(mos_pct)

        explanation = [
            f"Fair value: {fv:.2f}, Market price: {mp:.2f}",
            f"Margin of safety: {mos_pct:.1f}%",
        ]
        if mos_pct >= 15:
            explanation.append(f"Price is {mos_pct:.1f}% below fair value estimate")
        elif mos_pct <= -15:
            explanation.append(f"Price is {abs(mos_pct):.1f}% above fair value estimate")
        else:
            explanation.append("Price is near fair value estimate")

        return MarginOfSafetyProfile(
            fair_value            = fv,
            market_price          = mp,
            margin_of_safety_pct  = mos_pct,
            premium_discount_pct  = premium_pct,
            upside_to_fair_value  = upside,
            downside_to_fair_value= downside,
            band                  = band,
            is_undervalued        = mos_pct >= 15.0,
            is_overvalued         = mos_pct <= -15.0,
            explanation           = explanation,
        )
