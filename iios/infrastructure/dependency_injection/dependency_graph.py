"""
iios/infrastructure/dependency_injection/dependency_graph.py
=============================================================
Directed dependency graph with cycle detection and topological ordering.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from ..infrastructure_exceptions import CircularDependencyError

__all__ = ["DependencyGraph"]


class DependencyGraph:
    """Tracks service dependencies and detects cycles.

    Usage::

        graph = DependencyGraph()
        graph.add_dependency("B", "A")   # B depends on A
        graph.add_dependency("C", "B")
        order = graph.resolution_order()  # ["A", "B", "C"]
    """

    def __init__(self) -> None:
        # key → set of keys it depends on
        self._deps: dict[str, set[str]] = defaultdict(set)
        # key → set of keys that depend on it (reverse)
        self._rdeps: dict[str, set[str]] = defaultdict(set)
        self._nodes: set[str] = set()

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def add_node(self, key: str) -> None:
        self._nodes.add(key)

    def add_dependency(self, dependent: str, dependency: str) -> None:
        """Register that *dependent* requires *dependency*."""
        self._nodes.add(dependent)
        self._nodes.add(dependency)
        self._deps[dependent].add(dependency)
        self._rdeps[dependency].add(dependent)

    def remove_node(self, key: str) -> None:
        """Remove a node and all its edges."""
        for dep in list(self._deps.get(key, [])):
            self._rdeps[dep].discard(key)
        for rdep in list(self._rdeps.get(key, [])):
            self._deps[rdep].discard(key)
        self._deps.pop(key, None)
        self._rdeps.pop(key, None)
        self._nodes.discard(key)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def dependencies_of(self, key: str) -> set[str]:
        """Direct dependencies of *key*."""
        return set(self._deps.get(key, []))

    def dependents_of(self, key: str) -> set[str]:
        """Nodes that directly depend on *key*."""
        return set(self._rdeps.get(key, []))

    def all_dependencies_of(self, key: str) -> set[str]:
        """Transitive closure of all dependencies."""
        result: set[str] = set()
        queue: deque[str] = deque(self._deps.get(key, []))
        while queue:
            node = queue.popleft()
            if node not in result:
                result.add(node)
                queue.extend(self._deps.get(node, []))
        return result

    def has_cycle(self) -> bool:
        """Return True if the graph contains any cycle."""
        try:
            self.resolution_order()
            return False
        except CircularDependencyError:
            return True

    def resolution_order(self) -> list[str]:
        """Return a topological sort (dependencies before dependents).

        Raises:
            CircularDependencyError: If a cycle is detected.
        """
        in_degree: dict[str, int] = {n: 0 for n in self._nodes}
        for node in self._nodes:
            for dep in self._deps.get(node, []):
                in_degree[node] = in_degree.get(node, 0) + 1

        # Kahn's algorithm
        queue: deque[str] = deque(n for n, d in in_degree.items() if d == 0)
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for rdep in self._rdeps.get(node, []):
                in_degree[rdep] -= 1
                if in_degree[rdep] == 0:
                    queue.append(rdep)

        if len(order) != len(self._nodes):
            involved = [n for n, d in in_degree.items() if d > 0]
            raise CircularDependencyError(
                f"Circular dependency detected involving: {involved}",
                code="INF-DI-001",
                context={"nodes": involved},
            )

        return order

    def __contains__(self, key: str) -> bool:
        return key in self._nodes

    def __len__(self) -> int:
        return len(self._nodes)
