"""iios/investment/company/growth/growth_sustainability.py
Growth sustainability engine — orchestrates consistency, resilience and risk.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.growth.growth_profile import GrowthSustainabilityProfile
from iios.investment.company.growth.growth_consistency import compute_consistency_score
from iios.investment.company.growth.growth_resilience import compute_resilience_score
from iios.investment.company.growth.growth_risk import assess_growth_risk
from iios.investment.company.growth.growth_statistics import clamp


class GrowthSustainabilityEngine:
    """
    Produces a GrowthSustainabilityProfile from upstream snapshot signals.
    Sustainability = f(consistency, resilience, risk).
    """

    def compute(
        self,
        eps_volatility:     Optional[float] = None,
        revenue_volatility: Optional[float] = None,
        margin_volatility:  Optional[float] = None,
        consistency_score:  Optional[float] = None,   # 0-100 from EarningsSnapshot
        loss_rate:          Optional[float] = None,
        is_cyclical:        Optional[bool]  = None,
        avg_fcf_margin:     Optional[float] = None,
        net_margin:         Optional[float] = None,
        avg_net_margin:     Optional[float] = None,
        earnings_stability: Optional[float] = None,
        moat_score:         Optional[float] = None,
        resilience_score:   Optional[float] = None,
        history_depth:      int = 0,
    ) -> GrowthSustainabilityProfile:
        explanation: List[str] = []

        # ── Component scores ─────────────────────────────────────────────────────
        cons = compute_consistency_score(
            eps_volatility=eps_volatility,
            revenue_volatility=revenue_volatility,
            margin_volatility=margin_volatility,
            consistency_score=consistency_score,
            loss_rate=loss_rate,
            history_depth=history_depth,
        )

        res = compute_resilience_score(
            resilience_score=resilience_score,
            is_cyclical=is_cyclical,
            loss_rate=loss_rate,
            avg_fcf_margin=avg_fcf_margin,
            earnings_stability=earnings_stability,
            moat_score=moat_score,
        )

        risk = assess_growth_risk(
            eps_volatility=eps_volatility,
            revenue_volatility=revenue_volatility,
            loss_rate=loss_rate,
            is_cyclical=is_cyclical,
            avg_fcf_margin=avg_fcf_margin,
            net_margin=net_margin,
            avg_net_margin=avg_net_margin,
            history_depth=history_depth,
        )

        # ── Cyclicality score (0-100) ────────────────────────────────────────────
        cyclicality = 80.0 if is_cyclical else 20.0
        if eps_volatility is not None:
            cyclicality = clamp(cyclicality + eps_volatility * 20.0, 0, 100)

        # ── Predictability ───────────────────────────────────────────────────────
        predictability = clamp((cons + res) / 2.0 - risk.risk_score * 0.3, 0, 100)

        # ── Composite sustainability score ───────────────────────────────────────
        sustainability = clamp(
            cons * 0.35 + res * 0.35 + (100.0 - risk.risk_score) * 0.30,
            0.0, 100.0,
        )

        is_sustainable = sustainability >= 55.0

        # ── Explanation ─────────────────────────────────────────────────────────
        explanation.append(f"Consistency: {cons:.1f}/100")
        explanation.append(f"Resilience: {res:.1f}/100")
        explanation.append(f"Risk score: {risk.risk_score:.1f}/100")
        explanation.append(f"Sustainability: {sustainability:.1f}/100")
        if not is_sustainable:
            explanation.append("Growth sustainability concerns present")
        explanation.extend(risk.explanation)

        return GrowthSustainabilityProfile(
            sustainability_score=sustainability,
            consistency_score=cons,
            resilience_score=res,
            cyclicality=cyclicality,
            predictability=predictability,
            is_sustainable=is_sustainable,
            risk_factors=risk.risk_factors,
            explanation=explanation,
        )
