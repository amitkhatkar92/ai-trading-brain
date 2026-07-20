"""
iios/execution/analytics/snapshot/execution_analytics_snapshot.py
=================================================================
ExecutionAnalyticsSnapshot — the ONLY published representation of the
Analytics subsystem.

Every downstream subsystem MUST consume this object instead of
internal Analytics objects.

This object:
  - Is immutable (frozen dataclass)
  - Performs NO calculations
  - Performs NO forecasting
  - Contains validated analytics information only

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .analytics_snapshot_metadata import AnalyticsMetadata, AuditMetadata
from .constants import (
    SNAPSHOT_FRAMEWORK_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    AnalyticsHealth,
    AnalyticsMode,
    AnalyticsScope,
    AnalyticsStatus,
    SnapshotLifecycleState,
)


# ── Snapshot-internal summary value objects ───────────────────────────────────
# These are lightweight frozen dataclasses that summarise data from
# M1/M2/M3/M4.  Downstream consumers depend ONLY on these types.


@dataclass(frozen=True)
class PerformanceSummary:
    """High-level performance summary extracted from M3 Performance Analytics."""

    total_executions:       int   = 0
    successful_executions:  int   = 0
    success_rate:           float = 0.0
    avg_execution_time_ms:  float = 0.0
    total_pnl:              float = 0.0
    win_rate:               float = 0.0
    sharpe_ratio:           float = 0.0
    max_drawdown:           float = 0.0
    avg_slippage:           float = 0.0
    fill_rate:              float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_executions":      self.total_executions,
            "successful_executions": self.successful_executions,
            "success_rate":          self.success_rate,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "total_pnl":             self.total_pnl,
            "win_rate":              self.win_rate,
            "sharpe_ratio":          self.sharpe_ratio,
            "max_drawdown":          self.max_drawdown,
            "avg_slippage":          self.avg_slippage,
            "fill_rate":             self.fill_rate,
        }


@dataclass(frozen=True)
class PerformanceKPIs:
    """Key performance indicators extracted from M3 KPIReport."""

    execution_success_rate: float              = 0.0
    avg_latency_ms:         float              = 0.0
    fill_rate:              float              = 1.0
    slippage_rate:          float              = 0.0
    throughput_per_minute:  float              = 0.0
    error_rate:             float              = 0.0
    kpi_values:             Dict[str, float]   = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_success_rate": self.execution_success_rate,
            "avg_latency_ms":         self.avg_latency_ms,
            "fill_rate":              self.fill_rate,
            "slippage_rate":          self.slippage_rate,
            "throughput_per_minute":  self.throughput_per_minute,
            "error_rate":             self.error_rate,
            "kpi_values":             dict(self.kpi_values),
        }


@dataclass(frozen=True)
class PerformanceScorecard:
    """Performance scorecard extracted from M3 PerformanceScorecard."""

    overall_score:    float            = 0.0
    execution_score:  float            = 0.0
    risk_score:       float            = 0.0
    efficiency_score: float            = 0.0
    grade:            str              = "F"
    kpi_scores:       Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":    self.overall_score,
            "execution_score":  self.execution_score,
            "risk_score":       self.risk_score,
            "efficiency_score": self.efficiency_score,
            "grade":            self.grade,
            "kpi_scores":       dict(self.kpi_scores),
        }


@dataclass(frozen=True)
class TrendSummary:
    """Trend summary extracted from M3 trend analysis."""

    dominant_trend:   str = "unknown"
    trend_count:      int = 0
    improving_count:  int = 0
    degrading_count:  int = 0
    stable_count:     int = 0
    volatile_count:   int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dominant_trend":  self.dominant_trend,
            "trend_count":     self.trend_count,
            "improving_count": self.improving_count,
            "degrading_count": self.degrading_count,
            "stable_count":    self.stable_count,
            "volatile_count":  self.volatile_count,
        }


@dataclass(frozen=True)
class BenchmarkSummary:
    """Benchmark summary extracted from M3 BenchmarkReport."""

    overall_score:        float              = 0.0
    benchmark_count:      int                = 0
    within_threshold:     int                = 0
    exceeding_threshold:  int                = 0
    comparisons:          Dict[str, float]   = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":       self.overall_score,
            "benchmark_count":     self.benchmark_count,
            "within_threshold":    self.within_threshold,
            "exceeding_threshold": self.exceeding_threshold,
            "comparisons":         dict(self.comparisons),
        }


@dataclass(frozen=True)
class HistoricalSummary:
    """Summary of historical analytics data."""

    data_points:         int   = 0
    time_range_seconds:  float = 0.0
    oldest_timestamp:    float = 0.0
    newest_timestamp:    float = 0.0
    sessions_analyzed:   int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_points":        self.data_points,
            "time_range_seconds": self.time_range_seconds,
            "oldest_timestamp":   self.oldest_timestamp,
            "newest_timestamp":   self.newest_timestamp,
            "sessions_analyzed":  self.sessions_analyzed,
        }


@dataclass(frozen=True)
class PredictionSummary:
    """Prediction summary extracted from M4 PredictiveIntelligenceEngine output."""

    total_predictions:    int            = 0
    avg_confidence:       float          = 0.0
    high_confidence_count: int           = 0
    low_confidence_count:  int           = 0
    prediction_domains:   Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_predictions":     self.total_predictions,
            "avg_confidence":        self.avg_confidence,
            "high_confidence_count": self.high_confidence_count,
            "low_confidence_count":  self.low_confidence_count,
            "prediction_domains":    list(self.prediction_domains),
        }


@dataclass(frozen=True)
class SnapshotForecastSummary:
    """Forecast summary extracted from M4 ForecastSummary."""

    total_forecasts:  int   = 0
    dominant_trend:   str   = "unknown"
    forecast_horizon: str   = "next_hour"
    avg_confidence:   float = 0.0
    forecast_domain:  str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_forecasts":  self.total_forecasts,
            "dominant_trend":   self.dominant_trend,
            "forecast_horizon": self.forecast_horizon,
            "avg_confidence":   self.avg_confidence,
            "forecast_domain":  self.forecast_domain,
        }


@dataclass(frozen=True)
class ConfidenceSummary:
    """Aggregated confidence scores across all analytics frameworks."""

    overall_confidence:     float = 0.0
    performance_confidence: float = 0.0
    prediction_confidence:  float = 0.0
    risk_confidence:        float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_confidence":     self.overall_confidence,
            "performance_confidence": self.performance_confidence,
            "prediction_confidence":  self.prediction_confidence,
            "risk_confidence":        self.risk_confidence,
        }


@dataclass(frozen=True)
class SnapshotCapacityForecast:
    """Capacity forecast extracted from M4 CapacityForecast."""

    current_utilization:   float = 0.0
    forecasted_utilization: float = 0.0
    capacity_headroom:     float = 1.0
    bottleneck_risk:       float = 0.0
    risk_level:            str   = "minimal"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_utilization":    self.current_utilization,
            "forecasted_utilization": self.forecasted_utilization,
            "capacity_headroom":      self.capacity_headroom,
            "bottleneck_risk":        self.bottleneck_risk,
            "risk_level":             self.risk_level,
        }


@dataclass(frozen=True)
class SnapshotRiskForecast:
    """Risk forecast extracted from M4 RiskForecast."""

    risk_level:           str              = "minimal"
    risk_score:           float            = 0.0
    contributing_factors: Tuple[str, ...]  = field(default_factory=tuple)
    mitigation_indicators: Tuple[str, ...] = field(default_factory=tuple)
    confidence:           float            = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_level":            self.risk_level,
            "risk_score":            self.risk_score,
            "contributing_factors":  list(self.contributing_factors),
            "mitigation_indicators": list(self.mitigation_indicators),
            "confidence":            self.confidence,
        }


@dataclass(frozen=True)
class SnapshotAnalyticsStatistics:
    """Aggregated statistics from M1/M2/M3/M4 analytics components."""

    total_cycles:          int   = 0
    successful_cycles:     int   = 0
    failed_cycles:         int   = 0
    avg_cycle_time_ms:     float = 0.0
    total_events:          int   = 0
    performance_cycles:    int   = 0
    prediction_cycles:     int   = 0
    success_rate:          float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cycles":       self.total_cycles,
            "successful_cycles":  self.successful_cycles,
            "failed_cycles":      self.failed_cycles,
            "avg_cycle_time_ms":  self.avg_cycle_time_ms,
            "total_events":       self.total_events,
            "performance_cycles": self.performance_cycles,
            "prediction_cycles":  self.prediction_cycles,
            "success_rate":       self.success_rate,
        }


# ── Primary published object ──────────────────────────────────────────────────

@dataclass(frozen=True)
class ExecutionAnalyticsSnapshot:
    """
    The ONLY published representation of the Analytics subsystem.

    Every downstream subsystem — Analytics Integration, Decision
    Intelligence, Portfolio Intelligence, AI Supervisor, Compliance,
    Reporting, Dashboard, Enterprise Intelligence — MUST consume this
    object and MUST NOT reference internal M1/M2/M3/M4 objects.

    Immutable.  No calculations.  No forecasting.  Validated data only.
    """

    # ── Identifiers ───────────────────────────────────────────────────────────
    snapshot_id:          str
    snapshot_version:     str
    analytics_session_id: str
    execution_session_id: str
    workflow_id:          str
    portfolio_id:         str
    strategy_id:          str

    # ── Scope / Mode ──────────────────────────────────────────────────────────
    analytics_scope:  AnalyticsScope
    analytics_mode:   AnalyticsMode

    # ── State ─────────────────────────────────────────────────────────────────
    lifecycle_state:   SnapshotLifecycleState
    analytics_status:  AnalyticsStatus
    analytics_health:  AnalyticsHealth

    # ── Performance ───────────────────────────────────────────────────────────
    performance_summary:   Optional[PerformanceSummary]
    performance_kpis:      Optional[PerformanceKPIs]
    performance_scorecard: Optional[PerformanceScorecard]

    # ── Trends / Benchmarks / Historical ─────────────────────────────────────
    trend_summary:      Optional[TrendSummary]
    benchmark_summary:  Optional[BenchmarkSummary]
    historical_summary: Optional[HistoricalSummary]

    # ── Predictions ───────────────────────────────────────────────────────────
    prediction_summary:  Optional[PredictionSummary]
    forecast_summary:    Optional[SnapshotForecastSummary]
    confidence_summary:  Optional[ConfidenceSummary]

    # ── Operational ───────────────────────────────────────────────────────────
    operational_health_score: float
    capacity_forecast:        Optional[SnapshotCapacityForecast]
    risk_forecast:            Optional[SnapshotRiskForecast]

    # ── Analytics meta ────────────────────────────────────────────────────────
    analytics_statistics: Optional[SnapshotAnalyticsStatistics]
    analytics_metadata:   Optional[AnalyticsMetadata]
    audit_metadata:       Optional[AuditMetadata]

    # ── System ────────────────────────────────────────────────────────────────
    framework_version: str   = SNAPSHOT_FRAMEWORK_VERSION
    timestamp:         float = field(default_factory=time.time)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_published(self) -> bool:
        return self.lifecycle_state == SnapshotLifecycleState.PUBLISHED

    @property
    def is_valid(self) -> bool:
        return self.lifecycle_state not in (
            SnapshotLifecycleState.INVALID,
            SnapshotLifecycleState.BUILDING,
        )

    @property
    def has_performance(self) -> bool:
        return self.performance_summary is not None

    @property
    def has_predictions(self) -> bool:
        return self.prediction_summary is not None

    @property
    def has_forecasts(self) -> bool:
        return self.forecast_summary is not None

    @property
    def has_risk(self) -> bool:
        return self.risk_forecast is not None

    @property
    def has_capacity(self) -> bool:
        return self.capacity_forecast is not None

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":            self.snapshot_id,
            "snapshot_version":       self.snapshot_version,
            "analytics_session_id":   self.analytics_session_id,
            "execution_session_id":   self.execution_session_id,
            "workflow_id":            self.workflow_id,
            "portfolio_id":           self.portfolio_id,
            "strategy_id":            self.strategy_id,
            "analytics_scope":        self.analytics_scope.value,
            "analytics_mode":         self.analytics_mode.value,
            "lifecycle_state":        self.lifecycle_state.value,
            "analytics_status":       self.analytics_status.value,
            "analytics_health":       self.analytics_health.value,
            "performance_summary":    self.performance_summary.to_dict()
                                      if self.performance_summary else None,
            "performance_kpis":       self.performance_kpis.to_dict()
                                      if self.performance_kpis else None,
            "performance_scorecard":  self.performance_scorecard.to_dict()
                                      if self.performance_scorecard else None,
            "trend_summary":          self.trend_summary.to_dict()
                                      if self.trend_summary else None,
            "benchmark_summary":      self.benchmark_summary.to_dict()
                                      if self.benchmark_summary else None,
            "historical_summary":     self.historical_summary.to_dict()
                                      if self.historical_summary else None,
            "prediction_summary":     self.prediction_summary.to_dict()
                                      if self.prediction_summary else None,
            "forecast_summary":       self.forecast_summary.to_dict()
                                      if self.forecast_summary else None,
            "confidence_summary":     self.confidence_summary.to_dict()
                                      if self.confidence_summary else None,
            "operational_health_score": self.operational_health_score,
            "capacity_forecast":      self.capacity_forecast.to_dict()
                                      if self.capacity_forecast else None,
            "risk_forecast":          self.risk_forecast.to_dict()
                                      if self.risk_forecast else None,
            "analytics_statistics":   self.analytics_statistics.to_dict()
                                      if self.analytics_statistics else None,
            "analytics_metadata":     self.analytics_metadata.to_dict()
                                      if self.analytics_metadata else None,
            "audit_metadata":         self.audit_metadata.to_dict()
                                      if self.audit_metadata else None,
            "framework_version":      self.framework_version,
            "timestamp":              self.timestamp,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)
