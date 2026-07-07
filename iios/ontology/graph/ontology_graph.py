"""
iios/ontology/graph/ontology_graph.py
=======================================
Directed type-hierarchy graph supporting BFS/DFS traversal,
path finding, and subgraph extraction.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Optional

from ..ontology_exceptions import TypeNotFoundError
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import OntologyRelationshipDef, OntologyTypeDef

__all__ = [
    "OntologyGraph",
    "get_ontology_graph",
    "reset_ontology_graph",
]

_LOG  = logging.getLogger("iios.ontology.graph")
_lock = threading.Lock()
_graph: Optional["OntologyGraph"] = None


class OntologyGraph:
    """
    Live view of the type-inheritance and semantic-relationship graphs.
    Backed by the master OntologyRegistryManager — no separate storage.
    """

    @property
    def _mgr(self):
        return get_registry_manager()

    # ── Path finding ───────────────────────────────────────────────────────────

    def shortest_path(
        self,
        source_uri: str,
        target_uri: str,
    ) -> Optional[list[str]]:
        """
        BFS shortest path from *source_uri* to *target_uri* through the
        parent-child inheritance graph.
        Returns a list of URIs from source to target, or None if unreachable.
        """
        if source_uri == target_uri:
            return [source_uri]

        visited: set[str]             = {source_uri}
        queue:   deque[list[str]]     = deque([[source_uri]])

        while queue:
            path = queue.popleft()
            current = path[-1]
            # Expand both children and parent
            td = self._mgr.get_type_or_none(current)
            neighbours: set[str] = set(self._mgr.children_of(current))
            if td and td.parent_uri:
                neighbours.add(td.parent_uri)

            for nxt in neighbours:
                if nxt == target_uri:
                    return path + [nxt]
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(path + [nxt])
        return None

    # ── Subgraph ───────────────────────────────────────────────────────────────

    def subgraph(
        self,
        root_uri:     str,
        max_depth:    int = 10,
    ) -> dict[str, list[str]]:
        """
        Return the inheritance subgraph rooted at *root_uri* as an
        adjacency dict: parent_uri → [child_uri, …].
        """
        result: dict[str, list[str]] = {}
        queue  = deque([(root_uri, 0)])
        visited: set[str] = set()

        while queue:
            uri, depth = queue.popleft()
            if uri in visited or depth > max_depth:
                continue
            visited.add(uri)
            children = list(self._mgr.children_of(uri))
            result[uri] = children
            for child in children:
                queue.append((child, depth + 1))
        return result

    # ── Relationship graph ─────────────────────────────────────────────────────

    def relationship_graph(self) -> dict[str, list[str]]:
        """
        Return the semantic-relationship graph as an adjacency dict:
        source_uri → [target_uri, …].
        """
        adj: dict[str, list[str]] = {}
        for rel in self._mgr.list_relationships():
            adj.setdefault(rel.source_type_uri, []).append(rel.target_type_uri)
        return adj

    # ── Topology ───────────────────────────────────────────────────────────────

    def roots(self) -> list[OntologyTypeDef]:
        """Return types that have no parent (root types)."""
        return [
            td for td in self._mgr.list_all_types()
            if td.parent_uri is None
        ]

    def leaves(self) -> list[OntologyTypeDef]:
        """Return types that have no children."""
        return [
            td for td in self._mgr.list_all_types()
            if not self._mgr.children_of(td.uri)
        ]

    def depth_of(self, uri: str) -> int:
        """Number of edges from the type to its root ancestor (0 = root)."""
        td = self._mgr.get_type_or_none(uri)
        if td is None:
            raise TypeNotFoundError(uri)
        depth  = 0
        current = uri
        for _ in range(64):
            t = self._mgr.get_type_or_none(current)
            if t is None or t.parent_uri is None:
                break
            depth   += 1
            current  = t.parent_uri
        return depth

    # ── Traversal helpers ──────────────────────────────────────────────────────

    def bfs(self, root_uri: str) -> list[str]:
        """BFS order of all descendants (root first)."""
        visited: list[str]    = []
        queue:   deque[str]   = deque([root_uri])
        seen:    set[str]     = set()
        while queue:
            uri = queue.popleft()
            if uri in seen:
                continue
            seen.add(uri)
            visited.append(uri)
            queue.extend(self._mgr.children_of(uri))
        return visited

    def dfs(self, root_uri: str) -> list[str]:
        """DFS order of all descendants (root first, pre-order)."""
        visited: list[str] = []
        seen:    set[str]  = set()
        stack              = [root_uri]
        while stack:
            uri = stack.pop()
            if uri in seen:
                continue
            seen.add(uri)
            visited.append(uri)
            for child in sorted(self._mgr.children_of(uri)):
                stack.append(child)
        return visited

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        all_types = self._mgr.list_all_types()
        return {
            "total_types":     len(all_types),
            "root_types":      len(self.roots()),
            "leaf_types":      len(self.leaves()),
            "total_rels":      len(self._mgr.list_relationships()),
        }


def get_ontology_graph() -> OntologyGraph:
    global _graph
    if _graph is None:
        with _lock:
            if _graph is None:
                _graph = OntologyGraph()
    return _graph


def reset_ontology_graph() -> None:
    global _graph
    with _lock:
        _graph = None
