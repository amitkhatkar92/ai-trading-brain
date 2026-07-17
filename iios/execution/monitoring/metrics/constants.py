"""iios/execution/monitoring/metrics/constants.py
==================================================
Constants, enumerations, and configuration for the IIOS
Execution Metrics Framework.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

ENGINE_SYSTEM_ID    = "iios:execution:monitoring:metrics:engine"
MANAGER_SYSTEM_ID   = "iios:execution:monitoring:metrics:manager"
REGISTRY_SYSTEM_ID  = "iios:execution:monitoring:metrics:registry"
FACTORY_SYSTEM_ID   = "iios:execution:monitoring:metrics:factory"
COLLECTOR_SYSTEM_ID = "iios:execution:monitoring:metrics:collector"

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_HISTORY    = 1_000
DEFAULT_MAX_POINTS     = 10_000   # per MetricSeries
DEFAULT_MAX_SERIES     = 50_000

WINDOW_SECONDS: dict = {
    "1m":   60,
    "5m":   300,
    "15m":  900,
    "1h":   3_600,
    "1d":   86_400,
    "session": 0,   # entire session — treated as unbounded
    "custom":  0,   # caller supplies from_ts / to_ts
}


# ── Metric types ──────────────────────────────────────────────────────────────

class MetricType(str, Enum):
    # Execution performance
    EXECUTION_COUNT          = "execution_count"
    SUCCESS_RATE             = "success_rate"
    FAILURE_RATE             = "failure_rate"
    CANCELLATION_RATE        = "cancellation_rate"
    RETRY_RATE               = "retry_rate"
    TIMEOUT_RATE             = "timeout_rate"
    # Latency
    AVERAGE_EXECUTION_TIME   = "average_execution_time"
    MEDIAN_EXECUTION_TIME    = "median_execution_time"
    P95_LATENCY              = "p95_latency"
    P99_LATENCY              = "p99_latency"
    MAX_LATENCY              = "max_latency"
    MIN_LATENCY              = "min_latency"
    # Queue
    QUEUE_WAIT_TIME          = "queue_wait_time"
    # Dispatch / routing
    DISPATCH_TIME            = "dispatch_time"
    # Broker / gateway
    BROKER_UTILIZATION       = "broker_utilization"
    GATEWAY_THROUGHPUT       = "gateway_throughput"
    # Monitoring
    MONITORING_CYCLE_TIME    = "monitoring_cycle_time"


# ── Metric categories ─────────────────────────────────────────────────────────

class MetricCategory(str, Enum):
    EXECUTION_PERFORMANCE = "execution_performance"
    GATEWAY_PERFORMANCE   = "gateway_performance"
    BROKER_PERFORMANCE    = "broker_performance"
    QUEUE_PERFORMANCE     = "queue_performance"
    LATENCY               = "latency"
    RELIABILITY           = "reliability"
    AVAILABILITY          = "availability"
    THROUGHPUT            = "throughput"
    RISK_METRICS          = "risk_metrics"
    SESSION_METRICS       = "session_metrics"


# ── Metric → category mapping ─────────────────────────────────────────────────

METRIC_CATEGORY: dict = {
    MetricType.EXECUTION_COUNT:        MetricCategory.EXECUTION_PERFORMANCE,
    MetricType.SUCCESS_RATE:           MetricCategory.RELIABILITY,
    MetricType.FAILURE_RATE:           MetricCategory.RELIABILITY,
    MetricType.CANCELLATION_RATE:      MetricCategory.RELIABILITY,
    MetricType.RETRY_RATE:             MetricCategory.RELIABILITY,
    MetricType.TIMEOUT_RATE:           MetricCategory.RELIABILITY,
    MetricType.AVERAGE_EXECUTION_TIME: MetricCategory.LATENCY,
    MetricType.MEDIAN_EXECUTION_TIME:  MetricCategory.LATENCY,
    MetricType.P95_LATENCY:            MetricCategory.LATENCY,
    MetricType.P99_LATENCY:            MetricCategory.LATENCY,
    MetricType.MAX_LATENCY:            MetricCategory.LATENCY,
    MetricType.MIN_LATENCY:            MetricCategory.LATENCY,
    MetricType.QUEUE_WAIT_TIME:        MetricCategory.QUEUE_PERFORMANCE,
    MetricType.DISPATCH_TIME:          MetricCategory.GATEWAY_PERFORMANCE,
    MetricType.BROKER_UTILIZATION:     MetricCategory.BROKER_PERFORMANCE,
    MetricType.GATEWAY_THROUGHPUT:     MetricCategory.THROUGHPUT,
    MetricType.MONITORING_CYCLE_TIME:  MetricCategory.SESSION_METRICS,
}


# ── Window sizes ──────────────────────────────────────────────────────────────

class WindowSize(str, Enum):
    ONE_MINUTE      = "1m"
    FIVE_MINUTES    = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR        = "1h"
    DAILY           = "1d"
    SESSION         = "session"
    CUSTOM          = "custom"


# ── Aggregation types ─────────────────────────────────────────────────────────

class AggregationType(str, Enum):
    SUM     = "sum"
    AVERAGE = "average"
    MEDIAN  = "median"
    MIN     = "min"
    MAX     = "max"
    COUNT   = "count"
    RATE    = "rate"
    P95     = "p95"
    P99     = "p99"
    STD_DEV = "std_dev"


# ── Default aggregation per metric type ───────────────────────────────────────

METRIC_DEFAULT_AGGREGATION: dict = {
    MetricType.EXECUTION_COUNT:        AggregationType.COUNT,
    MetricType.SUCCESS_RATE:           AggregationType.AVERAGE,
    MetricType.FAILURE_RATE:           AggregationType.AVERAGE,
    MetricType.CANCELLATION_RATE:      AggregationType.AVERAGE,
    MetricType.RETRY_RATE:             AggregationType.AVERAGE,
    MetricType.TIMEOUT_RATE:           AggregationType.AVERAGE,
    MetricType.AVERAGE_EXECUTION_TIME: AggregationType.AVERAGE,
    MetricType.MEDIAN_EXECUTION_TIME:  AggregationType.MEDIAN,
    MetricType.P95_LATENCY:            AggregationType.P95,
    MetricType.P99_LATENCY:            AggregationType.P99,
    MetricType.MAX_LATENCY:            AggregationType.MAX,
    MetricType.MIN_LATENCY:            AggregationType.MIN,
    MetricType.QUEUE_WAIT_TIME:        AggregationType.AVERAGE,
    MetricType.DISPATCH_TIME:          AggregationType.AVERAGE,
    MetricType.BROKER_UTILIZATION:     AggregationType.AVERAGE,
    MetricType.GATEWAY_THROUGHPUT:     AggregationType.SUM,
    MetricType.MONITORING_CYCLE_TIME:  AggregationType.AVERAGE,
}


# ── Event types ───────────────────────────────────────────────────────────────

class MetricsEventType(str, Enum):
    METRICS_COLLECTED      = "METRICS_COLLECTED"
    METRICS_CALCULATED     = "METRICS_CALCULATED"
    METRICS_AGGREGATED     = "METRICS_AGGREGATED"
    METRICS_PUBLISHED      = "METRICS_PUBLISHED"
    CALCULATION_FAILED     = "CALCULATION_FAILED"
    AGGREGATION_COMPLETED  = "AGGREGATION_COMPLETED"
