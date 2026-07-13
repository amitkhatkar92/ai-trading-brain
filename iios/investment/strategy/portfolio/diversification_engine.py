"""iios/investment/strategy/portfolio/diversification_engine.py
DiversificationEngine — produces a DiversificationReport for a portfolio.
Combines correlation, overlap, and redundancy analyses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_portfolio import StrategyPortfolio
from iios.investment.strategy.portfolio.strategy_correlation import CorrelationMatrix
from iios.investment.strategy.portfolio.overlap_analysis import OverlapAnalysis, OverlapReport
from iios.investment.strategy.portfolio.redundancy_detector import (
    RedundancyDetector, RedundancyReport, DEFAULT_REDUNDANCY_THRESHOLD
)
from iios.investment.strategy.portfolio.portfolio_statistics import (
    herfindahl_index, effective_n, safe_div
)


@dataclass(frozen=True)
class DiversificationReport:
    portfolio_id:        str
    strategy_count:      int

    # Correlation metrics
    average_correlation: float     # 0 = uncorrelated, 1 = identical
    effective_n:         float     # effective number of independent strategies

    # Overlap analysis
    overlap:             OverlapReport

    # Redundancy
    redundancy:          RedundancyReport

    # Weight concentration
    hhi:                 float     # Herfindahl index
    diversification_score: float   # 0–100; higher = better

    generated_at:        datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def grade(self) -> str:
        if self.diversification_score >= 80:
            return "A"
        if self.diversification_score >= 65:
            return "B"
        if self.diversification_score >= 50:
            return "C"
        if self.diversification_score >= 35:
            return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":          self.portfolio_id,
            "strategy_count":        self.strategy_count,
            "average_correlation":   round(self.average_correlation, 4),
            "effective_n":           round(self.effective_n, 2),
            "hhi":                   round(self.hhi, 4),
            "diversification_score": round(self.diversification_score, 2),
            "grade":                 self.grade,
            "overlap":               self.overlap.to_dict(),
            "redundancy":            self.redundancy.to_dict(),
            "generated_at":          self.generated_at.isoformat(),
        }


class DiversificationEngine:
    """
    Evaluates portfolio diversification quality.
    Consumes PortfolioStrategy objects (supplied externally — not evaluated internally).
    """

    def __init__(
        self,
        redundancy_threshold: float = DEFAULT_REDUNDANCY_THRESHOLD,
    ) -> None:
        self._overlap      = OverlapAnalysis()
        self._redundancy   = RedundancyDetector(threshold=redundancy_threshold)

    def analyse(
        self,
        portfolio:   StrategyPortfolio,
        strategies:  List[PortfolioStrategy],   # must match portfolio's allocations
    ) -> DiversificationReport:
        """
        Produce a DiversificationReport.  strategies list provides the feature
        data needed for correlation and overlap; portfolio provides weights.
        """
        active_ids = {a.strategy_id for a in portfolio.active_allocations()}
        active_strats = [s for s in strategies if s.strategy_id in active_ids]

        if not active_strats:
            return DiversificationReport(
                portfolio_id=portfolio.portfolio_id,
                strategy_count=0,
                average_correlation=0.0,
                effective_n=0.0,
                overlap=self._overlap.analyse([]),
                redundancy=RedundancyReport([], 0.0, 0, 0.0),
                hhi=1.0,
                diversification_score=0.0,
            )

        corr_matrix = CorrelationMatrix(active_strats)
        avg_corr    = corr_matrix.average_correlation()

        eval_scores = {
            s.strategy_id: s.evaluation_score for s in active_strats
        }
        redundancy_report = self._redundancy.detect(corr_matrix, eval_scores)

        overlap_report = self._overlap.analyse(active_strats)

        # Weight-based concentration
        weights = [
            portfolio.allocations[a.strategy_id].weight
            for a in portfolio.active_allocations()
            if a.strategy_id in portfolio.allocations
        ]
        hhi  = herfindahl_index(weights) if weights else 1.0
        eff_n = effective_n(weights) if weights else 0.0

        # Diversification score (0–100)
        #  correlation penalty: (1 - avg_corr) * 40
        #  concentration bonus: (eff_n / n) * 30
        #  redundancy penalty:  (1 - redundancy_ratio) * 20
        #  overlap bonus:       (1 - tag_conc) * 10
        n = len(active_strats)
        corr_comp   = (1.0 - avg_corr) * 40.0
        conc_comp   = safe_div(eff_n, n, 0.0) * 30.0
        redund_comp = (1.0 - redundancy_report.redundancy_ratio) * 20.0
        overlap_comp = (1.0 - overlap_report.tag_concentration) * 10.0
        score = min(100.0, max(0.0, corr_comp + conc_comp + redund_comp + overlap_comp))

        return DiversificationReport(
            portfolio_id=portfolio.portfolio_id,
            strategy_count=n,
            average_correlation=avg_corr,
            effective_n=eff_n,
            overlap=overlap_report,
            redundancy=redundancy_report,
            hhi=hhi,
            diversification_score=score,
        )
