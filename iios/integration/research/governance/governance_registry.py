"""governance_registry.py — ResearchProject entity and thread-safe project registry."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import (
    DEFAULT_MAX_RESEARCH_PROJECTS,
    ResearchStatus,
)
from iios.integration.research.governance.governance_exceptions import (
    ResearchProjectAlreadyExistsError,
    ResearchProjectCapacityError,
    ResearchProjectNotFoundError,
    ResearchProjectStateError,
)


@dataclass
class ResearchProject:
    """
    A top-level research project tracked by the governance engine.
    """
    project_id:    str
    name:          str
    description:   Optional[str]
    status:        ResearchStatus
    author:        str
    tags:          list[str]
    created_at:    float
    updated_at:    float
    completed_at:  Optional[float]
    metadata:      dict[str, Any]

    @classmethod
    def create(
        cls,
        name:        str,
        author:      str,
        *,
        project_id:  Optional[str]       = None,
        description: Optional[str]       = None,
        tags:        Optional[list[str]] = None,
        metadata:    Optional[dict]      = None,
    ) -> "ResearchProject":
        now = time.time()
        return cls(
            project_id   = project_id or f"proj_{uuid.uuid4().hex[:10]}",
            name         = name,
            description  = description,
            status       = ResearchStatus.DRAFT,
            author       = author,
            tags         = tags or [],
            created_at   = now,
            updated_at   = now,
            completed_at = None,
            metadata     = metadata or {},
        )

    def start(self) -> None:
        if self.status != ResearchStatus.DRAFT:
            raise ResearchProjectStateError(
                f"Project '{self.project_id}' cannot be started from state {self.status.value}"
            )
        self.status     = ResearchStatus.ACTIVE
        self.updated_at = time.time()

    def complete(self) -> None:
        if self.status not in (ResearchStatus.ACTIVE, ResearchStatus.REVIEW):
            raise ResearchProjectStateError(
                f"Project '{self.project_id}' cannot be completed from state {self.status.value}"
            )
        self.status       = ResearchStatus.COMPLETED
        self.completed_at = time.time()
        self.updated_at   = self.completed_at

    def archive(self) -> None:
        self.status     = ResearchStatus.ARCHIVED
        self.updated_at = time.time()

    def is_terminal(self) -> bool:
        return self.status in (ResearchStatus.COMPLETED, ResearchStatus.ARCHIVED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id":   self.project_id,
            "name":         self.name,
            "description":  self.description,
            "status":       self.status.value,
            "author":       self.author,
            "tags":         self.tags,
            "created_at":   self.created_at,
            "updated_at":   self.updated_at,
            "completed_at": self.completed_at,
        }


class ProjectRegistry:
    """Thread-safe in-memory store for ResearchProject instances."""

    def __init__(self, max_projects: int = DEFAULT_MAX_RESEARCH_PROJECTS) -> None:
        self._projects: dict[str, ResearchProject] = {}
        self._max  = max_projects
        self._lock = threading.RLock()

    def register(self, project: ResearchProject) -> None:
        with self._lock:
            if project.project_id in self._projects:
                raise ResearchProjectAlreadyExistsError(
                    f"Project '{project.project_id}' already exists"
                )
            if len(self._projects) >= self._max:
                raise ResearchProjectCapacityError(
                    f"Project registry capacity ({self._max}) reached"
                )
            self._projects[project.project_id] = project

    def get(self, project_id: str) -> ResearchProject:
        with self._lock:
            proj = self._projects.get(project_id)
        if proj is None:
            raise ResearchProjectNotFoundError(f"Project '{project_id}' not found")
        return proj

    def has(self, project_id: str) -> bool:
        with self._lock:
            return project_id in self._projects

    def remove(self, project_id: str) -> None:
        with self._lock:
            self._projects.pop(project_id, None)

    def all_projects(self) -> list[ResearchProject]:
        with self._lock:
            return list(self._projects.values())

    def by_status(self, status: ResearchStatus) -> list[ResearchProject]:
        with self._lock:
            return [p for p in self._projects.values() if p.status == status]

    def count(self) -> int:
        with self._lock:
            return len(self._projects)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for p in self._projects.values():
                k = p.status.value
                by_status[k] = by_status.get(k, 0) + 1
            return {
                "total":     len(self._projects),
                "by_status": by_status,
                "capacity":  self._max,
            }
