"""iios/investment/market/correlation/diversification_engine.py
Diversification scoring and cluster analysis.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from iios.investment.market.correlation.models import (
    CorrelationMatrix,
    DiversificationLevel,
    DiversificationMetrics,
)
from iios.investment.market.correlation import portfolio_correlation as pc
from iios.investment.market.correlation import hedging_analysis as ha


# Level thresholds
_LEVEL_THRESHOLDS = [
    (75.0, DiversificationLevel.EXCELLENT),
    (55.0, DiversificationLevel.GOOD),
    (35.0, DiversificationLevel.FAIR),
    (15.0, DiversificationLevel.POOR),
    (0.0,  DiversificationLevel.CRITICAL),
]

_REDUNDANCY_THRESHOLD = 0.80
_HEDGE_THRESHOLD      = -0.40
_CLUSTER_THRESHOLD    = 0.70


class DiversificationScorer:
    """Computes diversification metrics from the correlation matrix."""

    def score(
        self, matrix: CorrelationMatrix
    ) -> DiversificationMetrics:
        syms = matrix.symbols
        n    = len(syms)

        if n < 2:
            return self._empty(n)

        portfolio_corr  = pc.equal_weight_portfolio_correlation(matrix)
        effective_n     = self._effective_n(portfolio_corr, n)
        clusters        = self._find_clusters(matrix, _CLUSTER_THRESHOLD)
        redundant       = matrix.highly_correlated_pairs(_REDUNDANCY_THRESHOLD)
        hedging_pairs   = ha.find_hedging_pairs(matrix, _HEDGE_THRESHOLD)
        div_score       = self._diversification_score(effective_n, n)
        level           = self._classify_level(div_score)

        return DiversificationMetrics(
            diversification_score=round(div_score, 2),
            diversification_level=level,
            effective_n_assets=round(effective_n, 2),
            correlation_clusters=clusters,
            redundant_pairs=redundant,
            hedging_pairs=hedging_pairs,
            portfolio_correlation=round(portfolio_corr, 4),
            cluster_count=len(clusters),
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _effective_n(self, avg_corr: float, n: int) -> float:
        """
        Markowitz effective number of independent assets:
            N_eff = 1 / (1 + (n-1) * avg_pairwise_corr / n)
        Simplified equal-weight version.
        """
        if n <= 1:
            return float(n)
        clamped = max(0.0, min(1.0, avg_corr))
        denom = 1.0 + (n - 1) * clamped / n
        if denom < 1e-9:
            return float(n)
        return max(1.0, min(float(n), float(n) / denom))

    def _diversification_score(self, effective_n: float, n: int) -> float:
        if n <= 1:
            return 50.0
        return max(0.0, min(100.0, (effective_n - 1) / max(n - 1, 1) * 100))

    def _find_clusters(
        self, matrix: CorrelationMatrix, threshold: float
    ) -> List[List[str]]:
        """
        Greedy union-find clustering: group symbols where |corr| >= threshold.
        Returns list of clusters (each cluster is a list of symbols).
        Singletons are excluded.
        """
        syms = matrix.symbols
        parent: Dict[str, str] = {s: s for s in syms}

        def find(s: str) -> str:
            r = s
            while parent[r] != r:
                r = parent[r]
            while parent[s] != r:
                parent[s], s = r, parent[s]
            return r

        for i, sa in enumerate(syms):
            for sb in syms[i + 1:]:
                v = matrix.get(sa, sb)
                if v is not None and abs(v) >= threshold:
                    ra, rb = find(sa), find(sb)
                    if ra != rb:
                        parent[ra] = rb

        groups: Dict[str, List[str]] = {}
        for s in syms:
            root = find(s)
            groups.setdefault(root, []).append(s)

        return [members for members in groups.values() if len(members) >= 2]

    def _classify_level(self, score: float) -> DiversificationLevel:
        for threshold, level in _LEVEL_THRESHOLDS:
            if score >= threshold:
                return level
        return DiversificationLevel.CRITICAL

    def _empty(self, n: int) -> DiversificationMetrics:
        return DiversificationMetrics(
            diversification_score=50.0 if n == 1 else 0.0,
            diversification_level=DiversificationLevel.POOR,
            effective_n_assets=float(n),
            correlation_clusters=[],
            redundant_pairs=[],
            hedging_pairs=[],
            portfolio_correlation=0.0,
            cluster_count=0,
        )
