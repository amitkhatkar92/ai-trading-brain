"""
iios/intelligence/workflow/workflow_registry.py
================================================
Named workflow registry — stores and retrieves WorkflowDefinition objects
by ID, supports versioning and tagging.

Singleton: get_workflow_registry() / reset_workflow_registry()
"""

from __future__ import annotations

import threading
from typing import Optional

from ..intelligence_constants import WorkflowType
from ..intelligence_exceptions import (
    WorkflowNotFoundError,
    WorkflowAlreadyRegisteredError,
)
from .workflow_builder import WorkflowDefinition

__all__ = [
    "WorkflowRegistry",
    "get_workflow_registry",
    "reset_workflow_registry",
]


class WorkflowRegistry:
    """
    Thread-safe registry for named WorkflowDefinitions.

    Multiple versions of the same logical workflow can coexist;
    `get()` always returns the latest registered version unless
    `version` is specified.
    """

    def __init__(self) -> None:
        # workflow_id -> {version -> WorkflowDefinition}
        self._store: dict[str, dict[str, WorkflowDefinition]] = {}
        self._lock  = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        definition: WorkflowDefinition,
        overwrite:  bool = False,
    ) -> None:
        with self._lock:
            versions = self._store.setdefault(definition.workflow_id, {})
            if definition.version in versions and not overwrite:
                raise WorkflowAlreadyRegisteredError(
                    f"{definition.workflow_id}@{definition.version}"
                )
            versions[definition.version] = definition

    def unregister(self, workflow_id: str, version: Optional[str] = None) -> bool:
        with self._lock:
            if workflow_id not in self._store:
                return False
            if version is not None:
                return bool(self._store[workflow_id].pop(version, None))
            del self._store[workflow_id]
            return True

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(
        self,
        workflow_id: str,
        version:     Optional[str] = None,
    ) -> WorkflowDefinition:
        with self._lock:
            versions = self._store.get(workflow_id)
            if not versions:
                raise WorkflowNotFoundError(workflow_id)
            if version is not None:
                d = versions.get(version)
                if d is None:
                    raise WorkflowNotFoundError(f"{workflow_id}@{version}")
                return d
            # Return latest (last registered)
            return list(versions.values())[-1]

    def has(self, workflow_id: str, version: Optional[str] = None) -> bool:
        with self._lock:
            versions = self._store.get(workflow_id)
            if not versions:
                return False
            if version:
                return version in versions
            return True

    def list_ids(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def list_by_type(self, wf_type: WorkflowType) -> list[WorkflowDefinition]:
        with self._lock:
            result = []
            for versions in self._store.values():
                for defn in versions.values():
                    if defn.workflow_type == wf_type:
                        result.append(defn)
            return result

    def search_by_tag(self, tag: str) -> list[WorkflowDefinition]:
        with self._lock:
            result = []
            for versions in self._store.values():
                for defn in versions.values():
                    if tag in defn.tags:
                        result.append(defn)
            return result

    def all_definitions(self) -> list[WorkflowDefinition]:
        with self._lock:
            return [
                defn
                for versions in self._store.values()
                for defn in versions.values()
            ]

    def stats(self) -> dict:
        with self._lock:
            total     = sum(len(vs) for vs in self._store.values())
            by_type: dict[str, int] = {}
            for versions in self._store.values():
                for d in versions.values():
                    k = d.workflow_type.value
                    by_type[k] = by_type.get(k, 0) + 1
            return {
                "unique_ids":    len(self._store),
                "total_versions": total,
                "by_type":       by_type,
            }


# ── Singleton ─────────────────────────────────────────────────────────────────

_wr_lock = threading.Lock()
_wr_inst: Optional[WorkflowRegistry] = None


def get_workflow_registry() -> WorkflowRegistry:
    global _wr_inst
    if _wr_inst is None:
        with _wr_lock:
            if _wr_inst is None:
                _wr_inst = WorkflowRegistry()
    return _wr_inst


def reset_workflow_registry() -> None:
    global _wr_inst
    with _wr_lock:
        _wr_inst = None
