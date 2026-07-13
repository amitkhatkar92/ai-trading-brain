"""iios/investment/company/valuation/sensitivity_analysis.py
Sensitivity analysis: vary key DCF assumptions ±10%, ±20%, ±30%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.company.valuation.valuation_assumptions import (
    DCFAssumptions, WACCAssumptions,
)
from iios.investment.company.valuation.valuation_model import ValuationStatus
from iios.investment.company.valuation.dcf_engine import DCFEngine
from iios.investment.company.valuation.valuation_statistics import clamp


# Perturbation levels applied to each axis
_LEVELS = (-0.30, -0.20, -0.10, 0.00, +0.10, +0.20, +0.30)


@dataclass
class SensitivityTable:
    """One-way sensitivity table for a single assumption."""
    parameter:   str
    base_value:  float
    results:     Dict[str, Optional[float]] = field(default_factory=dict)
    # key: "+10%" / "-20%" etc, value: fair value per share

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter":  self.parameter,
            "base_value": round(self.base_value, 4),
            "results":    {k: round(v, 2) if v else None for k, v in self.results.items()},
        }


@dataclass
class SensitivityAnalysisResult:
    wacc_sensitivity:   SensitivityTable
    growth_sensitivity: SensitivityTable
    terminal_sensitivity: SensitivityTable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wacc":     self.wacc_sensitivity.to_dict(),
            "growth":   self.growth_sensitivity.to_dict(),
            "terminal": self.terminal_sensitivity.to_dict(),
        }


class SensitivityAnalysisEngine:
    """Vary WACC, growth, and terminal growth independently."""

    _DCF = DCFEngine()

    def run(
        self,
        assumptions:        DCFAssumptions,
        fcf_base:           Optional[float],
        net_debt:           Optional[float],
        shares_outstanding: Optional[float],
    ) -> Optional[SensitivityAnalysisResult]:
        if not fcf_base or not shares_outstanding or shares_outstanding <= 0:
            return None

        base_wacc   = assumptions.wacc.wacc()
        base_growth = assumptions.near_term_growth
        base_tg     = assumptions.terminal_growth

        wacc_table     = self._vary_wacc(assumptions, fcf_base, net_debt, shares_outstanding)
        growth_table   = self._vary_growth(assumptions, fcf_base, net_debt, shares_outstanding)
        terminal_table = self._vary_terminal(assumptions, fcf_base, net_debt, shares_outstanding)

        return SensitivityAnalysisResult(
            wacc_sensitivity     = wacc_table,
            growth_sensitivity   = growth_table,
            terminal_sensitivity = terminal_table,
        )

    def _vary_wacc(
        self, base: DCFAssumptions, fcf: float,
        net_debt: Optional[float], shares: float,
    ) -> SensitivityTable:
        table = SensitivityTable(parameter="wacc", base_value=base.wacc.wacc())
        for delta in _LEVELS:
            new_wacc = clamp(base.wacc.wacc() + delta * base.wacc.wacc(), 0.04, 0.40)
            wacc_clone = WACCAssumptions(wacc_override=new_wacc)
            dcf_clone  = DCFAssumptions(
                wacc=wacc_clone,
                near_term_growth=base.near_term_growth,
                mid_term_growth=base.mid_term_growth,
                terminal_growth=base.terminal_growth,
                projection_years=base.projection_years,
                near_term_years=base.near_term_years,
                terminal_method=base.terminal_method,
                terminal_fcf_multiple=base.terminal_fcf_multiple,
            )
            result = self._DCF.estimate(dcf_clone, fcf, net_debt, shares)
            key    = f"{int(delta*100):+d}%"
            table.results[key] = (
                result.intrinsic_value if result.status == ValuationStatus.COMPUTED else None
            )
        return table

    def _vary_growth(
        self, base: DCFAssumptions, fcf: float,
        net_debt: Optional[float], shares: float,
    ) -> SensitivityTable:
        table = SensitivityTable(parameter="near_term_growth", base_value=base.near_term_growth)
        for delta in _LEVELS:
            g = clamp(base.near_term_growth * (1 + delta), -0.20, 0.80)
            dcf_clone = DCFAssumptions(
                wacc=base.wacc,
                near_term_growth=g,
                mid_term_growth=base.mid_term_growth * (1 + delta * 0.5),
                terminal_growth=base.terminal_growth,
                projection_years=base.projection_years,
                near_term_years=base.near_term_years,
                terminal_method=base.terminal_method,
                terminal_fcf_multiple=base.terminal_fcf_multiple,
            )
            result = self._DCF.estimate(dcf_clone, fcf, net_debt, shares)
            key    = f"{int(delta*100):+d}%"
            table.results[key] = (
                result.intrinsic_value if result.status == ValuationStatus.COMPUTED else None
            )
        return table

    def _vary_terminal(
        self, base: DCFAssumptions, fcf: float,
        net_debt: Optional[float], shares: float,
    ) -> SensitivityTable:
        table = SensitivityTable(parameter="terminal_growth", base_value=base.terminal_growth)
        for delta in _LEVELS:
            tg = clamp(base.terminal_growth + delta * base.terminal_growth, 0.005, 0.07)
            dcf_clone = DCFAssumptions(
                wacc=base.wacc,
                near_term_growth=base.near_term_growth,
                mid_term_growth=base.mid_term_growth,
                terminal_growth=tg,
                projection_years=base.projection_years,
                near_term_years=base.near_term_years,
                terminal_method=base.terminal_method,
                terminal_fcf_multiple=base.terminal_fcf_multiple,
            )
            result = self._DCF.estimate(dcf_clone, fcf, net_debt, shares)
            key    = f"{int(delta*100):+d}%"
            table.results[key] = (
                result.intrinsic_value if result.status == ValuationStatus.COMPUTED else None
            )
        return table
