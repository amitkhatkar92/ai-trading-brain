"""iios/integration/research/projects/project_manager.py"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from iios.integration.research.core.research_project      import ResearchProject
from iios.integration.research.core.research_metadata     import ResearchMetadata
from iios.integration.research.research_constants         import (
    DEFAULT_MAX_PROJECTS,
    ResearchProjectStatus,
)
from iios.integration.research.research_exceptions        import (
    ResearchProjectAlreadyExistsError,
    ResearchProjectCapacityError,
    ResearchProjectNotFoundError,
)

logger = logging.getLogger(__name__)


class ProjectManager:
    """
    Manages project lifecycle: create, update, archive, delete, clone.
    """

    def __init__(self, max_projects: int = DEFAULT_MAX_PROJECTS) -> None:
        self._max     = max_projects
        self._store:  dict[str, ResearchProject] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(self, project: ResearchProject) -> ResearchProject:
        if project.project_id in self._store:
            raise ResearchProjectAlreadyExistsError(
                f"Project '{project.project_id}' already exists."
            )
        if len(self._store) >= self._max:
            raise ResearchProjectCapacityError(
                f"Project capacity ({self._max}) reached."
            )
        self._store[project.project_id] = project
        logger.info("[ProjectManager] Created project '%s'.", project.name)
        return project

    def get(self, project_id: str) -> ResearchProject:
        p = self._store.get(project_id)
        if p is None:
            raise ResearchProjectNotFoundError(f"Project '{project_id}' not found.")
        return p

    def update(self, project: ResearchProject) -> ResearchProject:
        if project.project_id not in self._store:
            raise ResearchProjectNotFoundError(f"Project '{project.project_id}' not found.")
        project.touch()
        self._store[project.project_id] = project
        return project

    def delete(self, project_id: str) -> None:
        if project_id not in self._store:
            raise ResearchProjectNotFoundError(f"Project '{project_id}' not found.")
        del self._store[project_id]

    def has(self, project_id: str) -> bool:
        return project_id in self._store

    def all_projects(self) -> list[ResearchProject]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)

    # ── Lifecycle helpers ─────────────────────────────────────────────────────

    def activate(self, project_id: str) -> ResearchProject:
        p = self.get(project_id)
        p.status = ResearchProjectStatus.ACTIVE
        p.touch()
        return p

    def archive(self, project_id: str) -> ResearchProject:
        p = self.get(project_id)
        p.status = ResearchProjectStatus.ARCHIVED
        p.touch()
        return p

    def complete(self, project_id: str) -> ResearchProject:
        p = self.get(project_id)
        p.status       = ResearchProjectStatus.COMPLETED
        p.completed_at = time.time()
        p.touch()
        return p

    def cancel(self, project_id: str) -> ResearchProject:
        p = self.get(project_id)
        p.status = ResearchProjectStatus.CANCELLED
        p.touch()
        return p

    # ── Clone ─────────────────────────────────────────────────────────────────

    def clone(self, project_id: str, new_name: str = "") -> ResearchProject:
        """
        Clone a project.

        Copies metadata and associations but assigns a new project_id and
        resets all experiment_ids (cloned experiments are not created here).
        """
        src = self.get(project_id)
        cloned = ResearchProject(
            name        = new_name or f"{src.name} (clone)",
            description = src.description,
            objective   = src.objective,
            hypothesis  = src.hypothesis,
            methodology = src.methodology,
            owner       = src.owner,
            tags        = list(src.tags),
            status      = ResearchProjectStatus.DRAFT,
            metadata    = ResearchMetadata(
                owner   = src.metadata.owner,
                source  = src.metadata.source,
                notes   = src.metadata.notes,
                tags    = list(src.metadata.tags),
            ),
        )
        return self.create(cloned)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "total":    len(self._store),
            "capacity": self._max,
            "active":   sum(1 for p in self._store.values() if p.status == ResearchProjectStatus.ACTIVE),
        }
