"""iios/investment/company/valuation/dividend_discount_model.py
Gordon Growth Dividend Discount Model.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.valuation.valuation_model import (
    ValuationModelType, ValuationResult, ValuationStatus,
)
from iios.investment.company.valuation.valuation_assumptions import DDMAssumptions
from iios.investment.company.valuation.valuation_statistics import clamp


class DividendDiscountModel:
    """
    Single-stage Gordon Growth DDM.
    Intrinsic Value = D0 * (1 + g) / (ke - g)
    where D0 = current annual dividend per share.
    Only applicable when the company pays dividends.
    """

    def estimate(
        self,
        assumptions:         DDMAssumptions,
        dividend_per_share:  Optional[float],   # trailing annual DPS
        payout_ratio:        Optional[float],   # from financial data
        earnings_per_share:  Optional[float],   # trailing EPS
        confidence_inputs:   float = 0.6,
    ) -> ValuationResult:
        dps = dividend_per_share

        # Derive DPS from EPS × payout if not directly available
        if dps is None and earnings_per_share and payout_ratio:
            dps = earnings_per_share * payout_ratio

        if not dps or dps <= 0:
            return ValuationResult(
                model_type=ValuationModelType.DDM,
                status=ValuationStatus.SKIPPED,
                confidence=0.0,
                explanation=["No dividend — DDM not applicable"],
            )

        ke = assumptions.cost_of_equity.cost_of_equity()
        g  = assumptions.dividend_growth

        if ke <= g:
            g = ke * 0.90
            note = "Dividend growth capped at 90% of cost of equity"
        else:
            note = None

        d1 = dps * (1.0 + g)
        intrinsic_value = d1 / (ke - g)

        # Sensitivity: ±50bps on ke, ±100bps on g
        lo_val = (dps * (1.0 + max(0, g - 0.01))) / (ke + 0.005 - max(0, g - 0.01))
        hi_val = (dps * (1.0 + g + 0.01))         / (ke - 0.005 - (g + 0.01))

        confidence = clamp(confidence_inputs * 0.7, 0, 0.85)

        explanation = [
            f"DPS: {dps:.2f}, D1: {d1:.2f}",
            f"Cost of equity: {ke:.1%}, dividend growth: {g:.1%}",
            f"Intrinsic value: {intrinsic_value:.2f}",
        ]
        if note:
            explanation.append(note)

        return ValuationResult(
            model_type      = ValuationModelType.DDM,
            status          = ValuationStatus.COMPUTED,
            intrinsic_value = intrinsic_value,
            value_low       = max(0.0, lo_val),
            value_high      = max(intrinsic_value, hi_val),
            confidence      = confidence,
            assumptions_used = {
                "dps":             dps,
                "dividend_growth": g,
                "cost_of_equity":  round(ke, 4),
            },
            explanation = explanation,
        )
