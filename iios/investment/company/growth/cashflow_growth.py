"""iios/investment/company/growth/cashflow_growth.py
Free cash flow and operating cash flow growth analysis engine.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.growth.growth_profile import (
    CAGRProfile, CashflowGrowthProfile, GrowthTrend, classify_growth,
)
from iios.investment.company.growth.growth_statistics import (
    cagr, cagr_from_series, growth_rates_from_series,
    trend_from_growth_rates, yoy_growth,
)


class CashflowGrowthEngine:
    """
    Compute FCF and OCF growth intelligence.
    Uses explicit time-series when provided; falls back to snapshot aggregates.
    """

    def compute(
        self,
        current_revenue:    Optional[float] = None,   # FinancialSnapshot.revenue
        current_fcf:        Optional[float] = None,   # cashflow_metrics.free_cash_flow
        current_ocf:        Optional[float] = None,   # cashflow_metrics.operating_cash_flow
        avg_fcf_margin:     Optional[float] = None,   # profitability.avg_fcf_margin
        fcf_series:         Optional[List[float]] = None,   # optional explicit FCF series
        ocf_series:         Optional[List[float]] = None,   # optional explicit OCF series
        history_depth:      int = 0,
    ) -> CashflowGrowthProfile:
        explanation: List[str] = []
        profile = CashflowGrowthProfile()

        # ── FCF margin (current) ────────────────────────────────────────────────
        if current_fcf is not None and current_revenue and current_revenue > 0:
            profile.current_fcf_margin = current_fcf / current_revenue
        profile.avg_fcf_margin = avg_fcf_margin

        # ── FCF CAGR from series ────────────────────────────────────────────────
        profile.fcf_cagr = self._cagr_from_series(
            fcf_series, label="FCF", depth=history_depth, explanation=explanation
        )

        # ── OCF CAGR from series ────────────────────────────────────────────────
        profile.ocf_cagr = self._cagr_from_series(
            ocf_series, label="OCF", depth=history_depth, explanation=explanation
        )

        # ── FCF margin trend ────────────────────────────────────────────────────
        cur_m = profile.current_fcf_margin
        avg_m = avg_fcf_margin
        if cur_m is not None and avg_m is not None:
            delta = cur_m - avg_m
            if delta > 0.02:
                profile.fcf_margin_trend = GrowthTrend.ACCELERATING
                explanation.append(f"FCF margin expanding: {cur_m:.1%} vs avg {avg_m:.1%}")
            elif delta < -0.02:
                profile.fcf_margin_trend = GrowthTrend.DECELERATING
                explanation.append(f"FCF margin contracting: {cur_m:.1%} vs avg {avg_m:.1%}")
            else:
                profile.fcf_margin_trend = GrowthTrend.STABLE
        elif avg_fcf_margin is not None:
            explanation.append(f"Avg FCF margin: {avg_fcf_margin:.1%} (current not available)")

        profile.explanation = explanation
        return profile

    def _cagr_from_series(
        self,
        series:      Optional[List[float]],
        label:       str,
        depth:       int,
        explanation: List[str],
    ) -> CAGRProfile:
        if not series or len(series) < 2:
            return CAGRProfile(periods_used=depth)
        n = len(series)
        rates = growth_rates_from_series(series)
        trend = trend_from_growth_rates(rates) if rates else GrowthTrend.INSUFFICIENT_DATA
        c1  = cagr(series[-2], series[-1], 1)  if n >= 2 else None
        c3  = cagr(series[-4], series[-1], 3)  if n >= 4 else None
        c5  = cagr(series[-6], series[-1], 5)  if n >= 6 else None
        best = c5 or c3 or c1
        if best is not None:
            explanation.append(f"{label} CAGR (best): {best:.1%}")
        return CAGRProfile(
            cagr_1y=c1, cagr_3y=c3, cagr_5y=c5,
            best_available=best, trend=trend, periods_used=n,
            label=classify_growth(best),
        )
