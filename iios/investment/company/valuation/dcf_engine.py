"""iios/investment/company/valuation/dcf_engine.py
Two-stage DCF model consuming financial and earnings intelligence.
"""
from __future__ import annotations

import math
from typing import Any, List, Optional

from iios.investment.company.valuation.valuation_model import (
    ValuationModelType, ValuationResult, ValuationStatus,
)
from iios.investment.company.valuation.valuation_assumptions import DCFAssumptions
from iios.investment.company.valuation.valuation_statistics import (
    present_value, gordon_growth_terminal_value, clamp,
)


class DCFEngine:
    """
    Two-stage Free Cash Flow DCF model.

    Stage 1: Project FCF at near_term_growth for near_term_years.
    Stage 2: Project remaining years at mid_term_growth.
    Terminal: Gordon Growth or FCF multiple.

    Equity value per share = (EV + cash - total_debt) / shares_outstanding
    """

    def estimate(
        self,
        assumptions:        DCFAssumptions,
        fcf_base:           Optional[float],     # trailing FCF (absolute, same currency)
        net_debt:           Optional[float],     # total_debt - cash
        shares_outstanding: Optional[float],
        confidence_inputs:  float = 0.7,         # caller-supplied data confidence
    ) -> ValuationResult:
        """
        Args:
            assumptions:        DCFAssumptions (growth rates, WACC, terminal method)
            fcf_base:           Starting FCF — either trailing 12-month or normalised
            net_debt:           Net debt = total_debt - cash_and_equivalents
            shares_outstanding: Total diluted shares outstanding
            confidence_inputs:  Confidence in input data quality (0-1)
        """
        if fcf_base is None or shares_outstanding is None or shares_outstanding <= 0:
            return ValuationResult(
                model_type=ValuationModelType.DCF,
                status=ValuationStatus.INSUFFICIENT_DATA,
                explanation=["FCF base or shares outstanding not available"],
            )

        if fcf_base <= 0:
            return ValuationResult(
                model_type=ValuationModelType.DCF,
                status=ValuationStatus.INSUFFICIENT_DATA,
                confidence=0.1,
                explanation=["Negative or zero trailing FCF — DCF not applicable"],
            )

        wacc          = assumptions.wacc.wacc()
        g_near        = assumptions.near_term_growth
        g_mid         = assumptions.mid_term_growth
        g_term        = assumptions.terminal_growth
        n_total       = assumptions.projection_years
        n_near        = min(assumptions.near_term_years, n_total)

        if not assumptions.terminal_discount_check():
            g_term = wacc * 0.90   # enforce WACC > g

        # ── Project FCFs ───────────────────────────────────────────────────────
        cash_flows: List[float] = []
        fcf = fcf_base
        for t in range(1, n_total + 1):
            g = g_near if t <= n_near else g_mid
            fcf = fcf * (1.0 + g)
            cash_flows.append(fcf)

        fcf_terminal = cash_flows[-1]

        # ── Terminal value ────────────────────────────────────────────────────
        if assumptions.terminal_method == "multiple":
            tv = fcf_terminal * assumptions.terminal_fcf_multiple
        else:  # gordon
            tv = gordon_growth_terminal_value(fcf_terminal, wacc, g_term)

        # ── Present value ──────────────────────────────────────────────────────
        pv_fcfs = present_value(cash_flows, wacc)
        pv_tv   = tv / (1.0 + wacc) ** n_total

        enterprise_value = pv_fcfs + pv_tv

        # ── Bridge to equity value ─────────────────────────────────────────────
        net_d = net_debt or 0.0
        equity_value = enterprise_value - net_d

        if equity_value <= 0:
            return ValuationResult(
                model_type=ValuationModelType.DCF,
                status=ValuationStatus.COMPUTED,
                intrinsic_value=0.0,
                value_low=0.0,
                value_high=0.0,
                confidence=0.2,
                assumptions_used=assumptions.to_dict(),
                explanation=["Enterprise value below net debt — equity value negligible"],
            )

        per_share = equity_value / shares_outstanding

        # ── Sensitivity range (±20% on growth, ±50bps on WACC) ───────────────
        lo_val = self._estimate_value(
            fcf_base, wacc + 0.01, g_near * 0.80, g_mid * 0.80,
            g_term, n_near, n_total, net_d, shares_outstanding,
            assumptions.terminal_method, assumptions.terminal_fcf_multiple,
        )
        hi_val = self._estimate_value(
            fcf_base, wacc - 0.01, g_near * 1.20, g_mid * 1.20,
            g_term, n_near, n_total, net_d, shares_outstanding,
            assumptions.terminal_method, assumptions.terminal_fcf_multiple,
        )

        # ── Confidence ────────────────────────────────────────────────────────
        confidence = self._compute_confidence(
            fcf_base, g_near, wacc, confidence_inputs
        )

        return ValuationResult(
            model_type    = ValuationModelType.DCF,
            status        = ValuationStatus.COMPUTED,
            intrinsic_value = per_share,
            value_low     = max(0.0, lo_val),
            value_high    = hi_val,
            confidence    = confidence,
            assumptions_used = {
                **assumptions.to_dict(),
                "fcf_base":          fcf_base,
                "net_debt":          net_d,
                "shares":            shares_outstanding,
                "enterprise_value":  round(enterprise_value, 0),
            },
            explanation = [
                f"FCF base: {fcf_base:,.0f}",
                f"WACC: {wacc:.1%}, terminal growth: {g_term:.1%}",
                f"PV FCFs: {pv_fcfs:,.0f}, PV terminal: {pv_tv:,.0f}",
                f"EV: {enterprise_value:,.0f}, per share: {per_share:.2f}",
            ],
        )

    def _estimate_value(
        self, fcf_base, wacc, g_near, g_mid, g_term,
        n_near, n_total, net_debt, shares,
        terminal_method, terminal_multiple,
    ) -> float:
        if wacc <= g_term:
            g_term = wacc * 0.90
        cfs = []
        fcf = fcf_base
        for t in range(1, n_total + 1):
            g   = g_near if t <= n_near else g_mid
            fcf = fcf * (1.0 + g)
            cfs.append(fcf)
        tv = (
            cfs[-1] * terminal_multiple
            if terminal_method == "multiple"
            else gordon_growth_terminal_value(cfs[-1], wacc, g_term)
        )
        pv = present_value(cfs, wacc) + tv / (1.0 + wacc) ** n_total
        return max(0.0, (pv - net_debt) / shares)

    @staticmethod
    def _compute_confidence(
        fcf_base: float,
        growth: float,
        wacc: float,
        data_confidence: float,
    ) -> float:
        """Confidence in the DCF output."""
        c = data_confidence * 0.6   # base from data quality

        # Higher confidence when assumptions are conservative
        if growth <= 0.15 and wacc >= 0.08:
            c += 0.15
        elif growth <= 0.25:
            c += 0.10

        # Lower confidence for very high growth assumptions
        if growth > 0.30:
            c -= 0.15

        return clamp(c, 0, 1.0)
