"""iios/execution/risk/snapshot/__init__.py
==================================================
Public API for the Execution Risk Snapshot subsystem (C6 Phase 4 M5).

ExecutionRiskSnapshot is the ONLY published representation of an
execution risk evaluation.  Every downstream subsystem MUST consume
ExecutionRiskSnapshot instead of internal Execution Risk objects.

Usage
-----
    from iios.execution.risk.snapshot import (
        ExecutionRiskSnapshot,
        RuleSnapshot,
        SnapshotFactory,
        SnapshotBuilder,
        SnapshotRegistry,
        SnapshotStatus,
        make_snapshot_bundle,
    )

    # Build from M1-M4 pipeline objects
    snapshot = SnapshotFactory.build_from_pipeline(
        lifecycle, engine_result, rule_results, control_decision
    )

    # Or build step-by-step
    snapshot = (
        SnapshotBuilder()
        .with_lifecycle(lifecycle)
        .with_engine_result(engine_result)
        .with_rule_results(rule_results)
        .with_control_decision(control_decision)
        .build()
    )

    # Register and publish
    registry = SnapshotRegistry()
    registry.start()
    registry.register(snapshot)
    registry.publish(snapshot.snapshot_id)

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

# ── Core ──────────────────────────────────────────────────────────────────────
from .execution_risk_snapshot import (
    ExecutionRiskSnapshot,
    RuleSnapshot,
)

# ── Metadata ──────────────────────────────────────────────────────────────────
from .execution_risk_snapshot_metadata import (
    AuditMetadata,
    OverrideMetadata,
    RiskMetadata,
    make_audit_metadata,
    make_override_metadata_from,
    make_risk_metadata,
)

# ── Builder / Factory ─────────────────────────────────────────────────────────
from .execution_risk_snapshot_builder import SnapshotBuilder
from .execution_risk_snapshot_factory import SnapshotFactory

# ── Validation ────────────────────────────────────────────────────────────────
from .execution_risk_snapshot_validation import (
    SnapshotValidationResult,
    SnapshotValidator,
)

# ── Registry ──────────────────────────────────────────────────────────────────
from .execution_risk_snapshot_registry import SnapshotRegistry

# ── Store / Cache / History ───────────────────────────────────────────────────
from .execution_risk_snapshot_store import SnapshotStore
from .execution_risk_snapshot_cache import SnapshotCache
from .execution_risk_snapshot_history import SnapshotHistory

# ── Statistics ────────────────────────────────────────────────────────────────
from .execution_risk_snapshot_statistics import SnapshotStatistics

# ── Events ────────────────────────────────────────────────────────────────────
from .execution_risk_snapshot_events import (
    SnapshotEvent,
    make_snapshot_archived_event,
    make_snapshot_cached_event,
    make_snapshot_created_event,
    make_snapshot_published_event,
    make_snapshot_retrieved_event,
    make_snapshot_validated_event,
)

# ── Bundle ────────────────────────────────────────────────────────────────────
from .execution_risk_snapshot_bundle import (
    SnapshotBundle,
    make_snapshot_bundle,
)

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (
    PUBLISHABLE_STATUSES,
    REGISTRY_SYSTEM_ID,
    SNAPSHOT_SYSTEM_ID,
    SNAPSHOT_VERSION,
    TERMINAL_STATUSES,
    VALID_LIFECYCLE_STATES_FOR_SNAPSHOT,
    VERSION,
    SnapshotEventType,
    SnapshotStatus,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    DuplicateSnapshotError,
    ExecutionRiskSnapshotError,
    SnapshotBuildError,
    SnapshotNotFoundError,
    SnapshotRegistryNotRunningError,
    SnapshotSerializationError,
    SnapshotStoreError,
    SnapshotValidationError,
    SnapshotVersionError,
)

__all__ = [
    # Core
    "ExecutionRiskSnapshot",
    "RuleSnapshot",
    # Metadata
    "AuditMetadata",
    "OverrideMetadata",
    "RiskMetadata",
    "make_audit_metadata",
    "make_override_metadata_from",
    "make_risk_metadata",
    # Builder / Factory
    "SnapshotBuilder",
    "SnapshotFactory",
    # Validation
    "SnapshotValidationResult",
    "SnapshotValidator",
    # Registry
    "SnapshotRegistry",
    # Store / Cache / History
    "SnapshotStore",
    "SnapshotCache",
    "SnapshotHistory",
    # Statistics
    "SnapshotStatistics",
    # Events
    "SnapshotEvent",
    "make_snapshot_archived_event",
    "make_snapshot_cached_event",
    "make_snapshot_created_event",
    "make_snapshot_published_event",
    "make_snapshot_retrieved_event",
    "make_snapshot_validated_event",
    # Bundle
    "SnapshotBundle",
    "make_snapshot_bundle",
    # Constants / enums
    "PUBLISHABLE_STATUSES",
    "REGISTRY_SYSTEM_ID",
    "SNAPSHOT_SYSTEM_ID",
    "SNAPSHOT_VERSION",
    "TERMINAL_STATUSES",
    "VALID_LIFECYCLE_STATES_FOR_SNAPSHOT",
    "VERSION",
    "SnapshotEventType",
    "SnapshotStatus",
    # Exceptions
    "DuplicateSnapshotError",
    "ExecutionRiskSnapshotError",
    "SnapshotBuildError",
    "SnapshotNotFoundError",
    "SnapshotRegistryNotRunningError",
    "SnapshotSerializationError",
    "SnapshotStoreError",
    "SnapshotValidationError",
    "SnapshotVersionError",
]
