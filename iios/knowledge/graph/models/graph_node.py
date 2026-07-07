"""
iios/knowledge/graph/models/graph_node.py
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..graph_constants import GraphNodeType, NodeStatus, GRAPH_NAMESPACE
from .graph_metadata import GraphMetadata

__all__ = ["GraphNode"]


@dataclass
class GraphNode:
    node_id:      str
    node_type:    GraphNodeType
    label:        str
    status:       NodeStatus            = NodeStatus.ACTIVE
    properties:   dict[str, Any]        = field(default_factory=dict)
    metadata:     GraphMetadata         = field(default_factory=GraphMetadata)
    version:      str                   = "1.0.0"
    weight:       float                 = 1.0
    confidence:   float                 = 1.0
    knowledge_id: Optional[str]         = None  # link to KnowledgeRecord
    is_deleted:   bool                  = False

    @property
    def id(self) -> str:
        return self.node_id

    @property
    def is_active(self) -> bool:
        return self.status == NodeStatus.ACTIVE and not self.is_deleted

    def activate(self) -> None:
        self.status = NodeStatus.ACTIVE
        self.metadata.touch()

    def deactivate(self) -> None:
        self.status = NodeStatus.INACTIVE
        self.metadata.touch()

    def archive(self) -> None:
        self.status = NodeStatus.ARCHIVED
        self.metadata.touch()

    def merge(self) -> None:
        self.status = NodeStatus.MERGED
        self.metadata.touch()

    def touch(self, actor: str = "") -> None:
        self.metadata.touch(actor or self.metadata.updated_by)

    def set_property(self, key: str, value: Any) -> None:
        self.properties[key] = value

    def get_property(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id":      self.node_id,
            "node_type":    self.node_type.value,
            "label":        self.label,
            "status":       self.status.value,
            "properties":   dict(self.properties),
            "metadata":     self.metadata.to_dict(),
            "version":      self.version,
            "weight":       self.weight,
            "confidence":   self.confidence,
            "knowledge_id": self.knowledge_id,
            "is_deleted":   self.is_deleted,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GraphNode:
        return cls(
            node_id      = d["node_id"],
            node_type    = GraphNodeType(d["node_type"]),
            label        = d["label"],
            status       = NodeStatus(d.get("status", "active")),
            properties   = dict(d.get("properties", {})),
            metadata     = GraphMetadata.from_dict(d.get("metadata", {})),
            version      = d.get("version",      "1.0.0"),
            weight       = d.get("weight",       1.0),
            confidence   = d.get("confidence",   1.0),
            knowledge_id = d.get("knowledge_id"),
            is_deleted   = d.get("is_deleted",   False),
        )

    @classmethod
    def new(
        cls,
        label:     str,
        node_type: GraphNodeType = GraphNodeType.ENTITY,
        **kwargs:  Any,
    ) -> GraphNode:
        return cls(
            node_id   = f"{GRAPH_NAMESPACE}/{uuid.uuid4()}",
            node_type = node_type,
            label     = label,
            **kwargs,
        )
