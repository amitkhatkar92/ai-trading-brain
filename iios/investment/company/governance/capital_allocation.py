"""iios/investment/company/governance/capital_allocation.py
Capital allocation intelligence orchestrator.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.governance.management_profile import (
    CapitalAllocationProfile, CapitalAllocationLabel,
)
from iios.investment.company.governance.management_statistics import clamp
from iios.investment.company.governance.capital_efficiency import score_capital_efficiency
from iios.investment.company.governance.investment_quality import (
    score_reinvestment_quality, score_acquisition_quality,
)
from iios.investment.company.governance.shareholder_return import (
    score_dividend_policy, score_buyback_quality, score_debt_management,
)


def _label_capital(score: float) -> CapitalAllocationLabel:
    if score >= 80:
        return CapitalAllocationLabel.EXCEPTIONAL
    if score >= 65:
        return CapitalAllocationLabel.DISCIPLINED
    if score >= 45:
        return CapitalAllocationLabel.ADEQUATE
    if score >= 25:
        return CapitalAllocationLabel.QUESTIONABLE
    return CapitalAllocationLabel.DESTRUCTIVE


class CapitalAllocationEngine:
    """Compute CapitalAllocationProfile from financial snapshot data."""

    def compute(
        self,
        avg_roic:              Optional[float] = None,
        avg_roe:               Optional[float] = None,
        fcf_margin:            Optional[float] = None,
        avg_ocf_to_ni:         Optional[float] = None,
        dividend_payout_ratio: Optional[float] = None,
        dividend_per_share:    Optional[float] = None,
        debt_to_equity:        Optional[float] = None,
        avg_net_margin:        Optional[float] = None,
        net_margin:            Optional[float] = None,
        eps_cagr:              Optional[float] = None,
        revenue_cagr:          Optional[float] = None,
        sustainability:        Optional[float] = None,
    ) -> CapitalAllocationProfile:
        explanation: List[str] = []

        # ── Reinvestment quality ───────────────────────────────────────────────
        reinvest_score = score_reinvestment_quality(
            avg_roic=avg_roic,
            eps_cagr=eps_cagr,
            revenue_cagr=revenue_cagr,
            sustainability=sustainability,
        )
        if avg_roic is not None:
            explanation.append(f"Avg ROIC: {avg_roic:.1%} → reinvestment quality {reinvest_score:.0f}/100")

        # ── Capital efficiency ─────────────────────────────────────────────────
        cap_eff_score = score_capital_efficiency(
            avg_roic=avg_roic,
            avg_roe=avg_roe,
            fcf_margin=fcf_margin,
            avg_ocf_to_ni=avg_ocf_to_ni,
        )

        # ── Dividend policy ────────────────────────────────────────────────────
        div_score = score_dividend_policy(
            dividend_payout_ratio=dividend_payout_ratio,
            dividend_per_share=dividend_per_share,
            fcf_margin=fcf_margin,
        )
        if dividend_payout_ratio is not None:
            explanation.append(f"Dividend payout ratio: {dividend_payout_ratio:.0%}")

        # ── Buyback quality ────────────────────────────────────────────────────
        buyback_score = score_buyback_quality(
            avg_roic=avg_roic,
            fcf_margin=fcf_margin,
        )

        # ── Debt management ────────────────────────────────────────────────────
        debt_score = score_debt_management(
            debt_to_equity=debt_to_equity,
            avg_roic=avg_roic,
        )
        if debt_to_equity is not None:
            explanation.append(f"Debt/Equity: {debt_to_equity:.2f}")

        # ── Acquisition quality ────────────────────────────────────────────────
        acq_score = score_acquisition_quality(
            avg_roic=avg_roic,
            avg_net_margin=avg_net_margin,
            net_margin=net_margin,
        )

        # ── Composite ─────────────────────────────────────────────────────────
        overall = clamp(
            reinvest_score  * 0.25
            + cap_eff_score * 0.25
            + div_score     * 0.15
            + buyback_score * 0.10
            + debt_score    * 0.15
            + acq_score     * 0.10,
            0.0, 100.0,
        )
        label = _label_capital(overall)
        explanation.append(f"Capital allocation: {overall:.1f}/100 ({label.value})")

        return CapitalAllocationProfile(
            reinvestment_quality_score=round(reinvest_score, 1),
            dividend_policy_score=round(div_score, 1),
            buyback_quality_score=round(buyback_score, 1),
            debt_management_score=round(debt_score, 1),
            acquisition_quality_score=round(acq_score, 1),
            capital_efficiency_score=round(cap_eff_score, 1),
            overall_capital_score=round(overall, 1),
            capital_label=label,
            explanation=explanation,
        )
