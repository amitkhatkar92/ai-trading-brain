"""iios/investment/portfolio/risk/risk_analyzer.py
Derives multi-dimensional risk scores from portfolio composition and drawdown.
"""
from __future__ import annotations

from iios.investment.portfolio.portfolio_constants import RiskCategory, RiskLevel
from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.risk.drawdown_engine import DrawdownAnalysis
from iios.investment.portfolio.risk.risk_profile import RiskProfile


class RiskAnalyzer:
    """
    Computes the RiskProfile for a portfolio given:
    - Portfolio object (positions, cash, NAV)
    - DrawdownAnalysis (current drawdown metrics)
    - HHI / top position weight (from analytics layer)
    """

    def analyze(
        self,
        portfolio:        Portfolio,
        drawdown:         DrawdownAnalysis,
        hhi:              float = 0.0,
        top_position_weight: float = 0.0,
        cash_pct:         float | None = None,
    ) -> RiskProfile:
        nav = portfolio.total_nav
        cash_pct_v = (portfolio.cash / nav if nav > 0 else 1.0) if cash_pct is None else cash_pct

        concentration_risk = self._concentration_risk(top_position_weight, hhi)
        liquidity_risk     = self._liquidity_risk(cash_pct_v)
        drawdown_risk      = drawdown.drawdown_risk_score
        volatility_risk    = self._volatility_risk(drawdown)
        market_risk        = (concentration_risk * 0.4 + volatility_risk * 0.6)

        overall = (
            concentration_risk * 0.30
            + liquidity_risk   * 0.20
            + drawdown_risk    * 0.25
            + volatility_risk  * 0.25
        )
        overall = round(min(100.0, max(0.0, overall)), 2)

        profile = RiskProfile(
            portfolio_id              = portfolio.portfolio_id,
            overall_risk_score        = overall,
            market_risk_score         = round(market_risk, 2),
            concentration_risk_score  = round(concentration_risk, 2),
            liquidity_risk_score      = round(liquidity_risk, 2),
            volatility_risk_score     = round(volatility_risk, 2),
            drawdown_risk_score       = round(drawdown_risk, 2),
            risk_level                = self._classify(overall),
        )

        # Populate primary risk categories
        if concentration_risk >= 60:
            profile.primary_risk_categories.append(RiskCategory.CONCENTRATION)
            profile.add_factor("High position concentration detected")
        if liquidity_risk >= 60:
            profile.primary_risk_categories.append(RiskCategory.LIQUIDITY)
            profile.add_warning("Low cash reserve — liquidity risk elevated")
        if drawdown_risk >= 40:
            profile.primary_risk_categories.append(RiskCategory.VOLATILITY)
        if top_position_weight > 0.25:
            profile.add_warning(
                f"Largest position at {top_position_weight:.1%} exceeds 25% threshold"
            )

        return profile

    @staticmethod
    def _concentration_risk(top_weight: float, hhi: float) -> float:
        top_score = min(100.0, top_weight / 0.25 * 100)   # 25% cap = 100
        hhi_score = min(100.0, hhi * 400)                  # HHI of 0.25 = 100
        return top_score * 0.60 + hhi_score * 0.40

    @staticmethod
    def _liquidity_risk(cash_pct: float) -> float:
        """Higher cash_pct → lower liquidity risk."""
        if cash_pct >= 0.10:
            return 0.0
        elif cash_pct >= 0.05:
            return 25.0
        elif cash_pct >= 0.02:
            return 55.0
        else:
            return 85.0

    @staticmethod
    def _volatility_risk(drawdown: DrawdownAnalysis) -> float:
        return drawdown.drawdown_risk_score

    @staticmethod
    def _classify(score: float) -> RiskLevel:
        if score >= 75:
            return RiskLevel.VERY_HIGH
        elif score >= 55:
            return RiskLevel.HIGH
        elif score >= 35:
            return RiskLevel.MODERATE
        elif score >= 15:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
