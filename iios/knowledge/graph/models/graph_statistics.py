"""
iios/knowledge/graph/models/graph_statistics.py
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["NodeStatistics", "GraphStatistics", "ImpactResult"]


@dataclass
class NodeStatistics:
    """Per-node degree and centrality statistics."""
    node_id:         str   = ""
    in_degree:       int   = 0
    out_degree:      int   = 0
    neighbor_count:  int   = 0
    centrality:      float = 0.0
    influence_score: float = 0.0

    @property
    def total_degree(self) -> int:
        return self.in_degree + self.out_degree

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id":         self.node_id,
            "in_degree":       self.in_degree,
            "out_degree":      self.out_degree,
            "total_degree":    self.total_degree,
            "neighbor_count":  self.neighbor_count,
            "centrality":      self.centrality,
            "influence_score": self.influence_score,
        }


@dataclass
class GraphStatistics:
    """Aggregate statistics for the full graph."""
    node_count:          int            = 0
    edge_count:          int            = 0
    active_node_count:   int            = 0
    active_edge_count:   int            = 0
    deleted_node_count:  int            = 0
    deleted_edge_count:  int            = 0
    avg_in_degree:       float          = 0.0
    avg_out_degree:      float          = 0.0
    max_in_degree:       int            = 0
    max_out_degree:      int            = 0
    density:             float          = 0.0
    is_dag:              bool           = True
    component_count:     int            = 0
    isolated_node_count: int            = 0
    cycle_count:         int            = 0
    nodes_by_type:       dict[str, int] = field(default_factory=dict)
    edges_by_type:       dict[str, int] = field(default_factory=dict)
    computed_at:         float          = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count":          self.node_count,
            "edge_count":          self.edge_count,
            "active_node_count":   self.active_node_count,
            "active_edge_count":   self.active_edge_count,
            "deleted_node_count":  self.deleted_node_count,
            "deleted_edge_count":  self.deleted_edge_count,
            "avg_in_degree":       self.avg_in_degree,
            "avg_out_degree":      self.avg_out_degree,
            "max_in_degree":       self.max_in_degree,
            "max_out_degree":      self.max_out_degree,
            "density":             self.density,
            "is_dag":              self.is_dag,
            "component_count":     self.component_count,
            "isolated_node_count": self.isolated_node_count,
            "cycle_count":         self.cycle_count,
            "nodes_by_type":       dict(self.nodes_by_type),
            "edges_by_type":       dict(self.edges_by_type),
            "computed_at":         self.computed_at,
        }


@dataclass
class ImpactResult:
    """Downstream impact analysis of a single node."""
    node_id:                str        = ""
    direct_dependents:      list[str]  = field(default_factory=list)
    transitive_dependents:  list[str]  = field(default_factory=list)
    direct_predecessors:    list[str]  = field(default_factory=list)
    impact_score:           float      = 0.0
    max_depth:              int        = 0

    @property
    def total_affected(self) -> int:
        return len(self.transitive_dependents)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id":               self.node_id,
            "direct_dependents":     self.direct_dependents,
            "transitive_dependents": self.transitive_dependents,
            "direct_predecessors":   self.direct_predecessors,
            "impact_score":          self.impact_score,
            "max_depth":             self.max_depth,
            "total_affected":        self.total_affected,
        }
