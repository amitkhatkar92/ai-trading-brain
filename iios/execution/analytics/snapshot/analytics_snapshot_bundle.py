"""
iios/execution/analytics/snapshot/analytics_snapshot_bundle.py
==============================================================
AnalyticsSnapshotBundle — immutable group of ExecutionAnalyticsSnapshot
objects for batch operations.

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .constants import SNAPSHOT_FRAMEWORK_VERSION, AnalyticsHealth, AnalyticsStatus
from .execution_analytics_snapshot import ExecutionAnalyticsSnapshot


@dataclass(frozen=True)
class AnalyticsSnapshotBundle:
    """
    Immutable collection of ExecutionAnalyticsSnapshot objects.

    Used for batch publication, archiving, and reporting.
    """

    bundle_id:    str
    snapshots:    Tuple[ExecutionAnalyticsSnapshot, ...]
    label:        str  = ""
    created_at:   float = field(default_factory=time.time)
    version:      str  = SNAPSHOT_FRAMEWORK_VERSION

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return len(self.snapshots)

    @property
    def is_empty(self) -> bool:
        return len(self.snapshots) == 0

    @property
    def snapshot_ids(self) -> Tuple[str, ...]:
        return tuple(s.snapshot_id for s in self.snapshots)

    @property
    def session_ids(self) -> Tuple[str, ...]:
        return tuple(dict.fromkeys(s.analytics_session_id for s in self.snapshots))

    @property
    def avg_operational_health(self) -> float:
        if not self.snapshots:
            return 0.0
        return sum(s.operational_health_score for s in self.snapshots) / len(self.snapshots)

    @property
    def published_count(self) -> int:
        return sum(1 for s in self.snapshots if s.is_published)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[ExecutionAnalyticsSnapshot]:
        """Return a snapshot by ID, or None if not in this bundle."""
        for s in self.snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None

    def filter_by_status(self, status: AnalyticsStatus) -> "AnalyticsSnapshotBundle":
        """Return a new bundle containing only snapshots with the given status."""
        filtered = tuple(s for s in self.snapshots if s.analytics_status == status)
        return AnalyticsSnapshotBundle(
            bundle_id   = str(uuid.uuid4()),
            snapshots   = filtered,
            label       = f"{self.label}[{status.value}]",
            version     = self.version,
        )

    def filter_by_health(self, health: AnalyticsHealth) -> "AnalyticsSnapshotBundle":
        """Return a new bundle containing only snapshots with the given health."""
        filtered = tuple(s for s in self.snapshots if s.analytics_health == health)
        return AnalyticsSnapshotBundle(
            bundle_id   = str(uuid.uuid4()),
            snapshots   = filtered,
            label       = f"{self.label}[{health.value}]",
            version     = self.version,
        )

    def __iter__(self) -> Iterator[ExecutionAnalyticsSnapshot]:
        return iter(self.snapshots)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":            self.bundle_id,
            "count":                self.count,
            "label":                self.label,
            "created_at":           self.created_at,
            "version":              self.version,
            "avg_operational_health": self.avg_operational_health,
            "published_count":      self.published_count,
            "snapshots":            [s.to_dict() for s in self.snapshots],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


def make_snapshot_bundle(
    snapshots:  List[ExecutionAnalyticsSnapshot],
    label:      str = "",
    bundle_id:  Optional[str] = None,
) -> AnalyticsSnapshotBundle:
    """Factory function for AnalyticsSnapshotBundle."""
    return AnalyticsSnapshotBundle(
        bundle_id = bundle_id or str(uuid.uuid4()),
        snapshots = tuple(snapshots),
        label     = label,
    )
