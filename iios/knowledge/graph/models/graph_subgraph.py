"""
iios/knowledge/graph/models/graph_subgraph.py
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .graph_metadata import GraphMetadata
from .graph_node import GraphNode
from .graph_edge import GraphEdge

__all__ = ["GraphSubgraph"]


@dataclass
class GraphSubgraph:
    subgraph_id: str
    label:       str
    nodes:       dict[str, GraphNode] = field(default_factory=dict)
    edges:       dict[str, GraphEdge] = field(default_factory=dict)
    metadata:    GraphMetadata        = field(default_factory=GraphMetadata)
    root_id:     Optional[str]        = None
    properties:  dict[str, Any]       = field(default_factory=dict)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def node_ids(self) -> set[str]:
        return set(self.nodes.keys())

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self.nodes.get(node_id)

    def get_edges_from(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges.values() if e.source_id == node_id and e.is_active]

    def get_edges_to(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges.values() if e.target_id == node_id and e.is_active]

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges[edge.edge_id] = edge

    def to_dict(self) -> dict[str, Any]:
        return {
            "subgraph_id": self.subgraph_id,
            "label":       self.label,
            "nodes":       {k: v.to_dict() for k, v in self.nodes.items()},
            "edges":       {k: v.to_dict() for k, v in self.edges.items()},
            "metadata":    self.metadata.to_dict(),
            "root_id":     self.root_id,
            "properties":  dict(self.properties),
        }

    @classmethod
    def new(cls, label: str = "subgraph", root_id: Optional[str] = None) -> GraphSubgraph:
        return cls(
            subgraph_id = str(uuid.uuid4()),
            label       = label,
            root_id     = root_id,
        )
