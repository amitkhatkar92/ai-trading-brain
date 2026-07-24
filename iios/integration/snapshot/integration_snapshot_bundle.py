"""
integration_snapshot_bundle.py — iios.integration.snapshot
------------------------------------------------------------
IntegrationSnapshotBundle — ordered collection of related
IntegrationSnapshot objects.

A bundle groups snapshots from a single session or workflow for
batch retrieval, aggregation, and export.  The bundle itself is
mutable (snapshots can be added/removed) but each contained snapshot
remains immutable.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import BUNDLE_ID_PREFIX, DEFAULT_MAX_BUNDLE_SIZE
from .exceptions import SnapshotBundleError, SnapshotNotFoundError
from .integration_snapshot import IntegrationSnapshot

_log = get_logger(__name__)


@dataclass(frozen=True)
class BundleEntry:
    """Lightweight immutable reference to a snapshot inside a bundle."""
    snapshot_id:      str
    snapshot_version: str
    session_id:       str
    status:           str
    added_at:         str


class IntegrationSnapshotBundle:
    """
    Ordered, thread-safe collection of related IntegrationSnapshot objects.

    Responsibilities
    ----------------
    - Add / remove snapshots
    - Retrieve by snapshot_id
    - Iterate in insertion order
    - Produce a serialisable dict (for export / archival)
    - Enforce max-size capacity
    """

    def __init__(
        self,
        name:        str,
        description: str = "",
        max_size:    int  = DEFAULT_MAX_BUNDLE_SIZE,
        bundle_id:   Optional[str] = None,
    ) -> None:
        self._bundle_id:  str                              = (
            bundle_id or f"{BUNDLE_ID_PREFIX}{uuid.uuid4().hex[:12]}"
        )
        self._name:       str                              = name
        self._description: str                             = description
        self._max_size:   int                              = max_size
        self._snapshots:  Dict[str, IntegrationSnapshot]  = {}
        self._entries:    List[BundleEntry]                = []
        self._created_at: str                              = (
            datetime.now(tz=timezone.utc).isoformat()
        )
        self._updated_at: str                              = self._created_at
        self._lock:       threading.Lock                   = threading.Lock()

    # ── Properties ───────────────────────────────────────────────────

    @property
    def bundle_id(self) -> str:
        return self._bundle_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def max_size(self) -> int:
        return self._max_size

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    @property
    def created_at(self) -> str:
        return self._created_at

    @property
    def updated_at(self) -> str:
        with self._lock:
            return self._updated_at

    # ── Mutation ─────────────────────────────────────────────────────

    def add(self, snapshot: IntegrationSnapshot) -> bool:
        """
        Add a snapshot to the bundle.

        Returns True on success.
        Raises SnapshotBundleError if the bundle is full or the
        snapshot is already present.
        """
        with self._lock:
            if len(self._snapshots) >= self._max_size:
                raise SnapshotBundleError(
                    f"Bundle {self._bundle_id!r} is at capacity ({self._max_size})"
                )
            sid = snapshot.snapshot_id
            if sid in self._snapshots:
                raise SnapshotBundleError(
                    f"Snapshot {sid!r} already in bundle {self._bundle_id!r}"
                )
            self._snapshots[sid] = snapshot
            self._entries.append(BundleEntry(
                snapshot_id      = sid,
                snapshot_version = snapshot.snapshot_version,
                session_id       = snapshot.integration_session_id,
                status           = snapshot.status.value,
                added_at         = datetime.now(tz=timezone.utc).isoformat(),
            ))
            self._updated_at = datetime.now(tz=timezone.utc).isoformat()
        _log.debug(f"Bundle {self._bundle_id!r}: added snapshot {sid!r}")
        return True

    def remove(self, snapshot_id: str) -> bool:
        """Remove a snapshot by snapshot_id. Returns True if found."""
        with self._lock:
            if snapshot_id not in self._snapshots:
                return False
            del self._snapshots[snapshot_id]
            self._entries = [e for e in self._entries if e.snapshot_id != snapshot_id]
            self._updated_at = datetime.now(tz=timezone.utc).isoformat()
        _log.debug(f"Bundle {self._bundle_id!r}: removed snapshot {snapshot_id!r}")
        return True

    # ── Retrieval ─────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[IntegrationSnapshot]:
        """Return a snapshot by ID, or None if not present."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def get_or_raise(self, snapshot_id: str) -> IntegrationSnapshot:
        """Return a snapshot by ID; raise SnapshotNotFoundError if absent."""
        snap = self.get(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        return snap

    def snapshots(self) -> List[IntegrationSnapshot]:
        """Return all snapshots in insertion order."""
        with self._lock:
            return [self._snapshots[e.snapshot_id] for e in self._entries
                    if e.snapshot_id in self._snapshots]

    def entries(self) -> List[BundleEntry]:
        """Return all BundleEntry records in insertion order."""
        with self._lock:
            return list(self._entries)

    def snapshot_ids(self) -> List[str]:
        """Return all snapshot IDs in insertion order."""
        with self._lock:
            return [e.snapshot_id for e in self._entries]

    def __iter__(self) -> Iterator[IntegrationSnapshot]:
        return iter(self.snapshots())

    def __len__(self) -> int:
        return self.count

    def __contains__(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._snapshots

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Produce a JSON-safe dict representation of the bundle."""
        with self._lock:
            snaps = [
                self._snapshots[e.snapshot_id].to_dict()
                for e in self._entries
                if e.snapshot_id in self._snapshots
            ]
        return {
            "bundle_id":   self._bundle_id,
            "name":        self._name,
            "description": self._description,
            "max_size":    self._max_size,
            "count":       len(snaps),
            "created_at":  self._created_at,
            "updated_at":  self._updated_at,
            "snapshots":   snaps,
        }

    # ── Aggregation ───────────────────────────────────────────────────

    def aggregate_service_metrics(self) -> Dict[str, Any]:
        """
        Return the sum of service metrics across all snapshots in the bundle.
        """
        requests = responses = messages_pub = messages_con = events = 0
        retries = failures = 0
        latencies: List[float] = []
        for snap in self.snapshots():
            sm = snap.service_summary
            requests     += sm.requests_processed
            responses    += sm.responses_received
            messages_pub += sm.messages_published
            messages_con += sm.messages_consumed
            events       += sm.events_processed
            retries      += sm.retries
            failures     += sm.failures
            if sm.average_latency_ms > 0:
                latencies.append(sm.average_latency_ms)
        return {
            "requests_processed": requests,
            "responses_received": responses,
            "messages_published": messages_pub,
            "messages_consumed":  messages_con,
            "events_processed":   events,
            "retries":            retries,
            "failures":           failures,
            "average_latency_ms": (
                round(sum(latencies) / len(latencies), 3) if latencies else 0.0
            ),
        }
