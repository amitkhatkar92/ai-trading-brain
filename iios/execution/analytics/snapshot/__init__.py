"""
iios/execution/analytics/snapshot/__init__.py
=============================================
Public API for the Execution Analytics Snapshot package (C8 M5).

Primary published object: ExecutionAnalyticsSnapshot

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""

# Primary published object
from .execution_analytics_snapshot import (
    ExecutionAnalyticsSnapshot,
    PerformanceSummary,
    PerformanceKPIs,
    PerformanceScorecard,
    TrendSummary,
    BenchmarkSummary,
    HistoricalSummary,
    PredictionSummary,
    SnapshotForecastSummary,
    ConfidenceSummary,
    SnapshotCapacityForecast,
    SnapshotRiskForecast,
    SnapshotAnalyticsStatistics,
)

# Builder and factory
from .analytics_snapshot_builder import AnalyticsSnapshotBuilder
from .analytics_snapshot_factory import AnalyticsSnapshotFactory

# Store, cache, registry, history
from .analytics_snapshot_store import AnalyticsSnapshotStore
from .analytics_snapshot_cache import AnalyticsSnapshotCache
from .analytics_snapshot_registry import AnalyticsSnapshotRegistry
from .analytics_snapshot_history import AnalyticsSnapshotHistory

# Validation
from .analytics_snapshot_validation import (
    AnalyticsSnapshotValidator,
    SnapshotValidationResult,
)

# Statistics
from .analytics_snapshot_statistics import AnalyticsSnapshotStatistics

# Events
from .analytics_snapshot_events import (
    AnalyticsSnapshotEvent,
    make_snapshot_created_event,
    make_snapshot_validated_event,
    make_snapshot_published_event,
    make_snapshot_archived_event,
    make_snapshot_retrieved_event,
    make_snapshot_cached_event,
)

# Metadata
from .analytics_snapshot_metadata import AnalyticsMetadata, AuditMetadata

# Bundle
from .analytics_snapshot_bundle import AnalyticsSnapshotBundle, make_snapshot_bundle

# Constants (re-exported for downstream callers)
from .constants import (
    AnalyticsScope,
    AnalyticsMode,
    AnalyticsStatus,
    AnalyticsHealth,
    SnapshotLifecycleState,
    SnapshotEventType,
    SNAPSHOT_ENGINE_ID,
    BUILDER_SYSTEM_ID,
    STORE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    CACHE_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    DEFAULT_MAX_SNAPSHOTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_CACHE_SIZE,
    DEFAULT_SNAPSHOT_TTL,
    SNAPSHOT_FRAMEWORK_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    health_from_score,
)

# Exceptions
from .exceptions import (
    SnapshotError,
    SnapshotValidationError,
    SnapshotNotFoundError,
    SnapshotBuildError,
    SnapshotDuplicateError,
    SnapshotStoreError,
    SnapshotRegistryError,
    SnapshotEngineNotRunningError,
)

__all__ = [
    # Primary
    "ExecutionAnalyticsSnapshot",
    # Summary types
    "PerformanceSummary",
    "PerformanceKPIs",
    "PerformanceScorecard",
    "TrendSummary",
    "BenchmarkSummary",
    "HistoricalSummary",
    "PredictionSummary",
    "SnapshotForecastSummary",
    "ConfidenceSummary",
    "SnapshotCapacityForecast",
    "SnapshotRiskForecast",
    "SnapshotAnalyticsStatistics",
    # Infrastructure
    "AnalyticsSnapshotBuilder",
    "AnalyticsSnapshotFactory",
    "AnalyticsSnapshotStore",
    "AnalyticsSnapshotCache",
    "AnalyticsSnapshotRegistry",
    "AnalyticsSnapshotHistory",
    # Validation
    "AnalyticsSnapshotValidator",
    "SnapshotValidationResult",
    # Statistics
    "AnalyticsSnapshotStatistics",
    # Events
    "AnalyticsSnapshotEvent",
    "make_snapshot_created_event",
    "make_snapshot_validated_event",
    "make_snapshot_published_event",
    "make_snapshot_archived_event",
    "make_snapshot_retrieved_event",
    "make_snapshot_cached_event",
    # Metadata
    "AnalyticsMetadata",
    "AuditMetadata",
    # Bundle
    "AnalyticsSnapshotBundle",
    "make_snapshot_bundle",
    # Constants
    "AnalyticsScope",
    "AnalyticsMode",
    "AnalyticsStatus",
    "AnalyticsHealth",
    "SnapshotLifecycleState",
    "SnapshotEventType",
    "SNAPSHOT_ENGINE_ID",
    "BUILDER_SYSTEM_ID",
    "STORE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "CACHE_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "DEFAULT_MAX_SNAPSHOTS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_CACHE_SIZE",
    "DEFAULT_SNAPSHOT_TTL",
    "SNAPSHOT_FRAMEWORK_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "health_from_score",
    # Exceptions
    "SnapshotError",
    "SnapshotValidationError",
    "SnapshotNotFoundError",
    "SnapshotBuildError",
    "SnapshotDuplicateError",
    "SnapshotStoreError",
    "SnapshotRegistryError",
    "SnapshotEngineNotRunningError",
]
