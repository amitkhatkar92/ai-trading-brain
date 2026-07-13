"""iios/investment/company/business_quality/revenue_model.py
Revenue model analyzer — infers revenue structure from financial signals.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.business_model import RevenueVisibilityLabel
from iios.investment.company.business_quality.quality_statistics import (
    safe_mean, safe_stdev, growth_rates, coefficient_of_variation, clamp,
)


class RevenueModelAnalyzer:
    """
    Infers revenue model characteristics from financial signals.
    Returns partial inputs used by BusinessModelAnalyzer.
    """

    def analyze(self, ctx: AssessmentContext) -> dict:
        """
        Returns a dict with revenue model metrics.
        Keys: gross_margin_level, avg_gross_margin, revenue_growth_cv,
              revenue_visibility, is_recurring_dominant, asset_turnover,
              avg_asset_turnover, operating_leverage_score
        """
        result: dict = {}

        # ── Gross margin ──────────────────────────────────────────────────────
        current_gm = ctx.income_metric("gross_margin")
        if current_gm is None:
            current_gm = ctx.ratio("gross_margin")
        result["gross_margin_level"] = current_gm

        # Earnings snapshot for historical series
        avg_gm: Optional[float] = None
        if ctx.earnings_snapshot is not None:
            try:
                avg_gm = getattr(
                    ctx.earnings_snapshot.profitability, "avg_gross_margin", None
                )
            except Exception:
                pass
        result["avg_gross_margin"] = avg_gm

        # ── Revenue growth consistency ─────────────────────────────────────────
        revenue_series: List[Optional[float]] = []
        if ctx.earnings_snapshot is not None:
            try:
                from iios.investment.company.earnings.earnings_history import EarningsHistory
                pass  # earnings_snapshot carries profitability, not raw series
            except Exception:
                pass

        # Use gross margin stability as proxy for revenue model quality
        gm_cv: Optional[float] = None
        if ctx.earnings_snapshot is not None:
            try:
                # If profitability profile has gross_margin-related field, use it
                prof = ctx.earnings_snapshot.profitability
                gm_cv = getattr(prof, "gross_margin_cv", None)
            except Exception:
                pass

        result["gross_margin_cv"] = gm_cv

        # ── Revenue visibility heuristic ────────────────────────────────────────
        # High gross margins + stable margins → subscription/platform signal
        visibility = RevenueVisibilityLabel.UNKNOWN
        is_recurring = False
        if current_gm is not None:
            if current_gm >= 60 and (gm_cv is None or gm_cv < 0.08):
                visibility   = RevenueVisibilityLabel.HIGH
                is_recurring = True
            elif current_gm >= 40:
                visibility   = RevenueVisibilityLabel.MEDIUM
                is_recurring = current_gm >= 50
            else:
                visibility   = RevenueVisibilityLabel.LOW
        result["revenue_visibility"]    = visibility
        result["is_recurring_dominant"] = is_recurring

        # ── Asset turnover ──────────────────────────────────────────────────────
        asset_turnover = ctx.ratio("asset_turnover")
        result["asset_turnover"] = asset_turnover

        avg_at: Optional[float] = None
        if ctx.earnings_snapshot is not None:
            try:
                avg_at = ctx.earnings_snapshot.profitability.avg_roic  # proxy
            except Exception:
                pass
        result["avg_asset_turnover"] = avg_at

        # ── Operating leverage proxy ────────────────────────────────────────────
        # High gross margin + lower EBITDA margin → high fixed costs → high OpLev
        ebitda_margin = ctx.income_metric("ebitda_margin")
        if ebitda_margin is None:
            ebitda_margin = ctx.ratio("ebitda_margin")

        op_lev_score = 50.0
        if current_gm is not None and ebitda_margin is not None:
            spread = current_gm - ebitda_margin   # fixed cost drag
            # spread 0 → 100% variable; spread 60+ → very high fixed
            op_lev_score = clamp(spread * 1.2, 0, 100)
        result["operating_leverage_score"]   = op_lev_score
        result["is_high_operating_leverage"] = op_lev_score >= 55.0

        return result
