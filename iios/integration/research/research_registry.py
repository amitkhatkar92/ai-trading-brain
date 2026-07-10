"""iios/integration/research/research_registry.py

Thread-safe project registry for the research framework.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.integration.research.core.research_project import ResearchProject
from iios.integration.research.research_constants     import (
    DEFAULT_MAX_PROJECTS,
    ResearchProjectStatus,
)
from iios.integration.research.research_exceptions    import (
    ResearchProjectAlreadyExistsError,
    ResearchProjectNotFoundError,
    ResearchRegistryFullError,
)

logger = logging.getLogger(__name__)


class ResearchRegistry:
    """
    Central project registry with O(1) lookup.

    Maintains an index of all ResearchProject objects.
    Projects can also be looked up by name.
    """

    def __init__(self, max_projects: int = DEFAULT_MAX_PROJECTS) -> None:
        self._max   = max_projects
        self._lock  = threading.RLock()
        self._store: dict[str, ResearchProject] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, project: ResearchProject) -> None:
        with self._lock:
            if project.project_id in self._store:
                raise ResearchProjectAlreadyExistsError(
                    f"Project '{project.project_id}' already registered."
                )
            if len(self._store) >= self._max:
                raise ResearchRegistryFullError(
                    f"Registry capacity ({self._max} projects) reached."
                )
            self._store[project.project_id] = project
            logger.info("[ResearchRegistry] Registered project '%s'.", project.name)

    def unregister(self, project_id: str) -> None:
        with self._lock:
            if project_id not in self._store:
                raise ResearchProjectNotFoundError(f"Project '{project_id}' not found.")
            del self._store[project_id]

    def get(self, project_id: str) -> ResearchProject:
        with self._lock:
            p = self._store.get(project_id)
            if p is None:
                raise ResearchProjectNotFoundError(f"Project '{project_id}' not found.")
            return p

    def has(self, project_id: str) -> bool:
        with self._lock:
            return project_id in self._store

    def update(self, project: ResearchProject) -> None:
        with self._lock:
            if project.project_id not in self._store:
                raise ResearchProjectNotFoundError(f"Project '{project.project_id}' not found.")
            self._store[project.project_id] = project

    # ── Discovery ─────────────────────────────────────────────────────────────

    def all_projects(self) -> list[ResearchProject]:
        with self._lock:
            return list(self._store.values())

    def find_by_status(self, status: ResearchProjectStatus) -> list[ResearchProject]:
        with self._lock:
            return [p for p in self._store.values() if p.status == status]

    def find_by_owner(self, owner: str) -> list[ResearchProject]:
        with self._lock:
            return [p for p in self._store.values() if p.owner == owner]

    def find_by_tag(self, tag: str) -> list[ResearchProject]:
        with self._lock:
            return [p for p in self._store.values() if tag in p.tags]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":    len(self._store),
                "capacity": self._max,
                "active":   sum(1 for p in self._store.values()
                                if p.status == ResearchProjectStatus.ACTIVE),
            }
