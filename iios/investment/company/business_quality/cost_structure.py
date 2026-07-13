"""iios/investment/company/business_quality/cost_structure.py
Cost structure analyzer — infers cost model characteristics.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.business_model import CapexIntensityLabel
from iios.investment.company.business_quality.quality_statistics import safe_mean, clamp


class CostStructureAnalyzer:
    """Infers cost structure from financial snapshot ratios."""

    def analyze(self, ctx: AssessmentContext) -> dict:
        """
        Returns dict with:
        capex_pct_revenue, avg_capex_pct, capex_intensity,
        is_asset_light, sga_pct, rd_pct, is_rd_intensive
        """
        result: dict = {}

        # ── CapEx intensity ────────────────────────────────────────────────────
        capex_pct = ctx.cashflow_metric("capex_pct")
        if capex_pct is None:
            # Derive: capex / revenue (if both available)
            revenue = ctx.fs_metric("revenue")
            capex   = ctx.cashflow_metric("capex")
            if capex is None:
                capex = ctx.ratio("capex")
            if revenue and capex and revenue > 0:
                capex_pct = abs(capex) / revenue * 100.0

        result["capex_pct_revenue"] = capex_pct

        # Historical average capex pct via earnings profitability
        avg_capex: Optional[float] = None
        if ctx.earnings_snapshot is not None:
            try:
                avg_capex = getattr(
                    ctx.earnings_snapshot.profitability, "avg_fcf_capex_pct", None
                )
            except Exception:
                pass
        result["avg_capex_pct"] = avg_capex if avg_capex is not None else capex_pct

        # Classify CapEx intensity
        intensity = CapexIntensityLabel.UNKNOWN
        is_asset_light = False
        ref = capex_pct if capex_pct is not None else avg_capex
        if ref is not None:
            if ref < 5.0:
                intensity      = CapexIntensityLabel.LIGHT
                is_asset_light = True
            elif ref < 15.0:
                intensity = CapexIntensityLabel.MODERATE
            else:
                intensity = CapexIntensityLabel.HEAVY

        result["capex_intensity"] = intensity
        result["is_asset_light"]  = is_asset_light

        # ── SGA and R&D ────────────────────────────────────────────────────────
        sga_pct = ctx.income_metric("sga_pct")
        if sga_pct is None:
            sga_pct = ctx.ratio("sga_pct")
        result["sga_pct"] = sga_pct

        rd_pct = ctx.income_metric("rd_pct")
        if rd_pct is None:
            rd_pct = ctx.ratio("rd_pct")
        result["rd_pct"]        = rd_pct
        result["is_rd_intensive"] = (rd_pct is not None and rd_pct >= 5.0)

        return result
