"""iios/investment/portfolio/diversification/correlation_analysis.py

Statistical analysis of the proxy correlation matrix.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from iios.investment.portfolio.diversification.correlation_matrix import (
    CorrelationMatrix,
    build_correlation_matrix,
    diversification_ratio,
    portfolio_risk_from_matrix,
)
from iios.investment.portfolio.diversification.diversification_types import (
    CorrelationLevel,
    PositionData,
)


def _corr_level(corr: float) -> CorrelationLevel:
    if corr >= 0.80:
        return CorrelationLevel.EXTREME
    if corr >= 0.60:
        return CorrelationLevel.HIGH
    if corr >= 0.30:
        return CorrelationLevel.MODERATE
    return CorrelationLevel.LOW


@dataclass(frozen=True)
class HighCorrelationPair:
    symbol_a:    str   = ""
    symbol_b:    str   = ""
    correlation: float = 0.0
    same_sector: bool  = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol_a":    self.symbol_a,
            "symbol_b":    self.symbol_b,
            "correlation": round(self.correlation, 4),
            "same_sector": self.same_sector,
        }


@dataclass(frozen=True)
class CorrelationAnalysisResult:
    """Summary statistics of the proxy correlation matrix."""

    n_pairs:              int                      = 0
    avg_correlation:      float                    = 0.0
    max_correlation:      float                    = 0.0
    min_correlation:      float                    = 0.0
    n_high_pairs:         int                      = 0
    n_extreme_pairs:      int                      = 0
    avg_level:            CorrelationLevel         = CorrelationLevel.LOW
    high_pairs:           Tuple[HighCorrelationPair, ...] = field(default_factory=tuple)
    portfolio_risk:       float                    = 0.0
    diversification_ratio:float                    = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_pairs":              self.n_pairs,
            "avg_correlation":      round(self.avg_correlation, 4),
            "max_correlation":      round(self.max_correlation, 4),
            "min_correlation":      round(self.min_correlation, 4),
            "n_high_pairs":         self.n_high_pairs,
            "n_extreme_pairs":      self.n_extreme_pairs,
            "avg_level":            self.avg_level.value,
            "portfolio_risk":       round(self.portfolio_risk, 4),
            "diversification_ratio":round(self.diversification_ratio, 4),
            "high_pairs":           [hp.to_dict() for hp in self.high_pairs],
        }


def analyze_correlations(
    positions: List[PositionData],
    matrix:    CorrelationMatrix,
) -> CorrelationAnalysisResult:
    if not positions or not matrix.data:
        return CorrelationAnalysisResult()

    corr_values = list(matrix.data.values())
    avg_c = sum(corr_values) / len(corr_values)
    max_c = max(corr_values)
    min_c = min(corr_values)

    # Build lookup for sector matching
    sym_sector = {p.symbol: p.sector for p in positions}

    high_pairs = []
    extreme_count = 0
    for (a, b), v in matrix.data.items():
        if v >= 0.60:
            high_pairs.append(HighCorrelationPair(
                symbol_a    = a,
                symbol_b    = b,
                correlation = v,
                same_sector = sym_sector.get(a) == sym_sector.get(b),
            ))
        if v >= 0.80:
            extreme_count += 1

    # Sort high pairs by correlation descending
    high_pairs.sort(key=lambda hp: hp.correlation, reverse=True)

    port_risk = portfolio_risk_from_matrix(positions, matrix)
    div_ratio = diversification_ratio(positions, matrix)

    return CorrelationAnalysisResult(
        n_pairs               = len(corr_values),
        avg_correlation       = round(avg_c, 4),
        max_correlation       = round(max_c, 4),
        min_correlation       = round(min_c, 4),
        n_high_pairs          = len(high_pairs),
        n_extreme_pairs       = extreme_count,
        avg_level             = _corr_level(avg_c),
        high_pairs            = tuple(high_pairs[:20]),   # cap at 20 for readability
        portfolio_risk        = round(port_risk, 4),
        diversification_ratio = round(div_ratio, 4),
    )
