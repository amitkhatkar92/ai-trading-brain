"""iios/investment/company/valuation/asset_based_model.py
Asset-based / Net Asset Value model.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.valuation.valuation_model import (
    ValuationModelType, ValuationResult, ValuationStatus,
)
from iios.investment.company.valuation.valuation_statistics import clamp


class AssetBasedModel:
    """
    Asset-based valuation: NAV = (Total Assets × multiple) - Total Liabilities.
    Most relevant for: financial companies, real estate, liquidation scenarios.
    Applied with appropriate discount for going-concern businesses.
    """

    def estimate(
        self,
        total_assets:          Optional[float],
        total_liabilities:     Optional[float],
        shares_outstanding:    Optional[float],
        tangible_asset_multiple: float = 1.0,   # 1.0 = book, <1.0 = distressed, >1.0 = premium
        intangible_deduction:  float = 0.0,     # Intangibles to deduct (for conservative NAV)
        confidence_inputs:     float = 0.50,
    ) -> ValuationResult:
        if total_assets is None or total_liabilities is None or not shares_outstanding:
            return ValuationResult(
                model_type=ValuationModelType.ASSET_BASED,
                status=ValuationStatus.INSUFFICIENT_DATA,
                explanation=["Balance sheet data not available for NAV model"],
            )

        if shares_outstanding <= 0:
            return ValuationResult(
                model_type=ValuationModelType.ASSET_BASED,
                status=ValuationStatus.INSUFFICIENT_DATA,
                explanation=["Shares outstanding not available"],
            )

        adjusted_assets = (total_assets - intangible_deduction) * tangible_asset_multiple
        nav             = adjusted_assets - total_liabilities
        per_share       = nav / shares_outstanding

        # Range: apply ±20% to multiple assumption
        lo_per_share = max(
            0.0,
            ((total_assets * 0.80 - intangible_deduction) - total_liabilities) / shares_outstanding,
        )
        hi_per_share = (
            (total_assets * 1.20 - intangible_deduction * 0.5) - total_liabilities
        ) / shares_outstanding

        confidence = clamp(confidence_inputs * 0.6, 0, 0.75)

        return ValuationResult(
            model_type      = ValuationModelType.ASSET_BASED,
            status          = ValuationStatus.COMPUTED,
            intrinsic_value = per_share,
            value_low       = lo_per_share,
            value_high      = max(per_share, hi_per_share),
            confidence      = confidence,
            assumptions_used = {
                "tangible_multiple":    tangible_asset_multiple,
                "intangible_deduction": intangible_deduction,
                "nav":                  round(nav, 0),
            },
            explanation = [
                f"Total assets: {total_assets:,.0f}",
                f"Adjusted assets: {adjusted_assets:,.0f}",
                f"NAV: {nav:,.0f}, per share: {per_share:.2f}",
            ],
        )
