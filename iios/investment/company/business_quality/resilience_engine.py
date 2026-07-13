"""iios/investment/company/business_quality/resilience_engine.py
Orchestrates cyclicality, business risk, and stress resilience into ResilienceProfile.
"""
from __future__ import annotations

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.business_resilience import (
    ResilienceProfile, PricingPowerLabel,
)
from iios.investment.company.business_quality.cyclicality import CyclicalityDetector
from iios.investment.company.business_quality.business_risk import BusinessRiskAnalyzer
from iios.investment.company.business_quality.stress_resilience import StressResilienceAnalyzer
from iios.investment.company.business_quality.quality_statistics import clamp


class ResilienceEngine:
    """Produces a complete ResilienceProfile."""

    def __init__(self) -> None:
        self._cycl    = CyclicalityDetector()
        self._risk    = BusinessRiskAnalyzer()
        self._stress  = StressResilienceAnalyzer()

    def analyze(self, ctx: AssessmentContext) -> ResilienceProfile:
        cycl   = self._cycl.analyze(ctx)
        risk   = self._risk.analyze(ctx)
        stress = self._stress.analyze(ctx)

        # ── Pricing power inference ─────────────────────────────────────────────
        pricing_power, pp_score = self._infer_pricing_power(ctx)

        # ── Resilience composite ───────────────────────────────────────────────
        # Invert cyclicality (low cyclicality → high resilience)
        cyclicality_contribution = 100.0 - cycl.cyclicality_score
        # Invert risk (low risk → high resilience)
        risk_contribution = 100.0 - risk.financial_risk_score

        composite = (
            cyclicality_contribution * 0.30
            + risk_contribution      * 0.30
            + stress.stress_resilience_score * 0.25
            + pp_score               * 0.15
        )

        profile = ResilienceProfile(
            cyclicality       = cycl,
            business_risk     = risk,
            stress_resilience = stress,
            pricing_power     = pricing_power,
            pricing_power_score = pp_score,
            resilience_score  = clamp(composite),
            is_resilient      = composite >= 60.0,
        )

        # ── Flags ──────────────────────────────────────────────────────────────
        if profile.is_resilient:
            profile.flags.append("business_resilient")
        if risk.is_over_leveraged:
            profile.flags.append("leverage_risk")
        if risk.is_liquidity_stressed:
            profile.flags.append("liquidity_risk")
        if stress.is_stress_resilient:
            profile.flags.append("stress_resilient")

        return profile

    def _infer_pricing_power(self, ctx: AssessmentContext):
        """Infer pricing power from gross margin trend and level."""
        gm  = ctx.income_metric("gross_margin") or ctx.ratio("gross_margin")
        avg_gm = None
        if ctx.earnings_snapshot:
            try:
                avg_gm = ctx.earnings_snapshot.profitability.avg_gross_margin
            except Exception:
                pass

        ref = avg_gm or gm
        if ref is None:
            return PricingPowerLabel.UNKNOWN, 50.0

        # Gross margin > 50% → strong pricing power
        if ref >= 50.0:
            return PricingPowerLabel.STRONG, clamp(60.0 + (ref - 50.0) * 0.8)
        elif ref >= 35.0:
            return PricingPowerLabel.MODERATE, clamp(40.0 + (ref - 35.0) * 1.0)
        else:
            return PricingPowerLabel.WEAK, clamp(ref * 0.8)

    def score(self, profile: ResilienceProfile) -> float:
        return profile.resilience_score
