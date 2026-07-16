"""iios/execution/oms/persistence/repository_registry.py
==================================================
RepositoryRegistry — LifecycleAwareMixin registry of StorageContract instances.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import threading
from typing import Iterator

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.oms.persistence.constants import (
    DEFAULT_MAX_REPOSITORIES,
    REGISTRY_SYSTEM_ID,
    VERSION,
)
from iios.execution.oms.persistence.exceptions import (
    RepositoryCapacityError,
    RepositoryNotRunning,
)
from iios.execution.oms.persistence.repository_validation import RepositoryValidator
from iios.execution.oms.persistence.storage_contract import StorageContract


class RepositoryRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry of named StorageContract implementations.

    Repositories are keyed by their repository_id.
    The registry must be started before any reads/writes.
    """

    def __init__(self, max_repositories: int = DEFAULT_MAX_REPOSITORIES) -> None:
        super().__init__()
        self._max   = max_repositories
        self._store: dict[str, StorageContract] = {}
        self._lock  = threading.RLock()
        self._log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
        self._audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
        self._validator = RepositoryValidator()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        self._log.info("RepositoryRegistry started.", max_repositories=self._max)

    def _on_stop(self) -> None:
        self._audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        self._log.info("RepositoryRegistry stopped.", registered=self.count)

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RepositoryNotRunning(
                "RepositoryRegistry is not running",
                code="PE-005",
            )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register(self, repo: StorageContract) -> None:
        """Register a StorageContract.  Raises on capacity or contract violations."""
        self._assert_running()
        self._validator.assert_contract(repo)
        with self._lock:
            if len(self._store) >= self._max:
                raise RepositoryCapacityError(
                    f"Maximum repository limit ({self._max}) reached",
                    code="PE-004",
                )
            self._store[repo.repository_id] = repo
            self._log.info("Repository registered.", repository_id=repo.repository_id)

    def unregister(self, repository_id: str) -> bool:
        """Remove a repository by ID.  Returns True if removed."""
        self._assert_running()
        with self._lock:
            removed = self._store.pop(repository_id, None)
            if removed:
                self._log.info("Repository unregistered.", repository_id=repository_id)
            return removed is not None

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, repository_id: str) -> StorageContract | None:
        with self._lock:
            return self._store.get(repository_id)

    def default(self) -> StorageContract | None:
        """Return the first registered repository, or None."""
        with self._lock:
            return next(iter(self._store.values()), None)

    def all(self) -> list[StorageContract]:
        with self._lock:
            return list(self._store.values())

    def repository_ids(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def __iter__(self) -> Iterator[StorageContract]:
        with self._lock:
            snapshot = list(self._store.values())
        return iter(snapshot)

    def __len__(self) -> int:
        return self.count
