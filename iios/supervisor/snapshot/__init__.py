"""
__init__.py — iios.supervisor.snapshot
----------------------------------------
Public API for the AI Supervisor Snapshot.

Every downstream subsystem MUST consume SupervisorSnapshot instead of
directly accessing the AI Supervisor Engine, Governance Policy Framework,
or Autonomous Governance Framework.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

# --- Constants & enumerations ---
from .constants import (
    SUPERVISOR_SNAPSHOT_SYSTEM_ID,
    BUILDER_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    STORE_SYSTEM_ID,
    CACHE_SYSTEM_ID,
    BUNDLE_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    PLATFORM_VERSION,
    PLATFORM_DEPENDENCIES,
    DEFAULT_MAX_SNAPSHOTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_CACHE_TTL_S,
    DEFAULT_CACHE_MAX_SIZE,
    DEFAULT_BUILD_TIMEOUT_S,
    HEALTH_OPTIMAL_THRESHOLD,
    HEALTH_NORMAL_THRESHOLD,
    HEALTH_DEGRADED_THRESHOLD,
    HEALTH_CRITICAL_THRESHOLD,
    SnapshotStatus,
    SupervisorScope,
    SupervisorType,
    SnapshotLifecycleState,
    SnapshotGovernanceState,
    SnapshotEnterpriseState,
    OperationalStatus,
    GovernanceStatus,
    PlatformStatus,
    SubsystemSummaryStatus,
    AutomationReadiness,
    SnapshotEventType,
    SnapshotValidationCode,
)

# --- Exceptions ---
from .exceptions import (
    SupervisorSnapshotError,
    SupervisorSnapshotNotFoundError,
    SupervisorSnapshotValidationError,
    SupervisorSnapshotBuildError,
    SupervisorSnapshotRegistryError,
    SupervisorSnapshotCapacityError,
    SupervisorSnapshotStoreError,
    SupervisorSnapshotCacheError,
    SupervisorSnapshotBundleError,
)

# --- Metadata ---
from .supervisor_snapshot_metadata import SupervisorSnapshotMetadata

# --- Core snapshot & sections ---
from .supervisor_snapshot import (
    AnomalySummary,
    AuditSummary,
    DependencySummary,
    EnterpriseSummary,
    GovernanceSummary,
    SelfHealingSummary,
    SnapshotStatistics,
    SubsystemSummaryItem,
    SubsystemsSummary,
    SupervisionSummary,
    SupervisorSnapshot,
)

# --- Builder ---
from .supervisor_snapshot_builder import SupervisorSnapshotBuilder

# --- Validation ---
from .supervisor_snapshot_validation import (
    SnapshotValidationCheckResult,
    SupervisorSnapshotValidationResult,
    SupervisorSnapshotValidator,
)

# --- Factory ---
from .supervisor_snapshot_factory import SupervisorSnapshotFactory

# --- Registry ---
from .supervisor_snapshot_registry import SupervisorSnapshotRegistry

# --- Cache ---
from .supervisor_snapshot_cache import SupervisorSnapshotCache

# --- Store ---
from .supervisor_snapshot_store import SupervisorSnapshotStore

# --- History ---
from .supervisor_snapshot_history import SupervisorSnapshotHistory

# --- Statistics ---
from .supervisor_snapshot_statistics import SupervisorSnapshotStatistics

# --- Events ---
from .supervisor_snapshot_events import (
    SupervisorSnapshotEvent,
    make_snapshot_started_event,
    make_snapshot_built_event,
    make_snapshot_validated_event,
    make_snapshot_published_event,
    make_snapshot_registered_event,
    make_snapshot_retrieved_event,
    make_snapshot_invalidated_event,
    make_snapshot_cached_event,
    make_snapshot_expired_event,
    make_snapshot_archived_event,
    make_bundle_created_event,
    make_store_saved_event,
)

# --- Bundle ---
from .supervisor_snapshot_bundle import (
    SupervisorSnapshotBundle,
    SupervisorSnapshotBundleBuilder,
)

__all__ = [
    # Constants & enumerations
    "SUPERVISOR_SNAPSHOT_SYSTEM_ID",
    "BUILDER_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "STORE_SYSTEM_ID",
    "CACHE_SYSTEM_ID",
    "BUNDLE_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "PLATFORM_VERSION",
    "PLATFORM_DEPENDENCIES",
    "DEFAULT_MAX_SNAPSHOTS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_CACHE_TTL_S",
    "DEFAULT_CACHE_MAX_SIZE",
    "DEFAULT_BUILD_TIMEOUT_S",
    "HEALTH_OPTIMAL_THRESHOLD",
    "HEALTH_NORMAL_THRESHOLD",
    "HEALTH_DEGRADED_THRESHOLD",
    "HEALTH_CRITICAL_THRESHOLD",
    "SnapshotStatus",
    "SupervisorScope",
    "SupervisorType",
    "SnapshotLifecycleState",
    "SnapshotGovernanceState",
    "SnapshotEnterpriseState",
    "OperationalStatus",
    "GovernanceStatus",
    "PlatformStatus",
    "SubsystemSummaryStatus",
    "AutomationReadiness",
    "SnapshotEventType",
    "SnapshotValidationCode",
    # Exceptions
    "SupervisorSnapshotError",
    "SupervisorSnapshotNotFoundError",
    "SupervisorSnapshotValidationError",
    "SupervisorSnapshotBuildError",
    "SupervisorSnapshotRegistryError",
    "SupervisorSnapshotCapacityError",
    "SupervisorSnapshotStoreError",
    "SupervisorSnapshotCacheError",
    "SupervisorSnapshotBundleError",
    # Metadata
    "SupervisorSnapshotMetadata",
    # Core snapshot & sections
    "AnomalySummary",
    "AuditSummary",
    "DependencySummary",
    "EnterpriseSummary",
    "GovernanceSummary",
    "SelfHealingSummary",
    "SnapshotStatistics",
    "SubsystemSummaryItem",
    "SubsystemsSummary",
    "SupervisionSummary",
    "SupervisorSnapshot",
    # Builder
    "SupervisorSnapshotBuilder",
    # Validation
    "SnapshotValidationCheckResult",
    "SupervisorSnapshotValidationResult",
    "SupervisorSnapshotValidator",
    # Factory
    "SupervisorSnapshotFactory",
    # Registry
    "SupervisorSnapshotRegistry",
    # Cache
    "SupervisorSnapshotCache",
    # Store
    "SupervisorSnapshotStore",
    # History
    "SupervisorSnapshotHistory",
    # Statistics
    "SupervisorSnapshotStatistics",
    # Events
    "SupervisorSnapshotEvent",
    "make_snapshot_started_event",
    "make_snapshot_built_event",
    "make_snapshot_validated_event",
    "make_snapshot_published_event",
    "make_snapshot_registered_event",
    "make_snapshot_retrieved_event",
    "make_snapshot_invalidated_event",
    "make_snapshot_cached_event",
    "make_snapshot_expired_event",
    "make_snapshot_archived_event",
    "make_bundle_created_event",
    "make_store_saved_event",
    # Bundle
    "SupervisorSnapshotBundle",
    "SupervisorSnapshotBundleBuilder",
]
