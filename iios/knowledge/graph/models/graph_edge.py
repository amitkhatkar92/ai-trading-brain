"""
iios/knowledge/graph/models/graph_edge.py
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..graph_constants import (
    GraphEdgeType, EdgeStatus,
    DEFAULT_EDGE_WEIGHT, DEFAULT_EDGE_CONFIDENCE, GRAPH_NAMESPACE,
)
from .graph_metadata import GraphMetadata

__all__ = ["GraphEdge"]


@dataclass
class GraphEdge:
    edge_id:    str
    source_id:  str
    target_id:  str
    edge_type:  GraphEdgeType
    weight:     float          = DEFAULT_EDGE_WEIGHT
    confidence: float          = DEFAULT_EDGE_CONFIDENCE
    status:     EdgeStatus     = EdgeStatus.ACTIVE
    properties: dict[str, Any] = field(default_factory=dict)
    metadata:   GraphMetadata  = field(default_factory=GraphMetadata)
    is_directed: bool          = True
    expires_at: Optional[float] = None
    is_deleted: bool           = False

    @property
    def id(self) -> str:
        return self.edge_id

    @property
    def is_active(self) -> bool:
        return (
            self.status == EdgeStatus.ACTIVE
            and not self.is_deleted
            and not self.is_expired
        )

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at

    def activate(self) -> None:
        self.status = EdgeStatus.ACTIVE
        self.metadata.touch()

    def deactivate(self) -> None:
        self.status = EdgeStatus.INACTIVE
        self.metadata.touch()

    def expire(self) -> None:
        self.status = EdgeStatus.EXPIRED
        self.expires_at = time.time()
        self.metadata.touch()

    def set_weight(self, weight: float) -> None:
        self.weight = max(0.0, min(1.0, weight))

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id":    self.edge_id,
            "source_id":  self.source_id,
            "target_id":  self.target_id,
            "edge_type":  self.edge_type.value,
            "weight":     self.weight,
            "confidence": self.confidence,
            "status":     self.status.value,
            "properties": dict(self.properties),
            "metadata":   self.metadata.to_dict(),
            "is_directed": self.is_directed,
            "expires_at": self.expires_at,
            "is_deleted": self.is_deleted,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GraphEdge:
        return cls(
            edge_id    = d["edge_id"],
            source_id  = d["source_id"],
            target_id  = d["target_id"],
            edge_type  = GraphEdgeType(d["edge_type"]),
            weight     = d.get("weight",     DEFAULT_EDGE_WEIGHT),
            confidence = d.get("confidence", DEFAULT_EDGE_CONFIDENCE),
            status     = EdgeStatus(d.get("status", "active")),
            properties = dict(d.get("properties", {})),
            metadata   = GraphMetadata.from_dict(d.get("metadata", {})),
            is_directed = d.get("is_directed", True),
            expires_at = d.get("expires_at"),
            is_deleted = d.get("is_deleted", False),
        )

    @classmethod
    def new(
        cls,
        source_id: str,
        target_id: str,
        edge_type: GraphEdgeType,
        **kwargs: Any,
    ) -> GraphEdge:
        return cls(
            edge_id   = f"{GRAPH_NAMESPACE}/edge/{uuid.uuid4()}",
            source_id = source_id,
            target_id = target_id,
            edge_type = edge_type,
            **kwargs,
        )
