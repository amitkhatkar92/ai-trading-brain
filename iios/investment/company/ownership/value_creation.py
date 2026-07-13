"""iios/investment/company/ownership/value_creation.py
Value creation analysis engine.
"""
from __future__ import annotations

from typing import Any, Optional

from iios.investment.company.ownership.ownership_profile import (
    ShareholderValueProfile, ShareholderValueLabel,
)
from iios.investment.company.ownership.economic_return import (
    score_economic_value_added,
    score_earnings_power,
    score_growth_value,
)
from iios.investment.company.ownership.capital_productivity import score_capital_productivity
from iios.investment.company.ownership.capital_return import score_dividend_sustainability
from iios.investment.company.ownership.ownership_statistics import clamp


def _label_value(score: float) -> ShareholderValueLabel:
    if score >= 80:
        return ShareholderValueLabel.EXCEPTIONAL
    if score >= 65:
        return ShareholderValueLabel.STRONG
    if score >= 50:
        return ShareholderValueLabel.ADEQUATE
    if score >= 35:
        return ShareholderValueLabel.WEAK
    if score >= 20:
        return ShareholderValueLabel.VALUE_DESTRUCTIVE
    return ShareholderValueLabel.INSUFFICIENT


class ShareholderValueEngine:
    """
    Produces a ShareholderValueProfile from financial and growth inputs.
    """

    def compute(
        self,
        avg_roic:          Optional[float] = None,
        avg_roe:           Optional[float] = None,
        fcf_margin:        Optional[float] = None,
        fcf:               Optional[float] = None,
        total_equity:      Optional[float] = None,
        total_debt:        Optional[float] = None,
        payout_ratio:      Optional[float] = None,
        avg_ocf_to_ni:     Optional[float] = None,
        div_per_share:     Optional[float] = None,
        eps_cagr:          Optional[float] = None,
        revenue_cagr:      Optional[float] = None,
        net_margin:        Optional[float] = None,
        avg_net_margin:    Optional[float] = None,
        consistency_score: Optional[float] = None,
        sustainability_score: Optional[float] = None,
        management_snapshot: Any = None,
        growth_snapshot:     Any = None,
    ) -> ShareholderValueProfile:

        profile = ShareholderValueProfile()
        expl: list[str] = []

        # ── Economic return score ─────────────────────────────────────────────
        profile.economic_return_score = score_economic_value_added(
            avg_roic, avg_roe, fcf_margin
        )

        # ── Capital productivity ───────────────────────────────────────────────
        profile.capital_productivity_score = score_capital_productivity(
            fcf, total_equity, total_debt, avg_roic, revenue_cagr
        )

        # ── Dividend sustainability ────────────────────────────────────────────
        profile.dividend_sustainability_score = score_dividend_sustainability(
            payout_ratio, eps_cagr, avg_ocf_to_ni, div_per_share
        )

        # ── Earnings power ─────────────────────────────────────────────────────
        profile.earnings_power_score = score_earnings_power(
            net_margin, avg_net_margin, eps_cagr, consistency_score
        )

        # ── Growth value ──────────────────────────────────────────────────────
        profile.growth_value_score = score_growth_value(
            revenue_cagr, eps_cagr, sustainability_score
        )

        # Cross-engine boosts
        if growth_snapshot is not None:
            gs = getattr(growth_snapshot, "growth_score", None)
            g_overall = getattr(gs, "overall_score", None)
            if g_overall is not None and g_overall >= 70:
                profile.growth_value_score = clamp(profile.growth_value_score + 5.0)
                expl.append("Growth value boosted by Growth Intelligence Engine score.")

        if management_snapshot is not None:
            mgmt_q = getattr(management_snapshot, "management_quality", None)
            lt_score = getattr(mgmt_q, "long_term_orientation_score", None)
            if lt_score is not None and lt_score >= 70:
                profile.capital_productivity_score = clamp(
                    profile.capital_productivity_score + 4.0
                )
                expl.append("Capital productivity boosted by strong management long-term orientation.")

        # ── Overall value score ───────────────────────────────────────────────
        profile.overall_value_score = clamp(
            profile.economic_return_score        * 0.30
            + profile.capital_productivity_score * 0.25
            + profile.earnings_power_score       * 0.20
            + profile.dividend_sustainability_score * 0.15
            + profile.growth_value_score         * 0.10
        )

        profile.value_label = _label_value(profile.overall_value_score)
        profile.explanation = expl
        return profile
