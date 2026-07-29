"""
orchestrator_snapshot.py -- iios.ai.orchestrator.snapshot
===========================================================
:class:`OrchestratorSnapshot` — immutable point-in-time system state.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class OrchestratorSnapshot:
    """Immutable point-in-time snapshot of the orchestrator platform state."""

    snapshot_id:               str
    captured_at:               float
    is_running:                bool
    active_sessions:           int
    registered_workflows:      int
    active_workflow_instances: int
    queued_tasks:              int
    completed_tasks:           int
    failed_tasks:              int
    registered_agents:         int
    active_reservations:       int
    recovery_strategies:       int
    monitored_sessions:        int
    plan_count:                int
    event_history_size:        int

    @classmethod
    def build(
        cls,
        is_running:                bool,
        active_sessions:           int,
        registered_workflows:      int,
        active_workflow_instances: int,
        queued_tasks:              int,
        completed_tasks:           int,
        failed_tasks:              int,
        registered_agents:         int,
        active_reservations:       int,
        recovery_strategies:       int,
        monitored_sessions:        int,
        plan_count:                int,
        event_history_size:        int,
    ) -> "OrchestratorSnapshot":
        return cls(
            snapshot_id               = str(uuid.uuid4()),
            captured_at               = time.time(),
            is_running                = is_running,
            active_sessions           = active_sessions,
            registered_workflows      = registered_workflows,
            active_workflow_instances = active_workflow_instances,
            queued_tasks              = queued_tasks,
            completed_tasks           = completed_tasks,
            failed_tasks              = failed_tasks,
            registered_agents         = registered_agents,
            active_reservations       = active_reservations,
            recovery_strategies       = recovery_strategies,
            monitored_sessions        = monitored_sessions,
            plan_count                = plan_count,
            event_history_size        = event_history_size,
        )
