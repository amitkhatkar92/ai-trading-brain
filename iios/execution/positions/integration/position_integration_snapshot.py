"""iios/execution/positions/integration/position_integration_snapshot.py
==================================================
PositionIntegrationSnapshot — immutable point-in-time snapshot
of the entire Position Management subsystem state.

This is the primary output of PositionIntegrationEngine.snapshot().

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .constants import VERSION


@dataclass(frozen=True)
class PositionIntegrationSnapshot:
    """
    Immutable snapshot of the full Position Management subsystem state.

    Combines data from all five integrated components into a single
    coherent, point-in-time value object.

    Attributes
    ----------
    integration_snapshot_id
        UUID identifying this snapshot instance.
    engine_snapshot
        Serialized snapshot from PositionEngine (EngineSnapshot.to_dict()).
    book_snapshot
        Serialized snapshot from PositionBook (PositionBookSnapshot.to_dict()).
    risk_snapshot
        Serialized snapshot from PositionRiskManager (RiskBookSnapshot.to_dict()).
    position_snapshots
        Serialized SnapshotBundle from PositionSnapshotStore
        (SnapshotBundle.to_dict()).  Contains the published PositionSnapshot
        for every tracked position.
    health
        Serialized HealthReport (HealthReport.to_dict()).
    statistics
        Serialized IntegrationStatistics (IntegrationStatistics.to_dict()).
    position_count
        Total number of positions managed at snapshot time.
    published_snapshot_count
        Number of PositionSnapshots in PUBLISHED status.
    active_position_count
        Number of positions in an active lifecycle state.
    component_health_summary
        Per-component health string (e.g. ``{"position_engine": "HEALTHY"}``).
    version
        Module version at snapshot time.
    taken_at
        Unix timestamp of snapshot creation.
    """

    integration_snapshot_id:   str
    engine_snapshot:           Dict[str, Any] = field(default_factory=dict, compare=False)
    book_snapshot:             Dict[str, Any] = field(default_factory=dict, compare=False)
    risk_snapshot:             Dict[str, Any] = field(default_factory=dict, compare=False)
    position_snapshots:        Dict[str, Any] = field(default_factory=dict, compare=False)
    health:                    Dict[str, Any] = field(default_factory=dict, compare=False)
    statistics:                Dict[str, Any] = field(default_factory=dict, compare=False)
    position_count:            int    = 0
    published_snapshot_count:  int    = 0
    active_position_count:     int    = 0
    component_health_summary:  Dict[str, str] = field(default_factory=dict, compare=False)
    version:                   str    = VERSION
    taken_at:                  float  = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.health.get("overall_status") == "HEALTHY"

    @property
    def overall_health_status(self) -> str:
        return self.health.get("overall_status", "UNKNOWN")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_snapshot_id":  self.integration_snapshot_id,
            "engine_snapshot":          dict(self.engine_snapshot),
            "book_snapshot":            dict(self.book_snapshot),
            "risk_snapshot":            dict(self.risk_snapshot),
            "position_snapshots":       dict(self.position_snapshots),
            "health":                   dict(self.health),
            "statistics":               dict(self.statistics),
            "position_count":           self.position_count,
            "published_snapshot_count": self.published_snapshot_count,
            "active_position_count":    self.active_position_count,
            "component_health_summary": dict(self.component_health_summary),
            "version":                  self.version,
            "taken_at":                 self.taken_at,
        }


def make_integration_snapshot(
    *,
    engine_snapshot:          Dict[str, Any],
    book_snapshot:            Dict[str, Any],
    risk_snapshot:            Dict[str, Any],
    position_snapshots:       Dict[str, Any],
    health:                   Dict[str, Any],
    statistics:               Dict[str, Any],
    position_count:           int = 0,
    published_snapshot_count: int = 0,
    active_position_count:    int = 0,
    component_health_summary: Dict[str, str] | None = None,
) -> PositionIntegrationSnapshot:
    """Build a :class:`PositionIntegrationSnapshot` with a fresh UUID."""
    return PositionIntegrationSnapshot(
        integration_snapshot_id=str(uuid.uuid4()),
        engine_snapshot=engine_snapshot,
        book_snapshot=book_snapshot,
        risk_snapshot=risk_snapshot,
        position_snapshots=position_snapshots,
        health=health,
        statistics=statistics,
        position_count=position_count,
        published_snapshot_count=published_snapshot_count,
        active_position_count=active_position_count,
        component_health_summary=component_health_summary or {},
    )
