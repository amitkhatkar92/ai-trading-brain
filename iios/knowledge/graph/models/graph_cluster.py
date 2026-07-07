"""
iios/knowledge/graph/models/graph_cluster.py
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .graph_metadata import GraphMetadata

__all__ = ["GraphCluster"]


@dataclass
class GraphCluster:
    cluster_id:  str
    label:       str
    node_ids:    set[str]        = field(default_factory=set)
    metadata:    GraphMetadata   = field(default_factory=GraphMetadata)
    properties:  dict[str, Any]  = field(default_factory=dict)
    centroid_id: Optional[str]   = None  # representative node

    @property
    def size(self) -> int:
        return len(self.node_ids)

    def contains(self, node_id: str) -> bool:
        return node_id in self.node_ids

    def add_node(self, node_id: str) -> None:
        self.node_ids.add(node_id)

    def remove_node(self, node_id: str) -> None:
        self.node_ids.discard(node_id)

    def merge_with(self, other: GraphCluster) -> GraphCluster:
        """Create a new cluster that is the union of self and other."""
        return GraphCluster(
            cluster_id  = str(uuid.uuid4()),
            label       = f"{self.label}+{other.label}",
            node_ids    = self.node_ids | other.node_ids,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id":  self.cluster_id,
            "label":       self.label,
            "node_ids":    sorted(self.node_ids),
            "metadata":    self.metadata.to_dict(),
            "properties":  dict(self.properties),
            "centroid_id": self.centroid_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GraphCluster:
        return cls(
            cluster_id  = d["cluster_id"],
            label       = d["label"],
            node_ids    = set(d.get("node_ids", [])),
            metadata    = GraphMetadata.from_dict(d.get("metadata", {})),
            properties  = dict(d.get("properties", {})),
            centroid_id = d.get("centroid_id"),
        )

    @classmethod
    def new(cls, label: str, node_ids: Optional[set[str]] = None) -> GraphCluster:
        return cls(
            cluster_id = str(uuid.uuid4()),
            label      = label,
            node_ids   = set(node_ids or []),
        )
