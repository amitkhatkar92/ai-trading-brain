"""
integration_snapshot_store.py — iios.integration.snapshot
-----------------------------------------------------------
IntegrationSnapshotStore — thread-safe in-memory persistent store for
versioned IntegrationSnapshot objects.

Maintains multiple versions per snapshot_id, ordered by recorded time.
Supports save, load (by id or version), delete, and listing.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_STORE_MAX
from .exceptions import SnapshotNotFoundError, SnapshotStoreError
from .integration_snapshot import IntegrationSnapshot

_log = get_logger(__name__)


class IntegrationSnapshotStore:
    """
    Thread-safe in-memory versioned store for IntegrationSnapshot objects.

    Each save() call records a new version (entry) for the snapshot_id.
    The latest version is returned by load() unless version_index is specified.
    """

    def __init__(self, max_entries: int = DEFAULT_STORE_MAX) -> None:
        # snapshot_id → ordered list of (version_tag, snapshot)
        self._store:      Dict[str, List[Tuple[str, IntegrationSnapshot]]] = {}
        self._max_entries: int             = max_entries
        self._total:       int             = 0
        self._lock:        threading.Lock  = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────

    def save(self, snapshot: IntegrationSnapshot) -> str:
        """
        Save a snapshot (or a new version of it).

        Returns the snapshot_id.
        Raises SnapshotStoreError if the store is at capacity.
        """
        with self._lock:
            if self._total >= self._max_entries:
                raise SnapshotStoreError(
                    f"Store at capacity ({self._max_entries})"
                )
            sid = snapshot.snapshot_id
            version_tag = f"v{len(self._store.get(sid, [])) + 1}"
            self._store.setdefault(sid, []).append((version_tag, snapshot))
            self._total += 1
        _log.info(f"Snapshot stored: {sid!r} version={version_tag}")
        return sid

    def delete(self, snapshot_id: str) -> bool:
        """
        Delete all versions of a snapshot.

        Returns True if found, False if not.
        """
        with self._lock:
            if snapshot_id not in self._store:
                return False
            n = len(self._store.pop(snapshot_id))
            self._total -= n
        _log.info(f"Snapshot deleted from store: {snapshot_id!r} ({n} versions)")
        return True

    def delete_version(self, snapshot_id: str, version_tag: str) -> bool:
        """Delete a specific version of a snapshot."""
        with self._lock:
            entries = self._store.get(snapshot_id, [])
            for i, (vtag, _) in enumerate(entries):
                if vtag == version_tag:
                    del entries[i]
                    self._total -= 1
                    if not entries:
                        del self._store[snapshot_id]
                    _log.info(
                        f"Snapshot version deleted: {snapshot_id!r} {version_tag}"
                    )
                    return True
        return False

    # ── Read ──────────────────────────────────────────────────────────

    def load(
        self,
        snapshot_id:   str,
        version_tag:   Optional[str] = None,
    ) -> Optional[IntegrationSnapshot]:
        """
        Load a snapshot by ID.

        If version_tag is None, returns the latest version.
        Returns None if not found.
        """
        with self._lock:
            entries = self._store.get(snapshot_id, [])
            if not entries:
                return None
            if version_tag is None:
                return entries[-1][1]
            for vtag, snap in entries:
                if vtag == version_tag:
                    return snap
        return None

    def load_or_raise(
        self,
        snapshot_id: str,
        version_tag: Optional[str] = None,
    ) -> IntegrationSnapshot:
        """Load a snapshot; raise SnapshotNotFoundError if absent."""
        snap = self.load(snapshot_id, version_tag)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        return snap

    def list_versions(self, snapshot_id: str) -> List[str]:
        """Return all version tags recorded for a snapshot_id."""
        with self._lock:
            return [vtag for vtag, _ in self._store.get(snapshot_id, [])]

    def list_ids(self) -> List[str]:
        """Return all snapshot IDs in the store."""
        with self._lock:
            return list(self._store.keys())

    def exists(self, snapshot_id: str) -> bool:
        """Return True if snapshot_id has at least one version stored."""
        with self._lock:
            return snapshot_id in self._store and len(self._store[snapshot_id]) > 0

    # ── Properties ───────────────────────────────────────────────────

    @property
    def count(self) -> int:
        """Total number of stored snapshot versions across all IDs."""
        with self._lock:
            return self._total

    @property
    def unique_ids(self) -> int:
        """Number of distinct snapshot IDs stored."""
        with self._lock:
            return len(self._store)

    @property
    def max_entries(self) -> int:
        return self._max_entries

    def clear(self) -> int:
        """Remove all entries. Returns the count removed."""
        with self._lock:
            n = self._total
            self._store.clear()
            self._total = 0
        return n
