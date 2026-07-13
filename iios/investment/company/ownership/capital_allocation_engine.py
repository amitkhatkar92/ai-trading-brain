"""iios/investment/company/ownership/capital_allocation_engine.py
Capital allocation intelligence engine (ownership perspective).
Evaluates how management deploys and returns capital to shareholders.
"""
from __future__ import annotations

from typing import Any, Optional

from iios.investment.company.ownership.ownership_profile import (
    OwnershipCapitalAllocationProfile, CapitalAllocationQuality,
)
from iios.investment.company.ownership.capital_return import (
    score_dividend_sustainability,
    score_total_shareholder_return_quality,
    score_cash_return_policy,
)
from iios.investment.company.ownership.capital_deployment import (
    score_capex_quality,
    score_cash_utilization,
)
from iios.investment.company.ownership.capital_efficiency import (
    score_capital_efficiency_composite,
)
from iios.investment.company.ownership.ownership_statistics import (
    clamp, score_dividend_policy, score_buyback_quality,
)


def _label_capital_quality(score: float) -> CapitalAllocationQuality:
    if score >= 80:
        return CapitalAllocationQuality.EXCEPTIONAL
    if score >= 65:
        return CapitalAllocationQuality.DISCIPLINED
    if score >= 50:
        return CapitalAllocationQuality.ADEQUATE
    if score >= 35:
        return CapitalAllocationQuality.QUESTIONABLE
    if score >= 20:
        return CapitalAllocationQuality.DESTRUCTIVE
    return CapitalAllocationQuality.INSUFFICIENT


class OwnershipCapitalAllocationEngine:
    """
    Evaluates capital allocation from the shareholder value perspective.
    Distinct from governance/capital_allocation.py which focuses on board-level
    allocation quality; this engine focuses on shareholder returns, cash conversion,
    and capital productivity.
    """

    def compute(
        self,
        avg_roic:         Optional[float] = None,
        avg_roe:          Optional[float] = None,
        fcf_margin:       Optional[float] = None,
        fcf:              Optional[float] = None,
        net_income:       Optional[float] = None,
        avg_ocf_to_ni:    Optional[float] = None,
        payout_ratio:     Optional[float] = None,
        div_per_share:    Optional[float] = None,
        eps_cagr:         Optional[float] = None,
        revenue_cagr:     Optional[float] = None,
        capex:            Optional[float] = None,
        revenue:          Optional[float] = None,
        total_assets:     Optional[float] = None,
        total_equity:     Optional[float] = None,
        total_debt:       Optional[float] = None,
        cash:             Optional[float] = None,
        management_snapshot: Any = None,   # Optional[ManagementSnapshot]
    ) -> OwnershipCapitalAllocationProfile:

        profile = OwnershipCapitalAllocationProfile()
        expl: list[str] = []

        # ── Dividend policy ───────────────────────────────────────────────────
        profile.dividend_policy_score = score_dividend_policy(payout_ratio, eps_cagr)

        # ── Buyback quality ───────────────────────────────────────────────────
        profile.buyback_quality_score = score_buyback_quality(avg_roic, fcf_margin)

        # ── Reinvestment quality ──────────────────────────────────────────────
        capex_s = score_capex_quality(capex, revenue, revenue_cagr, avg_roic)
        profile.reinvestment_score = clamp(
            capex_s * 0.70 + (score_buyback_quality(avg_roic, fcf_margin) * 0.30)
        )

        # ── Debt management ───────────────────────────────────────────────────
        if total_equity and total_equity > 0 and total_debt is not None:
            de = total_debt / total_equity
            if de <= 0.3:
                profile.debt_management_score = 90.0
            elif de <= 0.7:
                profile.debt_management_score = 75.0
            elif de <= 1.5:
                profile.debt_management_score = 55.0
            elif de <= 3.0:
                profile.debt_management_score = 30.0
            else:
                profile.debt_management_score = 10.0
        else:
            profile.debt_management_score = 50.0

        # ── CapEx efficiency ──────────────────────────────────────────────────
        profile.capex_efficiency_score = score_capex_quality(capex, revenue, revenue_cagr, avg_roic)

        # ── Cash utilization ──────────────────────────────────────────────────
        profile.cash_utilization_score = score_cash_utilization(cash, revenue, fcf)

        # ── Cross-engine boosts from management governance ────────────────────
        if management_snapshot is not None:
            mgmt_cap = getattr(management_snapshot, "capital_allocation", None)
            mgmt_cap_score = getattr(mgmt_cap, "overall_capital_score", None)
            if mgmt_cap_score is not None and mgmt_cap_score >= 65:
                # Governance-confirmed disciplined capital allocation
                profile.dividend_policy_score  = clamp(profile.dividend_policy_score + 3.0)
                profile.buyback_quality_score  = clamp(profile.buyback_quality_score + 3.0)
                expl.append("Capital allocation boosted by governance-confirmed discipline.")

        # ── Overall capital score ─────────────────────────────────────────────
        profile.overall_capital_score = clamp(
            profile.dividend_policy_score  * 0.25
            + profile.buyback_quality_score  * 0.20
            + profile.reinvestment_score     * 0.25
            + profile.debt_management_score  * 0.20
            + profile.cash_utilization_score * 0.10
        )

        profile.capital_quality = _label_capital_quality(profile.overall_capital_score)
        profile.explanation = expl
        return profile
