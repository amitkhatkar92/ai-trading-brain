"""iios/investment/company/business_quality/market_position.py
Market position analyzer — absolute quality signals.
"""
from __future__ import annotations

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.competitive_position import (
    MarketPositionProfile, MarketLeadershipLabel, CompetitivePressureLabel,
)
from iios.investment.company.business_quality.quality_statistics import clamp


class MarketPositionAnalyzer:
    """Estimates market position from absolute financial quality signals."""

    def analyze(self, ctx: AssessmentContext) -> MarketPositionProfile:
        p = MarketPositionProfile()

        gm   = ctx.income_metric("gross_margin") or ctx.ratio("gross_margin")
        roic = ctx.ratio("roic") or ctx.ratio("return_on_invested_capital")

        avg_gm   = None
        avg_roic = None
        if ctx.earnings_snapshot:
            try:
                prof     = ctx.earnings_snapshot.profitability
                avg_gm   = getattr(prof, "avg_gross_margin", None)
                avg_roic = getattr(prof, "avg_roic", None)
            except Exception:
                pass

        ref_gm   = avg_gm   or gm
        ref_roic = avg_roic or roic

        # ── Premium margins ────────────────────────────────────────────────────
        p.is_premium_margins = (ref_gm is not None and ref_gm >= 45.0)
        p.is_high_roic       = (ref_roic is not None and ref_roic >= 15.0)

        # ── Revenue growth vs industry proxy ───────────────────────────────────
        if ctx.earnings_snapshot:
            try:
                trend = ctx.earnings_snapshot.trend
                from iios.investment.company.earnings.earnings_report import TrendDirection
                rev_dir = getattr(trend, "revenue_direction", None)
                p.is_market_share_gainer = rev_dir in [
                    TrendDirection.ACCELERATING, TrendDirection.RECOVERING,
                    TrendDirection.REVERSAL_UP,
                ]
            except Exception:
                pass

        # ── Leadership inference ───────────────────────────────────────────────
        quality_signals = sum([
            p.is_premium_margins,
            p.is_high_roic,
            p.is_market_share_gainer,
        ])

        if quality_signals >= 3:
            p.leadership = MarketLeadershipLabel.LEADER
        elif quality_signals >= 2:
            p.leadership = MarketLeadershipLabel.CHALLENGER
        elif quality_signals == 1:
            p.leadership = MarketLeadershipLabel.FOLLOWER
        else:
            p.leadership = MarketLeadershipLabel.UNKNOWN

        # ── Competitive pressure ────────────────────────────────────────────────
        if ref_gm is not None:
            if ref_gm >= 50.0:
                p.competitive_pressure = CompetitivePressureLabel.LOW
            elif ref_gm >= 30.0:
                p.competitive_pressure = CompetitivePressureLabel.MODERATE
            else:
                p.competitive_pressure = CompetitivePressureLabel.HIGH

        # ── Market position score (0-100) ──────────────────────────────────────
        score = 40.0
        if p.is_premium_margins:
            score += 20.0
        if p.is_high_roic:
            score += 20.0
        if p.is_market_share_gainer:
            score += 15.0
        if p.competitive_pressure == CompetitivePressureLabel.LOW:
            score += 5.0
        elif p.competitive_pressure == CompetitivePressureLabel.HIGH:
            score -= 15.0

        p.market_position_score = clamp(score)

        # Flags
        if p.leadership == MarketLeadershipLabel.LEADER:
            p.flags.append("market_leader_signals")
        if p.competitive_pressure == CompetitivePressureLabel.HIGH:
            p.flags.append("high_competitive_pressure")

        return p
