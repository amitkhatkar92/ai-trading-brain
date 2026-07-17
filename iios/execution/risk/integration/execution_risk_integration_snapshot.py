"""iios/execution/risk/integration/execution_risk_integration_snapshot.py
==================================================
ExecutionRiskIntegrationSnapshot — point-in-time health and statistics
snapshot of the integration subsystem.

This is NOT the M5 ExecutionRiskSnapshot (which represents a single
evaluation result).  This is a subsystem-level diagnostic snapshot.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ExecutionRiskIntegrationSnapshot:
    """
    Immutable point-in-time diagnostic snapshot of the integration subsystem.

    Produced by ExecutionRiskIntegrationEngine.snapshot() and returned to
    callers that need to inspect subsystem health, statistics, and recent
    activity without querying the full history.
    """

    snapshot_id:       str
    taken_at:          float
    subsystem_state:   str       # EngineState value of the integration engine
    is_running:        bool
    is_healthy:        bool
    component_health:  Dict[str, Any]   # component_type → ComponentHealth.to_dict()
    statistics:        Dict[str, Any]   # IntegrationStatistics.to_dict()
    recent_events:     List[Dict[str, Any]]   # last N IntegrationEvent.to_dict()
    evaluation_count:  int        # number of evaluations processed
    snapshot_count:    int        # number of M5 snapshots in the M5 registry
    uptime_sec:        float
    version:           str
    metadata:          Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":      self.snapshot_id,
            "taken_at":         self.taken_at,
            "subsystem_state":  self.subsystem_state,
            "is_running":       self.is_running,
            "is_healthy":       self.is_healthy,
            "component_health": self.component_health,
            "statistics":       self.statistics,
            "recent_events":    self.recent_events,
            "evaluation_count": self.evaluation_count,
            "snapshot_count":   self.snapshot_count,
            "uptime_sec":       self.uptime_sec,
            "version":          self.version,
            "metadata":         dict(self.metadata),
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ── Factory ───────────────────────────────────────────────────────────────────

def make_integration_snapshot(
    subsystem_state:  str,
    is_running:       bool,
    is_healthy:       bool,
    component_health: Dict[str, Any],
    statistics:       Dict[str, Any],
    recent_events:    List[Dict[str, Any]],
    evaluation_count: int,
    snapshot_count:   int,
    uptime_sec:       float,
    version:          str,
    **metadata,
) -> ExecutionRiskIntegrationSnapshot:
    return ExecutionRiskIntegrationSnapshot(
        snapshot_id=str(uuid.uuid4()),
        taken_at=time.time(),
        subsystem_state=subsystem_state,
        is_running=is_running,
        is_healthy=is_healthy,
        component_health=component_health,
        statistics=statistics,
        recent_events=recent_events,
        evaluation_count=evaluation_count,
        snapshot_count=snapshot_count,
        uptime_sec=uptime_sec,
        version=version,
        metadata=metadata,
    )
