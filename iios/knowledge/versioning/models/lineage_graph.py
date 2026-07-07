"""
iios/knowledge/versioning/models/lineage_graph.py
==================================================
LineageNode, LineageEdge, and LineageGraph — in-memory graph representation
of knowledge lineage produced by LineageManager.get_lineage().

The lineage graph is a DAG (directed acyclic graph) where nodes are
knowledge items and edges represent derivation / dependency relationships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..version_constants import LineageRelationType

__all__ = ["LineageNode", "LineageEdge", "LineageGraph"]


@dataclass
class LineageNode:
    """A single knowledge item in the lineage graph."""

    node_id:    str                  # knowledge_id
    label:      str    = ""          # human-readable label (title)
    version_id: Optional[str] = None # pinned version, None = latest
    depth:      int    = 0           # hops from root
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id":    self.node_id,
            "label":      self.label,
            "version_id": self.version_id,
            "depth":      self.depth,
            "attributes": dict(self.attributes),
        }


@dataclass
class LineageEdge:
    """A directed relationship between two knowledge items."""

    source_id:  str
    target_id:  str
    relation:   LineageRelationType = LineageRelationType.DERIVED_FROM
    weight:     float = 1.0
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id":  self.source_id,
            "target_id":  self.target_id,
            "relation":   self.relation.value,
            "weight":     self.weight,
            "attributes": dict(self.attributes),
        }


@dataclass
class LineageGraph:
    """Complete lineage sub-graph anchored at a root knowledge item."""

    root_id: str
    nodes:   list[LineageNode] = field(default_factory=list)
    edges:   list[LineageEdge] = field(default_factory=list)
    depth:   int = 0           # traversal depth used to build this graph

    # ── Queries ───────────────────────────────────────────────────────────────

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def get_node(self, node_id: str) -> Optional[LineageNode]:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def ancestors_of(self, node_id: str) -> list[str]:
        """Return all node_ids that have an edge pointing TO ``node_id``."""
        return [e.source_id for e in self.edges if e.target_id == node_id]

    def descendants_of(self, node_id: str) -> list[str]:
        """Return all node_ids that ``node_id`` has an edge pointing TO."""
        return [e.target_id for e in self.edges if e.source_id == node_id]

    def edges_for(self, node_id: str) -> list[LineageEdge]:
        return [e for e in self.edges
                if e.source_id == node_id or e.target_id == node_id]

    def all_node_ids(self) -> list[str]:
        return [n.node_id for n in self.nodes]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_id":    self.root_id,
            "depth":      self.depth,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "nodes":      [n.to_dict() for n in self.nodes],
            "edges":      [e.to_dict() for e in self.edges],
        }
