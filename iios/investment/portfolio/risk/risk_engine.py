"""iios/investment/portfolio/risk/risk_engine.py
Orchestrates the full risk analysis pipeline.
"""
from __future__ import annotations

import threading

from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.risk.drawdown_engine import DrawdownAnalysis, DrawdownEngine
from iios.investment.portfolio.risk.risk_analyzer import RiskAnalyzer
from iios.investment.portfolio.risk.risk_profile import RiskProfile
from iios.investment.portfolio.risk.risk_registry import RiskRegistry
from iios.investment.portfolio.risk.risk_statistics import RiskStatistics


class RiskEngine:
    """
    Top-level risk intelligence coordinator.

    Accepts a Portfolio + DrawdownAnalysis (already computed by DrawdownEngine)
    plus optional pre-computed analytics (hhi, top_position_weight) and
    delegates to RiskAnalyzer to build a RiskProfile.
    """

    def __init__(
        self,
        drawdown_engine: DrawdownEngine | None = None,
        risk_analyzer:   RiskAnalyzer   | None = None,
        risk_registry:   RiskRegistry   | None = None,
    ) -> None:
        self._lock       = threading.RLock()
        self._drawdown   = drawdown_engine or DrawdownEngine()
        self._analyzer   = risk_analyzer   or RiskAnalyzer()
        self._registry   = risk_registry   or RiskRegistry()
        self._stats:     dict[str, RiskStatistics] = {}

    def analyze(
        self,
        portfolio:           Portfolio,
        drawdown:            DrawdownAnalysis,
        hhi:                 float = 0.0,
        top_position_weight: float = 0.0,
        cash_pct:            float | None = None,
    ) -> RiskProfile:
        profile = self._analyzer.analyze(
            portfolio,
            drawdown,
            hhi                 = hhi,
            top_position_weight = top_position_weight,
            cash_pct            = cash_pct,
        )

        # Update per-portfolio statistics
        with self._lock:
            pid   = portfolio.portfolio_id
            stats = self._stats.setdefault(pid, RiskStatistics(portfolio_id=pid))
            stats.update(profile.overall_risk_score)

        return profile

    def get_statistics(self, portfolio_id: str) -> RiskStatistics | None:
        with self._lock:
            return self._stats.get(portfolio_id)

    def registry(self) -> RiskRegistry:
        return self._registry
