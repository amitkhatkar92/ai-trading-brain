"""
market_health.py — iios.market.engine
========================================
Health reporting for the Market Engine subsystem.

Aggregates component statuses into a single health report dict.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Dict

from .market_session_manager import MarketSessionManager
from .market_dispatcher import MarketDispatcher


class MarketEngineHealth:
    """
    Produces a health-check snapshot for the Market Engine.

    Parameters
    ----------
    max_sessions :  Session limit — used to determine session headroom.
    """

    def __init__(self, max_sessions: int = 200) -> None:
        self._max_sessions = max_sessions

    def report(
        self,
        session_manager: MarketSessionManager,
        dispatcher:      MarketDispatcher,
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

        session_status    = "healthy" if headroom > 0 else "degraded"
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
                    "has_analytics_framework": dispatcher.has_analytics_framework,
                },
            },
            "checked_at": time.time(),
        }
