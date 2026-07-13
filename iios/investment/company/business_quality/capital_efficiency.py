"""iios/investment/company/business_quality/capital_efficiency.py
Capital efficiency analyzer.
"""
from __future__ import annotations

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.operational_quality import CapitalEfficiencyProfile
from iios.investment.company.business_quality.quality_statistics import clamp, safe_mean


class CapitalEfficiencyAnalyzer:
    """Computes capital efficiency metrics from financial snapshot ratios."""

    def analyze(self, ctx: AssessmentContext) -> CapitalEfficiencyProfile:
        p = CapitalEfficiencyProfile()

        # ── Returns on capital ─────────────────────────────────────────────────
        p.current_roic = ctx.ratio("roic") or ctx.ratio("return_on_invested_capital")
        p.current_roe  = ctx.ratio("roe")  or ctx.ratio("return_on_equity")
        p.current_roa  = ctx.ratio("roa")  or ctx.ratio("return_on_assets")

        if ctx.earnings_snapshot is not None:
            try:
                prof = ctx.earnings_snapshot.profitability
                p.avg_roic = getattr(prof, "avg_roic", None)
                p.avg_roe  = getattr(prof, "avg_roe", None)
                p.avg_roa  = getattr(prof, "avg_roa", None)
            except Exception:
                pass

        if p.avg_roic is None:
            p.avg_roic = p.current_roic
        if p.avg_roe is None:
            p.avg_roe = p.current_roe

        # ── Asset utilisation ──────────────────────────────────────────────────
        p.asset_turnover     = ctx.ratio("asset_turnover")
        p.avg_asset_turnover = p.asset_turnover   # fallback to current

        p.inventory_turnover = ctx.ratio("inventory_turnover")
        p.receivables_days   = (
            ctx.ratio("receivable_turnover_days")
            or ctx.ratio("dso")
            or ctx.ratio("days_sales_outstanding")
        )
        p.payables_days = (
            ctx.ratio("payable_turnover_days")
            or ctx.ratio("dpo")
            or ctx.ratio("days_payable_outstanding")
        )

        # Cash conversion cycle
        if (
            p.receivables_days is not None
            and p.payables_days is not None
        ):
            inv_days = (
                365.0 / p.inventory_turnover
                if p.inventory_turnover and p.inventory_turnover > 0
                else 0.0
            )
            p.cash_conversion_cycle = p.receivables_days + inv_days - p.payables_days

        # ── FCF metrics ────────────────────────────────────────────────────────
        p.fcf_margin  = ctx.cashflow_metric("fcf_margin") or ctx.ratio("fcf_margin")
        p.ocf_to_ni   = ctx.cashflow_metric("ocf_to_ni")

        if ctx.earnings_snapshot is not None:
            try:
                prof = ctx.earnings_snapshot.profitability
                p.avg_fcf_margin = getattr(prof, "avg_fcf_margin", None)
            except Exception:
                pass

        capex = ctx.cashflow_metric("capex_pct") or ctx.ratio("capex_pct")
        p.capex_pct = capex

        # ── Capital efficiency score (0-100) ───────────────────────────────────
        roic_score = 0.0
        if p.avg_roic is not None:
            roic_score = clamp(p.avg_roic * 3.5, 0, 70)   # 20% ROIC → 70 pts

        at_score = 0.0
        if p.asset_turnover is not None:
            at_score = clamp(p.asset_turnover * 15, 0, 30)   # AT=2 → 30 pts

        p.capital_efficiency_score = clamp(roic_score + at_score * 0.3, 0, 100)

        # ── Asset utilisation score ────────────────────────────────────────────
        at_util = 0.0
        if p.asset_turnover is not None:
            at_util = clamp(p.asset_turnover * 30, 0, 60)
        inv_util = 0.0
        if p.inventory_turnover is not None:
            inv_util = clamp(p.inventory_turnover * 2, 0, 30)
        rec_util = 0.0
        if p.receivables_days is not None:
            # Lower is better: 30 days → 30 pts, 90 days → 0 pts
            rec_util = clamp(max(0.0, 30.0 - (p.receivables_days - 30) / 2), 0, 30)

        p.asset_utilisation_score = clamp(
            at_util * 0.5 + inv_util * 0.3 + rec_util * 0.2, 0, 100
        )

        p.is_capital_efficient = p.capital_efficiency_score >= 60.0

        # ── Flags ──────────────────────────────────────────────────────────────
        if p.current_roic is not None and p.current_roic >= 20.0:
            p.flags.append("exceptional_roic")
        if p.cash_conversion_cycle is not None and p.cash_conversion_cycle < 0:
            p.flags.append("negative_ccc_float_business")
        if p.fcf_margin is not None and p.fcf_margin < 0:
            p.flags.append("negative_fcf")

        return p
