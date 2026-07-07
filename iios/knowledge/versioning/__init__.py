"""
iios/knowledge/versioning/__init__.py

Backward-compatible exports (KnowledgeVersioningEngine) plus all new
Knowledge Versioning & Evolution Engine symbols.
"""
from __future__ import annotations

# ── Backward-compatible (Wave 3) ──────────────────────────────────────────────
from .knowledge_versioning import (
    KnowledgeVersioningEngine,
    get_versioning_engine,
    reset_versioning_engine,
)

# ── New constants & exceptions ────────────────────────────────────────────────
from .version_constants import (
    VersionEventType,
    BranchStatus,
    MergeStrategy,
    ChangeType,
    ProvenanceType,
    LineageRelationType,
    DEFAULT_BRANCH,
    SYSTEM_VERSIONING_ACTOR,
)
from .version_exceptions import (
    VersionError,
    VersionNotFoundError,
    VersionAlreadyExistsError,
    VersionConflictError,
    VersionRollbackError,
    VersionValidationError,
    BranchError,
    BranchNotFoundError,
    BranchAlreadyExistsError,
    BranchMergeError,
    BranchConflictError,
    DiffError,
    ProvenanceError,
    LineageError,
    LineageCycleError,
    AuditError,
    VersionEngineError,
)

# ── Models ────────────────────────────────────────────────────────────────────
from .models import (
    KnowledgeVersion,
    VersionHistory,
    VersionBranch,
    ConflictInfo,
    MergeResult,
    FieldChange,
    RecordDiff,
    AuditEntry,
    ProvenanceRecord,
    LineageNode,
    LineageEdge,
    LineageGraph,
)

# ── Services ──────────────────────────────────────────────────────────────────
from .version_manager    import VersionManager, get_version_manager, reset_version_manager
from .branch_manager     import BranchManager, get_branch_manager, reset_branch_manager
from .diff_engine        import DiffEngine, get_diff_engine, reset_diff_engine
from .audit_log          import AuditLog, get_audit_log, reset_audit_log
from .provenance_tracker import ProvenanceTracker, get_provenance_tracker, reset_provenance_tracker
from .lineage_manager    import (
    LineageManager,
    DependencyTracker,
    get_lineage_manager,
    reset_lineage_manager,
    get_dependency_tracker,
    reset_dependency_tracker,
)

# ── Infrastructure ────────────────────────────────────────────────────────────
from .version_context import (
    VersionContext,
    get_version_context,
    reset_version_context,
    version_operation,
    current_version_actor,
    current_version_operation_id,
)
from .version_factory  import VersionFactory, get_version_factory, reset_version_factory
from .version_engine   import VersionEngine, get_version_engine, reset_version_engine
from .version_registry import VersionRegistry, get_version_registry, reset_version_registry

__all__ = [
    # backward-compat
    "KnowledgeVersioningEngine",
    "get_versioning_engine",
    "reset_versioning_engine",
    # constants
    "VersionEventType",
    "BranchStatus",
    "MergeStrategy",
    "ChangeType",
    "ProvenanceType",
    "LineageRelationType",
    "DEFAULT_BRANCH",
    "SYSTEM_VERSIONING_ACTOR",
    # exceptions
    "VersionError",
    "VersionNotFoundError",
    "VersionAlreadyExistsError",
    "VersionConflictError",
    "VersionRollbackError",
    "VersionValidationError",
    "BranchError",
    "BranchNotFoundError",
    "BranchAlreadyExistsError",
    "BranchMergeError",
    "BranchConflictError",
    "DiffError",
    "ProvenanceError",
    "LineageError",
    "LineageCycleError",
    "AuditError",
    "VersionEngineError",
    # models
    "KnowledgeVersion",
    "VersionHistory",
    "VersionBranch",
    "ConflictInfo",
    "MergeResult",
    "FieldChange",
    "RecordDiff",
    "AuditEntry",
    "ProvenanceRecord",
    "LineageNode",
    "LineageEdge",
    "LineageGraph",
    # services
    "VersionManager",
    "get_version_manager",
    "reset_version_manager",
    "BranchManager",
    "get_branch_manager",
    "reset_branch_manager",
    "DiffEngine",
    "get_diff_engine",
    "reset_diff_engine",
    "AuditLog",
    "get_audit_log",
    "reset_audit_log",
    "ProvenanceTracker",
    "get_provenance_tracker",
    "reset_provenance_tracker",
    "LineageManager",
    "DependencyTracker",
    "get_lineage_manager",
    "reset_lineage_manager",
    "get_dependency_tracker",
    "reset_dependency_tracker",
    # infrastructure
    "VersionContext",
    "get_version_context",
    "reset_version_context",
    "version_operation",
    "current_version_actor",
    "current_version_operation_id",
    "VersionFactory",
    "get_version_factory",
    "reset_version_factory",
    "VersionEngine",
    "get_version_engine",
    "reset_version_engine",
    "VersionRegistry",
    "get_version_registry",
    "reset_version_registry",
]
