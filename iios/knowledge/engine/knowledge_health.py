"""
knowledge_health.py — iios.knowledge.engine
---------------------------------------------
Health reporting for the Knowledge Engine.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict

from .knowledge_registry import KnowledgeEngineRegistry
from .knowledge_scheduler import KnowledgeScheduler
from .knowledge_session_manager import KnowledgeSessionManager
from .knowledge_dispatcher import KnowledgeDispatcher


class KnowledgeEngineHealth:
    """
    Aggregates health information from all engine subsystems.

    All subsystems are optional — missing subsystems report degraded status.
    """

    def __init__(
        self,
        session_manager: KnowledgeSessionManager,
        dispatcher:      KnowledgeDispatcher,
        scheduler:       KnowledgeScheduler,
        registry:        KnowledgeEngineRegistry,
    ) -> None:
        self._session_mgr = session_manager
        self._dispatcher  = dispatcher
        self._scheduler   = scheduler
        self._registry    = registry

    def assess(
        self,
        engine_state:  str = "running",
        statistics:    Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Return a health assessment dictionary."""
        scheduler_stats = self._scheduler.statistics()
        session_health  = self._session_mgr.health()

        status = "healthy"
        if engine_state not in ("running",):
            status = "degraded"
        if scheduler_stats.get("drop_count", 0) > 0:
            status = "degraded"

        return {
            "status":              status,
            "engine_state":        engine_state,
            "active_sessions":     self._session_mgr.active_count(),
            "active_pipelines":    self._registry.active_count(),
            "archived_pipelines":  self._registry.archived_count(),
            "scheduler_depth":     scheduler_stats.get("queue_depth", 0),
            "scheduler_drops":     scheduler_stats.get("drop_count", 0),
            "governance_available": self._dispatcher.has_governance(),
            "intelligence_available": self._dispatcher.has_intelligence(),
            "session_health":      session_health,
            "statistics":          statistics or {},
        }
