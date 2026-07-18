"""
iios/execution/analytics/performance/performance_kpi.py
=======================================================
KPIValue and KPIReport — immutable KPI result types for the Performance
Analytics Framework.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION, AggregationWindow, KPIType, PerformanceDomain


@dataclass(frozen=True)
class KPIValue:
    """
    Immutable result of a single KPI computation.

    Fields
    ------
    kpi_id:       Unique value ID.
    kpi_type:     Which KPI was computed.
    value:        Computed numeric value.
    domain:       Performance domain.
    window:       Aggregation window.
    sample_count: Number of data points used.
    unit:         Human-readable unit (e.g. 'ms', '%', 'tps').
    computed_at:  Wall-time of computation.
    version:      Framework version.
    metadata:     Supplementary data.
    """

    kpi_id:       str
    kpi_type:     KPIType
    value:        float
    domain:       PerformanceDomain
    window:       AggregationWindow
    sample_count: int              = 0
    unit:         str              = ""
    computed_at:  float            = field(default_factory=time.time)
    version:      str              = VERSION
    metadata:     Dict[str, Any]   = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi_id":       self.kpi_id,
            "kpi_type":     self.kpi_type.value,
            "value":        self.value,
            "domain":       self.domain.value,
            "window":       self.window.value,
            "sample_count": self.sample_count,
            "unit":         self.unit,
            "computed_at":  self.computed_at,
            "version":      self.version,
        }


@dataclass(frozen=True)
class KPIReport:
    """
    Immutable collection of KPI values for a domain / window combination.

    Fields
    ------
    report_id:    Unique report ID.
    domain:       Performance domain.
    window:       Aggregation window.
    kpi_values:   Tuple of computed KPIValue objects.
    generated_at: Wall-time of report generation.
    version:      Framework version.
    metadata:     Supplementary data.
    """

    report_id:    str
    domain:       PerformanceDomain
    window:       AggregationWindow
    kpi_values:   Tuple[KPIValue, ...]    = field(default_factory=tuple)
    generated_at: float                  = field(default_factory=time.time)
    version:      str                    = VERSION
    metadata:     Dict[str, Any]         = field(default_factory=dict, compare=False)

    @property
    def kpi_count(self) -> int:
        return len(self.kpi_values)

    def get(self, kpi_type: KPIType) -> Optional[KPIValue]:
        """Return the KPIValue for the given type, or None."""
        for v in self.kpi_values:
            if v.kpi_type == kpi_type:
                return v
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":    self.report_id,
            "domain":       self.domain.value,
            "window":       self.window.value,
            "kpi_count":    self.kpi_count,
            "kpi_values":   [v.to_dict() for v in self.kpi_values],
            "generated_at": self.generated_at,
            "version":      self.version,
        }


# ── KPI unit mapping ──────────────────────────────────────────────────────────

KPI_UNITS: Dict[KPIType, str] = {
    KPIType.EXECUTION_SUCCESS_RATE:   "ratio",
    KPIType.EXECUTION_FAILURE_RATE:   "ratio",
    KPIType.AVG_EXECUTION_TIME_MS:    "ms",
    KPIType.MEDIAN_EXECUTION_TIME_MS: "ms",
    KPIType.P95_LATENCY_MS:           "ms",
    KPIType.P99_LATENCY_MS:           "ms",
    KPIType.RECOVERY_SUCCESS_RATE:    "ratio",
    KPIType.MEAN_TIME_TO_RECOVERY_MS: "ms",
    KPIType.GATEWAY_AVAILABILITY:     "ratio",
    KPIType.BROKER_AVAILABILITY:      "ratio",
    KPIType.MONITORING_AVAILABILITY:  "ratio",
    KPIType.SYSTEM_THROUGHPUT:        "ratio",
    KPIType.QUEUE_EFFICIENCY:         "ratio",
    KPIType.ORDER_COMPLETION_RATE:    "ratio",
    KPIType.POSITION_ACCURACY:        "ratio",
    KPIType.RISK_RULE_EFFECTIVENESS:  "ratio",
    KPIType.PORTFOLIO_EFFICIENCY:     "ratio",
    KPIType.STRATEGY_EFFICIENCY:      "ratio",
    KPIType.RESOURCE_UTILIZATION:     "ratio",
}


def make_kpi_value(
    kpi_type:     KPIType,
    value:        float,
    *,
    domain:       PerformanceDomain  = PerformanceDomain.EXECUTION,
    window:       AggregationWindow  = AggregationWindow.REAL_TIME,
    sample_count: int                = 0,
    kpi_id:       Optional[str]      = None,
    metadata:     Optional[Dict[str, Any]] = None,
) -> KPIValue:
    """Create a new KPIValue."""
    return KPIValue(
        kpi_id       = kpi_id or str(uuid.uuid4()),
        kpi_type     = kpi_type,
        value        = value,
        domain       = domain,
        window       = window,
        sample_count = sample_count,
        unit         = KPI_UNITS.get(kpi_type, ""),
        metadata     = metadata or {},
    )


def make_kpi_report(
    kpi_values: List[KPIValue],
    domain:     PerformanceDomain,
    window:     AggregationWindow,
    *,
    report_id: Optional[str]           = None,
    metadata:  Optional[Dict[str, Any]]= None,
) -> KPIReport:
    """Create a new KPIReport."""
    return KPIReport(
        report_id  = report_id or str(uuid.uuid4()),
        domain     = domain,
        window     = window,
        kpi_values = tuple(kpi_values),
        metadata   = metadata or {},
    )
