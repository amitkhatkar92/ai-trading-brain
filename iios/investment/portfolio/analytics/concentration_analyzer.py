"""iios/investment/portfolio/analytics/concentration_analyzer.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.core.portfolio import Portfolio


@dataclass
class ConcentrationAnalysis:
    portfolio_id:        str   = ""
    top1_weight:         float = 0.0
    top3_weight:         float = 0.0
    top5_weight:         float = 0.0
    top10_weight:        float = 0.0
    concentration_score: float = 100.0   # 0–100; higher = LESS concentrated
    is_concentrated:     bool  = False   # top1 > 25%
    metadata:            dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":       self.portfolio_id,
            "top1_weight":        self.top1_weight,
            "top3_weight":        self.top3_weight,
            "top5_weight":        self.top5_weight,
            "top10_weight":       self.top10_weight,
            "concentration_score": self.concentration_score,
            "is_concentrated":    self.is_concentrated,
            "metadata":           self.metadata,
        }


class ConcentrationAnalyzer:
    """
    Scores concentration risk based on top-N position weights.

    score = max(0, (1 − top1_weight / 0.25) × 100)
      → 0% top1: 100   (no concentration)
      → 25% top1: 0    (at the limit)
    """

    _MAX_SINGLE = 0.25

    def analyze(self, portfolio: Portfolio) -> ConcentrationAnalysis:
        positions = list(portfolio.positions.values())
        nav       = portfolio.total_nav

        if not positions or nav <= 0:
            return ConcentrationAnalysis(portfolio_id=portfolio.portfolio_id)

        sorted_w = sorted(
            (p.market_value / nav for p in positions),
            reverse=True,
        )

        top1  = sorted_w[0]  if len(sorted_w) >= 1 else 0.0
        top3  = sum(sorted_w[:3])
        top5  = sum(sorted_w[:5])
        top10 = sum(sorted_w[:10])

        score = max(0.0, (1.0 - top1 / self._MAX_SINGLE) * 100.0)

        return ConcentrationAnalysis(
            portfolio_id        = portfolio.portfolio_id,
            top1_weight         = round(top1,  6),
            top3_weight         = round(top3,  6),
            top5_weight         = round(top5,  6),
            top10_weight        = round(top10, 6),
            concentration_score = round(score, 2),
            is_concentrated     = top1 > self._MAX_SINGLE,
            metadata            = {"n_positions": len(positions)},
        )
