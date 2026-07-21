"""
iios.decision.snapshot
=======================
Decision Snapshot Subsystem — C9 Decision Intelligence, Phase 1, Module 5.

DecisionSnapshot is the ONLY published representation of the Decision
Intelligence subsystem.  Every downstream module MUST consume
DecisionSnapshot instead of internal Decision objects.

This package:
  - DOES     build, validate, store, cache, and publish snapshots
  - DOES NOT evaluate policies
  - DOES NOT perform optimization
  - DOES NOT execute trades
  - DOES NOT expose M1–M4 internal objects

Primary entry point: :class:`DecisionSnapshotBuilder`
Snapshot type:       :class:`DecisionSnapshot`
Store:               :class:`DecisionSnapshotStore`
"""

# ── Constants ──────────────────────────────────────────────────────────────
from .constants import (
    ACTOR_BUILDER,
    ACTOR_CACHE,
    ACTOR_FACTORY,
    ACTOR_OPERATOR,
    ACTOR_PUBLISHER,
    ACTOR_REGISTRY,
    ACTOR_STORE,
    ACTOR_SYSTEM,
    DEFAULT_CACHE_SIZE,
    DEFAULT_MAX_BUNDLE_SIZE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SNAPSHOTS,
    DEFAULT_MAX_VERSIONS,
    EMA_ALPHA,
    SCHEMA_VERSION,
    SNAPSHOT_SYSTEM_ID,
    SOURCE_M1,
    SOURCE_M2,
    SOURCE_M3,
    SOURCE_M4,
    THROUGHPUT_WINDOW_S,
    VERSION,
    DecisionHealth,
    DecisionOutcome,
    DecisionStatus,
    SnapshotEventType,
    SnapshotStatus,
    SnapshotValidationCode,
)

# ── Exceptions ────────────────────────────────────────────────────────────
from .exceptions import (
    DecisionSnapshotError,
    DuplicateSnapshotError,
    SnapshotBuildError,
    SnapshotCacheError,
    SnapshotConfigurationError,
    SnapshotNotFoundError,
    SnapshotRegistryError,
    SnapshotStoreError,
    SnapshotValidationError,
    SnapshotVersionError,
)

# ── Core value objects ────────────────────────────────────────────────────
from .decision_snapshot import DecisionSnapshot
from .decision_snapshot_metadata import DecisionSnapshotMetadata, SnapshotAuditMetadata
from .decision_snapshot_bundle import DecisionSnapshotBundle
from .decision_snapshot_events import (
    DecisionSnapshotEvent,
    make_snapshot_archived,
    make_snapshot_cached,
    make_snapshot_created,
    make_snapshot_published,
    make_snapshot_retrieved,
    make_snapshot_validated,
)

# ── Validation ────────────────────────────────────────────────────────────
from .decision_snapshot_validation import (
    DecisionSnapshotValidator,
    SnapshotValidationCheckResult,
    SnapshotValidationResult,
)

# ── Builder + Factory ────────────────────────────────────────────────────
from .decision_snapshot_builder import DecisionSnapshotBuilder
from .decision_snapshot_factory import DecisionSnapshotFactory

# ── Registry ──────────────────────────────────────────────────────────────
from .decision_snapshot_registry import DecisionSnapshotRegistry

# ── Store + Cache ─────────────────────────────────────────────────────────
from .decision_snapshot_store import DecisionSnapshotStore
from .decision_snapshot_cache import DecisionSnapshotCache

# ── Observability ─────────────────────────────────────────────────────────
from .decision_snapshot_history import DecisionSnapshotHistory
from .decision_snapshot_statistics import DecisionSnapshotStatistics

__all__ = [
    # Constants
    "ACTOR_BUILDER",
    "ACTOR_CACHE",
    "ACTOR_FACTORY",
    "ACTOR_OPERATOR",
    "ACTOR_PUBLISHER",
    "ACTOR_REGISTRY",
    "ACTOR_STORE",
    "ACTOR_SYSTEM",
    "DEFAULT_CACHE_SIZE",
    "DEFAULT_MAX_BUNDLE_SIZE",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_SNAPSHOTS",
    "DEFAULT_MAX_VERSIONS",
    "EMA_ALPHA",
    "SCHEMA_VERSION",
    "SNAPSHOT_SYSTEM_ID",
    "SOURCE_M1",
    "SOURCE_M2",
    "SOURCE_M3",
    "SOURCE_M4",
    "THROUGHPUT_WINDOW_S",
    "VERSION",
    "DecisionHealth",
    "DecisionOutcome",
    "DecisionStatus",
    "SnapshotEventType",
    "SnapshotStatus",
    "SnapshotValidationCode",
    # Exceptions
    "DecisionSnapshotError",
    "DuplicateSnapshotError",
    "SnapshotBuildError",
    "SnapshotCacheError",
    "SnapshotConfigurationError",
    "SnapshotNotFoundError",
    "SnapshotRegistryError",
    "SnapshotStoreError",
    "SnapshotValidationError",
    "SnapshotVersionError",
    # Core value objects
    "DecisionSnapshot",
    "DecisionSnapshotBundle",
    "DecisionSnapshotEvent",
    "DecisionSnapshotMetadata",
    "SnapshotAuditMetadata",
    # Validation
    "DecisionSnapshotValidator",
    "SnapshotValidationCheckResult",
    "SnapshotValidationResult",
    # Builder + Factory
    "DecisionSnapshotBuilder",
    "DecisionSnapshotFactory",
    # Registry
    "DecisionSnapshotRegistry",
    # Store + Cache
    "DecisionSnapshotCache",
    "DecisionSnapshotStore",
    # Observability
    "DecisionSnapshotHistory",
    "DecisionSnapshotStatistics",
    # Event factories
    "make_snapshot_archived",
    "make_snapshot_cached",
    "make_snapshot_created",
    "make_snapshot_published",
    "make_snapshot_retrieved",
    "make_snapshot_validated",
]
