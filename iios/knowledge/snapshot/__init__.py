"""
__init__.py — iios.knowledge.snapshot
--------------------------------------
Public API for the Institutional Knowledge Snapshot system (C14 M5).

All downstream IIOS components MUST consume KnowledgeSnapshot rather
than directly accessing the Knowledge Engine, Knowledge Governance
Policy Framework, or Knowledge Intelligence Framework.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

# ---- Constants & Enums -------------------------------------------------
from .constants import (
    ACTOR_BUILDER,
    ACTOR_SNAPSHOT,
    ACTOR_SYSTEM,
    BUILD_VERSION,
    DEFAULT_CACHE_SIZE,
    DEFAULT_MAX_BUNDLES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SNAPSHOTS,
    FRAMEWORK_VERSION,
    SCHEMA_VERSION,
    SNAPSHOT_SYSTEM_ID,
    VERSION,
    KnowledgeScope,
    KnowledgeType,
    SnapshotEventType,
    SnapshotState,
    SnapshotValidationCode,
    SnapshotVersionTag,
)

# ---- Exceptions --------------------------------------------------------
from .exceptions import (
    KnowledgeSnapshotError,
    SnapshotBuildError,
    SnapshotCapacityError,
    SnapshotIntegrityError,
    SnapshotNotFoundError,
    SnapshotSerializationError,
    SnapshotStoreError,
    SnapshotValidationError,
    SnapshotVersionError,
)

# ---- Core domain objects -----------------------------------------------
from .knowledge_snapshot import (
    EmbeddingSummary,
    GraphSummary,
    KnowledgeSummary,
    KnowledgeSnapshot,
    RecommendationSummary,
    RetrievalSummary,
    SnapshotAudit,
    SnapshotMemorySummary,
    SnapshotMetadata,
    SnapshotStatistics,
    VectorIndexSummary,
)

# ---- Metadata ----------------------------------------------------------
from .knowledge_snapshot_metadata import SnapshotMetadataBuilder

# ---- Builder & Factory -------------------------------------------------
from .knowledge_snapshot_builder import KnowledgeSnapshotBuilder
from .knowledge_snapshot_factory import KnowledgeSnapshotFactory

# ---- Validation --------------------------------------------------------
from .knowledge_snapshot_validation import (
    KnowledgeSnapshotValidation,
    SnapshotValidationReport,
    SnapshotValidationResult,
)

# ---- Storage -----------------------------------------------------------
from .knowledge_snapshot_registry import KnowledgeSnapshotRegistry
from .knowledge_snapshot_store import KnowledgeSnapshotStore
from .knowledge_snapshot_cache import KnowledgeSnapshotCache
from .knowledge_snapshot_history import KnowledgeSnapshotHistory

# ---- Statistics --------------------------------------------------------
from .knowledge_snapshot_statistics import (
    KnowledgeSnapshotStatistics,
    SnapshotStatisticsReport,
)

# ---- Events ------------------------------------------------------------
from .knowledge_snapshot_events import SnapshotEvent, SnapshotEventBus

# ---- Bundle ------------------------------------------------------------
from .knowledge_snapshot_bundle import (
    KnowledgeSnapshotBundle,
    KnowledgeSnapshotBundleRegistry,
)

__all__ = [
    # Constants
    "SNAPSHOT_SYSTEM_ID", "VERSION", "SCHEMA_VERSION",
    "FRAMEWORK_VERSION", "BUILD_VERSION",
    "ACTOR_SNAPSHOT", "ACTOR_BUILDER", "ACTOR_SYSTEM",
    "DEFAULT_MAX_SNAPSHOTS", "DEFAULT_CACHE_SIZE",
    "DEFAULT_MAX_HISTORY", "DEFAULT_MAX_BUNDLES",
    # Enums
    "SnapshotState", "SnapshotVersionTag", "KnowledgeScope", "KnowledgeType",
    "SnapshotEventType", "SnapshotValidationCode",
    # Exceptions
    "KnowledgeSnapshotError", "SnapshotBuildError", "SnapshotValidationError",
    "SnapshotNotFoundError", "SnapshotVersionError", "SnapshotSerializationError",
    "SnapshotStoreError", "SnapshotCapacityError", "SnapshotIntegrityError",
    # Core domain objects
    "KnowledgeSummary", "GraphSummary", "EmbeddingSummary",
    "VectorIndexSummary", "RetrievalSummary", "RecommendationSummary",
    "SnapshotMemorySummary", "SnapshotAudit", "SnapshotStatistics",
    "SnapshotMetadata", "KnowledgeSnapshot",
    # Metadata
    "SnapshotMetadataBuilder",
    # Builder & Factory
    "KnowledgeSnapshotBuilder", "KnowledgeSnapshotFactory",
    # Validation
    "SnapshotValidationResult", "SnapshotValidationReport",
    "KnowledgeSnapshotValidation",
    # Storage
    "KnowledgeSnapshotRegistry", "KnowledgeSnapshotStore",
    "KnowledgeSnapshotCache", "KnowledgeSnapshotHistory",
    # Statistics
    "SnapshotStatisticsReport", "KnowledgeSnapshotStatistics",
    # Events
    "SnapshotEvent", "SnapshotEventBus",
    # Bundle
    "KnowledgeSnapshotBundle", "KnowledgeSnapshotBundleRegistry",
]
