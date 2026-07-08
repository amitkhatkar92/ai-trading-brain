"""
iios/ontology/reasoning/inference/inference_graph.py
=====================================================
In-memory inference graph built during a reasoning session.

Captures the typed graph of inferred relationships between ontology types,
with confidence weights and rule attribution.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = [
    "InferenceNode",
    "InferenceEdge",
    "InferenceGraph",
]


@dataclass
class InferenceNode:
    """A type in the inference graph."""
    uri:                  str
    name:                 str
    namespace_uri:        str
    abstract:             bool
    inferred_properties:  list[str]           = field(default_factory=list)
    confidence:           float               = 1.0
    metadata:             dict[str, Any]      = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "uri":                 self.uri,
            "name":                self.name,
            "namespace_uri":       self.namespace_uri,
            "abstract":            self.abstract,
            "inferred_properties": self.inferred_properties,
            "confidence":          round(self.confidence, 4),
        }


@dataclass
class InferenceEdge:
    """A directed edge representing an inferred or asserted relation."""
    source:     str
    target:     str
    relation:   str              # predicate / relation name
    confidence: float = 1.0
    rule_id:    str   = ""
    inferred:   bool  = True

    def to_dict(self) -> dict:
        return {
            "source":     self.source,
            "target":     self.target,
            "relation":   self.relation,
            "confidence": round(self.confidence, 4),
            "rule_id":    self.rule_id,
            "inferred":   self.inferred,
        }


class InferenceGraph:
    """
    Typed directed graph of inferred ontology relationships.

    Supports path finding, cycle detection, and neighbourhood queries.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, InferenceNode]   = {}
        self._edges: list[InferenceEdge]         = []
        self._adj:   dict[str, list[InferenceEdge]] = {}  # source -> edges
        self._rev:   dict[str, list[InferenceEdge]] = {}  # target -> edges

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_node(self, node: InferenceNode) -> None:
        self._nodes[node.uri] = node
        self._adj.setdefault(node.uri, [])
        self._rev.setdefault(node.uri, [])

    def add_edge(self, edge: InferenceEdge) -> None:
        self._edges.append(edge)
        self._adj.setdefault(edge.source, []).append(edge)
        self._rev.setdefault(edge.target, []).append(edge)
        # Ensure both endpoints exist as at least empty adjacency entries
        self._adj.setdefault(edge.target, [])
        self._rev.setdefault(edge.source, [])

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get_node(self, uri: str) -> Optional[InferenceNode]:
        return self._nodes.get(uri)

    def edges_from(self, uri: str) -> list[InferenceEdge]:
        return list(self._adj.get(uri, []))

    def edges_to(self, uri: str) -> list[InferenceEdge]:
        return list(self._rev.get(uri, []))

    def edges_with_relation(self, relation: str) -> list[InferenceEdge]:
        return [e for e in self._edges if e.relation == relation]

    def neighbours(self, uri: str) -> set[str]:
        return {e.target for e in self._adj.get(uri, [])}

    def reverse_neighbours(self, uri: str) -> set[str]:
        return {e.source for e in self._rev.get(uri, [])}

    # ── Path finding ──────────────────────────────────────────────────────────

    def find_path(
        self,
        source: str,
        target: str,
        max_hops: int = 16,
    ) -> list[str]:
        """BFS shortest path from *source* to *target*. Returns [] if none."""
        if source == target:
            return [source]
        visited: set[str]          = {source}
        queue:   deque[list[str]]  = deque([[source]])

        while queue:
            path = queue.popleft()
            current = path[-1]
            if len(path) > max_hops + 1:
                continue
            for nb in self.neighbours(current):
                if nb == target:
                    return path + [nb]
                if nb not in visited:
                    visited.add(nb)
                    queue.append(path + [nb])
        return []

    def all_paths(
        self,
        source:   str,
        target:   str,
        max_hops: int = 8,
    ) -> list[list[str]]:
        """All simple paths from *source* to *target* within *max_hops*."""
        if source == target:
            return [[source]]
        results: list[list[str]] = []
        stack:   list[tuple[str, list[str], set[str]]] = [
            (source, [source], {source})
        ]
        while stack:
            current, path, visited = stack.pop()
            if len(path) > max_hops + 1:
                continue
            for nb in self.neighbours(current):
                if nb == target:
                    results.append(path + [nb])
                elif nb not in visited:
                    stack.append((nb, path + [nb], visited | {nb}))
        return results

    def detect_cycles(self) -> list[list[str]]:
        """
        Detect all cycles using DFS with colouring.
        Returns a list of cycle paths (each path is a list of URIs).
        """
        WHITE, GREY, BLACK = 0, 1, 2
        colour: dict[str, int]   = {}
        cycles: list[list[str]]  = []
        parent: dict[str, Optional[str]] = {}

        def dfs(node: str) -> None:
            colour[node] = GREY
            for e in self._adj.get(node, []):
                nb = e.target
                if colour.get(nb) == GREY:
                    # Found a back edge — reconstruct cycle
                    cycle: list[str] = [nb]
                    cur = node
                    while cur != nb and cur is not None:
                        cycle.append(cur)
                        cur = parent.get(cur)
                    cycle.append(nb)
                    cycles.append(list(reversed(cycle)))
                elif colour.get(nb, WHITE) == WHITE:
                    parent[nb] = node
                    dfs(nb)
            colour[node] = BLACK

        for uri in self._nodes:
            if colour.get(uri, WHITE) == WHITE:
                parent[uri] = None
                dfs(uri)

        return cycles

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
        }

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
        }
