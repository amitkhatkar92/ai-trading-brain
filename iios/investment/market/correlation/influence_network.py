"""iios/investment/market/correlation/influence_network.py
Computes influence/centrality scores for each asset based on the
dependency graph and correlation matrix.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from iios.investment.market.correlation.models import (
    CorrelationMatrix,
    DependencyGraph,
)


def compute_influence_scores(
    dep_graph: DependencyGraph,
    matrix: CorrelationMatrix,
) -> Dict[str, float]:
    """
    Score each asset 0-1 based on how many others it leads and
    how strongly it correlates with those followers.
    """
    scores: Dict[str, float] = {s: 0.0 for s in matrix.symbols}

    for edge in dep_graph.edges:
        # Leader gets credit: correlation strength + 1 count
        scores[edge.source] = scores.get(edge.source, 0.0) + abs(edge.correlation)

    # Normalize
    max_score = max(scores.values()) if scores else 1.0
    if max_score > 0:
        scores = {s: v / max_score for s, v in scores.items()}

    return scores


def most_influential_assets(
    dep_graph: DependencyGraph,
    matrix: CorrelationMatrix,
    top_n: int = 5,
) -> List[str]:
    """Return top_n most influential (leading) assets."""
    scores = compute_influence_scores(dep_graph, matrix)
    return sorted(scores, key=lambda s: -scores[s])[:top_n]


def network_density(dep_graph: DependencyGraph, n_symbols: int) -> float:
    """
    0-1 density of the dependency network.
    1 = every pair has a directed edge.
    """
    max_edges = max(n_symbols * (n_symbols - 1), 1)
    return min(1.0, len(dep_graph.edges) / max_edges)


def compute_interconnectedness(
    matrix: CorrelationMatrix,
    threshold: float = 0.50,
) -> float:
    """
    Fraction of asset pairs with |correlation| > threshold.
    Measures how interconnected the system is.
    """
    syms = matrix.symbols
    n    = len(syms)
    if n < 2:
        return 0.0
    count = 0
    total = 0
    for i, sa in enumerate(syms):
        for sb in syms[i + 1:]:
            v = matrix.get(sa, sb)
            if v is not None:
                total += 1
                if abs(v) >= threshold:
                    count += 1
    return count / max(total, 1)
