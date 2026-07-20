"""
iios/execution/analytics/predictive/predictive_context.py
=========================================================
PredictiveContext — immutable analytics context for the Predictive
Intelligence Framework.

Carries all input data needed for a complete prediction cycle.
Snapshots and reports from M3 (Performance Analytics) are accepted as
Optional[Any] to avoid hard coupling.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import ACTOR_SYSTEM, VERSION, ForecastHorizon, PredictionDomain


@dataclass(frozen=True)
class PredictiveContext:
    """
    Immutable context for a prediction cycle.

    Fields
    ------
    context_id:             Unique context ID.
    request_id:             Parent PredictionRequest ID.
    domain:                 Prediction domain.
    horizon:                Forecast horizon.
    performance_report:     Optional M3 PerformanceAnalyticsReport.
    performance_snapshot:   Optional M3 PerformanceSnapshot.
    monitoring_snapshot:    Optional snapshot from the Monitoring subsystem.
    recovery_snapshot:      Optional snapshot from the Recovery subsystem.
    gateway_snapshot:       Optional snapshot from the Gateway subsystem.
    historical_analytics:   Dict of historical KPI/metric series keyed by
                            PredictionType value strings.
    raw_metrics:            Raw numeric sample lists keyed by metric name.
    execution_statistics:   Optional execution stats object.
    custom_horizon_seconds: Override horizon in seconds (for CUSTOM horizon).
    requester:              Actor requesting this context.
    metadata:               Supplementary data.
    created_at:             Wall-time of creation.
    framework_version:      Framework version.
    """

    context_id:             str
    request_id:             str
    domain:                 PredictionDomain
    horizon:                ForecastHorizon
    performance_report:     Optional[Any]            = None
    performance_snapshot:   Optional[Any]            = None
    monitoring_snapshot:    Optional[Any]            = None
    recovery_snapshot:      Optional[Any]            = None
    gateway_snapshot:       Optional[Any]            = None
    historical_analytics:   Dict[str, List[float]]   = field(default_factory=dict)
    raw_metrics:            Dict[str, List[float]]   = field(default_factory=dict)
    execution_statistics:   Optional[Any]            = None
    custom_horizon_seconds: float                    = 0.0
    requester:              str                      = ACTOR_SYSTEM
    metadata:               Dict[str, Any]           = field(default_factory=dict)
    created_at:             float                    = field(default_factory=time.time)
    framework_version:      str                      = VERSION

    @property
    def has_performance_report(self) -> bool:
        return self.performance_report is not None

    @property
    def has_performance_snapshot(self) -> bool:
        return self.performance_snapshot is not None

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
    def available_snapshot_count(self) -> int:
        return sum(1 for s in (
            self.performance_report, self.performance_snapshot,
            self.monitoring_snapshot, self.recovery_snapshot, self.gateway_snapshot,
        ) if s is not None)

    @property
    def has_historical_data(self) -> bool:
        return bool(self.historical_analytics)

    @property
    def has_raw_metrics(self) -> bool:
        return bool(self.raw_metrics)

    def horizon_seconds(self) -> float:
        """Effective horizon in seconds."""
        from .constants import HORIZON_SECONDS
        if self.horizon == ForecastHorizon.CUSTOM:
            return self.custom_horizon_seconds
        return HORIZON_SECONDS.get(self.horizon, 3600.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":            self.context_id,
            "request_id":            self.request_id,
            "domain":                self.domain.value,
            "horizon":               self.horizon.value,
            "has_performance_report":self.has_performance_report,
            "available_snapshots":   self.available_snapshot_count,
            "historical_keys":       list(self.historical_analytics.keys()),
            "raw_metric_keys":       list(self.raw_metrics.keys()),
            "created_at":            self.created_at,
            "framework_version":     self.framework_version,
        }


def make_predictive_context(
    request_id:             str,
    domain:                 PredictionDomain,
    horizon:                ForecastHorizon,
    *,
    context_id:             Optional[str]                    = None,
    performance_report:     Optional[Any]                    = None,
    performance_snapshot:   Optional[Any]                    = None,
    monitoring_snapshot:    Optional[Any]                    = None,
    recovery_snapshot:      Optional[Any]                    = None,
    gateway_snapshot:       Optional[Any]                    = None,
    historical_analytics:   Optional[Dict[str, List[float]]] = None,
    raw_metrics:            Optional[Dict[str, List[float]]] = None,
    execution_statistics:   Optional[Any]                    = None,
    custom_horizon_seconds: float                            = 0.0,
    requester:              str                              = ACTOR_SYSTEM,
    metadata:               Optional[Dict[str, Any]]         = None,
) -> PredictiveContext:
    """Create a new PredictiveContext."""
    return PredictiveContext(
        context_id             = context_id or str(uuid.uuid4()),
        request_id             = request_id,
        domain                 = domain,
        horizon                = horizon,
        performance_report     = performance_report,
        performance_snapshot   = performance_snapshot,
        monitoring_snapshot    = monitoring_snapshot,
        recovery_snapshot      = recovery_snapshot,
        gateway_snapshot       = gateway_snapshot,
        historical_analytics   = historical_analytics or {},
        raw_metrics            = raw_metrics or {},
        execution_statistics   = execution_statistics,
        custom_horizon_seconds = custom_horizon_seconds,
        requester              = requester,
        metadata               = metadata or {},
    )
