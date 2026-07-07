"""
iios/knowledge/versioning/lineage_manager.py
=============================================
LineageManager and DependencyTracker — manage the directed acyclic graph
(DAG) of knowledge lineage and dependency relationships.

LineageManager owns the edge store and provides DAG traversal (ancestors,
descendants, full sub-graph up to a given depth).  It enforces the
no-cycle invariant: adding an edge that would create a cycle raises
LineageCycleError.

DependencyTracker is a thin façade over LineageManager that uses the
DEPENDS_ON relation type exclusively and is the preferred API for
tracking runtime dependencies between knowledge items.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict, deque
from typing import Any, Optional

from .version_constants import LineageRelationType, SYSTEM_VERSIONING_ACTOR, MAX_LINEAGE_DEPTH
from .version_exceptions import LineageError, LineageCycleError
from .models.lineage_graph import LineageEdge, LineageGraph, LineageNode

__all__ = [
    "LineageManager",
    "DependencyTracker",
    "get_lineage_manager",
    "reset_lineage_manager",
    "get_dependency_tracker",
    "reset_dependency_tracker",
]

_LOG = logging.getLogger("iios.knowledge.versioning.lineage")
_lock = threading.Lock()
_lm: Optional["LineageManager"] = None
_dt: Optional["DependencyTracker"] = None


class LineageManager:
    """Thread-safe directed acyclic graph of knowledge lineage."""

    def __init__(self, max_depth: int = MAX_LINEAGE_DEPTH) -> None:
        self._lock = threading.RLock()
        self._max_depth = max_depth

        # source_id → list[(target_id, LineageRelationType, weight)]
        self._outgoing: dict[str, list[tuple[str, LineageRelationType, float]]] = \
            defaultdict(list)
        # target_id → set[source_id]  (for fast ancestor lookup)
        self._incoming: dict[str, set[str]] = defaultdict(set)

        # Optional node labels (knowledge_id → title)
        self._labels: dict[str, str] = {}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _would_cycle(self, source_id: str, target_id: str) -> bool:
        """Return True if adding source→target would create a cycle.

        Uses iterative BFS from target_id following outgoing edges.
        If we can reach source_id from target_id, adding the edge
        would create a cycle.
        """
        if source_id == target_id:
            return True
        visited: set[str] = set()
        queue: deque[str] = deque([target_id])
        while queue:
            node = queue.popleft()
            if node == source_id:
                return True
            if node in visited:
                continue
            visited.add(node)
            for (nxt, _, _) in self._outgoing.get(node, []):
                if nxt not in visited:
                    queue.append(nxt)
        return False

    # ── Edge management ───────────────────────────────────────────────────────

    def add_edge(
        self,
        source_id:  str,
        target_id:  str,
        relation:   LineageRelationType = LineageRelationType.DERIVED_FROM,
        weight:     float = 1.0,
        source_label: str = "",
        target_label: str = "",
    ) -> LineageEdge:
        """Add a directed lineage edge source_id → target_id.

        Raises LineageCycleError if the edge would create a cycle.
        Silently ignores duplicate edges (same source, target, relation).
        """
        if not source_id or not target_id:
            raise LineageError("source_id and target_id must be non-empty.",
                               code="LM-001")

        with self._lock:
            if self._would_cycle(source_id, target_id):
                raise LineageCycleError(
                    f"Adding edge {source_id!r} → {target_id!r} would create a cycle.",
                    code="LM-002",
                )
            # Duplicate check
            for (t, r, _) in self._outgoing.get(source_id, []):
                if t == target_id and r == relation:
                    return LineageEdge(source_id, target_id, relation, weight)

            self._outgoing[source_id].append((target_id, relation, weight))
            self._incoming[target_id].add(source_id)
            if source_label:
                self._labels[source_id] = source_label
            if target_label:
                self._labels[target_id] = target_label

        _LOG.debug("Lineage edge: %s → %s (%s)", source_id[:16], target_id[:16],
                   relation.value)
        return LineageEdge(source_id, target_id, relation, weight)

    def remove_edge(
        self,
        source_id: str,
        target_id: str,
        relation:  LineageRelationType = LineageRelationType.DERIVED_FROM,
    ) -> None:
        with self._lock:
            edges = self._outgoing.get(source_id, [])
            self._outgoing[source_id] = [
                (t, r, w) for (t, r, w) in edges
                if not (t == target_id and r == relation)
            ]
            self._incoming[target_id].discard(source_id)

    def has_edge(
        self,
        source_id: str,
        target_id: str,
        relation:  Optional[LineageRelationType] = None,
    ) -> bool:
        with self._lock:
            for (t, r, _) in self._outgoing.get(source_id, []):
                if t == target_id:
                    if relation is None or r == relation:
                        return True
        return False

    # ── Traversal ─────────────────────────────────────────────────────────────

    def get_ancestors(
        self,
        knowledge_id: str,
        max_depth:    Optional[int] = None,
    ) -> list[str]:
        """BFS traversal following INCOMING edges (parents / ancestors)."""
        limit = max_depth if max_depth is not None else self._max_depth
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(knowledge_id, 0)])
        result: list[str] = []
        while queue:
            node, depth = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            if node != knowledge_id:
                result.append(node)
            if depth < limit:
                with self._lock:
                    parents = list(self._incoming.get(node, set()))
                for p in parents:
                    if p not in visited:
                        queue.append((p, depth + 1))
        return result

    def get_descendants(
        self,
        knowledge_id: str,
        max_depth:    Optional[int] = None,
    ) -> list[str]:
        """BFS traversal following OUTGOING edges (children / descendants)."""
        limit = max_depth if max_depth is not None else self._max_depth
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(knowledge_id, 0)])
        result: list[str] = []
        while queue:
            node, depth = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            if node != knowledge_id:
                result.append(node)
            if depth < limit:
                with self._lock:
                    children = [(t, w) for (t, _, w) in self._outgoing.get(node, [])]
                for (c, _) in children:
                    if c not in visited:
                        queue.append((c, depth + 1))
        return result

    def get_lineage(
        self,
        knowledge_id: str,
        depth:        int = 3,
    ) -> LineageGraph:
        """Build a LineageGraph centred on *knowledge_id*."""
        depth = min(depth, self._max_depth)
        visited_nodes: dict[str, int] = {}   # node_id → depth
        edges_out: list[LineageEdge] = []

        queue: deque[tuple[str, int]] = deque([(knowledge_id, 0)])
        while queue:
            node, d = queue.popleft()
            if node in visited_nodes:
                continue
            visited_nodes[node] = d
            if d < depth:
                with self._lock:
                    out = list(self._outgoing.get(node, []))
                    inc = list(self._incoming.get(node, set()))
                for (tgt, rel, wt) in out:
                    if tgt not in visited_nodes:
                        queue.append((tgt, d + 1))
                    edges_out.append(LineageEdge(node, tgt, rel, wt))
                for src in inc:
                    with self._lock:
                        src_out = self._outgoing.get(src, [])
                    for (t, rel, wt) in src_out:
                        if t == node:
                            if src not in visited_nodes:
                                queue.append((src, d + 1))
                            edges_out.append(LineageEdge(src, node, rel, wt))

        # Deduplicate edges
        seen_edges: set[tuple[str, str, str]] = set()
        unique_edges: list[LineageEdge] = []
        for e in edges_out:
            key = (e.source_id, e.target_id, e.relation.value)
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append(e)

        with self._lock:
            labels = dict(self._labels)

        nodes = [
            LineageNode(
                node_id = nid,
                label   = labels.get(nid, ""),
                depth   = d,
            )
            for nid, d in visited_nodes.items()
        ]
        return LineageGraph(
            root_id = knowledge_id,
            nodes   = nodes,
            edges   = unique_edges,
            depth   = depth,
        )

    # ── Impact analysis ───────────────────────────────────────────────────────

    def impact_analysis(self, knowledge_id: str) -> dict[str, Any]:
        """Return summary of items impacted by changes to *knowledge_id*."""
        descendants = self.get_descendants(knowledge_id)
        ancestors   = self.get_ancestors(knowledge_id)
        with self._lock:
            direct_deps = [t for (t, _, _) in self._outgoing.get(knowledge_id, [])]
        return {
            "knowledge_id":     knowledge_id,
            "direct_dependents": direct_deps,
            "total_downstream": len(descendants),
            "total_upstream":   len(ancestors),
            "descendants":      descendants,
            "ancestors":        ancestors,
        }

    def set_label(self, knowledge_id: str, label: str) -> None:
        with self._lock:
            self._labels[knowledge_id] = label

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total_edges = sum(len(v) for v in self._outgoing.values())
            return {
                "total_nodes": len(self._outgoing) + len(self._incoming),
                "total_edges": total_edges,
            }


# ── DependencyTracker ─────────────────────────────────────────────────────────

class DependencyTracker:
    """Façade over LineageManager for DEPENDS_ON relationships."""

    def __init__(self, lineage_manager: LineageManager) -> None:
        self._lm = lineage_manager

    def add_dependency(
        self,
        dependent_id:  str,
        dependency_id: str,
        weight:        float = 1.0,
    ) -> LineageEdge:
        """Register that *dependent_id* depends on *dependency_id*."""
        return self._lm.add_edge(
            dependent_id, dependency_id,
            LineageRelationType.DEPENDS_ON, weight,
        )

    def remove_dependency(self, dependent_id: str, dependency_id: str) -> None:
        self._lm.remove_edge(
            dependent_id, dependency_id, LineageRelationType.DEPENDS_ON
        )

    def get_dependencies(self, knowledge_id: str) -> list[str]:
        with self._lm._lock:
            return [
                t for (t, r, _) in self._lm._outgoing.get(knowledge_id, [])
                if r == LineageRelationType.DEPENDS_ON
            ]

    def get_dependents(self, knowledge_id: str) -> list[str]:
        """Items that depend ON *knowledge_id*."""
        with self._lm._lock:
            result = []
            for (src, edges) in self._lm._outgoing.items():
                for (t, r, _) in edges:
                    if t == knowledge_id and r == LineageRelationType.DEPENDS_ON:
                        result.append(src)
            return result

    def has_dependency(self, dependent_id: str, dependency_id: str) -> bool:
        return self._lm.has_edge(
            dependent_id, dependency_id, LineageRelationType.DEPENDS_ON
        )

    def transitive_dependencies(
        self, knowledge_id: str, max_depth: int = MAX_LINEAGE_DEPTH
    ) -> list[str]:
        return self._lm.get_descendants(knowledge_id, max_depth)


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_lineage_manager() -> LineageManager:
    global _lm
    if _lm is None:
        with _lock:
            if _lm is None:
                _lm = LineageManager()
    return _lm


def reset_lineage_manager() -> None:
    global _lm
    with _lock:
        _lm = None


def get_dependency_tracker() -> DependencyTracker:
    global _dt
    if _dt is None:
        with _lock:
            if _dt is None:
                _dt = DependencyTracker(get_lineage_manager())
    return _dt


def reset_dependency_tracker() -> None:
    global _dt
    with _lock:
        _dt = None
