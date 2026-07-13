"""iios/investment/strategy/lifecycle/dependency_graph.py
Directed acyclic graph for strategy execution dependencies.

Semantics: an edge A → B means "A must complete before B executes."
Cycles are rejected at insertion time via DFS.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Set


class CyclicDependencyError(Exception):
    """Raised when a dependency edge would create a cycle."""


@dataclass
class DependencyNode:
    """Single node in the dependency DAG."""

    strategy_id: str
    dependencies: Set[str] = field(default_factory=set)  # must complete before me
    dependents: Set[str] = field(default_factory=set)    # must wait for me

    def add_dependency(self, dep_id: str) -> None:
        self.dependencies.add(dep_id)

    def remove_dependency(self, dep_id: str) -> None:
        self.dependencies.discard(dep_id)

    def add_dependent(self, dep_id: str) -> None:
        self.dependents.add(dep_id)


class DependencyGraph:
    """
    Thread-safe directed acyclic graph of strategy dependencies.

    Key operations:
      add_dependency(strategy, depends_on)  — declares ordering constraint
      topological_sort()                    — full execution order
      independent_sets()                    — parallel execution batches
      is_ready(strategy_id, completed)      — runtime readiness check
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._nodes: Dict[str, DependencyNode] = {}

    # ── Mutation ──────────────────────────────────────────────────────────────

    def ensure_node(self, strategy_id: str) -> DependencyNode:
        """Return existing node or create a new one."""
        with self._lock:
            if strategy_id not in self._nodes:
                self._nodes[strategy_id] = DependencyNode(strategy_id=strategy_id)
            return self._nodes[strategy_id]

    def add_dependency(self, strategy_id: str, depends_on: str) -> None:
        """
        Record that strategy_id must wait for depends_on.

        Raises CyclicDependencyError if the edge would form a cycle.
        """
        with self._lock:
            self.ensure_node(strategy_id)
            self.ensure_node(depends_on)
            if strategy_id == depends_on:
                raise CyclicDependencyError(
                    f"Strategy {strategy_id!r} cannot depend on itself"
                )
            # Would adding depends_on → strategy_id create a cycle?
            # i.e. is there already a path from strategy_id to depends_on?
            if self._has_path_locked(strategy_id, depends_on):
                raise CyclicDependencyError(
                    f"Adding {strategy_id!r} depends_on {depends_on!r} creates a cycle"
                )
            self._nodes[strategy_id].add_dependency(depends_on)
            self._nodes[depends_on].add_dependent(strategy_id)

    def remove_dependency(self, strategy_id: str, depends_on: str) -> None:
        with self._lock:
            node = self._nodes.get(strategy_id)
            if node:
                node.remove_dependency(depends_on)
            dep_node = self._nodes.get(depends_on)
            if dep_node:
                dep_node.dependents.discard(strategy_id)

    def remove_strategy(self, strategy_id: str) -> None:
        """Remove a strategy and all edges touching it."""
        with self._lock:
            node = self._nodes.pop(strategy_id, None)
            if node is None:
                return
            for dep_id in node.dependents:
                if dep_id in self._nodes:
                    self._nodes[dep_id].remove_dependency(strategy_id)
            for pre_id in node.dependencies:
                if pre_id in self._nodes:
                    self._nodes[pre_id].dependents.discard(strategy_id)

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_dependencies(self, strategy_id: str) -> FrozenSet[str]:
        with self._lock:
            node = self._nodes.get(strategy_id)
            return frozenset(node.dependencies) if node else frozenset()

    def get_dependents(self, strategy_id: str) -> FrozenSet[str]:
        with self._lock:
            node = self._nodes.get(strategy_id)
            return frozenset(node.dependents) if node else frozenset()

    def all_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._nodes.keys())

    def topological_sort(self) -> List[str]:
        """
        Kahn's algorithm — returns strategies in dependency-first order.

        Raises CyclicDependencyError if a cycle exists.
        """
        with self._lock:
            in_degree: Dict[str, int] = {sid: 0 for sid in self._nodes}
            for node in self._nodes.values():
                for dep in node.dependencies:
                    if dep in in_degree:
                        in_degree[node.strategy_id] += 1

            queue = [sid for sid, deg in in_degree.items() if deg == 0]
            order: List[str] = []

            while queue:
                current = queue.pop(0)
                order.append(current)
                for dep_id in self._nodes[current].dependents:
                    if dep_id not in in_degree:
                        continue
                    in_degree[dep_id] -= 1
                    if in_degree[dep_id] == 0:
                        queue.append(dep_id)

            if len(order) != len(self._nodes):
                raise CyclicDependencyError(
                    "Cycle detected during topological sort"
                )
            return order

    def independent_sets(self) -> List[List[str]]:
        """
        Return batches of strategies that can execute concurrently.

        Each batch depends only on strategies in earlier batches.
        Returns [] when the graph is empty.
        """
        with self._lock:
            if not self._nodes:
                return []

            in_degree: Dict[str, int] = {sid: 0 for sid in self._nodes}
            for node in self._nodes.values():
                for dep in node.dependencies:
                    if dep in in_degree:
                        in_degree[node.strategy_id] += 1

            batches: List[List[str]] = []
            remaining = set(self._nodes.keys())

            while remaining:
                batch = [
                    sid for sid in remaining if in_degree.get(sid, 0) == 0
                ]
                if not batch:
                    raise CyclicDependencyError(
                        "Cycle detected while computing independent sets"
                    )
                batches.append(sorted(batch))
                for sid in batch:
                    remaining.discard(sid)
                    for dep_id in self._nodes[sid].dependents:
                        if dep_id in remaining:
                            in_degree[dep_id] -= 1

            return batches

    def is_ready(self, strategy_id: str, completed: Set[str]) -> bool:
        """True if all dependencies of strategy_id are in the completed set."""
        return self.get_dependencies(strategy_id).issubset(completed)

    def __len__(self) -> int:
        with self._lock:
            return len(self._nodes)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _has_path_locked(self, from_id: str, to_id: str) -> bool:
        """DFS reachability check — caller must hold _lock."""
        visited: Set[str] = set()
        stack = [from_id]
        while stack:
            current = stack.pop()
            if current == to_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            node = self._nodes.get(current)
            if node:
                # Follow dependents (outgoing edges from from_id's perspective)
                stack.extend(node.dependents)
        return False
