"""iios/investment/market/correlation/systemic_risk.py
Systemic risk metrics derived from the correlation matrix and dependency graph.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np

from iios.investment.market.correlation.models import (
    CorrelationMatrix,
    DependencyGraph,
    RiskLevel,
    SystemicRiskMetrics,
)
from iios.investment.market.correlation import influence_network as inf_net


# Thresholds for systemic risk classification
_HIGH_CORR_THRESHOLD   = 0.70
_CONTAGION_THRESHOLD   = 0.50
_RISK_LEVEL_THRESHOLDS = [
    (80.0, RiskLevel.CRITICAL),
    (65.0, RiskLevel.HIGH),
    (50.0, RiskLevel.ELEVATED),
    (35.0, RiskLevel.MODERATE),
    (0.0,  RiskLevel.LOW),
]


class SystemicRiskCalculator:
    """Computes network-based systemic risk metrics from the correlation matrix."""

    def calculate(
        self,
        matrix: CorrelationMatrix,
        dep_graph: DependencyGraph,
    ) -> SystemicRiskMetrics:
        if len(matrix.symbols) < 2:
            return self._empty_metrics()

        avg_corr      = matrix.avg_correlation()
        avg_abs_corr  = matrix.avg_abs_correlation()
        conc          = self._concentration(matrix)
        contagion_idx = inf_net.compute_interconnectedness(matrix, _CONTAGION_THRESHOLD)
        interconn     = inf_net.compute_interconnectedness(matrix, _HIGH_CORR_THRESHOLD)
        top_n         = inf_net.most_influential_assets(dep_graph, matrix, top_n=5)
        n_clusters    = self._count_clusters(matrix, threshold=_HIGH_CORR_THRESHOLD)

        score = self._systemic_score(
            avg_abs_corr, conc, contagion_idx, interconn
        )
        risk_level = self._classify_risk(score)

        return SystemicRiskMetrics(
            risk_level=risk_level,
            avg_pairwise_correlation=round(avg_corr, 4),
            avg_abs_correlation=round(avg_abs_corr, 4),
            correlation_concentration=round(conc, 4),
            contagion_index=round(contagion_idx, 4),
            interconnectedness=round(interconn, 4),
            systemic_risk_score=round(score, 2),
            most_interconnected=top_n,
            n_correlated_clusters=n_clusters,
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _concentration(self, matrix: CorrelationMatrix) -> float:
        """Fraction of pairs with |corr| > HIGH_CORR_THRESHOLD."""
        syms = matrix.symbols
        n = len(syms)
        if n < 2:
            return 0.0
        count = total = 0
        for i, sa in enumerate(syms):
            for sb in syms[i + 1:]:
                v = matrix.get(sa, sb)
                if v is not None:
                    total += 1
                    if abs(v) >= _HIGH_CORR_THRESHOLD:
                        count += 1
        return count / max(total, 1)

    def _count_clusters(
        self, matrix: CorrelationMatrix, threshold: float
    ) -> int:
        """Count greedy correlation clusters (connected components)."""
        syms = matrix.symbols
        parent = {s: s for s in syms}

        def find(s: str) -> str:
            while parent[s] != s:
                parent[s] = parent[parent[s]]
                s = parent[s]
            return s

        for i, sa in enumerate(syms):
            for sb in syms[i + 1:]:
                v = matrix.get(sa, sb)
                if v is not None and abs(v) >= threshold:
                    pa, pb = find(sa), find(sb)
                    if pa != pb:
                        parent[pa] = pb

        return len({find(s) for s in syms})

    def _systemic_score(
        self,
        avg_abs: float,
        concentration: float,
        contagion: float,
        interconn: float,
    ) -> float:
        score = (
            avg_abs      * 35
            + concentration * 30
            + contagion     * 20
            + interconn     * 15
        )
        return max(0.0, min(100.0, score))

    def _classify_risk(self, score: float) -> RiskLevel:
        for threshold, level in _RISK_LEVEL_THRESHOLDS:
            if score >= threshold:
                return level
        return RiskLevel.LOW

    def _empty_metrics(self) -> SystemicRiskMetrics:
        return SystemicRiskMetrics(
            risk_level=RiskLevel.LOW,
            avg_pairwise_correlation=0.0,
            avg_abs_correlation=0.0,
            correlation_concentration=0.0,
            contagion_index=0.0,
            interconnectedness=0.0,
            systemic_risk_score=0.0,
            most_interconnected=[],
            n_correlated_clusters=0,
        )
