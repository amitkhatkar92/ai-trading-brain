"""
health_report.py -- iios.ai.model_management.health
=====================================================
:class:`HealthReport` — immutable point-in-time health snapshot for one model.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .availability_status import AvailabilityStatus


@dataclass(frozen=True)
class HealthReport:
    """Immutable health report for a single model."""
    model_id:       str
    status:         AvailabilityStatus
    failure_count:  int
    recovery_count: int
    last_check_at:  Optional[float]
    last_failure_at: Optional[float]

    @property
    def is_healthy(self) -> bool:
        return self.status in (AvailabilityStatus.AVAILABLE, AvailabilityStatus.DEGRADED)
