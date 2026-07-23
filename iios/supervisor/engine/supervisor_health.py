"""
supervisor_health.py — iios.supervisor.engine
----------------------------------------------
Health reporting for the Supervisor Engine.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional


class SupervisorEngineHealth:
    """
    Composes health information for the Supervisor Engine.

    Derived from:
    - Session manager active session count
    - Dispatcher framework registration status
    - Scheduler queue depth
    - Registry capacity state

    Parameters
    ----------
    session_manager : Provides active_session_count()
    dispatcher :      Provides has_governance_framework / has_autonomous_framework
    scheduler :       Provides queue_depth()
    registry :        Provides is_ready() / active_pipeline_count()
    """

    def __init__(
        self,
        session_manager = None,
        dispatcher      = None,
        scheduler       = None,
        registry        = None,
    ) -> None:
        self._sm  = session_manager
        self._dsp = dispatcher
        self._sch = scheduler
        self._reg = registry

    # ------------------------------------------------------------------

    def report(self, engine_state: Optional[str] = None) -> Dict[str, Any]:
        """Return the current health snapshot dict."""
        component_health: Dict[str, Any] = {}
        issues = []

        # Session manager
        if self._sm is not None:
            try:
                active = self._sm.active_session_count()
                component_health["session_manager"] = {
                    "status":          "healthy",
                    "active_sessions": active,
                }
            except Exception as exc:       # noqa: BLE001
                component_health["session_manager"] = {
                    "status": "degraded",
                    "error":  str(exc),
                }
                issues.append("session_manager degraded")

        # Dispatcher
        if self._dsp is not None:
            try:
                component_health["dispatcher"] = {
                    "status":                    "healthy",
                    "has_governance_framework":  self._dsp.has_governance_framework,
                    "has_autonomous_framework":  self._dsp.has_autonomous_framework,
                }
            except Exception as exc:       # noqa: BLE001
                component_health["dispatcher"] = {
                    "status": "degraded",
                    "error":  str(exc),
                }
                issues.append("dispatcher degraded")

        # Scheduler
        if self._sch is not None:
            try:
                depth = self._sch.queue_depth()
                component_health["scheduler"] = {
                    "status":      "healthy",
                    "queue_depth": depth,
                }
            except Exception as exc:       # noqa: BLE001
                component_health["scheduler"] = {
                    "status": "degraded",
                    "error":  str(exc),
                }
                issues.append("scheduler degraded")

        # Registry
        if self._reg is not None:
            try:
                ready = self._reg.is_ready()
                component_health["registry"] = {
                    "status":          "healthy" if ready else "at_capacity",
                    "active_pipelines": self._reg.active_pipeline_count(),
                    "ready":           ready,
                }
                if not ready:
                    issues.append("registry at capacity")
            except Exception as exc:       # noqa: BLE001
                component_health["registry"] = {
                    "status": "degraded",
                    "error":  str(exc),
                }
                issues.append("registry degraded")

        overall = "healthy" if not issues else (
            "at_capacity" if all("capacity" in i for i in issues) else "degraded"
        )

        return {
            "overall":       overall,
            "engine_state":  engine_state,
            "components":    component_health,
            "issues":        issues,
            "checked_at":    time.time(),
        }
