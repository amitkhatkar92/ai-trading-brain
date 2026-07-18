"""
iios/execution/analytics/performance/performance_response.py
=============================================================
Output types for the Performance Analytics Framework:
  - PerformanceSnapshot
  - TrendAnalysis
  - BenchmarkReport
  - PerformanceScorecard
  - PerformanceAnalyticsReport

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    VERSION,
    AggregationWindow,
    BenchmarkStatus,
    KPIType,
    PerformanceDomain,
    PerformanceGrade,
    TrendDirection,
    score_to_grade,
)
from .performance_kpi import KPIReport, KPIValue


# ── PerformanceSnapshot ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class PerformanceSnapshot:
    """
    Immutable point-in-time performance snapshot.

    Published after every successful analytics cycle.
    """

    snapshot_id:   str
    domain:        PerformanceDomain
    window:        AggregationWindow
    kpi_values:    Tuple[KPIValue, ...]  = field(default_factory=tuple)
    captured_at:   float                = field(default_factory=time.time)
    version:       str                  = VERSION
    metadata:      Dict[str, Any]       = field(default_factory=dict, compare=False)

    @property
    def kpi_count(self) -> int:
        return len(self.kpi_values)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "domain":      self.domain.value,
            "window":      self.window.value,
            "kpi_count":   self.kpi_count,
            "captured_at": self.captured_at,
            "version":     self.version,
        }


# ── TrendAnalysis ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TrendAnalysis:
    """
    Immutable result of a trend analysis for a single KPI.

    Fields
    ------
    trend_id:       Unique trend ID.
    kpi_type:       KPI being analysed.
    domain:         Performance domain.
    direction:      Detected trend direction.
    slope:          Linear trend slope (change per period).
    magnitude:      Relative magnitude [0, 1].
    data_points:    Number of data points analysed.
    min_value:      Minimum observed value.
    max_value:      Maximum observed value.
    mean_value:     Mean of observed values.
    std_dev:        Standard deviation.
    window_seconds: Duration of the analysis window.
    analyzed_at:    Wall-time of analysis.
    version:        Framework version.
    """

    trend_id:       str
    kpi_type:       KPIType
    domain:         PerformanceDomain
    direction:      TrendDirection
    slope:          float               = 0.0
    magnitude:      float               = 0.0
    data_points:    int                 = 0
    min_value:      float               = 0.0
    max_value:      float               = 0.0
    mean_value:     float               = 0.0
    std_dev:        float               = 0.0
    window_seconds: float               = 0.0
    analyzed_at:    float               = field(default_factory=time.time)
    version:        str                 = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_id":       self.trend_id,
            "kpi_type":       self.kpi_type.value,
            "domain":         self.domain.value,
            "direction":      self.direction.value,
            "slope":          self.slope,
            "magnitude":      self.magnitude,
            "data_points":    self.data_points,
            "min_value":      self.min_value,
            "max_value":      self.max_value,
            "mean_value":     self.mean_value,
            "std_dev":        self.std_dev,
            "window_seconds": self.window_seconds,
            "analyzed_at":    self.analyzed_at,
        }


# ── BenchmarkReport ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BenchmarkComparison:
    """Single KPI benchmark comparison result."""

    kpi_type:         KPIType
    actual_value:     float
    warning_threshold:float
    critical_threshold:float
    status:           BenchmarkStatus
    score:            float           # normalised [0, 1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi_type":           self.kpi_type.value,
            "actual_value":       self.actual_value,
            "warning_threshold":  self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "status":             self.status.value,
            "score":              self.score,
        }


@dataclass(frozen=True)
class BenchmarkReport:
    """
    Immutable report of benchmark comparisons for a domain / window.
    """

    report_id:     str
    domain:        PerformanceDomain
    window:        AggregationWindow
    comparisons:   Tuple[BenchmarkComparison, ...] = field(default_factory=tuple)
    overall_score: float                          = 0.0
    generated_at:  float                         = field(default_factory=time.time)
    version:       str                           = VERSION

    @property
    def comparison_count(self) -> int:
        return len(self.comparisons)

    @property
    def above_target_count(self) -> int:
        return sum(1 for c in self.comparisons if c.status == BenchmarkStatus.ABOVE_TARGET)

    @property
    def below_target_count(self) -> int:
        return sum(1 for c in self.comparisons if c.status == BenchmarkStatus.BELOW_TARGET)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":       self.report_id,
            "domain":          self.domain.value,
            "window":          self.window.value,
            "comparison_count":self.comparison_count,
            "overall_score":   self.overall_score,
            "above_target":    self.above_target_count,
            "below_target":    self.below_target_count,
            "generated_at":    self.generated_at,
            "comparisons":     [c.to_dict() for c in self.comparisons],
        }


# ── PerformanceScorecard ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class PerformanceScorecard:
    """
    Immutable performance scorecard for a domain / window.
    """

    scorecard_id:  str
    domain:        PerformanceDomain
    window:        AggregationWindow
    grade:         PerformanceGrade
    overall_score: float                  = 0.0
    kpi_scores:    Dict[str, float]       = field(default_factory=dict, compare=False)
    generated_at:  float                  = field(default_factory=time.time)
    version:       str                    = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scorecard_id":  self.scorecard_id,
            "domain":        self.domain.value,
            "window":        self.window.value,
            "grade":         self.grade.value,
            "overall_score": self.overall_score,
            "kpi_scores":    dict(self.kpi_scores),
            "generated_at":  self.generated_at,
        }


# ── PerformanceAnalyticsReport ────────────────────────────────────────────────

@dataclass(frozen=True)
class PerformanceAnalyticsReport:
    """
    Immutable full performance analytics report — the primary output of
    the Performance Analytics Framework.

    Returned by PerformanceAnalyticsEngine.process().
    """

    report_id:        str
    request_id:       str
    domain:           PerformanceDomain
    window:           AggregationWindow
    kpi_report:       KPIReport
    snapshot:         PerformanceSnapshot
    trends:           Tuple[TrendAnalysis, ...]  = field(default_factory=tuple)
    benchmark_report: Optional[BenchmarkReport] = None
    scorecard:        Optional[PerformanceScorecard] = None
    error_message:    str                        = ""
    processing_ms:    float                      = 0.0
    generated_at:     float                      = field(default_factory=time.time)
    version:          str                        = VERSION

    @property
    def is_success(self) -> bool:
        return not self.error_message

    @property
    def kpi_count(self) -> int:
        return self.kpi_report.kpi_count

    @property
    def trend_count(self) -> int:
        return len(self.trends)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":        self.report_id,
            "request_id":       self.request_id,
            "domain":           self.domain.value,
            "window":           self.window.value,
            "kpi_count":        self.kpi_count,
            "trend_count":      self.trend_count,
            "has_benchmark":    self.benchmark_report is not None,
            "has_scorecard":    self.scorecard is not None,
            "error_message":    self.error_message,
            "processing_ms":    self.processing_ms,
            "generated_at":     self.generated_at,
            "version":          self.version,
        }


# ── Factory functions ─────────────────────────────────────────────────────────

def make_performance_snapshot(
    domain:     PerformanceDomain,
    window:     AggregationWindow,
    kpi_values: List[KPIValue],
    *,
    snapshot_id: Optional[str]           = None,
    metadata:    Optional[Dict[str, Any]]= None,
) -> PerformanceSnapshot:
    return PerformanceSnapshot(
        snapshot_id = snapshot_id or str(uuid.uuid4()),
        domain      = domain,
        window      = window,
        kpi_values  = tuple(kpi_values),
        metadata    = metadata or {},
    )
