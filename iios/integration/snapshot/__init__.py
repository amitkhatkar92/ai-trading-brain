"""
__init__.py — iios.integration.snapshot
-----------------------------------------
Public API surface for the Integration Snapshot module.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

# ── Constants ────────────────────────────────────────────────────────────
from .constants import (
    ConnectivityState,
    GovernanceState,
    LifecycleState,
    ProtocolHealth,
    SnapshotEventType,
    SnapshotIntegrationType,
    SnapshotScope,
    SnapshotStatus,
    SnapshotValidationCheck,
    SNAPSHOT_VERSION,
    FRAMEWORK_VERSION,
    SNAPSHOT_ID_PREFIX,
    BUNDLE_ID_PREFIX,
    EVENT_ID_PREFIX,
    ENTRY_ID_PREFIX,
    DEFAULT_SNAPSHOT_TTL_SECONDS,
    DEFAULT_HISTORY_SIZE,
    DEFAULT_CACHE_SIZE,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_MAX_BUNDLE_SIZE,
    DEFAULT_STORE_MAX,
    VALIDATION_CHECK_ORDER,
)

# ── Exceptions ────────────────────────────────────────────────────────────
from .exceptions import (
    IntegrationSnapshotError,
    SnapshotBuildError,
    SnapshotBundleError,
    SnapshotCacheError,
    SnapshotExpiredError,
    SnapshotNotFoundError,
    SnapshotRegistryError,
    SnapshotSerializationError,
    SnapshotStoreError,
    SnapshotValidationError,
    SnapshotVersionError,
)

# ── Core snapshot objects ─────────────────────────────────────────────────
from .integration_snapshot import (
    AdapterSummary,
    AuditSummary,
    ConnectivitySummary,
    ConnectorSummary,
    IntegrationSnapshot,
    ProtocolSummary,
    SecuritySummary,
    ServiceSummary,
    SnapshotStatisticsSummary,
)

# ── Metadata ──────────────────────────────────────────────────────────────
from .integration_snapshot_metadata import SnapshotMetadata

# ── Builder ───────────────────────────────────────────────────────────────
from .integration_snapshot_builder import IntegrationSnapshotBuilder

# ── Factory ───────────────────────────────────────────────────────────────
from .integration_snapshot_factory import IntegrationSnapshotFactory

# ── Validation ────────────────────────────────────────────────────────────
from .integration_snapshot_validation import (
    IntegrationSnapshotValidation,
    SnapshotValidationIssue,
    SnapshotValidationReport,
)

# ── Registry ──────────────────────────────────────────────────────────────
from .integration_snapshot_registry import IntegrationSnapshotRegistry

# ── Store ─────────────────────────────────────────────────────────────────
from .integration_snapshot_store import IntegrationSnapshotStore

# ── Cache ─────────────────────────────────────────────────────────────────
from .integration_snapshot_cache import (
    CacheStats,
    IntegrationSnapshotCache,
)

# ── History ───────────────────────────────────────────────────────────────
from .integration_snapshot_history import (
    IntegrationSnapshotHistory,
    SnapshotHistoryEntry,
    SnapshotHistoryReport,
)

# ── Statistics ────────────────────────────────────────────────────────────
from .integration_snapshot_statistics import (
    IntegrationSnapshotStatistics,
    SnapshotStatisticsReport,
)

# ── Events ────────────────────────────────────────────────────────────────
from .integration_snapshot_events import (
    IntegrationSnapshotEventBus,
    SnapshotEvent,
)

# ── Bundle ────────────────────────────────────────────────────────────────
from .integration_snapshot_bundle import (
    BundleEntry,
    IntegrationSnapshotBundle,
)

# ── Public API surface ────────────────────────────────────────────────────
__all__: list = [
    # Constants — enums
    "ConnectivityState",
    "GovernanceState",
    "LifecycleState",
    "ProtocolHealth",
    "SnapshotEventType",
    "SnapshotIntegrationType",
    "SnapshotScope",
    "SnapshotStatus",
    "SnapshotValidationCheck",
    # Constants — scalars
    "SNAPSHOT_VERSION",
    "FRAMEWORK_VERSION",
    "SNAPSHOT_ID_PREFIX",
    "BUNDLE_ID_PREFIX",
    "EVENT_ID_PREFIX",
    "ENTRY_ID_PREFIX",
    "DEFAULT_SNAPSHOT_TTL_SECONDS",
    "DEFAULT_HISTORY_SIZE",
    "DEFAULT_CACHE_SIZE",
    "DEFAULT_CACHE_TTL_SECONDS",
    "DEFAULT_MAX_BUNDLE_SIZE",
    "DEFAULT_STORE_MAX",
    "VALIDATION_CHECK_ORDER",
    # Exceptions
    "IntegrationSnapshotError",
    "SnapshotBuildError",
    "SnapshotBundleError",
    "SnapshotCacheError",
    "SnapshotExpiredError",
    "SnapshotNotFoundError",
    "SnapshotRegistryError",
    "SnapshotSerializationError",
    "SnapshotStoreError",
    "SnapshotValidationError",
    "SnapshotVersionError",
    # Core snapshot
    "AdapterSummary",
    "AuditSummary",
    "ConnectivitySummary",
    "ConnectorSummary",
    "IntegrationSnapshot",
    "ProtocolSummary",
    "SecuritySummary",
    "ServiceSummary",
    "SnapshotStatisticsSummary",
    # Metadata
    "SnapshotMetadata",
    # Builder
    "IntegrationSnapshotBuilder",
    # Factory
    "IntegrationSnapshotFactory",
    # Validation
    "IntegrationSnapshotValidation",
    "SnapshotValidationIssue",
    "SnapshotValidationReport",
    # Registry
    "IntegrationSnapshotRegistry",
    # Store
    "IntegrationSnapshotStore",
    # Cache
    "CacheStats",
    "IntegrationSnapshotCache",
    # History
    "IntegrationSnapshotHistory",
    "SnapshotHistoryEntry",
    "SnapshotHistoryReport",
    # Statistics
    "IntegrationSnapshotStatistics",
    "SnapshotStatisticsReport",
    # Events
    "IntegrationSnapshotEventBus",
    "SnapshotEvent",
    # Bundle
    "BundleEntry",
    "IntegrationSnapshotBundle",
]
