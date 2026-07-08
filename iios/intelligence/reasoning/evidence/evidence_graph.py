"""
iios/intelligence/reasoning/evidence/evidence_graph.py
======================================================
Graph of relationships between evidence items.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import EvidenceRelation


@dataclass
class EvidenceNode:
    evidence_id: str
    weight:      float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "weight": self.weight}


@dataclass
class EvidenceEdge:
    edge_id:   str                   = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    from_id:   str                   = ""
    to_id:     str                   = ""
    relation:  EvidenceRelation      = EvidenceRelation.SUPPORTS
    weight:    float                 = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id":  self.edge_id,
            "from_id":  self.from_id,
            "to_id":    self.to_id,
            "relation": self.relation.value,
            "weight":   self.weight,
        }


class EvidenceGraph:
    """
    Directed graph capturing how evidence items relate to each other.

    Nodes = evidence IDs.
    Edges = typed relationships (supports, contradicts, …).
    Thread-safe.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, EvidenceNode] = {}
        self._edges: list[EvidenceEdge]      = []
        self._lock:  threading.RLock          = threading.RLock()

    # -- Mutation ──────────────────────────────────────────────────────────────

    def add_node(self, evidence_id: str, weight: float = 1.0) -> None:
        with self._lock:
            if evidence_id not in self._nodes:
                self._nodes[evidence_id] = EvidenceNode(evidence_id, weight)

    def add_edge(
        self,
        from_id:  str,
        to_id:    str,
        relation: EvidenceRelation = EvidenceRelation.SUPPORTS,
        weight:   float            = 1.0,
    ) -> EvidenceEdge:
        with self._lock:
            # Auto-register nodes
            for eid in (from_id, to_id):
                if eid not in self._nodes:
                    self._nodes[eid] = EvidenceNode(eid)
            edge = EvidenceEdge(from_id=from_id, to_id=to_id, relation=relation, weight=weight)
            self._edges.append(edge)
            return edge

    def remove_node(self, evidence_id: str) -> None:
        with self._lock:
            self._nodes.pop(evidence_id, None)
            self._edges = [
                e for e in self._edges
                if e.from_id != evidence_id and e.to_id != evidence_id
            ]

    # -- Query ─────────────────────────────────────────────────────────────────

    def _edges_by_relation(
        self, evidence_id: str, relation: EvidenceRelation
    ) -> list[str]:
        with self._lock:
            return [
                e.to_id for e in self._edges
                if e.from_id == evidence_id and e.relation == relation
            ]

    def get_supporters(self, evidence_id: str) -> list[str]:
        return self._edges_by_relation(evidence_id, EvidenceRelation.SUPPORTS)

    def get_contradictors(self, evidence_id: str) -> list[str]:
        return self._edges_by_relation(evidence_id, EvidenceRelation.CONTRADICTS)

    def get_corroborators(self, evidence_id: str) -> list[str]:
        return self._edges_by_relation(evidence_id, EvidenceRelation.CORROBORATES)

    def get_edges_for(self, evidence_id: str) -> list[EvidenceEdge]:
        with self._lock:
            return [
                e for e in self._edges
                if e.from_id == evidence_id or e.to_id == evidence_id
            ]

    def has_node(self, evidence_id: str) -> bool:
        with self._lock:
            return evidence_id in self._nodes

    @property
    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    @property
    def edge_count(self) -> int:
        with self._lock:
            return len(self._edges)

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "nodes": [n.to_dict() for n in self._nodes.values()],
                "edges": [e.to_dict() for e in self._edges],
            }
