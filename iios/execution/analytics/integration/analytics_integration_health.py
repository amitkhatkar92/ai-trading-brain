"""
analytics_integration_health.py — iios.execution.analytics.integration
=======================================================================
Health value objects for the Execution Analytics Integration subsystem.

Provides:
  * :class:`ComponentHealth`       — per-component health record
  * :class:`AnalyticsIntegrationHealth`  — overall integration health
  * :func:`assess_integration_health`    — aggregate helper
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from .constants import (
    INTEGRATION_VERSION,
    ComponentType,
    IntegrationHealthLevel,
)


# ---------------------------------------------------------------------------
# Per-component health
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ComponentHealth:
    """
    Immutable per-component health record.

    Fields
    ------
    component :     Which analytics component this record describes.
    health :        Current :class:`IntegrationHealthLevel`.
    score :         Numeric health score in [0.0, 1.0]; 1.0 = fully healthy.
    is_running :    ``True`` when the component is in a running lifecycle state.
    message :       Human-readable health summary.
    assessed_at :   Unix timestamp of assessment.
    """
    component:   ComponentType
    health:      IntegrationHealthLevel
    score:       float
    is_running:  bool
    message:     str  = ""
    assessed_at: float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        """``True`` for HEALTHY status."""
        return self.health == IntegrationHealthLevel.HEALTHY

    @property
    def is_degraded(self) -> bool:
        """``True`` for DEGRADED status."""
        return self.health == IntegrationHealthLevel.DEGRADED

    @property
    def is_critical(self) -> bool:
        """``True`` for CRITICAL or NOT_STARTED status."""
        return self.health in (
            IntegrationHealthLevel.CRITICAL,
            IntegrationHealthLevel.NOT_STARTED,
        )


def _component_health(
    component: ComponentType,
    *,
    is_running: bool,
    score: float = 1.0,
    message: str = "",
) -> ComponentHealth:
    """Build a :class:`ComponentHealth` from running flag and score."""
    if not is_running:
        level = IntegrationHealthLevel.NOT_STARTED
        score = 0.0
    elif score >= 0.8:
        level = IntegrationHealthLevel.HEALTHY
    elif score >= 0.5:
        level = IntegrationHealthLevel.DEGRADED
    else:
        level = IntegrationHealthLevel.CRITICAL
    return ComponentHealth(
        component  = component,
        health     = level,
        score      = score,
        is_running = is_running,
        message    = message,
    )


# ---------------------------------------------------------------------------
# Integration-level health
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AnalyticsIntegrationHealth:
    """
    Immutable overall health record for the analytics integration subsystem.

    Aggregates per-component health into a single overall assessment.

    Fields
    ------
    lifecycle_health :    M1 component health.
    engine_health :       M2 component health.
    performance_health :  M3 component health.
    predictive_health :   M4 component health.
    snapshot_health :     M5 component health.
    overall_health :      Aggregated :class:`IntegrationHealthLevel`.
    overall_score :       Numeric aggregate in [0.0, 1.0].
    is_operational :      ``True`` when the subsystem can accept requests.
    error_messages :      Tuple of error messages from degraded components.
    assessed_at :         Unix timestamp of assessment.
    framework_version :   Framework version string.
    """
    lifecycle_health:   ComponentHealth
    engine_health:      ComponentHealth
    performance_health: ComponentHealth
    predictive_health:  ComponentHealth
    snapshot_health:    ComponentHealth

    overall_health:     IntegrationHealthLevel
    overall_score:      float
    is_operational:     bool
    error_messages:     Tuple[str, ...] = field(default_factory=tuple)
    assessed_at:        float = field(default_factory=time.time)
    framework_version:  str   = INTEGRATION_VERSION

    @property
    def component_healths(self) -> Dict[ComponentType, ComponentHealth]:
        """All component health records as a dict keyed by :class:`ComponentType`."""
        return {
            ComponentType.LIFECYCLE:   self.lifecycle_health,
            ComponentType.ENGINE:      self.engine_health,
            ComponentType.PERFORMANCE: self.performance_health,
            ComponentType.PREDICTIVE:  self.predictive_health,
            ComponentType.SNAPSHOT:    self.snapshot_health,
        }

    @property
    def is_healthy(self) -> bool:
        """``True`` when overall health is HEALTHY."""
        return self.overall_health == IntegrationHealthLevel.HEALTHY

    @property
    def is_degraded(self) -> bool:
        """``True`` when overall health is DEGRADED."""
        return self.overall_health == IntegrationHealthLevel.DEGRADED

    @property
    def is_critical(self) -> bool:
        """``True`` for CRITICAL or worse overall health."""
        return self.overall_health in (
            IntegrationHealthLevel.CRITICAL,
            IntegrationHealthLevel.NOT_STARTED,
        )


# ---------------------------------------------------------------------------
# Aggregation helper
# ---------------------------------------------------------------------------
def assess_integration_health(
    *,
    lifecycle_running:   bool,
    engine_running:      bool,
    performance_running: bool,
    predictive_running:  bool,
    snapshot_running:    bool,
    lifecycle_score:     float = 1.0,
    engine_score:        float = 1.0,
    performance_score:   float = 1.0,
    predictive_score:    float = 1.0,
    snapshot_score:      float = 1.0,
    integration_running: bool = True,
    messages: Optional[Dict[ComponentType, str]] = None,
) -> AnalyticsIntegrationHealth:
    """
    Aggregate per-component running flags and scores into an
    :class:`AnalyticsIntegrationHealth`.

    Only M1 (lifecycle), M2 (engine), and M5 (snapshot) being healthy are
    required for the subsystem to be considered *operational*.  M3 and M4
    contribute to health score but are non-blocking.
    """
    msgs = messages or {}

    lc_h   = _component_health(ComponentType.LIFECYCLE,   is_running=lifecycle_running,   score=lifecycle_score,   message=msgs.get(ComponentType.LIFECYCLE,   ""))
    eng_h  = _component_health(ComponentType.ENGINE,      is_running=engine_running,      score=engine_score,      message=msgs.get(ComponentType.ENGINE,      ""))
    perf_h = _component_health(ComponentType.PERFORMANCE, is_running=performance_running, score=performance_score, message=msgs.get(ComponentType.PERFORMANCE, ""))
    pred_h = _component_health(ComponentType.PREDICTIVE,  is_running=predictive_running,  score=predictive_score,  message=msgs.get(ComponentType.PREDICTIVE,  ""))
    snap_h = _component_health(ComponentType.SNAPSHOT,    is_running=snapshot_running,    score=snapshot_score,    message=msgs.get(ComponentType.SNAPSHOT,    ""))

    # Aggregate: simple average, weighted by criticality
    # M1/M2/M5 weight=2, M3/M4 weight=1
    total_weight = 2 + 2 + 1 + 1 + 2
    overall_score = (
        lc_h.score   * 2
        + eng_h.score  * 2
        + perf_h.score * 1
        + pred_h.score * 1
        + snap_h.score * 2
    ) / total_weight

    if overall_score >= 0.8:
        overall_level = IntegrationHealthLevel.HEALTHY
    elif overall_score >= 0.5:
        overall_level = IntegrationHealthLevel.DEGRADED
    else:
        overall_level = IntegrationHealthLevel.CRITICAL

    # Operational requires M1, M2, M5 to be running
    is_operational = (
        integration_running
        and lc_h.is_running
        and eng_h.is_running
        and snap_h.is_running
    )

    # Collect error messages from critical/not-started components
    error_msgs: list[str] = []
    for comp_h in (lc_h, eng_h, perf_h, pred_h, snap_h):
        if comp_h.is_critical and comp_h.message:
            error_msgs.append(f"{comp_h.component.value}: {comp_h.message}")
        elif comp_h.is_critical:
            error_msgs.append(f"{comp_h.component.value}: {comp_h.health.value}")

    return AnalyticsIntegrationHealth(
        lifecycle_health   = lc_h,
        engine_health      = eng_h,
        performance_health = perf_h,
        predictive_health  = pred_h,
        snapshot_health    = snap_h,
        overall_health     = overall_level,
        overall_score      = overall_score,
        is_operational     = is_operational,
        error_messages     = tuple(error_msgs),
    )
