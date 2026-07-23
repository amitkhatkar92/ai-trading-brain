"""
iios.market.snapshot — Market Snapshot subsystem
=================================================
C12 Market Intelligence — Phase 1, Module 5

The Market Snapshot is the ONLY published representation of the complete
Market Intelligence subsystem.  Every downstream subsystem MUST consume
:class:`MarketSnapshot` instead of directly accessing the Market Engine,
Policy Framework, or Analytics Framework.

Public API
----------
Primary object
    MarketSnapshot             — immutable published representation

Sections (all frozen)
    MarketSummary
    RegimeSummary
    TrendSummary
    SectorSummary
    BreadthSummary
    VolatilitySummary
    LiquiditySummary
    CorrelationSummary
    ForecastSummary
    SystemHealth
    AuditInfo
    SnapshotStats
    SnapshotMetadata

Construction
    MarketSnapshotBuilder      — fluent builder
    MarketSnapshotFactory      — factory from component dicts

Infrastructure
    MarketSnapshotRegistry     — thread-safe in-memory registry
    MarketSnapshotStore        — thread-safe in-memory store
    MarketSnapshotCache        — TTL cache for fast retrieval
    MarketSnapshotHistory      — bounded ring-buffer history
    MarketSnapshotStatistics   — thread-safe statistics

Bundle
    MarketSnapshotBundle       — immutable ordered collection
    MarketSnapshotBundleBuilder — fluent bundle builder

Validation
    MarketSnapshotValidation   — 7-check validator
    SnapshotValidationResult
    SnapshotCheckResult

Events
    MarketSnapshotEvent
    snapshot_created_event, snapshot_built_event,
    snapshot_validated_event, snapshot_published_event,
    snapshot_invalidated_event, snapshot_archived_event,
    snapshot_expired_event, snapshot_retrieved_event,
    snapshot_updated_event, snapshot_failed_event

Exceptions
    MarketSnapshotError
    MarketSnapshotNotFoundError
    MarketSnapshotValidationError
    MarketSnapshotBuilderError
    MarketSnapshotRegistryError
    MarketSnapshotStoreError
    MarketSnapshotCapacityError
    MarketSnapshotPublishError
    MarketSnapshotSerializationError
    MarketSnapshotBundleError

Enumerations
    SnapshotStatus, SnapshotEventType, SnapshotValidationCode,
    HealthStatus, SnapshotIntegrity
"""

from .constants import (
    SNAPSHOT_SYSTEM_ID,
    VERSION,
    HealthStatus,
    SnapshotEventType,
    SnapshotIntegrity,
    SnapshotStatus,
    SnapshotValidationCode,
)
from .exceptions import (
    MarketSnapshotBundleError,
    MarketSnapshotBuilderError,
    MarketSnapshotCapacityError,
    MarketSnapshotError,
    MarketSnapshotNotFoundError,
    MarketSnapshotPublishError,
    MarketSnapshotRegistryError,
    MarketSnapshotSerializationError,
    MarketSnapshotStoreError,
    MarketSnapshotValidationError,
)
from .market_snapshot import (
    AuditInfo,
    BreadthSummary,
    CorrelationSummary,
    ForecastSummary,
    LiquiditySummary,
    MarketSnapshot,
    MarketSummary,
    RegimeSummary,
    SectorSummary,
    SnapshotStats,
    SystemHealth,
    TrendSummary,
    VolatilitySummary,
)
from .market_snapshot_builder import MarketSnapshotBuilder
from .market_snapshot_bundle import MarketSnapshotBundle, MarketSnapshotBundleBuilder
from .market_snapshot_cache import MarketSnapshotCache
from .market_snapshot_events import (
    MarketSnapshotEvent,
    snapshot_archived_event,
    snapshot_built_event,
    snapshot_created_event,
    snapshot_expired_event,
    snapshot_failed_event,
    snapshot_invalidated_event,
    snapshot_published_event,
    snapshot_retrieved_event,
    snapshot_updated_event,
    snapshot_validated_event,
)
from .market_snapshot_factory import MarketSnapshotFactory
from .market_snapshot_history import MarketSnapshotHistory
from .market_snapshot_metadata import SnapshotMetadata
from .market_snapshot_registry import MarketSnapshotRegistry
from .market_snapshot_statistics import MarketSnapshotStatistics
from .market_snapshot_store import MarketSnapshotStore
from .market_snapshot_validation import (
    MarketSnapshotValidation,
    SnapshotCheckResult,
    SnapshotValidationResult,
)

__all__ = [
    # Version
    "VERSION",
    "SNAPSHOT_SYSTEM_ID",
    # Primary object
    "MarketSnapshot",
    # Section objects
    "MarketSummary",
    "RegimeSummary",
    "TrendSummary",
    "SectorSummary",
    "BreadthSummary",
    "VolatilitySummary",
    "LiquiditySummary",
    "CorrelationSummary",
    "ForecastSummary",
    "SystemHealth",
    "AuditInfo",
    "SnapshotStats",
    "SnapshotMetadata",
    # Construction
    "MarketSnapshotBuilder",
    "MarketSnapshotFactory",
    # Infrastructure
    "MarketSnapshotRegistry",
    "MarketSnapshotStore",
    "MarketSnapshotCache",
    "MarketSnapshotHistory",
    "MarketSnapshotStatistics",
    # Bundle
    "MarketSnapshotBundle",
    "MarketSnapshotBundleBuilder",
    # Validation
    "MarketSnapshotValidation",
    "SnapshotValidationResult",
    "SnapshotCheckResult",
    # Events
    "MarketSnapshotEvent",
    "snapshot_created_event",
    "snapshot_built_event",
    "snapshot_validated_event",
    "snapshot_published_event",
    "snapshot_invalidated_event",
    "snapshot_archived_event",
    "snapshot_expired_event",
    "snapshot_retrieved_event",
    "snapshot_updated_event",
    "snapshot_failed_event",
    # Exceptions
    "MarketSnapshotError",
    "MarketSnapshotNotFoundError",
    "MarketSnapshotValidationError",
    "MarketSnapshotBuilderError",
    "MarketSnapshotRegistryError",
    "MarketSnapshotStoreError",
    "MarketSnapshotCapacityError",
    "MarketSnapshotPublishError",
    "MarketSnapshotSerializationError",
    "MarketSnapshotBundleError",
    # Enumerations
    "SnapshotStatus",
    "SnapshotEventType",
    "SnapshotValidationCode",
    "HealthStatus",
    "SnapshotIntegrity",
]
