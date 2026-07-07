"""
iios/knowledge/versioning/version_constants.py
===============================================
Constants and enumerations for the Knowledge Versioning & Evolution Engine.

Existing VersionBump and VersionStatus from knowledge_constants are reused
throughout; the symbols here cover branching, change tracking, provenance,
lineage, and audit that the base snapshot engine does not address.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    # enums
    "VersionEventType",
    "BranchStatus",
    "MergeStrategy",
    "ChangeType",
    "ProvenanceType",
    "LineageRelationType",
    # constants
    "VERSIONING_NAMESPACE",
    "SYSTEM_VERSIONING_ACTOR",
    "DEFAULT_BRANCH",
    "MAIN_BRANCH",
    "MAX_BRANCH_NAME_LEN",
    "MAX_VERSIONS_PER_ITEM",
    "MAX_AUDIT_ENTRIES_PER_ITEM",
    "MAX_LINEAGE_DEPTH",
    "VERSIONING_SCHEMA_VERSION",
    "DIFF_SKIP_FIELDS",
]


class VersionEventType(str, Enum):
    """Audit event types emitted by the versioning engine."""

    VERSION_CREATED    = "version.created"
    VERSION_RELEASED   = "version.released"
    VERSION_ARCHIVED   = "version.archived"
    VERSION_DELETED    = "version.deleted"
    BRANCH_CREATED     = "branch.created"
    BRANCH_MERGED      = "branch.merged"
    BRANCH_CLOSED      = "branch.closed"
    ROLLBACK           = "version.rollback"
    CONFLICT_DETECTED  = "merge.conflict_detected"
    CONFLICT_RESOLVED  = "merge.conflict_resolved"
    PROVENANCE_LINKED  = "provenance.linked"
    LINEAGE_LINKED     = "lineage.linked"
    DEPENDENCY_ADDED   = "dependency.added"
    DEPENDENCY_REMOVED = "dependency.removed"
    DRAFT_PROMOTED     = "version.draft_promoted"


class BranchStatus(str, Enum):
    """Lifecycle state of a knowledge branch."""

    OPEN       = "open"
    MERGED     = "merged"
    CLOSED     = "closed"
    CONFLICTED = "conflicted"
    ARCHIVED   = "archived"


class MergeStrategy(str, Enum):
    """Strategy for resolving merge conflicts between branches."""

    OURS   = "ours"    # keep target branch (discard source changes on conflicts)
    THEIRS = "theirs"  # accept source branch (override target on conflicts)
    LATEST = "latest"  # most recently modified version wins
    MANUAL = "manual"  # raise error on any conflict; caller must resolve


class ChangeType(str, Enum):
    """Type of change recorded in a field-level diff."""

    ADDED     = "added"
    MODIFIED  = "modified"
    REMOVED   = "removed"
    UNCHANGED = "unchanged"


class ProvenanceType(str, Enum):
    """How a knowledge record came into existence."""

    CREATED      = "created"
    DERIVED_FROM = "derived_from"
    MERGED_FROM  = "merged_from"
    IMPORTED     = "imported"
    TRANSFORMED  = "transformed"
    VALIDATED    = "validated"
    COPIED       = "copied"
    INFERRED     = "inferred"


class LineageRelationType(str, Enum):
    """Relationship type in the knowledge lineage graph."""

    DERIVED_FROM = "derived_from"
    DEPENDS_ON   = "depends_on"
    SUPERSEDES   = "supersedes"
    MERGED_FROM  = "merged_from"
    PART_OF      = "part_of"
    VALIDATES    = "validates"
    INFLUENCES   = "influences"


# ── Module-level constants ────────────────────────────────────────────────────

VERSIONING_NAMESPACE:          Final[str] = "iios.versioning"
SYSTEM_VERSIONING_ACTOR:       Final[str] = "iios:system"
DEFAULT_BRANCH:                Final[str] = "main"
MAIN_BRANCH:                   Final[str] = "main"
MAX_BRANCH_NAME_LEN:           Final[int] = 64
MAX_VERSIONS_PER_ITEM:         Final[int] = 1_000
MAX_AUDIT_ENTRIES_PER_ITEM:    Final[int] = 10_000
MAX_LINEAGE_DEPTH:             Final[int] = 20
VERSIONING_SCHEMA_VERSION:     Final[str] = "1.0.0"

# Fields excluded from field-level diff computation (timestamps that always
# change and carry no semantic meaning for conflict detection).
DIFF_SKIP_FIELDS: Final[frozenset[str]] = frozenset({
    "updated_at",
    "version_sequence",
    "previous_version_id",
})
