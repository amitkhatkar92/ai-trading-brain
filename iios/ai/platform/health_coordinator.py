"""
health_coordinator.py — iios.ai.platform
==========================================
Aggregates health signals from all registered platform gateways into a
unified platform-level health report.

Resolves the "no platform-level health aggregation" observation from the
Enterprise Design Review (R-007 — noted as MEDIUM, included here because
it directly enables the bootstrap health() API required by R-001).

F0.1 Critical Architecture Resolution — R-001 Platform Bootstrap
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .platform_registry import PlatformRegistry
from .platform_types import PlatformPhase, PlatformStatus

__all__ = [
    "HealthCoordinator",
    "HEALTH_HEALTHY",
    "HEALTH_DEGRADED",
    "HEALTH_UNKNOWN",
    "HEALTH_DOWN",
]

_log = logging.getLogger(__name__)

HEALTH_HEALTHY  = "healthy"
HEALTH_DEGRADED = "degraded"
HEALTH_UNKNOWN  = "unknown"
HEALTH_DOWN     = "down"


class HealthCoordinator:
    """
    Calls ``health()`` on every registered gateway and aggregates results.

    Health derivation rules
    -----------------------
    - Platform in FAILED or STOPPED phase → ``HEALTH_DOWN`` (no gateway call)
    - Platform not in RUNNING phase       → ``HEALTH_UNKNOWN``
    - Gateway missing ``health()``        → ``HEALTH_UNKNOWN``
    - ``gateway.health()`` raises         → ``HEALTH_DEGRADED``
    - Otherwise: use the dict returned by ``gateway.health()`` and default
      its ``"status"`` key to ``HEALTH_HEALTHY`` if absent

    Aggregate status
    ----------------
    ``"down"``     — at least one platform is DOWN
    ``"degraded"`` — at least one platform is DEGRADED or UNKNOWN
    ``"healthy"``  — all platforms are HEALTHY

    Usage::

        coordinator = HealthCoordinator(registry)
        report = coordinator.check_all()
        agg    = coordinator.aggregate_status()
    """

    def __init__(self, registry: PlatformRegistry) -> None:
        self._registry = registry

    # ── public API ────────────────────────────────────────────────────────────

    def check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Return ``{platform_id: health_dict}`` for every registered platform.
        """
        return {pid: self._check_one(pid) for pid in self._registry.list_ids()}

    def aggregate_status(self) -> str:
        """
        Derive a single aggregate health string for the whole platform.
        """
        health_map = self.check_all()
        statuses   = [v.get("status", HEALTH_UNKNOWN) for v in health_map.values()]
        if any(s == HEALTH_DOWN for s in statuses):
            return HEALTH_DOWN
        if any(s in (HEALTH_DEGRADED, HEALTH_UNKNOWN) for s in statuses):
            return HEALTH_DEGRADED
        if not statuses:
            return HEALTH_UNKNOWN
        return HEALTH_HEALTHY

    def build_platform_status(self) -> PlatformStatus:
        """Return a :class:`PlatformStatus` snapshot from current registry state."""
        phases = self._registry.all_phases()
        return PlatformStatus.create(phases=phases, results=[])

    # ── internal ──────────────────────────────────────────────────────────────

    def _check_one(self, platform_id: str) -> Dict[str, Any]:
        phase   = self._registry.get_phase(platform_id)
        gateway = self._registry.get_gateway(platform_id)

        base = {"platform_id": platform_id, "phase": phase.value}

        if phase in (PlatformPhase.FAILED, PlatformPhase.STOPPED):
            return {**base, "status": HEALTH_DOWN}

        if phase != PlatformPhase.RUNNING:
            return {**base, "status": HEALTH_UNKNOWN}

        if gateway is None or not hasattr(gateway, "health"):
            return {**base, "status": HEALTH_UNKNOWN}

        try:
            data = gateway.health()
            if not isinstance(data, dict):
                data = {"raw": str(data)}
            return {**base, "status": HEALTH_HEALTHY, **data}
        except Exception as exc:
            _log.warning("health() failed for platform %r: %s", platform_id, exc)
            return {**base, "status": HEALTH_DEGRADED, "error": str(exc)}
