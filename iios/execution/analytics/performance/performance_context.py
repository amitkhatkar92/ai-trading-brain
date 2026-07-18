"""
iios/execution/analytics/performance/performance_context.py
============================================================
PerformanceContext — immutable analytics context for the Performance
Analytics Framework.

Carries all input data needed for a complete performance analytics cycle.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import ACTOR_SYSTEM, VERSION, AggregationWindow, KPIType, PerformanceDomain


@dataclass(frozen=True)
class PerformanceContext:
    """
    Immutable context for a performance analytics cycle.

    Input snapshots are Optional to accommodate partial subsystem
    availability at computation time.

    The ``historical_kpi_data`` field holds time-series of past KPI values,
    keyed by KPIType, enabling rolling-window and trend calculations.

    The ``raw_sample_data`` field carries raw numeric samples (e.g. latency
    measurements) keyed by a descriptive name, enabling percentile calculations.

    Fields
    ------
    context_id:           Unique context ID.
    request_id:           Parent PerformanceRequest ID.
    domain:               Performance domain.
    window:               Aggregation window.
    monitoring_snapshot:  Optional snapshot from the Monitoring subsystem.
    recovery_snapshot:    Optional snapshot from the Recovery subsystem.
    gateway_snapshot:     Optional snapshot from the Gateway subsystem.
    risk_snapshot:        Optional snapshot from the Risk subsystem.
    historical_kpi_data:  Past KPI time-series keyed by KPIType value string.
    raw_sample_data:      Raw numeric sample lists keyed by metric name.
    custom_window_seconds: Window size override (for AggregationWindow.CUSTOM).
    requester:            Actor requesting this context.
    metadata:             Supplementary data.
    created_at:           Wall-time of context creation.
    framework_version:    Framework version.
    """

    context_id:            str
    request_id:            str
    domain:                PerformanceDomain
    window:                AggregationWindow
    monitoring_snapshot:   Optional[Any]            = None
    recovery_snapshot:     Optional[Any]            = None
    gateway_snapshot:      Optional[Any]            = None
    risk_snapshot:         Optional[Any]            = None
    historical_kpi_data:   Dict[str, List[float]]   = field(default_factory=dict)
    raw_sample_data:       Dict[str, List[float]]   = field(default_factory=dict)
    custom_window_seconds: float                    = 0.0
    requester:             str                      = ACTOR_SYSTEM
    metadata:              Dict[str, Any]           = field(default_factory=dict)
    created_at:            float                    = field(default_factory=time.time)
    framework_version:     str                      = VERSION

    @property
    def has_monitoring(self) -> bool:
        return self.monitoring_snapshot is not None

    @property
    def has_recovery(self) -> bool:
        return self.recovery_snapshot is not None

    @property
    def has_gateway(self) -> bool:
        return self.gateway_snapshot is not None

    @property
    def has_risk(self) -> bool:
        return self.risk_snapshot is not None

    @property
    def available_snapshot_count(self) -> int:
        return sum(1 for s in (
            self.monitoring_snapshot, self.recovery_snapshot,
            self.gateway_snapshot, self.risk_snapshot,
        ) if s is not None)

    @property
    def has_historical_data(self) -> bool:
        return bool(self.historical_kpi_data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":            self.context_id,
            "request_id":            self.request_id,
            "domain":                self.domain.value,
            "window":                self.window.value,
            "has_monitoring":        self.has_monitoring,
            "has_recovery":          self.has_recovery,
            "has_gateway":           self.has_gateway,
            "has_risk":              self.has_risk,
            "available_snapshots":   self.available_snapshot_count,
            "historical_kpi_keys":   list(self.historical_kpi_data.keys()),
            "raw_sample_keys":       list(self.raw_sample_data.keys()),
            "created_at":            self.created_at,
            "framework_version":     self.framework_version,
        }


def make_performance_context(
    request_id: str,
    domain:     PerformanceDomain,
    window:     AggregationWindow,
    *,
    context_id:            Optional[str]                   = None,
    monitoring_snapshot:   Optional[Any]                   = None,
    recovery_snapshot:     Optional[Any]                   = None,
    gateway_snapshot:      Optional[Any]                   = None,
    risk_snapshot:         Optional[Any]                   = None,
    historical_kpi_data:   Optional[Dict[str, List[float]]]= None,
    raw_sample_data:       Optional[Dict[str, List[float]]]= None,
    custom_window_seconds: float                           = 0.0,
    requester:             str                             = ACTOR_SYSTEM,
    metadata:              Optional[Dict[str, Any]]        = None,
) -> PerformanceContext:
    """Create a new PerformanceContext."""
    return PerformanceContext(
        context_id            = context_id or str(uuid.uuid4()),
        request_id            = request_id,
        domain                = domain,
        window                = window,
        monitoring_snapshot   = monitoring_snapshot,
        recovery_snapshot     = recovery_snapshot,
        gateway_snapshot      = gateway_snapshot,
        risk_snapshot         = risk_snapshot,
        historical_kpi_data   = historical_kpi_data or {},
        raw_sample_data       = raw_sample_data or {},
        custom_window_seconds = custom_window_seconds,
        requester             = requester,
        metadata              = metadata or {},
    )
