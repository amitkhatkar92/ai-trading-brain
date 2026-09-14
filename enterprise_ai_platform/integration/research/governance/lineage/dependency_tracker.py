"""lineage/dependency_tracker.py — Tracks runtime dependencies between entities."""
from __future__ import annotations

import threading
from typing import Any, Optional


class DependencyTracker:
    """
    Maintains a forward and reverse dependency map for fast impact analysis.

    ``entity A depends on entity B`` means changes to B may affect A.

    Thread-safe via a single RLock.
    """

    def __init__(self) -> None:
        self._deps:   dict[str, set[str]] = {}   # entity_id → {depends on ...}
        self._rdeps:  dict[str, set[str]] = {}   # entity_id → {depended on by ...}
        self._lock    = threading.RLock()

    def add_dependency(self, dependent: str, dependency: str) -> None:
        """Record that ``dependent`` depends on ``dependency``."""
        with self._lock:
            self._deps.setdefault(dependent, set()).add(dependency)
            self._rdeps.setdefault(dependency, set()).add(dependent)
            # ensure both appear as keys
            self._deps.setdefault(dependency, set())
            self._rdeps.setdefault(dependent, set())

    def remove_dependency(self, dependent: str, dependency: str) -> None:
        with self._lock:
            self._deps.get(dependent, set()).discard(dependency)
            self._rdeps.get(dependency, set()).discard(dependent)

    def dependencies_of(self, entity_id: str) -> set[str]:
        """Return all entities that ``entity_id`` depends on."""
        with self._lock:
            return set(self._deps.get(entity_id, set()))

    def dependents_of(self, entity_id: str) -> set[str]:
        """Return all entities that depend on ``entity_id``."""
        with self._lock:
            return set(self._rdeps.get(entity_id, set()))

    def transitive_dependents(self, entity_id: str) -> set[str]:
        """Return all entities (direct and transitive) that depend on ``entity_id``."""
        with self._lock:
            visited: set[str] = set()
            queue = [entity_id]
            while queue:
                current = queue.pop()
                for dep in self._rdeps.get(current, set()):
                    if dep not in visited:
                        visited.add(dep)
                        queue.append(dep)
            return visited

    def impact_of_change(self, entity_id: str) -> list[str]:
        """Ordered list of all affected entities if ``entity_id`` changes."""
        return sorted(self.transitive_dependents(entity_id))

    def remove_entity(self, entity_id: str) -> None:
        with self._lock:
            for dep in self._deps.pop(entity_id, set()):
                self._rdeps.get(dep, set()).discard(entity_id)
            for dep in self._rdeps.pop(entity_id, set()):
                self._deps.get(dep, set()).discard(entity_id)

    def entity_count(self) -> int:
        with self._lock:
            return len(self._deps)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total_deps = sum(len(v) for v in self._deps.values())
            return {
                "entities":    len(self._deps),
                "total_edges": total_deps,
            }
