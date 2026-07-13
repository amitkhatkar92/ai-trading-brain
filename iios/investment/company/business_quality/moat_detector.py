"""iios/investment/company/business_quality/moat_detector.py
Detects and scores economic moat from financial signals.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.economic_moat import (
    EconomicMoatProfile, MoatSignal, MoatStrength, MoatType,
)
from iios.investment.company.business_quality.competitive_advantage import (
    CompetitiveAdvantageDetector,
)
from iios.investment.company.business_quality.quality_statistics import (
    safe_mean, safe_stdev, clamp,
)


class MoatDetector:
    """
    Detects economic moat from financial signal patterns.
    A wide moat requires persistent ROIC significantly above cost of capital
    and durable gross margins over multiple periods.
    """

    _MIN_PERIODS_FOR_WIDE = 5   # Need 5+ years for wide moat classification

    def __init__(self) -> None:
        self._adv = CompetitiveAdvantageDetector()

    def analyze(self, ctx: AssessmentContext) -> EconomicMoatProfile:
        profile = EconomicMoatProfile()

        # ── Detect signals ─────────────────────────────────────────────────────
        signals = self._adv.detect(ctx)
        profile.signals = signals

        # ── Aggregate by moat type ─────────────────────────────────────────────
        type_scores: Dict[str, float] = {}
        for sig in signals:
            key = sig.moat_type.value
            type_scores[key] = max(type_scores.get(key, 0.0), sig.strength)

        profile.brand_score          = clamp(type_scores.get("brand", 0.0) * 100)
        profile.network_score        = clamp(type_scores.get("network_effect", 0.0) * 100)
        profile.cost_advantage_score = clamp(type_scores.get("cost_advantage", 0.0) * 100)
        profile.switching_cost_score = clamp(type_scores.get("switching_costs", 0.0) * 100)
        profile.scale_score          = clamp(type_scores.get("scale_advantage", 0.0) * 100)
        profile.ip_score             = clamp(type_scores.get("intellectual_property", 0.0) * 100)
        profile.regulatory_score     = clamp(type_scores.get("regulatory", 0.0) * 100)
        profile.distribution_score   = clamp(type_scores.get("distribution", 0.0) * 100)

        # ── Key financial evidence ─────────────────────────────────────────────
        profile.avg_roic = None
        profile.avg_roe  = None
        profile.avg_gross_margin = None

        if ctx.earnings_snapshot is not None:
            try:
                prof = ctx.earnings_snapshot.profitability
                profile.avg_roic         = getattr(prof, "avg_roic", None)
                profile.avg_roe          = getattr(prof, "avg_roe", None)
                profile.avg_gross_margin = getattr(prof, "avg_gross_margin", None)
                profile.fcf_conversion   = getattr(prof, "avg_fcf_margin", None)
            except Exception:
                pass

        if profile.avg_roic is None:
            profile.avg_roic = ctx.ratio("roic")
        if profile.avg_gross_margin is None:
            profile.avg_gross_margin = (
                ctx.income_metric("gross_margin") or ctx.ratio("gross_margin")
            )

        # ── Compute periods analyzed ───────────────────────────────────────────
        if ctx.earnings_snapshot is not None:
            try:
                profile.periods_analyzed = ctx.earnings_snapshot.history_depth
            except Exception:
                profile.periods_analyzed = 1
        else:
            profile.periods_analyzed = 1 if ctx.financial_snapshot else 0

        # ── ROIC stability ─────────────────────────────────────────────────────
        if ctx.earnings_snapshot is not None:
            try:
                risk = ctx.earnings_snapshot.risk
                profile.roic_stability = getattr(risk, "eps_volatility", None)
            except Exception:
                pass

        # ── Moat score ─────────────────────────────────────────────────────────
        component_weights = {
            "brand":                  0.25,
            "network_effect":         0.15,
            "cost_advantage":         0.20,
            "switching_costs":        0.15,
            "scale_advantage":        0.10,
            "intellectual_property":  0.10,
            "distribution":           0.05,
        }
        weighted_score = sum(
            type_scores.get(k, 0.0) * w for k, w in component_weights.items()
        )
        profile.moat_score = clamp(weighted_score * 100)

        # Moat consistency bonus: ROIC > 15% persistently
        if profile.avg_roic is not None and profile.avg_roic >= 15.0:
            bonus = min(20.0, (profile.avg_roic - 15.0) * 1.0)
            profile.moat_score = clamp(profile.moat_score + bonus)

        # ── Moat type list ─────────────────────────────────────────────────────
        profile.detected_moat_types = [
            MoatType(k) for k, v in type_scores.items() if v >= 0.30
        ]

        # ── Moat strength classification ───────────────────────────────────────
        profile.moat_strength = self._classify_strength(profile)

        # ── Flags ──────────────────────────────────────────────────────────────
        if profile.avg_roic is not None and profile.avg_roic >= 20.0:
            profile.flags.append("exceptional_roic")
        if profile.avg_gross_margin is not None and profile.avg_gross_margin >= 55.0:
            profile.flags.append("premium_gross_margins")
        if not profile.detected_moat_types:
            profile.flags.append("no_identifiable_moat")

        return profile

    def _classify_strength(self, profile: EconomicMoatProfile) -> MoatStrength:
        if profile.periods_analyzed < 2:
            return MoatStrength.UNKNOWN

        score     = profile.moat_score
        avg_roic  = profile.avg_roic or 0.0
        avg_gm    = profile.avg_gross_margin or 0.0
        n_types   = len(profile.detected_moat_types)

        if (
            score >= 55.0
            and avg_roic >= 20.0
            and avg_gm >= 40.0
            and n_types >= 2
            and profile.periods_analyzed >= self._MIN_PERIODS_FOR_WIDE
        ):
            return MoatStrength.WIDE

        if score >= 35.0 and (avg_roic >= 12.0 or avg_gm >= 35.0):
            return MoatStrength.NARROW

        return MoatStrength.NONE
