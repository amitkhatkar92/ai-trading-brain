"""
iios.workflow.snapshot — C16 M5: Workflow Snapshot

Public API — all symbols that external code should import are exported here.

The WorkflowSnapshot is the ONLY published representation of Enterprise
Workflow & Process Orchestration.  All downstream IIOS components MUST
consume WorkflowSnapshot rather than directly accessing M1-M4 internals.
"""
from .constants import (
    ACTOR_BUILDER,
    ACTOR_REGISTRY,
    ACTOR_STORE,
    ACTOR_VALIDATOR,
    BUILD_VERSION,
    DEFAULT_CACHE_SIZE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REGISTRY,
    DEFAULT_MAX_SNAPSHOTS,
    FRAMEWORK_VERSION,
    PREFIX_BUNDLE,
    PREFIX_EVENT,
    PREFIX_META,
    PREFIX_SNAPSHOT,
    SNAPSHOT_VERSION,
    VERSION,
    ExecutionStatus,
    GovernanceDecision,
    LifecycleState,
    SnapshotCategory,
    SnapshotEventType,
    SnapshotStatus,
    WorkflowHealthStatus,
)
from .exceptions import (
    WorkflowSnapshotBuildError,
    WorkflowSnapshotBundleError,
    WorkflowSnapshotCacheError,
    WorkflowSnapshotError,
    WorkflowSnapshotNotFoundError,
    WorkflowSnapshotRegistryError,
    WorkflowSnapshotSerializationError,
    WorkflowSnapshotStoreError,
    WorkflowSnapshotValidationError,
    WorkflowSnapshotVersionError,
)
from .workflow_snapshot import WorkflowSnapshot
from .workflow_snapshot_builder import WorkflowSnapshotBuilder
from .workflow_snapshot_bundle import WorkflowSnapshotBundle
from .workflow_snapshot_cache import WorkflowSnapshotCache
from .workflow_snapshot_events import WorkflowSnapshotEvent, WorkflowSnapshotEventBus
from .workflow_snapshot_factory import WorkflowSnapshotFactory
from .workflow_snapshot_history import WorkflowSnapshotHistory
from .workflow_snapshot_metadata import WorkflowSnapshotMetadata
from .workflow_snapshot_registry import WorkflowSnapshotRegistry
from .workflow_snapshot_statistics import (
    WorkflowSnapshotStatistics,
    WorkflowSnapshotStatisticsReport,
)
from .workflow_snapshot_store import WorkflowSnapshotStore
from .workflow_snapshot_validation import (
    SnapshotValidationResult,
    WorkflowSnapshotValidation,
)

__all__ = [
    # Constants & enums
    "VERSION",
    "BUILD_VERSION",
    "SNAPSHOT_VERSION",
    "FRAMEWORK_VERSION",
    "PREFIX_SNAPSHOT",
    "PREFIX_BUNDLE",
    "PREFIX_EVENT",
    "PREFIX_META",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_REGISTRY",
    "DEFAULT_CACHE_SIZE",
    "DEFAULT_MAX_SNAPSHOTS",
    "ACTOR_BUILDER",
    "ACTOR_REGISTRY",
    "ACTOR_STORE",
    "ACTOR_VALIDATOR",
    "SnapshotStatus",
    "SnapshotEventType",
    "SnapshotCategory",
    "WorkflowHealthStatus",
    "GovernanceDecision",
    "ExecutionStatus",
    "LifecycleState",
    # Exceptions
    "WorkflowSnapshotError",
    "WorkflowSnapshotNotFoundError",
    "WorkflowSnapshotValidationError",
    "WorkflowSnapshotBuildError",
    "WorkflowSnapshotRegistryError",
    "WorkflowSnapshotStoreError",
    "WorkflowSnapshotCacheError",
    "WorkflowSnapshotBundleError",
    "WorkflowSnapshotVersionError",
    "WorkflowSnapshotSerializationError",
    # Domain objects
    "WorkflowSnapshotMetadata",
    "WorkflowSnapshot",
    "WorkflowSnapshotBundle",
    "WorkflowSnapshotEvent",
    "WorkflowSnapshotStatisticsReport",
    "SnapshotValidationResult",
    # Services
    "WorkflowSnapshotBuilder",
    "WorkflowSnapshotValidation",
    "WorkflowSnapshotRegistry",
    "WorkflowSnapshotStore",
    "WorkflowSnapshotCache",
    "WorkflowSnapshotHistory",
    "WorkflowSnapshotStatistics",
    "WorkflowSnapshotEventBus",
    "WorkflowSnapshotFactory",
]
