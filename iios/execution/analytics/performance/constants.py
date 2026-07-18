"""
iios/execution/analytics/performance/constants.py
=================================================
Constants and enumerations for the C8 Performance Analytics Framework.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet


# ── System identifiers ────────────────────────────────────────────────────────

ENGINE_SYSTEM_ID    = "iios:execution:analytics:performance:engine"
MANAGER_SYSTEM_ID   = "iios:execution:analytics:performance:manager"
CALC_SYSTEM_ID      = "iios:execution:analytics:performance:calculator"
REGISTRY_SYSTEM_ID  = "iios:execution:analytics:performance:registry"
FACTORY_SYSTEM_ID   = "iios:execution:analytics:performance:factory"

# ── Versioning ────────────────────────────────────────────────────────────────

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Default limits ────────────────────────────────────────────────────────────

DEFAULT_MAX_REQUESTS  = 5_000
DEFAULT_MAX_HISTORY   = 2_000
DEFAULT_MIN_SAMPLES   = 2          # minimum samples for trend analysis
DEFAULT_WINDOW_S      = 300.0      # default 5-minute window

# ── Actor constants ───────────────────────────────────────────────────────────

ACTOR_ENGINE     = "iios:execution:analytics:performance:engine"
ACTOR_CALCULATOR = "iios:execution:analytics:performance:calculator"
ACTOR_SYSTEM     = "iios:system"
ACTOR_OPERATOR   = "operator"


# ── Performance domain enumeration ────────────────────────────────────────────

class PerformanceDomain(str, Enum):
    """Domains covered by the Performance Analytics Framework."""

    EXECUTION       = "execution"
    ORDER           = "order"
    POSITION        = "position"
    RISK            = "risk"
    GATEWAY         = "gateway"
    MONITORING      = "monitoring"
    RECOVERY        = "recovery"
    BROKER          = "broker"
    PORTFOLIO       = "portfolio"
    STRATEGY        = "strategy"
    INFRASTRUCTURE  = "infrastructure"


# ── KPI type enumeration ──────────────────────────────────────────────────────

class KPIType(str, Enum):
    """All institutional KPIs supported by the framework."""

    EXECUTION_SUCCESS_RATE     = "execution_success_rate"
    EXECUTION_FAILURE_RATE     = "execution_failure_rate"
    AVG_EXECUTION_TIME_MS      = "avg_execution_time_ms"
    MEDIAN_EXECUTION_TIME_MS   = "median_execution_time_ms"
    P95_LATENCY_MS             = "p95_latency_ms"
    P99_LATENCY_MS             = "p99_latency_ms"
    RECOVERY_SUCCESS_RATE      = "recovery_success_rate"
    MEAN_TIME_TO_RECOVERY_MS   = "mean_time_to_recovery_ms"
    GATEWAY_AVAILABILITY       = "gateway_availability"
    BROKER_AVAILABILITY        = "broker_availability"
    MONITORING_AVAILABILITY    = "monitoring_availability"
    SYSTEM_THROUGHPUT          = "system_throughput"
    QUEUE_EFFICIENCY           = "queue_efficiency"
    ORDER_COMPLETION_RATE      = "order_completion_rate"
    POSITION_ACCURACY          = "position_accuracy"
    RISK_RULE_EFFECTIVENESS    = "risk_rule_effectiveness"
    PORTFOLIO_EFFICIENCY       = "portfolio_efficiency"
    STRATEGY_EFFICIENCY        = "strategy_efficiency"
    RESOURCE_UTILIZATION       = "resource_utilization"


# ── Aggregation window enumeration ────────────────────────────────────────────

class AggregationWindow(str, Enum):
    """Supported time-window aggregations."""

    REAL_TIME      = "real_time"
    ONE_MINUTE     = "1m"
    FIVE_MINUTES   = "5m"
    FIFTEEN_MINUTES= "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR       = "1h"
    DAILY          = "1d"
    WEEKLY         = "1w"
    MONTHLY        = "1M"
    CUSTOM         = "custom"


# ── Window durations in seconds ───────────────────────────────────────────────

WINDOW_SECONDS: Dict[AggregationWindow, float] = {
    AggregationWindow.REAL_TIME:       0.0,
    AggregationWindow.ONE_MINUTE:      60.0,
    AggregationWindow.FIVE_MINUTES:    300.0,
    AggregationWindow.FIFTEEN_MINUTES: 900.0,
    AggregationWindow.THIRTY_MINUTES:  1_800.0,
    AggregationWindow.ONE_HOUR:        3_600.0,
    AggregationWindow.DAILY:           86_400.0,
    AggregationWindow.WEEKLY:          604_800.0,
    AggregationWindow.MONTHLY:         2_592_000.0,
    AggregationWindow.CUSTOM:          0.0,   # set at runtime
}


# ── Trend direction enumeration ───────────────────────────────────────────────

class TrendDirection(str, Enum):
    """Direction of a detected performance trend."""

    UP       = "up"
    DOWN     = "down"
    FLAT     = "flat"
    VOLATILE = "volatile"


# ── Benchmark status enumeration ─────────────────────────────────────────────

class BenchmarkStatus(str, Enum):
    """How a KPI compares to its institutional benchmark."""

    ABOVE_TARGET = "above_target"
    MEETS_TARGET = "meets_target"
    BELOW_TARGET = "below_target"
    NO_DATA      = "no_data"


# ── Performance grade enumeration ────────────────────────────────────────────

class PerformanceGrade(str, Enum):
    """Overall performance grade for a domain."""

    EXCELLENT  = "excellent"    # ≥ 0.90
    GOOD       = "good"         # ≥ 0.75
    ACCEPTABLE = "acceptable"   # ≥ 0.60
    POOR       = "poor"         # ≥ 0.40
    CRITICAL   = "critical"     # < 0.40


GRADE_THRESHOLDS = {
    PerformanceGrade.EXCELLENT:  0.90,
    PerformanceGrade.GOOD:       0.75,
    PerformanceGrade.ACCEPTABLE: 0.60,
    PerformanceGrade.POOR:       0.40,
    PerformanceGrade.CRITICAL:   0.0,
}


def score_to_grade(score: float) -> PerformanceGrade:
    """Convert a normalised score [0, 1] to a PerformanceGrade."""
    if score >= GRADE_THRESHOLDS[PerformanceGrade.EXCELLENT]:
        return PerformanceGrade.EXCELLENT
    if score >= GRADE_THRESHOLDS[PerformanceGrade.GOOD]:
        return PerformanceGrade.GOOD
    if score >= GRADE_THRESHOLDS[PerformanceGrade.ACCEPTABLE]:
        return PerformanceGrade.ACCEPTABLE
    if score >= GRADE_THRESHOLDS[PerformanceGrade.POOR]:
        return PerformanceGrade.POOR
    return PerformanceGrade.CRITICAL


# ── Performance event type enumeration ───────────────────────────────────────

class PerformanceEventType(str, Enum):
    """Domain events emitted by the Performance Analytics Framework."""

    ANALYTICS_STARTED     = "analytics_started"
    KPI_CALCULATED        = "kpi_calculated"
    TREND_DETECTED        = "trend_detected"
    BENCHMARK_COMPLETED   = "benchmark_completed"
    REPORT_GENERATED      = "report_generated"
    ANALYTICS_PUBLISHED   = "analytics_published"
    ANALYTICS_FAILED      = "analytics_failed"


# ── Benchmark thresholds ──────────────────────────────────────────────────────
# (warning, critical, direction: ABOVE means higher is better, BELOW means lower is better)

class _Threshold:
    """Internal benchmark threshold descriptor."""
    __slots__ = ("warning", "critical", "higher_is_better")

    def __init__(self, warning: float, critical: float, higher_is_better: bool = True):
        self.warning          = warning
        self.critical         = critical
        self.higher_is_better = higher_is_better


KPI_BENCHMARKS: Dict[KPIType, _Threshold] = {
    KPIType.EXECUTION_SUCCESS_RATE:   _Threshold(0.95,  0.90,  True),
    KPIType.EXECUTION_FAILURE_RATE:   _Threshold(0.05,  0.10,  False),
    KPIType.AVG_EXECUTION_TIME_MS:    _Threshold(100.0, 500.0, False),
    KPIType.MEDIAN_EXECUTION_TIME_MS: _Threshold(80.0,  400.0, False),
    KPIType.P95_LATENCY_MS:           _Threshold(200.0, 1000.0,False),
    KPIType.P99_LATENCY_MS:           _Threshold(500.0, 2000.0,False),
    KPIType.RECOVERY_SUCCESS_RATE:    _Threshold(0.99,  0.95,  True),
    KPIType.MEAN_TIME_TO_RECOVERY_MS: _Threshold(5000.0,15000.0,False),
    KPIType.GATEWAY_AVAILABILITY:     _Threshold(0.999, 0.99,  True),
    KPIType.BROKER_AVAILABILITY:      _Threshold(0.999, 0.99,  True),
    KPIType.MONITORING_AVAILABILITY:  _Threshold(0.999, 0.99,  True),
    KPIType.SYSTEM_THROUGHPUT:        _Threshold(0.70,  0.50,  True),
    KPIType.QUEUE_EFFICIENCY:         _Threshold(0.80,  0.60,  True),
    KPIType.ORDER_COMPLETION_RATE:    _Threshold(0.95,  0.90,  True),
    KPIType.POSITION_ACCURACY:        _Threshold(0.99,  0.95,  True),
    KPIType.RISK_RULE_EFFECTIVENESS:  _Threshold(0.95,  0.85,  True),
    KPIType.PORTFOLIO_EFFICIENCY:     _Threshold(0.70,  0.50,  True),
    KPIType.STRATEGY_EFFICIENCY:      _Threshold(0.70,  0.50,  True),
    KPIType.RESOURCE_UTILIZATION:     _Threshold(0.85,  0.95,  False),
}
