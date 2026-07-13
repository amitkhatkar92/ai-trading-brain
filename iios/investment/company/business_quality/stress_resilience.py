"""iios/investment/company/business_quality/stress_resilience.py
Stress resilience analyzer — FCF durability and balance sheet buffers.
"""
from __future__ import annotations

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.business_resilience import StressResilienceProfile
from iios.investment.company.business_quality.quality_statistics import clamp


class StressResilienceAnalyzer:
    """Evaluates ability to sustain through economic downturns."""

    def analyze(self, ctx: AssessmentContext) -> StressResilienceProfile:
        p = StressResilienceProfile()

        # ── FCF durability ─────────────────────────────────────────────────────
        p.avg_fcf_margin = None
        p.min_fcf_margin = None
        p.is_fcf_positive_all = False

        if ctx.earnings_snapshot is not None:
            try:
                prof = ctx.earnings_snapshot.profitability
                p.avg_fcf_margin = getattr(prof, "avg_fcf_margin", None)
                p.min_fcf_margin = getattr(prof, "trough_fcf_margin", None)

                # Check if any FCF negative periods
                risk = ctx.earnings_snapshot.risk
                loss_rate = getattr(risk, "loss_rate", None)
                p.is_fcf_positive_all = (loss_rate is not None and loss_rate == 0.0)
            except Exception:
                pass

        if p.avg_fcf_margin is None:
            p.avg_fcf_margin = ctx.cashflow_metric("fcf_margin") or ctx.ratio("fcf_margin")

        # ── Margin floors ──────────────────────────────────────────────────────
        p.min_gross_margin = None
        p.min_ebit_margin  = None

        if ctx.earnings_snapshot is not None:
            try:
                prof = ctx.earnings_snapshot.profitability
                p.min_gross_margin = getattr(prof, "trough_gross_margin", None)
                p.min_ebit_margin  = getattr(prof, "trough_ebit_margin", None)
            except Exception:
                pass

        # ── Interest coverage ──────────────────────────────────────────────────
        p.avg_interest_coverage = (
            ctx.ratio("interest_coverage")
            or ctx.ratio("ebit_to_interest")
        )

        # ── Resilience score (0-100, high = more resilient) ───────────────────
        score = 40.0   # baseline

        if p.avg_fcf_margin is not None:
            if p.avg_fcf_margin >= 15.0:
                score += 25.0
            elif p.avg_fcf_margin >= 5.0:
                score += 15.0
            elif p.avg_fcf_margin >= 0.0:
                score += 5.0
            else:
                score -= 15.0

        if p.is_fcf_positive_all:
            score += 10.0

        if p.min_gross_margin is not None:
            if p.min_gross_margin >= 30.0:
                score += 10.0
            elif p.min_gross_margin < 10.0:
                score -= 10.0

        if p.avg_interest_coverage is not None:
            if p.avg_interest_coverage >= 10.0:
                score += 10.0
            elif p.avg_interest_coverage >= 5.0:
                score += 5.0
            elif p.avg_interest_coverage < 2.0:
                score -= 15.0

        p.stress_resilience_score = clamp(score, 0, 100)
        p.is_stress_resilient     = p.stress_resilience_score >= 60.0

        # ── Flags ──────────────────────────────────────────────────────────────
        if p.avg_fcf_margin is not None and p.avg_fcf_margin >= 15.0:
            p.flags.append("strong_fcf_generator")
        if p.avg_fcf_margin is not None and p.avg_fcf_margin < 0:
            p.flags.append("fcf_negative")
        if p.avg_interest_coverage is not None and p.avg_interest_coverage < 2.0:
            p.flags.append("debt_service_risk")

        return p
