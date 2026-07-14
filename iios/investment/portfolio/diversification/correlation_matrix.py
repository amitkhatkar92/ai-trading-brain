"""iios/investment/portfolio/diversification/correlation_matrix.py

Proxy correlation matrix built from sector/industry/asset-class similarity.
All calculations are pure-Python; no market price data is required.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.diversification.diversification_types import (
    CORR_DIFFERENT,
    CORR_SAME_ASSET_CLASS,
    CORR_SAME_INDUSTRY,
    CORR_SAME_SECTOR,
    CORR_SAME_SYMBOL,
    PositionData,
)


@dataclass(frozen=True)
class CorrelationMatrix:
    """
    Symmetric proxy correlation matrix.

    Storage: {(sym_a, sym_b): correlation} where sym_a < sym_b (lexicographic).
    The diagonal (self-correlation = 1.0) is implied.
    """

    symbols:  Tuple[str, ...]            = field(default_factory=tuple)
    data:     Dict[Tuple[str, str], float] = field(default_factory=dict)
    n:        int                         = 0

    def get(self, a: str, b: str) -> float:
        """Return correlation between symbols a and b."""
        if a == b:
            return 1.0
        key = (min(a, b), max(a, b))
        return self.data.get(key, CORR_DIFFERENT)

    @property
    def avg_off_diagonal(self) -> float:
        """Average pairwise correlation (excludes diagonal)."""
        if not self.data:
            return 0.0
        return sum(self.data.values()) / len(self.data)

    @property
    def max_off_diagonal(self) -> float:
        if not self.data:
            return 0.0
        return max(self.data.values())

    @property
    def min_off_diagonal(self) -> float:
        if not self.data:
            return 0.0
        return min(self.data.values())

    @property
    def n_high_pairs(self) -> int:
        """Number of pairs with correlation ≥ 0.70."""
        return sum(1 for v in self.data.values() if v >= 0.70)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbols":          list(self.symbols),
            "n":                self.n,
            "avg_correlation":  round(self.avg_off_diagonal, 4),
            "max_correlation":  round(self.max_off_diagonal, 4),
            "min_correlation":  round(self.min_off_diagonal, 4),
            "n_high_pairs":     self.n_high_pairs,
            "matrix":           {f"{a}|{b}": round(v, 4) for (a, b), v in self.data.items()},
        }


def _proxy_correlation(a: PositionData, b: PositionData) -> float:
    """Determine proxy correlation between two positions."""
    if a.symbol == b.symbol:
        return CORR_SAME_SYMBOL
    if a.industry == b.industry and a.industry not in ("unknown", ""):
        return CORR_SAME_INDUSTRY
    if a.sector == b.sector and a.sector not in ("unknown", ""):
        return CORR_SAME_SECTOR
    if a.asset_class == b.asset_class and a.asset_class not in ("unknown", ""):
        return CORR_SAME_ASSET_CLASS
    return CORR_DIFFERENT


def build_correlation_matrix(positions: List[PositionData]) -> CorrelationMatrix:
    """Build an n×n proxy correlation matrix from sector/industry similarity."""
    if not positions:
        return CorrelationMatrix()

    symbols = tuple(p.symbol for p in positions)
    data: Dict[Tuple[str, str], float] = {}

    for i, a in enumerate(positions):
        for j, b in enumerate(positions):
            if j <= i:
                continue
            key  = (min(a.symbol, b.symbol), max(a.symbol, b.symbol))
            corr = _proxy_correlation(a, b)
            data[key] = corr

    return CorrelationMatrix(symbols=symbols, data=data, n=len(positions))


def portfolio_risk_from_matrix(
    positions: List[PositionData],
    matrix:    CorrelationMatrix,
) -> float:
    """
    Compute portfolio risk (σ_p) using proxy correlation matrix.
    σ_p = sqrt(Σ_i Σ_j w_i w_j ρ_ij σ_i σ_j)
    """
    variance = 0.0
    for a in positions:
        for b in positions:
            rho  = matrix.get(a.symbol, b.symbol)
            variance += a.weight * b.weight * rho * a.risk_score * b.risk_score
    return math.sqrt(max(0.0, variance))


def diversification_ratio(
    positions: List[PositionData],
    matrix:    CorrelationMatrix,
) -> float:
    """
    DR = Σ(w_i σ_i) / σ_portfolio.
    DR > 1 indicates diversification benefit; higher is better.
    """
    if not positions:
        return 1.0
    weighted_risk_sum = sum(p.weight * p.risk_score for p in positions)
    sigma_p = portfolio_risk_from_matrix(positions, matrix)
    return weighted_risk_sum / max(sigma_p, 1e-10)
