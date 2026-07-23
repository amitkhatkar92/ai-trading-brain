"""
market_integration_health.py — iios.market.integration
========================================================
Aggregate health reporter for the Market Integration subsystem.

Collects component statuses and derives an overall health rating.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional


class MarketIntegrationHealth:
    """
    Produces an aggregate health report for the Market Integration subsystem.

    Component probes are registered at construction time via
    ``component_probes`` — a dict mapping component name to a callable
    that returns a dict with at least an ``"overall"`` key.

    If a probe raises, that component is marked ``"unhealthy"``.
    """

    def __init__(
        self,
        component_probes: Optional[Dict[str, Callable[[], Dict[str, Any]]]] = None,
    ) -> None:
        self._probes: Dict[str, Callable[[], Dict[str, Any]]] = dict(
            component_probes or {}
        )

    def register_probe(
        self, name: str, probe: Callable[[], Dict[str, Any]]
    ) -> None:
        """Register a new component health probe."""
        self._probes[name] = probe

    def report(self) -> Dict[str, Any]:
        """
        Build and return the aggregate health report.

        Returns a dict with keys:
          - ``overall``    : "healthy" | "degraded" | "unhealthy"
          - ``components`` : per-component status dicts
          - ``checked_at`` : wall-clock check time
        """
        components: Dict[str, Any] = {}
        statuses: list             = []

        for name, probe in self._probes.items():
            try:
                result = probe()
                status = result.get("overall", "unknown")
            except Exception as exc:  # noqa: BLE001
                result = {"overall": "unhealthy", "error": str(exc)}
                status = "unhealthy"
            components[name] = result
            statuses.append(status)

        if not statuses:
            overall = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        elif any(s in ("degraded", "unknown") for s in statuses):
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "overall":    overall,
            "components": components,
            "checked_at": time.time(),
        }

    def is_healthy(self) -> bool:
        return self.report().get("overall") == "healthy"

    def component_status(self, name: str) -> str:
        """Return the health status string for a single component."""
        if name not in self._probes:
            return "unknown"
        try:
            return self._probes[name]().get("overall", "unknown")
        except Exception:  # noqa: BLE001
            return "unhealthy"
