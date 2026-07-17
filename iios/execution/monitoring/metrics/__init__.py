"""iios/execution/monitoring/metrics/__init__.py
==================================================
Public API for the Execution Metrics Framework.

C6 Execution Intelligence — Phase 6, Module 3
"""
from .constants import (
    AggregationType,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POINTS,
    DEFAULT_MAX_SERIES,
    ENGINE_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    METRIC_CATEGORY,
    METRIC_DEFAULT_AGGREGATION,
    MetricCategory,
    MetricType,
    MetricsEventType,
    REGISTRY_SYSTEM_ID,
    SCHEMA_VERSION,
    VERSION,
    WINDOW_SECONDS,
    WindowSize,
)
from .exceptions import (
    InsufficientDataError,
    MetricAggregationError,
    MetricCalculationError,
    MetricSeriesNotFoundError,
    MetricsEngineNotRunningError,
    MetricsFrameworkError,
    MetricsRegistryCapacityError,
    MetricsSnapshotError,
    MetricsValidationError,
)
from .metrics_context import MetricsContext, make_metrics_context
from .metrics_events import (
    MetricsEvent,
    make_aggregation_completed,
    make_calculation_failed,
    make_metrics_aggregated,
    make_metrics_calculated,
    make_metrics_collected,
    make_metrics_published,
)
from .metrics_factory import MetricsFactory
from .metrics_history import MetricsHistory
from .metrics_request import MetricsRequest, make_metrics_request
from .metrics_response import MetricsResponse, make_metrics_response
from .metrics_snapshot import MetricsSnapshot, make_metrics_snapshot
from .metrics_statistics import MetricsStatistics
from .metrics_validation import MetricsValidator, ValidationResult
from .metrics_calculator import MetricsCalculator
from .metrics_collector import MetricPoint, MetricsCollector
from .metrics_aggregator import MetricsAggregator
from .metrics_registry import MetricsRegistry
from .metrics_manager import MetricsManager
from .metrics_engine import MetricsEngine

__all__ = [
    # Constants
    "AggregationType",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_POINTS",
    "DEFAULT_MAX_SERIES",
    "ENGINE_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "METRIC_CATEGORY",
    "METRIC_DEFAULT_AGGREGATION",
    "MetricCategory",
    "MetricType",
    "MetricsEventType",
    "REGISTRY_SYSTEM_ID",
    "SCHEMA_VERSION",
    "VERSION",
    "WINDOW_SECONDS",
    "WindowSize",
    # Exceptions
    "InsufficientDataError",
    "MetricAggregationError",
    "MetricCalculationError",
    "MetricSeriesNotFoundError",
    "MetricsEngineNotRunningError",
    "MetricsFrameworkError",
    "MetricsRegistryCapacityError",
    "MetricsSnapshotError",
    "MetricsValidationError",
    # Context
    "MetricsContext",
    "make_metrics_context",
    # Events
    "MetricsEvent",
    "make_aggregation_completed",
    "make_calculation_failed",
    "make_metrics_aggregated",
    "make_metrics_calculated",
    "make_metrics_collected",
    "make_metrics_published",
    # Request / Response / Snapshot
    "MetricsRequest",
    "make_metrics_request",
    "MetricsResponse",
    "make_metrics_response",
    "MetricsSnapshot",
    "make_metrics_snapshot",
    # Stats / History / Validation
    "MetricsStatistics",
    "MetricsHistory",
    "MetricsValidator",
    "ValidationResult",
    # Calculation / Collection / Aggregation
    "MetricPoint",
    "MetricsCalculator",
    "MetricsCollector",
    "MetricsAggregator",
    # Infrastructure
    "MetricsRegistry",
    "MetricsFactory",
    "MetricsManager",
    # Primary API
    "MetricsEngine",
]
