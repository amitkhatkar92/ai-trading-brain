"""
iios/execution/recovery/snapshot/recovery_snapshot_registry.py
==============================================================
RecoverySnapshotRegistry — lifecycle-aware registry that tracks
snapshot IDs through their CREATED → VALIDATED → PUBLISHED → ARCHIVED
lifecycle.

Prevents duplicate snapshot_id registrations.

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import REGISTRY_ID, VERSION
from .exceptions import SnapshotDuplicateError, SnapshotNotFoundError, SnapshotNotRunningError

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})

# Registry entry status strings
_ST_REGISTERED = "registered"
_ST_VALIDATED  = "validated"
_ST_PUBLISHED  = "published"
_ST_ARCHIVED   = "archived"


class RecoverySnapshotRegistry(LifecycleAwareMixin):
    """
    Lifecycle-aware registry for snapshot IDs.

    Tracks which snapshot IDs are registered, published, or archived.
    Raises SnapshotDuplicateError on duplicate registration.
    """

    VERSION   = VERSION
    SYSTEM_ID = REGISTRY_ID

    def __init__(self) -> None:
        super().__init__()
        self._lock: threading.Lock = threading.Lock()
        self._entries: Dict[str, str] = {}  # snapshot_id → status
        self._session_map: Dict[str, List[str]] = {}  # recovery_session_id → [snapshot_ids]

    def _on_start(self) -> None:
        _log.info("RecoverySnapshotRegistry started", system_id=REGISTRY_ID)

    def _on_stop(self) -> None:
        _log.info("RecoverySnapshotRegistry stopped", system_id=REGISTRY_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise SnapshotNotRunningError()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, snapshot_id: str, recovery_session_id: str) -> None:
        """Register a new snapshot_id. Raises SnapshotDuplicateError if already present."""
        self._assert_running()
        with self._lock:
            if snapshot_id in self._entries:
                raise SnapshotDuplicateError(snapshot_id)
            self._entries[snapshot_id] = _ST_REGISTERED
            self._session_map.setdefault(recovery_session_id, []).append(snapshot_id)
            _log.debug(
                "Snapshot registered",
                snapshot_id=snapshot_id,
                recovery_session_id=recovery_session_id,
            )

    def validate(self, snapshot_id: str) -> None:
        """Mark snapshot as validated."""
        self._assert_running()
        with self._lock:
            if snapshot_id not in self._entries:
                raise SnapshotNotFoundError(snapshot_id)
            self._entries[snapshot_id] = _ST_VALIDATED

    def publish(self, snapshot_id: str) -> None:
        """Mark snapshot as published."""
        self._assert_running()
        with self._lock:
            if snapshot_id not in self._entries:
                raise SnapshotNotFoundError(snapshot_id)
            self._entries[snapshot_id] = _ST_PUBLISHED

    def archive(self, snapshot_id: str) -> None:
        """Mark snapshot as archived."""
        self._assert_running()
        with self._lock:
            if snapshot_id not in self._entries:
                raise SnapshotNotFoundError(snapshot_id)
            self._entries[snapshot_id] = _ST_ARCHIVED

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_registered(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._entries

    def is_published(self, snapshot_id: str) -> bool:
        with self._lock:
            return self._entries.get(snapshot_id) == _ST_PUBLISHED

    def is_archived(self, snapshot_id: str) -> bool:
        with self._lock:
            return self._entries.get(snapshot_id) == _ST_ARCHIVED

    def is_validated(self, snapshot_id: str) -> bool:
        with self._lock:
            return self._entries.get(snapshot_id) == _ST_VALIDATED

    def active_ids(self) -> List[str]:
        """Return snapshot IDs that are not archived."""
        with self._lock:
            return [sid for sid, st in self._entries.items() if st != _ST_ARCHIVED]

    def ids_for_session(self, recovery_session_id: str) -> List[str]:
        with self._lock:
            return list(self._session_map.get(recovery_session_id, []))

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def registered_count(self) -> int:
        with self._lock:
            return len(self._entries)

    @property
    def published_count(self) -> int:
        with self._lock:
            return sum(1 for st in self._entries.values() if st == _ST_PUBLISHED)

    @property
    def archived_count(self) -> int:
        with self._lock:
            return sum(1 for st in self._entries.values() if st == _ST_ARCHIVED)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._session_map.clear()
