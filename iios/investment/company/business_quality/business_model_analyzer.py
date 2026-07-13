"""iios/investment/company/business_quality/business_model_analyzer.py
Orchestrates revenue model and cost structure into a BusinessModelProfile.
"""
from __future__ import annotations

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.business_model import (
    BusinessModelProfile, BusinessModelType, CapexIntensityLabel,
    RevenueVisibilityLabel,
)
from iios.investment.company.business_quality.revenue_model import RevenueModelAnalyzer
from iios.investment.company.business_quality.cost_structure import CostStructureAnalyzer
from iios.investment.company.business_quality.quality_statistics import clamp


class BusinessModelAnalyzer:
    """
    Infers business model classification and profile from financial signals.
    Output: BusinessModelProfile.
    """

    def __init__(self) -> None:
        self._revenue = RevenueModelAnalyzer()
        self._costs   = CostStructureAnalyzer()

    def analyze(self, ctx: AssessmentContext) -> BusinessModelProfile:
        rev  = self._revenue.analyze(ctx)
        cost = self._costs.analyze(ctx)

        p = BusinessModelProfile(
            gross_margin_level      = rev.get("gross_margin_level"),
            avg_gross_margin        = rev.get("avg_gross_margin"),
            revenue_visibility      = rev.get("revenue_visibility", RevenueVisibilityLabel.UNKNOWN),
            is_recurring_dominant   = rev.get("is_recurring_dominant", False),
            capex_intensity         = cost.get("capex_intensity", CapexIntensityLabel.UNKNOWN),
            capex_pct_revenue       = cost.get("capex_pct_revenue"),
            avg_capex_pct           = cost.get("avg_capex_pct"),
            is_asset_light          = cost.get("is_asset_light", False),
            operating_leverage_score = rev.get("operating_leverage_score", 50.0),
            is_high_operating_leverage = rev.get("is_high_operating_leverage", False),
            sga_pct                 = cost.get("sga_pct"),
            rd_pct                  = cost.get("rd_pct"),
            is_rd_intensive         = cost.get("is_rd_intensive", False),
            asset_turnover          = rev.get("asset_turnover"),
            avg_asset_turnover      = rev.get("avg_asset_turnover"),
        )

        # ── Classification heuristics ──────────────────────────────────────────
        gm  = p.gross_margin_level or 0.0
        cap = p.capex_intensity

        if gm >= 65 and cap == CapexIntensityLabel.LIGHT:
            model_type   = BusinessModelType.ASSET_LIGHT
            confidence   = 0.80
        elif gm >= 50 and p.is_recurring_dominant:
            model_type   = BusinessModelType.SUBSCRIPTION
            confidence   = 0.65
        elif p.is_rd_intensive and gm >= 40:
            model_type   = BusinessModelType.ASSET_LIGHT   # tech/pharma
            confidence   = 0.55
        elif cap == CapexIntensityLabel.HEAVY and gm < 40:
            model_type   = BusinessModelType.ASSET_HEAVY
            confidence   = 0.75
        elif gm < 25:
            model_type   = BusinessModelType.COMMODITY
            confidence   = 0.60
        elif cap == CapexIntensityLabel.HEAVY:
            model_type   = BusinessModelType.MANUFACTURING
            confidence   = 0.65
        elif gm >= 30 and cap != CapexIntensityLabel.HEAVY:
            model_type   = BusinessModelType.SERVICES
            confidence   = 0.45
        else:
            model_type   = BusinessModelType.HYBRID
            confidence   = 0.30

        p.model_type       = model_type
        p.model_confidence = confidence

        # ── Flags ──────────────────────────────────────────────────────────────
        if p.is_asset_light and gm >= 60:
            p.flags.append("high_quality_asset_light")
        if p.is_rd_intensive:
            p.flags.append("rd_intensive")
        if cap == CapexIntensityLabel.HEAVY:
            p.flags.append("capital_intensive")
        if gm < 20:
            p.flags.append("thin_margins_commodity_risk")

        return p

    def score(self, profile: BusinessModelProfile) -> float:
        """Convert BusinessModelProfile to 0-100 model quality score."""
        gm   = profile.avg_gross_margin or profile.gross_margin_level or 0.0
        base = clamp(gm * 1.2, 0, 70)   # max 70 from gross margin

        bonus = 0.0
        if profile.is_asset_light:
            bonus += 15.0
        if profile.is_recurring_dominant:
            bonus += 10.0
        if profile.is_rd_intensive:
            bonus += 5.0
        if profile.is_high_operating_leverage:
            bonus -= 5.0   # risk penalty

        return clamp(base + bonus, 0, 100)
