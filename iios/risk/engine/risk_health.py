"""
risk_health.py — iios.risk.engine
====================================
Health reporting for the Risk Engine subsystem.

Aggregates component statuses into a single health report dict.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Dict

from .risk_session_manager import RiskSessionManager
from .risk_dispatcher import RiskDispatcher


class RiskEngineHealth:
    """
    Produces a health-check snapshot for the Risk Engine.

    Parameters
    ----------
    max_sessions :  Session limit — used to determine session headroom.
    """

    def __init__(self, max_sessions: int = 100) -> None:
        self._max_sessions = max_sessions

    def report(
        self,
        session_manager: RiskSessionManager,
        dispatcher:      RiskDispatcher,
    ) -> Dict[str, Any]:
        """
        Build and return the health report.

        Returns
        -------
        dict with keys:
          - overall       : "healthy" | "degraded" | "unhealthy"
          - components    : sub-component statuses
          - checked_at    : wall-clock time
        """
        active   = session_manager.active_session_count()
        headroom = max(0, self._max_sessions - active)

        # Determine component status
        session_status = "healthy" if headroom > 0 else "degraded"
        dispatcher_status = "healthy"

        overall = "healthy"
        if session_status == "degraded" or dispatcher_status == "degraded":
            overall = "degraded"

        return {
            "overall": overall,
            "components": {
                "session_manager": {
                    "status":          session_status,
                    "active_sessions": active,
                    "headroom":        headroom,
                    "max_sessions":    self._max_sessions,
                },
                "dispatcher": {
                    "status":                  dispatcher_status,
                    "has_policy_framework":    dispatcher.has_policy_framework,
                    "has_assessment_framework": dispatcher.has_assessment_framework,
                },
            },
            "checked_at": time.time(),
        }
