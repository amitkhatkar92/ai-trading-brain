"""iios/investment/company/business_quality/business_risk.py
Business risk profile analyzer.
"""
from __future__ import annotations

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.business_resilience import BusinessRiskProfile
from iios.investment.company.business_quality.quality_statistics import clamp


class BusinessRiskAnalyzer:
    """Computes financial and earnings risk signals."""

    def analyze(self, ctx: AssessmentContext) -> BusinessRiskProfile:
        p = BusinessRiskProfile()

        # ── Leverage ───────────────────────────────────────────────────────────
        p.debt_to_equity = (
            ctx.ratio("debt_to_equity")
            or ctx.ratio("total_debt_to_equity")
            or ctx.balance_metric("debt_to_equity")
        )
        p.interest_coverage = (
            ctx.ratio("interest_coverage")
            or ctx.ratio("ebit_to_interest")
        )
        p.net_debt_to_ebitda = ctx.ratio("net_debt_to_ebitda")

        if p.debt_to_equity is not None and p.debt_to_equity > 2.5:
            p.is_over_leveraged = True
            p.flags.append(f"high_leverage:{p.debt_to_equity:.1f}x")
        if p.interest_coverage is not None and p.interest_coverage < 3.0:
            p.flags.append(f"low_interest_coverage:{p.interest_coverage:.1f}x")

        # ── Liquidity ──────────────────────────────────────────────────────────
        p.current_ratio = ctx.ratio("current_ratio") or ctx.balance_metric("current_ratio")
        p.quick_ratio   = ctx.ratio("quick_ratio")

        if p.current_ratio is not None and p.current_ratio < 1.0:
            p.is_liquidity_stressed = True
            p.flags.append("current_ratio_below_1")

        # ── Earnings quality ───────────────────────────────────────────────────
        if ctx.earnings_snapshot is not None:
            try:
                p.earnings_quality_score = ctx.earnings_snapshot.quality.overall_score
                p.has_high_accruals = (
                    getattr(ctx.earnings_snapshot.quality, "avg_accruals_ratio", 0.0) or 0.0
                ) > 0.08
            except Exception:
                pass

        # ── Financial risk score (0-100, higher = riskier) ────────────────────
        risk = 30.0   # baseline

        if p.debt_to_equity is not None:
            risk += clamp((p.debt_to_equity - 1.0) * 10, 0, 30)

        if p.interest_coverage is not None:
            if p.interest_coverage < 3.0:
                risk += 20.0
            elif p.interest_coverage < 5.0:
                risk += 10.0

        if p.is_liquidity_stressed:
            risk += 15.0

        if p.earnings_quality_score < 40.0:
            risk += 10.0

        p.financial_risk_score = clamp(risk, 0, 100)

        return p
