"""iios/investment/portfolio/analytics/portfolio_analyzer.py
Top-level analytics coordinator: coordinates all sub-analyzers and
produces a PortfolioAnalytics object consumed by PortfolioManager.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.risk.drawdown_engine import DrawdownAnalysis
from iios.investment.portfolio.exposure.exposure_report import ExposureReport
from iios.investment.portfolio.allocation.allocation_report import AllocationReport
from iios.investment.portfolio.analytics.performance_analyzer import (
    PerformanceAnalysis,
    PerformanceAnalyzer,
)
from iios.investment.portfolio.analytics.diversification_analyzer import (
    DiversificationAnalysis,
    DiversificationAnalyzer,
)
from iios.investment.portfolio.analytics.concentration_analyzer import (
    ConcentrationAnalysis,
    ConcentrationAnalyzer,
)
from iios.investment.portfolio.analytics.allocation_analyzer import (
    AllocationAnalysis,
    AllocationAnalyzer,
)


@dataclass
class PortfolioAnalytics:
    """
    Composite analytics result produced by PortfolioAnalyzer.
    Consumed by PortfolioManager to build PortfolioIntelligence.
    """

    portfolio_id:          str   = ""
    timestamp:             float = field(default_factory=time.time)

    # Scores (0–100)
    diversification_score: float = 50.0
    concentration_score:   float = 50.0
    performance_score:     float = 50.0
    allocation_score:      float = 50.0
    liquidity_score:       float = 50.0

    # Raw metrics
    hhi:                   float = 0.0
    top1_weight:           float = 0.0
    top3_weight:           float = 0.0
    top5_weight:           float = 0.0
    unrealized_pnl:        float = 0.0
    unrealized_pnl_pct:    float = 0.0
    effective_positions:   float = 0.0

    # Breakdowns
    by_sector:             dict[str, float] = field(default_factory=dict)
    by_country:            dict[str, float] = field(default_factory=dict)
    by_asset_class:        dict[str, float] = field(default_factory=dict)

    # Sub-analyses
    performance:           PerformanceAnalysis     | None = None
    diversification:       DiversificationAnalysis | None = None
    concentration:         ConcentrationAnalysis   | None = None
    allocation:            AllocationAnalysis      | None = None

    metadata:              dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":          self.portfolio_id,
            "timestamp":             self.timestamp,
            "diversification_score": self.diversification_score,
            "concentration_score":   self.concentration_score,
            "performance_score":     self.performance_score,
            "allocation_score":      self.allocation_score,
            "liquidity_score":       self.liquidity_score,
            "hhi":                   self.hhi,
            "top1_weight":           self.top1_weight,
            "top3_weight":           self.top3_weight,
            "unrealized_pnl":        self.unrealized_pnl,
            "unrealized_pnl_pct":    self.unrealized_pnl_pct,
            "effective_positions":   self.effective_positions,
            "by_sector":             self.by_sector,
            "by_country":            self.by_country,
            "by_asset_class":        self.by_asset_class,
            "metadata":              self.metadata,
        }


class PortfolioAnalyzer:
    """
    Coordinates all portfolio sub-analyzers into a single PortfolioAnalytics.
    """

    def __init__(
        self,
        performance_analyzer:    PerformanceAnalyzer    | None = None,
        diversification_analyzer: DiversificationAnalyzer | None = None,
        concentration_analyzer:  ConcentrationAnalyzer  | None = None,
        allocation_analyzer:     AllocationAnalyzer     | None = None,
    ) -> None:
        self._lock    = threading.RLock()
        self._perf    = performance_analyzer    or PerformanceAnalyzer()
        self._div     = diversification_analyzer or DiversificationAnalyzer()
        self._conc    = concentration_analyzer  or ConcentrationAnalyzer()
        self._alloc   = allocation_analyzer     or AllocationAnalyzer()

    def analyze(
        self,
        portfolio:     Portfolio,
        drawdown:      DrawdownAnalysis,
        exposure:      ExposureReport,
        alloc_report:  AllocationReport,
    ) -> PortfolioAnalytics:
        perf   = self._perf.analyze(portfolio)
        div    = self._div.analyze(portfolio)
        conc   = self._conc.analyze(portfolio)
        alloc  = self._alloc.analyze(portfolio, alloc_report)

        nav      = portfolio.total_nav
        liq_score = self._liquidity_score(exposure.cash_pct)

        # Build breakdowns from exposure report
        by_sector = dict(exposure.by_sector)
        by_country = dict(exposure.by_country)
        by_ac     = dict(exposure.by_asset_class)

        return PortfolioAnalytics(
            portfolio_id          = portfolio.portfolio_id,
            diversification_score = div.diversification_score,
            concentration_score   = conc.concentration_score,
            performance_score     = perf.performance_score,
            allocation_score      = alloc.allocation_score,
            liquidity_score       = liq_score,
            hhi                   = div.hhi,
            top1_weight           = conc.top1_weight,
            top3_weight           = conc.top3_weight,
            top5_weight           = conc.top5_weight,
            unrealized_pnl        = perf.unrealized_pnl,
            unrealized_pnl_pct    = perf.unrealized_pnl_pct,
            effective_positions   = div.effective_positions,
            by_sector             = by_sector,
            by_country            = by_country,
            by_asset_class        = by_ac,
            performance           = perf,
            diversification       = div,
            concentration         = conc,
            allocation            = alloc,
            metadata              = {"nav": nav},
        )

    @staticmethod
    def _liquidity_score(cash_pct: float) -> float:
        if cash_pct >= 0.15:
            return 100.0
        elif cash_pct >= 0.10:
            return 85.0
        elif cash_pct >= 0.05:
            return 65.0
        elif cash_pct >= 0.02:
            return 40.0
        else:
            return 15.0
