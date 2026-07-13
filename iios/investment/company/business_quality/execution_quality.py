"""iios/investment/company/business_quality/execution_quality.py
Execution quality analyzer — consistency and discipline of management execution.
"""
from __future__ import annotations

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.operational_quality import ExecutionQualityProfile
from iios.investment.company.business_quality.quality_statistics import clamp, safe_mean


class ExecutionQualityAnalyzer:
    """Measures operational execution quality from earnings and financial patterns."""

    def analyze(self, ctx: AssessmentContext) -> ExecutionQualityProfile:
        p = ExecutionQualityProfile()

        # ── Data from earnings snapshot ────────────────────────────────────────
        if ctx.earnings_snapshot is not None:
            try:
                earn = ctx.earnings_snapshot
                prof = earn.profitability
                risk = earn.risk
                qual = earn.quality

                # Revenue growth consistency: inverse of revenue volatility
                rev_vol = getattr(risk, "revenue_volatility", None)
                if rev_vol is not None:
                    # CV of revenue growth: 0 = perfect, 2+ = very inconsistent
                    p.revenue_growth_consistency = clamp(
                        100.0 - min(100.0, rev_vol * 40.0), 0, 100
                    )

                # Margin consistency: inverse of margin volatility
                margin_vol = getattr(risk, "margin_volatility", None)
                if margin_vol is not None:
                    p.margin_consistency = clamp(
                        100.0 - min(100.0, margin_vol * 15.0), 0, 100
                    )

                # Cost discipline: quality consistency score
                p.cost_discipline_score = getattr(qual, "consistency_score", 50.0)

                p.periods_analyzed = earn.history_depth

            except Exception:
                pass

        # ── Working capital trend ──────────────────────────────────────────────
        ccc = ctx.ratio("cash_conversion_cycle")
        if ccc is not None:
            if ccc < 30:
                p.working_capital_trend    = "excellent"
                p.wc_efficiency_score      = 90.0
            elif ccc < 60:
                p.working_capital_trend    = "good"
                p.wc_efficiency_score      = 70.0
            elif ccc < 90:
                p.working_capital_trend    = "average"
                p.wc_efficiency_score      = 55.0
            else:
                p.working_capital_trend    = "poor"
                p.wc_efficiency_score      = 30.0
        else:
            p.wc_efficiency_score = 50.0

        # ── Execution composite score ──────────────────────────────────────────
        components = []
        if p.revenue_growth_consistency is not None:
            components.append(p.revenue_growth_consistency * 0.35)
        if p.margin_consistency is not None:
            components.append(p.margin_consistency * 0.35)
        components.append(p.cost_discipline_score * 0.20)
        components.append(p.wc_efficiency_score * 0.10)

        p.execution_score = clamp(
            sum(components) / max(0.001, sum(
                [0.35 if p.revenue_growth_consistency else 0,
                 0.35 if p.margin_consistency else 0,
                 0.20, 0.10]
            )),
            0, 100,
        )

        p.consistency_score = safe_mean([
            p.revenue_growth_consistency,
            p.margin_consistency,
        ]) or p.cost_discipline_score

        # ── Flags ──────────────────────────────────────────────────────────────
        if p.execution_score >= 75.0:
            p.flags.append("high_execution_quality")
        if p.execution_score < 40.0:
            p.flags.append("poor_execution_consistency")

        return p
