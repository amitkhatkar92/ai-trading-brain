"""iios/execution/positions/integration/position_component_health.py
==================================================
ComponentHealthRecord and HealthReport — per-component and
aggregate health representation.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .constants import HealthStatus, VERSION


@dataclass(frozen=True)
class ComponentHealthRecord:
    """
    Immutable health record for a single component.

    Produced by a health check at a specific point in time.
    """

    component_name: str
    status:         str       # HealthStatus value
    is_running:     bool
    message:        str
    checked_at:     float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name": self.component_name,
            "status":         self.status,
            "is_running":     self.is_running,
            "message":        self.message,
            "checked_at":     self.checked_at,
        }


@dataclass(frozen=True)
class HealthReport:
    """
    Immutable aggregate health report for the entire Position Integration
    subsystem.

    Attributes
    ----------
    report_id
        UUID for this report instance.
    overall_status
        Aggregate ``HealthStatus`` value.
    components
        Mapping of component_name → ``ComponentHealthRecord.to_dict()``.
    healthy_count
        Number of components that are HEALTHY.
    total_count
        Total number of components evaluated.
    generated_at
        Unix timestamp of report generation.
    details
        Optional free-form notes / anomaly descriptions.
    version
        Module version at report generation time.
    """

    report_id:      str
    overall_status: str   # HealthStatus value
    components:     Dict[str, Any]   = field(default_factory=dict, compare=False)
    healthy_count:  int              = 0
    total_count:    int              = 0
    generated_at:   float            = field(default_factory=time.time)
    details:        str              = ""
    version:        str              = VERSION

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == HealthStatus.HEALTHY

    @property
    def is_fully_healthy(self) -> bool:
        return self.healthy_count == self.total_count and self.total_count > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":      self.report_id,
            "overall_status": self.overall_status,
            "components":     dict(self.components),
            "healthy_count":  self.healthy_count,
            "total_count":    self.total_count,
            "generated_at":   self.generated_at,
            "details":        self.details,
            "version":        self.version,
        }


def make_health_report(
    component_records: List[ComponentHealthRecord],
    *,
    details: str = "",
) -> HealthReport:
    """
    Build a ``HealthReport`` from a list of per-component records.

    Aggregation rules
    -----------------
    * All HEALTHY → overall HEALTHY
    * Any CRITICAL → overall CRITICAL
    * Any non-HEALTHY but no CRITICAL → overall DEGRADED
    * No records → overall UNKNOWN
    """
    if not component_records:
        return HealthReport(
            report_id=str(uuid.uuid4()),
            overall_status=HealthStatus.UNKNOWN,
            components={},
            healthy_count=0,
            total_count=0,
            details=details,
        )

    components   = {r.component_name: r.to_dict() for r in component_records}
    healthy      = sum(1 for r in component_records if r.is_healthy)
    has_critical = any(r.status == HealthStatus.CRITICAL for r in component_records)

    if has_critical:
        overall = HealthStatus.CRITICAL
    elif healthy == len(component_records):
        overall = HealthStatus.HEALTHY
    else:
        overall = HealthStatus.DEGRADED

    return HealthReport(
        report_id=str(uuid.uuid4()),
        overall_status=overall,
        components=components,
        healthy_count=healthy,
        total_count=len(component_records),
        details=details,
    )
