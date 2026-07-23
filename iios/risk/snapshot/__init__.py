"""
iios.risk.snapshot
===================
Institutional Risk Snapshot Framework — C11 Risk Intelligence, Module 5.

The Risk Snapshot is the ONLY published representation of the Risk
Intelligence subsystem.  Every downstream subsystem MUST consume
RiskSnapshot instead of directly accessing Risk Engine, Risk Policy
Framework or Risk Assessment Framework.

Public exports from this package:

Constants & Enumerations
------------------------
SNAPSHOT_SYSTEM_ID, BUILDER_SYSTEM_ID, REGISTRY_SYSTEM_ID,
STORE_SYSTEM_ID, CACHE_SYSTEM_ID, FACTORY_SYSTEM_ID,
HISTORY_SYSTEM_ID, BUNDLE_SYSTEM_ID, VERSION
SnapshotStatus, RiskScope, RiskType, RiskPriority, RiskLevel,
RiskRating, RiskTrend, IntegrityStatus, SnapshotEventType,
SnapshotValidationCode

Exceptions
----------
RiskSnapshotError, RiskSnapshotNotFoundError, RiskSnapshotBuilderError,
RiskSnapshotValidationError, RiskSnapshotIntegrityError,
RiskSnapshotRegistryError, RiskSnapshotStoreError, RiskSnapshotCacheError,
RiskSnapshotCapacityError, RiskSnapshotSerializationError

Metadata Value Objects
----------------------
DomainRiskSummary, AssessmentSummarySection, QuantitativeMetrics,
StressTestSummary, OptimizationSummary, PolicySummary,
SystemHealthSummary, SnapshotAudit, SnapshotStatisticsSection,
SnapshotMetadata

Core Value Object
-----------------
RiskSnapshotSummary, RiskSnapshot

Events
------
RiskSnapshotEvent,
make_snapshot_built, make_snapshot_published, make_snapshot_validated,
make_snapshot_superseded, make_snapshot_archived, make_snapshot_failed,
make_snapshot_retrieved, make_snapshot_expired, make_snapshot_bundled,
make_snapshot_stored

Validation
----------
SnapshotValidationCheck, SnapshotValidationResult, RiskSnapshotValidator

Builder
-------
RiskSnapshotBuilder

Factory
-------
RiskSnapshotFactory

Registry
--------
RiskSnapshotRegistry

Store
-----
RiskSnapshotStore

Cache
-----
RiskSnapshotCache

History
-------
RiskSnapshotHistory

Statistics
----------
RiskSnapshotStatistics

Bundle
------
RiskSnapshotBundle, RiskSnapshotBundleBuilder
"""
from __future__ import annotations

# ── Constants & enumerations ────────────────────────────────────────────────
from .constants import (
    ACTOR_OPERATOR,
    ACTOR_SNAPSHOT_BUILDER,
    ACTOR_SNAPSHOT_FACTORY,
    ACTOR_SNAPSHOT_REGISTRY,
    ACTOR_SYSTEM,
    AVG_SNAPSHOT_SIZE_BYTES,
    BUILDER_SYSTEM_ID,
    BUNDLE_SYSTEM_ID,
    CACHE_SYSTEM_ID,
    DEFAULT_CACHE_MAX_SIZE,
    DEFAULT_CACHE_TTL_S,
    DEFAULT_MAX_BUNDLE_SIZE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SNAPSHOTS,
    DEFAULT_SNAPSHOT_TIMEOUT_S,
    FACTORY_SYSTEM_ID,
    HISTORY_SYSTEM_ID,
    IntegrityStatus,
    LEVEL_TO_PRIORITY,
    REGISTRY_SYSTEM_ID,
    RISK_SCORE_EXCELLENT,
    RISK_SCORE_FAIR,
    RISK_SCORE_GOOD,
    RISK_SCORE_HIGH,
    RISK_SCORE_LOW,
    RISK_SCORE_MEDIUM,
    RISK_SCORE_MINIMAL,
    RISK_SCORE_POOR,
    RiskLevel,
    RiskPriority,
    RiskRating,
    RiskScope,
    RiskTrend,
    RiskType,
    SCHEMA_VERSION,
    SCORE_TO_LEVEL,
    SCORE_TO_RATING,
    SNAPSHOT_SYSTEM_ID,
    SnapshotEventType,
    SnapshotStatus,
    SnapshotValidationCode,
    STORE_SYSTEM_ID,
    VERSION,
)

# ── Exceptions ───────────────────────────────────────────────────────────────
from .exceptions import (
    RiskSnapshotBuilderError,
    RiskSnapshotCacheError,
    RiskSnapshotCapacityError,
    RiskSnapshotError,
    RiskSnapshotIntegrityError,
    RiskSnapshotNotFoundError,
    RiskSnapshotRegistryError,
    RiskSnapshotSerializationError,
    RiskSnapshotStoreError,
    RiskSnapshotValidationError,
)

