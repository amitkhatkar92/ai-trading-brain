"""
health_models.py -- iios.ai.foundation.health
=============================================
Enterprise health reporting for the AI Platform.

Provides HealthStatus, ReadinessStatus, LivenessStatus and the
HealthReporter that aggregates them.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Status levels
# ---------------------------------------------------------------------------

class HealthLevel(str, Enum):
    """Standard health level enumeration."""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ---------------------------------------------------------------------------
# Individual status objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HealthStatus:
    """
    Overall health status of a component.

    Fields
    ------
    component :  Component identifier.
    level :      :class:`HealthLevel`.
    message :    Human-readable description.
    checks :     Dict of individual check name -> pass/fail bool.
    timestamp :  Wall-clock time of this status.
    """
    component:  str
    level:      HealthLevel
    message:    str
    checks:     Dict[str, bool]    = field(default_factory=dict)
    details:    Dict[str, Any]     = field(default_factory=dict)
    timestamp:  float              = field(default_factory=time.time)
    schema:     str                = SCHEMA_VERSION

    @property
    def is_healthy(self) -> bool:
        return self.level == HealthLevel.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "level":     self.level.value,
            "message":   self.message,
            "checks":    self.checks,
            "details":   self.details,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class ReadinessStatus:
    """
    Readiness probe result -- is the component ready to serve traffic?

    Fields
    ------
    component :  Component identifier.
    ready :      ``True`` iff ready.
    reason :     Explanation when not ready.
    timestamp :  Wall-clock time.
    """
    component: str
    ready:     bool
    reason:    str   = ""
    timestamp: float = field(default_factory=time.time)
    schema:    str   = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "ready":     self.ready,
            "reason":    self.reason,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class LivenessStatus:
    """
    Liveness probe result -- is the component alive (not deadlocked/crashed)?

    Fields
    ------
    component :  Component identifier.
    alive :      ``True`` iff alive.
    uptime_s :   Seconds since the component started.
    timestamp :  Wall-clock time.
    """
    component:  str
    alive:      bool
    uptime_s:   float
    reason:     str   = ""
    timestamp:  float = field(default_factory=time.time)
    schema:     str   = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "alive":     self.alive,
            "uptime_s":  round(self.uptime_s, 2),
            "reason":    self.reason,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Abstract HealthCheck
# ---------------------------------------------------------------------------

class HealthCheck(abc.ABC):
    """
    Abstract health check.

    Implement one check per concern (provider connectivity, config
    validity, session limit, etc.) and register with :class:`HealthReporter`.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique check identifier."""

    @abc.abstractmethod
    def check(self) -> bool:
        """Execute the check.  Return ``True`` if healthy, ``False`` otherwise."""

    def details(self) -> Dict[str, Any]:
        """Optional additional details to include in the health report."""
        return {}


# ---------------------------------------------------------------------------
# HealthReporter
# ---------------------------------------------------------------------------

class HealthReporter:
    """
    Aggregates multiple :class:`HealthCheck` instances into composite
    health, readiness, and liveness reports.

    Parameters
    ----------
    component :   Component name included in all reports.
    started_at :  Wall-clock start time (defaults to construction time).
    """

    def __init__(self, component: str, started_at: Optional[float] = None) -> None:
        self._component  = component
        self._started_at = started_at or time.time()
        self._checks: List[HealthCheck] = []

    def add_check(self, check: HealthCheck) -> None:
        self._checks.append(check)

    def health(self) -> HealthStatus:
        """Run all checks and return a composite :class:`HealthStatus`."""
        results:  Dict[str, bool] = {}
        all_details: Dict[str, Any] = {}

        for chk in self._checks:
            try:
                ok = chk.check()
            except Exception as exc:
                ok = False
                all_details[chk.name] = {"error": str(exc)}
            results[chk.name] = ok
            d = chk.details()
            if d:
                all_details[chk.name] = d

        if all(results.values()):
            level, msg = HealthLevel.HEALTHY, "All checks passed."
        elif any(results.values()):
            level, msg = HealthLevel.DEGRADED, "Some checks failed."
        else:
            level, msg = HealthLevel.UNHEALTHY, "All checks failed."

        return HealthStatus(
            component = self._component,
            level     = level,
            message   = msg,
            checks    = results,
            details   = all_details,
        )

    def readiness(self) -> ReadinessStatus:
        """Return readiness based on health (HEALTHY or DEGRADED = ready)."""
        h     = self.health()
        ready = h.level in (HealthLevel.HEALTHY, HealthLevel.DEGRADED)
        return ReadinessStatus(
            component = self._component,
            ready     = ready,
            reason    = "" if ready else h.message,
        )

    def liveness(self) -> LivenessStatus:
        """Return liveness (alive as long as not UNHEALTHY)."""
        h    = self.health()
        alive = h.level != HealthLevel.UNHEALTHY
        return LivenessStatus(
            component = self._component,
            alive     = alive,
            uptime_s  = time.time() - self._started_at,
            reason    = "" if alive else h.message,
        )
