"""iios/investment/company/valuation/scenario_engine.py
Bull / Base / Bear scenario generation.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from iios.investment.company.valuation.valuation_assumptions import (
    DCFAssumptions, WACCAssumptions, ValuationAssumptions,
)
from iios.investment.company.valuation.valuation_model import ValuationStatus
from iios.investment.company.valuation.valuation_snapshot import ScenarioResult
from iios.investment.company.valuation.dcf_engine import DCFEngine
from iios.investment.company.valuation.valuation_statistics import clamp


class ScenarioEngine:
    """
    Generate bull / base / bear valuation scenarios by perturbing assumptions.

    Bear:  near_term_growth × 0.70, WACC +150bps
    Base:  as-provided assumptions
    Bull:  near_term_growth × 1.20, WACC -100bps

    Each scenario runs a DCF and returns a ScenarioResult.
    """

    _DCF = DCFEngine()

    def run(
        self,
        base_assumptions:     DCFAssumptions,
        fcf_base:             Optional[float],
        net_debt:             Optional[float],
        shares_outstanding:   Optional[float],
        market_price:         Optional[float],
    ) -> Tuple[Optional[ScenarioResult], Optional[ScenarioResult], Optional[ScenarioResult]]:
        """
        Returns (bull, base, bear) ScenarioResult tuples.
        Any may be None if FCF data is unavailable.
        """
        if fcf_base is None or shares_outstanding is None or shares_outstanding <= 0:
            return None, None, None

        bull_result = self._run_scenario(
            "bull", base_assumptions, fcf_base, net_debt, shares_outstanding,
            growth_factor=1.20, wacc_delta=-0.01, market_price=market_price,
        )
        base_result = self._run_scenario(
            "base", base_assumptions, fcf_base, net_debt, shares_outstanding,
            growth_factor=1.00, wacc_delta=0.00, market_price=market_price,
        )
        bear_result = self._run_scenario(
            "bear", base_assumptions, fcf_base, net_debt, shares_outstanding,
            growth_factor=0.70, wacc_delta=+0.015, market_price=market_price,
        )
        return bull_result, base_result, bear_result

    def _run_scenario(
        self,
        scenario:          str,
        base:              DCFAssumptions,
        fcf_base:          float,
        net_debt:          Optional[float],
        shares:            float,
        growth_factor:     float,
        wacc_delta:        float,
        market_price:      Optional[float],
    ) -> Optional[ScenarioResult]:
        # Clone wacc assumptions
        wacc_clone         = WACCAssumptions(
            risk_free_rate     = base.wacc.risk_free_rate,
            equity_risk_premium= base.wacc.equity_risk_premium,
            beta               = base.wacc.beta,
            cost_of_debt       = base.wacc.cost_of_debt,
            tax_rate           = base.wacc.tax_rate,
            debt_weight        = base.wacc.debt_weight,
            equity_weight      = base.wacc.equity_weight,
            wacc_override      = clamp(base.wacc.wacc() + wacc_delta, 0.04, 0.30),
        )
        scenario_dcf       = DCFAssumptions(
            wacc                = wacc_clone,
            projection_years    = base.projection_years,
            near_term_years     = base.near_term_years,
            near_term_growth    = base.near_term_growth * growth_factor,
            mid_term_growth     = base.mid_term_growth  * growth_factor,
            terminal_growth     = base.terminal_growth,
            terminal_method     = base.terminal_method,
            terminal_fcf_multiple = base.terminal_fcf_multiple,
        )

        result = self._DCF.estimate(
            assumptions        = scenario_dcf,
            fcf_base           = fcf_base,
            net_debt           = net_debt,
            shares_outstanding = shares,
            confidence_inputs  = 0.6,
        )

        fair_value = result.intrinsic_value if result.status == ValuationStatus.COMPUTED else None

        mos_pct: Optional[float] = None
        if fair_value and market_price and market_price > 0:
            mos_pct = (fair_value - market_price) / fair_value * 100.0

        return ScenarioResult(
            scenario   = scenario,
            fair_value = fair_value,
            mos_pct    = mos_pct,
            assumptions= {
                "near_term_growth": round(scenario_dcf.near_term_growth, 4),
                "mid_term_growth":  round(scenario_dcf.mid_term_growth, 4),
                "wacc":             round(wacc_clone.wacc(), 4),
                "terminal_growth":  round(scenario_dcf.terminal_growth, 4),
            },
            explanation = result.explanation,
        )
