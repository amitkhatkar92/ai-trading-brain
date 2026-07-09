"""iios/investment/market/analytics/correlation_analyzer.py
Cross-asset correlation analysis using Pearson correlation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_constants import CorrelationRegime


@dataclass
class CorrelationAnalysis:
    regime:          CorrelationRegime = CorrelationRegime.MODERATE
    avg_correlation: float             = 0.0
    max_correlation: float             = 0.0
    min_correlation: float             = 0.0
    score:           float             = 50.0   # 0–100
    metadata:        dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime":          self.regime.value,
            "avg_correlation": self.avg_correlation,
            "max_correlation": self.max_correlation,
            "min_correlation": self.min_correlation,
            "score":           self.score,
            "metadata":        self.metadata,
        }


class CorrelationAnalyzer:
    """
    Computes average pairwise Pearson correlation from a dict of return series.

    Input : dict[symbol, list[float]]  (returns, oldest first).
    Output: CorrelationAnalysis.
    """

    def analyze(
        self,
        return_series: dict[str, list[float]],
    ) -> CorrelationAnalysis:
        symbols = [s for s, r in return_series.items() if len(r) >= 2]
        if len(symbols) < 2:
            return CorrelationAnalysis()

        correlations: list[float] = []
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                r1   = return_series[symbols[i]]
                r2   = return_series[symbols[j]]
                n    = min(len(r1), len(r2))
                corr = self._pearson(r1[-n:], r2[-n:])
                if corr is not None:
                    correlations.append(corr)

        if not correlations:
            return CorrelationAnalysis()

        avg_corr = sum(correlations) / len(correlations)
        max_corr = max(correlations)
        min_corr = min(correlations)

        # Score: 0 = fully anti-correlated, 100 = fully correlated
        score = (avg_corr + 1.0) / 2.0 * 100.0

        if avg_corr >= 0.70:
            regime = CorrelationRegime.HIGH_CORRELATION
        elif avg_corr >= 0.30:
            regime = CorrelationRegime.MODERATE
        elif avg_corr >= -0.30:
            regime = CorrelationRegime.LOW_CORRELATION
        else:
            regime = CorrelationRegime.DECORRELATED

        return CorrelationAnalysis(
            regime          = regime,
            avg_correlation = round(avg_corr, 4),
            max_correlation = round(max_corr, 4),
            min_correlation = round(min_corr, 4),
            score           = round(score, 2),
            metadata        = {
                "n_pairs":   len(correlations),
                "n_symbols": len(symbols),
            },
        )

    @staticmethod
    def _pearson(x: list[float], y: list[float]) -> float | None:
        n = len(x)
        if n < 2:
            return None
        mx  = sum(x) / n
        my  = sum(y) / n
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        dx  = math.sqrt(sum((xi - mx) ** 2 for xi in x))
        dy  = math.sqrt(sum((yi - my) ** 2 for yi in y))
        if dx == 0.0 or dy == 0.0:
            return None
        return num / (dx * dy)
