"""
decision_health.py — iios.decision.engine
===========================================
Health assessment for the Decision Engine and its subsystems.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import EngineHealthStatus, VERSION


@dataclass(frozen=True)
class SubsystemHealth:
    """
    Health record for one named subsystem.

    Fields
    ------
    name :      Subsystem name.
    status :    :class:`EngineHealthStatus` value.
    message :   Human-readable detail (empty on healthy).
    checked_at: Wall-clock time of this check.
    """
    name:       str
    status:     EngineHealthStatus
    message:    str   = ""
    checked_at: float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.status == EngineHealthStatus.HEALTHY


@dataclass(frozen=True)
class DecisionEngineHealth:
    """
    Aggregate health of the decision engine and all registered subsystems.

    Fields
    ------
    overall :           Overall health status.
    subsystems :        Tuple of individual subsystem health records.
    healthy_count :     Number of healthy subsystems.
    degraded_count :    Number of degraded subsystems.
    unhealthy_count :   Number of unhealthy subsystems.
    message :           Human-readable summary.
    assessed_at :       Wall-clock time of assessment.
    framework_version : Framework version string.
    """
    overall:          EngineHealthStatus
    subsystems:       tuple[SubsystemHealth, ...]
    healthy_count:    int
    degraded_count:   int
    unhealthy_count:  int
    message:          str   = ""
    assessed_at:      float = field(default_factory=time.time)
    framework_version: str  = VERSION

    @property
    def is_healthy(self) -> bool:
        return self.overall == EngineHealthStatus.HEALTHY

    @property
    def total_subsystems(self) -> int:
        return len(self.subsystems)


def assess_engine_health(
    engine_running: bool,
    *,
    lifecycle_ok:   bool = True,
    scheduler_ok:   bool = True,
    dispatcher_ok:  bool = True,
    registry_ok:    bool = True,
    extra: Optional[Dict[str, bool]] = None,
) -> DecisionEngineHealth:
    """
    Produce a :class:`DecisionEngineHealth` from component health booleans.

    Parameters
    ----------
    engine_running : Whether the engine's lifecycle is in RUNNING state.
    lifecycle_ok :   Decision Lifecycle (M1) is operational.
    scheduler_ok :   Decision Scheduler is operational.
    dispatcher_ok :  Decision Dispatcher is operational.
    registry_ok :    Decision Registry is consistent.
    extra :          Additional subsystem name → healthy mappings.

    Returns
    -------
    DecisionEngineHealth
    """
    checks: Dict[str, bool] = {
        "engine":     engine_running,
        "lifecycle":  lifecycle_ok,
        "scheduler":  scheduler_ok,
        "dispatcher": dispatcher_ok,
        "registry":   registry_ok,
    }
    if extra:
        checks.update(extra)

    subsystems: List[SubsystemHealth] = []
    for name, ok in checks.items():
        subsystems.append(
            SubsystemHealth(
                name    = name,
                status  = EngineHealthStatus.HEALTHY if ok else EngineHealthStatus.UNHEALTHY,
                message = "" if ok else f"{name} is not healthy",
            )
        )

    healthy   = sum(1 for s in subsystems if s.status == EngineHealthStatus.HEALTHY)
    degraded  = sum(1 for s in subsystems if s.status == EngineHealthStatus.DEGRADED)
    unhealthy = sum(1 for s in subsystems if s.status == EngineHealthStatus.UNHEALTHY)

    if unhealthy > 0:
        overall = EngineHealthStatus.UNHEALTHY
        msg     = f"{unhealthy} subsystem(s) unhealthy"
    elif degraded > 0:
        overall = EngineHealthStatus.DEGRADED
        msg     = f"{degraded} subsystem(s) degraded"
    else:
        overall = EngineHealthStatus.HEALTHY
        msg     = "All subsystems healthy"

    return DecisionEngineHealth(
        overall         = overall,
        subsystems      = tuple(subsystems),
        healthy_count   = healthy,
        degraded_count  = degraded,
        unhealthy_count = unhealthy,
        message         = msg,
    )
