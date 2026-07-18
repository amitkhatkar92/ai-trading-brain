"""
iios/execution/analytics/performance/__init__.py
================================================
Public API for the Institutional Performance Analytics Framework (C8 M3).

Primary entry point: PerformanceAnalyticsEngine

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""

# Primary public interface
from .performance_analytics_engine import PerformanceAnalyticsEngine

# Request / Context / Response types
from .performance_request import PerformanceRequest, make_performance_request
from .performance_context import PerformanceContext, make_performance_context
from .performance_response import (
    PerformanceAnalyticsReport,
    PerformanceSnapshot,
    TrendAnalysis,
    BenchmarkReport,
    BenchmarkComparison,
    PerformanceScorecard,
    make_performance_snapshot,
)

# KPI types
from .performance_kpi import (
    KPIValue,
    KPIReport,
    make_kpi_value,
    make_kpi_report,
    KPI_UNITS,
)

# Constants
from .constants import (
    PerformanceDomain,
    KPIType,
    AggregationWindow,
    TrendDirection,
    BenchmarkStatus,
    PerformanceGrade,
    PerformanceEventType,
    WINDOW_SECONDS,
    KPI_BENCHMARKS,
    GRADE_THRESHOLDS,
    score_to_grade,
    ENGINE_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    CALC_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
)

# Exceptions
from .exceptions import (
    PerformanceAnalyticsError,
    PerformanceEngineNotRunningError,
    PerformanceRequestNotFoundError,
    PerformanceCalculationError,
    PerformanceValidationError,
    PerformanceDataInsufficientError,
    PerformanceBenchmarkError,
    PerformanceTrendError,
    PerformanceAggregationError,
)

# Supporting components (for DI / testing)
from .performance_collector import PerformanceCollector, CollectedData
from .performance_calculator import PerformanceCalculator
from .performance_aggregator import PerformanceAggregator
from .performance_benchmark import PerformanceBenchmark
from .performance_trend_analyzer import PerformanceTrendAnalyzer
from .performance_scorecard import PerformanceScorecardBuilder
from .performance_validation import PerformanceValidator, PerformanceValidationResult
from .performance_statistics import PerformanceAnalyticsStatistics
from .performance_history import PerformanceAnalyticsHistory
from .performance_events import (
    PerformanceAnalyticsEvent,
    make_analytics_started_event,
    make_kpi_calculated_event,
    make_trend_detected_event,
    make_benchmark_completed_event,
    make_report_generated_event,
    make_analytics_published_event,
    make_analytics_failed_event,
)
from .performance_factory import PerformanceAnalyticsFactory
from .performance_registry import PerformanceAnalyticsRegistry
from .performance_manager import PerformanceManager

__all__ = [
    # Primary interface
    "PerformanceAnalyticsEngine",
    # Request / Context / Response
    "PerformanceRequest",
    "make_performance_request",
    "PerformanceContext",
    "make_performance_context",
    "PerformanceAnalyticsReport",
    "PerformanceSnapshot",
    "TrendAnalysis",
    "BenchmarkReport",
    "BenchmarkComparison",
    "PerformanceScorecard",
    "make_performance_snapshot",
    # KPI
    "KPIValue",
    "KPIReport",
    "make_kpi_value",
    "make_kpi_report",
    "KPI_UNITS",
    # Constants
    "PerformanceDomain",
    "KPIType",
    "AggregationWindow",
    "TrendDirection",
    "BenchmarkStatus",
    "PerformanceGrade",
    "PerformanceEventType",
    "WINDOW_SECONDS",
    "KPI_BENCHMARKS",
    "GRADE_THRESHOLDS",
    "score_to_grade",
    "ENGINE_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "CALC_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    # Exceptions
    "PerformanceAnalyticsError",
    "PerformanceEngineNotRunningError",
    "PerformanceRequestNotFoundError",
    "PerformanceCalculationError",
    "PerformanceValidationError",
    "PerformanceDataInsufficientError",
    "PerformanceBenchmarkError",
    "PerformanceTrendError",
    "PerformanceAggregationError",
    # Supporting components
    "PerformanceCollector",
    "CollectedData",
    "PerformanceCalculator",
    "PerformanceAggregator",
    "PerformanceBenchmark",
    "PerformanceTrendAnalyzer",
    "PerformanceScorecardBuilder",
    "PerformanceValidator",
    "PerformanceValidationResult",
    "PerformanceAnalyticsStatistics",
    "PerformanceAnalyticsHistory",
    "PerformanceAnalyticsEvent",
    "make_analytics_started_event",
    "make_kpi_calculated_event",
    "make_trend_detected_event",
    "make_benchmark_completed_event",
    "make_report_generated_event",
    "make_analytics_published_event",
    "make_analytics_failed_event",
    "PerformanceAnalyticsFactory",
    "PerformanceAnalyticsRegistry",
    "PerformanceManager",
]
