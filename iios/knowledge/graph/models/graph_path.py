"""
iios/knowledge/graph/models/graph_path.py
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = ["PathStep", "GraphPath"]


@dataclass
class PathStep:
    node_id:     str
    edge_id:     Optional[str] = None
    depth:       int           = 0
    edge_type:   str           = ""
    edge_weight: float         = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id":     self.node_id,
            "edge_id":     self.edge_id,
            "depth":       self.depth,
            "edge_type":   self.edge_type,
            "edge_weight": self.edge_weight,
        }


@dataclass
class GraphPath:
    source_id:  str
    target_id:  str
    steps:      list[PathStep]
    total_cost: float = 0.0
    algorithm:  str   = "bfs"
    path_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def node_ids(self) -> list[str]:
        return [s.node_id for s in self.steps]

    @property
    def edge_ids(self) -> list[str]:
        return [s.edge_id for s in self.steps if s.edge_id is not None]

    @property
    def total_depth(self) -> int:
        return max(0, len(self.steps) - 1)

    @property
    def is_valid(self) -> bool:
        if not self.steps:
            return False
        return (
            self.steps[0].node_id == self.source_id
            and self.steps[-1].node_id == self.target_id
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_id":     self.path_id,
            "source_id":   self.source_id,
            "target_id":   self.target_id,
            "steps":       [s.to_dict() for s in self.steps],
            "total_cost":  self.total_cost,
            "total_depth": self.total_depth,
            "algorithm":   self.algorithm,
        }
