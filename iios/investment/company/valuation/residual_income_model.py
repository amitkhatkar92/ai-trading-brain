"""iios/investment/company/valuation/residual_income_model.py
Residual Income Model (Ohlson / EVA-based).
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.valuation.valuation_model import (
    ValuationModelType, ValuationResult, ValuationStatus,
)
from iios.investment.company.valuation.valuation_assumptions import RIMAssumptions
from iios.investment.company.valuation.valuation_statistics import clamp, present_value


class ResidualIncomeModel:
    """
    Residual Income Model — intrinsic value as book value plus discounted
    future residual incomes (ROE above cost of equity).

    Value = BV0 + sum(PV of RI_t for t=1..n) + PV(terminal RI)
    RI_t  = (ROE_t - ke) * BV_{t-1}

    Uses a fade model: ROE decays linearly toward RIM target over fade_years.
    """

    def estimate(
        self,
        assumptions:         RIMAssumptions,
        book_value_per_share: Optional[float],   # current BV/share
        roe:                 Optional[float],    # current or avg ROE (fraction, not %)
        confidence_inputs:   float = 0.6,
    ) -> ValuationResult:
        if book_value_per_share is None or book_value_per_share <= 0:
            return ValuationResult(
                model_type=ValuationModelType.RESIDUAL_INCOME,
                status=ValuationStatus.INSUFFICIENT_DATA,
                explanation=["Book value per share not available"],
            )

        if roe is None:
            return ValuationResult(
                model_type=ValuationModelType.RESIDUAL_INCOME,
                status=ValuationStatus.INSUFFICIENT_DATA,
                explanation=["ROE not available for RIM"],
            )

        ke              = assumptions.cost_of_equity.cost_of_equity()
        target_roe      = assumptions.roe_mean_reversion
        fade_years      = assumptions.roe_fade_years

        # ── Fade ROE from current toward target ───────────────────────────────
        bv   = book_value_per_share
        ri_series = []
        current_roe = roe

        for t in range(1, fade_years + 1):
            # Linear fade toward target
            progress    = t / fade_years
            roe_t       = current_roe + progress * (target_roe - current_roe)
            ri_t        = (roe_t - ke) * bv
            ri_series.append(ri_t)
            bv          = bv * (1.0 + roe_t * 0.4)   # retain 40% earnings

        # ── Terminal RI (zero after fade — conservative) ───────────────────────
        pv_ris = present_value(ri_series, ke)
        intrinsic_value = book_value_per_share + pv_ris

        # Confidence: lower when ROE is highly above ke (harder to sustain)
        excess_roe = roe - ke
        if excess_roe > 0.15:
            conf_adj = -0.10
        elif excess_roe < 0:
            conf_adj = -0.15
        else:
            conf_adj = 0.0

        confidence = clamp(confidence_inputs * 0.7 + conf_adj, 0, 0.90)

        # Simple range: ±15%
        return ValuationResult(
            model_type      = ValuationModelType.RESIDUAL_INCOME,
            status          = ValuationStatus.COMPUTED,
            intrinsic_value = max(0.0, intrinsic_value),
            value_low       = max(0.0, intrinsic_value * 0.85),
            value_high      = intrinsic_value * 1.15,
            confidence      = confidence,
            assumptions_used = {
                "book_value_per_share": round(book_value_per_share, 2),
                "current_roe":         round(roe, 4),
                "cost_of_equity":      round(ke, 4),
                "target_roe":          round(target_roe, 4),
                "fade_years":          fade_years,
            },
            explanation = [
                f"BV/share: {book_value_per_share:.2f}, ROE: {roe:.1%}",
                f"Cost of equity: {ke:.1%}",
                f"PV residual incomes: {pv_ris:.2f}",
                f"Intrinsic value: {intrinsic_value:.2f}",
            ],
        )
