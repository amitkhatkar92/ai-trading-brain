"""
knowledge_status.py — iios.knowledge.engine
---------------------------------------------
Engine status reporting for the Knowledge Engine.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .constants import EngineState, VERSION


class KnowledgeEngineStatus:
    """
    Snapshot of the current operational status of the Knowledge Engine.

    Constructed on demand and returned to callers of ``KnowledgeEngine.status()``.
    """

    @staticmethod
    def build(
        lifecycle_state:   str,
        engine_state:      EngineState,
        active_sessions:   int,
        active_pipelines:  int,
        archived_pipelines: int,
        scheduler_depth:   int,
        statistics:        Dict[str, Any],
        recent_history:    List[Any],
        *,
        uptime_seconds:    float = 0.0,
    ) -> Dict[str, Any]:
        """Build and return a status dictionary."""
        return {
            "lifecycle_state":    lifecycle_state,
            "engine_state":       engine_state.value,
            "active_sessions":    active_sessions,
            "active_pipelines":   active_pipelines,
            "archived_pipelines": archived_pipelines,
            "scheduler_depth":    scheduler_depth,
            "uptime_seconds":     round(uptime_seconds, 2),
            "statistics":         statistics,
            "recent_pipeline_count": len(recent_history),
            "framework_version":  VERSION,
            "reported_at":        time.time(),
        }
