"""
supervisor_integration_status.py — iios.supervisor.integration
--------------------------------------------------------------
Status reporter for the AI Supervisor Integration layer.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import time
from typing import Any, Dict

from .constants import INTEGRATION_SYSTEM_ID, VERSION


class SupervisorIntegrationStatus:
    """
    Builds a comprehensive status report for the integration layer.

    Combines lifecycle state, statistics, history counts, and component
    inventory into a single plain-dict report suitable for dashboards and
    introspection endpoints.
    """

    def build_status(
        self,
        engine:     Any,  # SupervisorIntegrationEngine (duck-typed)
        statistics: Any,  # SupervisorIntegrationStatistics (duck-typed)
        history:    Any,  # SupervisorIntegrationHistory (duck-typed)
        component_registry: Any,  # SupervisorComponentRegistry (duck-typed)
    ) -> Dict[str, Any]:
        """
        Return a plain-dict status snapshot.

        Parameters are duck-typed to avoid circular imports.
        """
        # Lifecycle state
        lifecycle_state = "unknown"
        lc = getattr(engine, "lifecycle_state", None)
        if callable(lc):
            s = lc()
            lifecycle_state = getattr(s, "value", str(s))

        # Statistics
        stats: Dict[str, Any] = {}
        if statistics is not None:
            snap_fn = getattr(statistics, "snapshot", None)
            if callable(snap_fn):
                stats = snap_fn()

        # History counts
        history_counts: Dict[str, int] = {}
        if history is not None:
            cnt_fn = getattr(history, "counts", None)
            if callable(cnt_fn):
                history_counts = cnt_fn()

        # Component count
        component_count = 0
        if component_registry is not None:
            cnt = getattr(component_registry, "count", None)
            if cnt is not None:
                component_count = cnt() if callable(cnt) else cnt

        return {
            "system_id":        INTEGRATION_SYSTEM_ID,
            "framework_version": VERSION,
            "lifecycle_state":  lifecycle_state,
            "is_running":       lifecycle_state == "running",
            "statistics":       stats,
            "history_counts":   history_counts,
            "component_count":  component_count,
            "generated_at":     time.time(),
        }
