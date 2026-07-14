"""iios/investment/portfolio/diversification/relationship_graph.py

Lightweight relationship graph: nodes = positions, edges = high-correlation pairs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

from iios.investment.portfolio.diversification.correlation_matrix import CorrelationMatrix
from iios.investment.portfolio.diversification.diversification_types import PositionData


@dataclass(frozen=True)
class RelationshipEdge:
    symbol_a:    str   = ""
    symbol_b:    str   = ""
    correlation: float = 0.0
    same_sector: bool  = False
    same_industry:bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol_a":     self.symbol_a,
            "symbol_b":     self.symbol_b,
            "correlation":  round(self.correlation, 4),
            "same_sector":  self.same_sector,
            "same_industry":self.same_industry,
        }


@dataclass(frozen=True)
class RelationshipGraph:
    """
    Adjacency representation of high-correlation position pairs.
    Only edges with correlation ≥ threshold are stored.
    """

    nodes:          Tuple[str, ...]              = field(default_factory=tuple)
    edges:          Tuple[RelationshipEdge, ...] = field(default_factory=tuple)
    threshold:      float                        = 0.55
    n_nodes:        int                          = 0
    n_edges:        int                          = 0
    max_degree_node:str                          = ""
    max_degree:     int                          = 0

    def neighbours(self, symbol: str) -> List[str]:
        """Return symbols directly connected to *symbol*."""
        result = []
        for e in self.edges:
            if e.symbol_a == symbol:
                result.append(e.symbol_b)
            elif e.symbol_b == symbol:
                result.append(e.symbol_a)
        return result

    def is_connected(self, a: str, b: str) -> bool:
        for e in self.edges:
            if (e.symbol_a == a and e.symbol_b == b) or (e.symbol_a == b and e.symbol_b == a):
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_nodes":        self.n_nodes,
            "n_edges":        self.n_edges,
            "threshold":      self.threshold,
            "max_degree_node":self.max_degree_node,
            "max_degree":     self.max_degree,
            "edges":          [e.to_dict() for e in self.edges[:50]],
        }


def build_relationship_graph(
    positions: List[PositionData],
    matrix:    CorrelationMatrix,
    threshold: float = 0.55,
) -> RelationshipGraph:
    """Build the high-correlation relationship graph."""
    if not positions:
        return RelationshipGraph()

    sym_map = {p.symbol: p for p in positions}
    edges: List[RelationshipEdge] = []
    degree: Dict[str, int] = {}

    for (a, b), corr in matrix.data.items():
        if corr >= threshold:
            pa = sym_map.get(a)
            pb = sym_map.get(b)
            same_sec = (pa is not None and pb is not None and pa.sector == pb.sector)
            same_ind = (pa is not None and pb is not None and pa.industry == pb.industry)
            edges.append(RelationshipEdge(
                symbol_a     = a,
                symbol_b     = b,
                correlation  = corr,
                same_sector  = same_sec,
                same_industry= same_ind,
            ))
            degree[a] = degree.get(a, 0) + 1
            degree[b] = degree.get(b, 0) + 1

    edges.sort(key=lambda e: e.correlation, reverse=True)
    max_sym  = max(degree, key=degree.get) if degree else ""
    max_deg  = degree.get(max_sym, 0)

    return RelationshipGraph(
        nodes           = tuple(p.symbol for p in positions),
        edges           = tuple(edges),
        threshold       = threshold,
        n_nodes         = len(positions),
        n_edges         = len(edges),
        max_degree_node = max_sym,
        max_degree      = max_deg,
    )