# ── Metadata value objects ───────────────────────────────────────────────────
from .risk_snapshot_metadata import (
    AssessmentSummarySection,
    DomainRiskSummary,
    OptimizationSummary,
    PolicySummary,
    QuantitativeMetrics,
    SnapshotAudit,
    SnapshotMetadata,
    SnapshotStatisticsSection,
    StressTestSummary,
    SystemHealthSummary,
)

# ── Core snapshot ────────────────────────────────────────────────────────────
from .risk_snapshot import RiskSnapshot, RiskSnapshotSummary

# ── Events ───────────────────────────────────────────────────────────────────
from .risk_snapshot_events import (
    RiskSnapshotEvent,
    make_snapshot_archived,
    make_snapshot_built,
    make_snapshot_bundled,
    make_snapshot_expired,
    make_snapshot_failed,
    make_snapshot_published,
    make_snapshot_retrieved,
    make_snapshot_stored,
    make_snapshot_superseded,
    make_snapshot_validated,
)

# ── Validation ───────────────────────────────────────────────────────────────
from .risk_snapshot_validation import (
    RiskSnapshotValidator,
    SnapshotValidationCheck,
    SnapshotValidationResult,
)

# ── Builder ──────────────────────────────────────────────────────────────────
from .risk_snapshot_builder import RiskSnapshotBuilder

# ── Factory ──────────────────────────────────────────────────────────────────
from .risk_snapshot_factory import RiskSnapshotFactory

# ── Registry ─────────────────────────────────────────────────────────────────
from .risk_snapshot_registry import RiskSnapshotRegistry

# ── Store ────────────────────────────────────────────────────────────────────
from .risk_snapshot_store import RiskSnapshotStore

# ── Cache ────────────────────────────────────────────────────────────────────
from .risk_snapshot_cache import RiskSnapshotCache

# ── History ──────────────────────────────────────────────────────────────────
from .risk_snapshot_history import RiskSnapshotHistory

# ── Statistics ───────────────────────────────────────────────────────────────
from .risk_snapshot_statistics import RiskSnapshotStatistics

# ── Bundle ───────────────────────────────────────────────────────────────────
from .risk_snapshot_bundle import RiskSnapshotBundle, RiskSnapshotBundleBuilder

__all__ = [
    # Constants
    "SNAPSHOT_SYSTEM_ID", "BUILDER_SYSTEM_ID", "REGISTRY_SYSTEM_ID",
    "STORE_SYSTEM_ID", "CACHE_SYSTEM_ID", "FACTORY_SYSTEM_ID",
    "HISTORY_SYSTEM_ID", "BUNDLE_SYSTEM_ID", "VERSION", "SCHEMA_VERSION",
    # Enums
    "SnapshotStatus", "RiskScope", "RiskType", "RiskPriority", "RiskLevel",
    "RiskRating", "RiskTrend", "IntegrityStatus", "SnapshotEventType",
    "SnapshotValidationCode",
    # Exceptions
    "RiskSnapshotError", "RiskSnapshotNotFoundError", "RiskSnapshotBuilderError",
    "RiskSnapshotValidationError", "RiskSnapshotIntegrityError",
    "RiskSnapshotRegistryError", "RiskSnapshotStoreError", "RiskSnapshotCacheError",
    "RiskSnapshotCapacityError", "RiskSnapshotSerializationError",
    # Metadata
    "DomainRiskSummary", "AssessmentSummarySection", "QuantitativeMetrics",
    "StressTestSummary", "OptimizationSummary", "PolicySummary",
    "SystemHealthSummary", "SnapshotAudit", "SnapshotStatisticsSection",
    "SnapshotMetadata",
    # Core
    "RiskSnapshotSummary", "RiskSnapshot",
    # Events
    "RiskSnapshotEvent",
    "make_snapshot_built", "make_snapshot_published", "make_snapshot_validated",
    "make_snapshot_superseded", "make_snapshot_archived", "make_snapshot_failed",
    "make_snapshot_retrieved", "make_snapshot_expired", "make_snapshot_bundled",
    "make_snapshot_stored",
    # Validation
    "SnapshotValidationCheck", "SnapshotValidationResult", "RiskSnapshotValidator",
    # Services
    "RiskSnapshotBuilder", "RiskSnapshotFactory", "RiskSnapshotRegistry",
    "RiskSnapshotStore", "RiskSnapshotCache", "RiskSnapshotHistory",
    "RiskSnapshotStatistics",
    # Bundle
    "RiskSnapshotBundle", "RiskSnapshotBundleBuilder",
]
