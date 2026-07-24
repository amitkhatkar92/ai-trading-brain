"""
knowledge_snapshot_bundle.py — iios.knowledge.snapshot
--------------------------------------------------------
KnowledgeSnapshotBundle — groups of related KnowledgeSnapshot objects.

A bundle aggregates snapshots from multiple subsystems into a
single publishable unit.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_BUNDLES, DEFAULT_MAX_SNAPSHOTS
from .exceptions import SnapshotCapacityError, SnapshotNotFoundError
from .knowledge_snapshot import KnowledgeSnapshot

_log = get_logger(__name__)


@dataclass(frozen=True)
class KnowledgeSnapshotBundle:
    """
    An immutable, ordered collection of related KnowledgeSnapshot objects.

    Represents the complete published intelligence output for a
    multi-subsystem enterprise knowledge cycle.
    """
    bundle_id:    str
    name:         str
    description:  str
    snapshots:    tuple          # Tuple[KnowledgeSnapshot]
    created_at:   str
    schema_version: str = "1.0"

    @classmethod
    def create(
        cls,
        name:        str,
        snapshots:   List[KnowledgeSnapshot],
        *,
        description: str = "",
        bundle_id:   str = "",
    ) -> "KnowledgeSnapshotBundle":
        return cls(
            bundle_id     = bundle_id or f"bundle-{uuid.uuid4().hex[:12]}",
            name          = name,
            description   = description,
            snapshots     = tuple(snapshots),
            created_at    = datetime.now(tz=timezone.utc).isoformat(),
        )

    @property
    def snapshot_count(self) -> int:
        return len(self.snapshots)

    @property
    def snapshot_ids(self) -> List[str]:
        return [s.snapshot_id for s in self.snapshots]

    def get(self, snapshot_id: str) -> Optional[KnowledgeSnapshot]:
        for snap in self.snapshots:
            if snap.snapshot_id == snapshot_id:
                return snap
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":      self.bundle_id,
            "name":           self.name,
            "description":    self.description,
            "snapshot_count": self.snapshot_count,
            "snapshot_ids":   self.snapshot_ids,
            "created_at":     self.created_at,
            "schema_version": self.schema_version,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """Full dict including all snapshot contents."""
        d = self.to_dict()
        d["snapshots"] = [s.to_dict() for s in self.snapshots]
        return d


class KnowledgeSnapshotBundleRegistry:
    """Thread-safe registry of KnowledgeSnapshotBundle objects."""

    def __init__(self, max_bundles: int = DEFAULT_MAX_BUNDLES) -> None:
        self._max     = max_bundles
        self._store:  Dict[str, KnowledgeSnapshotBundle] = {}
        self._lock    = threading.Lock()

    def register(self, bundle: KnowledgeSnapshotBundle) -> None:
        with self._lock:
            if (
                len(self._store) >= self._max
                and bundle.bundle_id not in self._store
            ):
                raise SnapshotCapacityError(limit=self._max)
            self._store[bundle.bundle_id] = bundle
        _log.debug(f"Bundle registered: id={bundle.bundle_id!r} name={bundle.name!r}")

    def get(self, bundle_id: str) -> Optional[KnowledgeSnapshotBundle]:
        with self._lock:
            return self._store.get(bundle_id)

    def get_or_raise(self, bundle_id: str) -> KnowledgeSnapshotBundle:
        b = self.get(bundle_id)
        if b is None:
            raise SnapshotNotFoundError(bundle_id)
        return b

    def remove(self, bundle_id: str) -> bool:
        with self._lock:
            if bundle_id in self._store:
                del self._store[bundle_id]
                return True
            return False

    def all_bundles(self) -> List[KnowledgeSnapshotBundle]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
