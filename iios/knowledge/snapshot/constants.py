"""
constants.py — iios.knowledge.snapshot
========================================
Enumerations, identifiers, and defaults for the
Institutional Knowledge Snapshot system.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
SNAPSHOT_SYSTEM_ID: str = "iios:knowledge:snapshot"
BUILDER_SYSTEM_ID:  str = "iios:knowledge:snapshot:builder"
STORE_SYSTEM_ID:    str = "iios:knowledge:snapshot:store"
CACHE_SYSTEM_ID:    str = "iios:knowledge:snapshot:cache"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:           str = "1.0.0"
SCHEMA_VERSION:    str = "1.0"
FRAMEWORK_VERSION: str = "1.0.0"
BUILD_VERSION:     str = "1.0.0-stable"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_SNAPSHOT: str = "iios:knowledge:snapshot"
ACTOR_BUILDER:  str = "iios:knowledge:snapshot:builder"
ACTOR_SYSTEM:   str = "iios:system"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_SNAPSHOTS: int = 10_000
DEFAULT_CACHE_SIZE:    int = 100
DEFAULT_MAX_HISTORY:   int = 1_000
DEFAULT_MAX_BUNDLES:   int = 500


# ---------------------------------------------------------------------------
# SnapshotState — (6 states)
# ---------------------------------------------------------------------------
class SnapshotState(str, Enum):
    """Processing/publication state of a knowledge snapshot."""
    BUILDING   = "building"
    VALIDATING = "validating"
    BUILT      = "built"
    PUBLISHED  = "published"
    EXPIRED    = "expired"
    ARCHIVED   = "archived"


# ---------------------------------------------------------------------------
# SnapshotVersionTag — (4 tags)
# ---------------------------------------------------------------------------
class SnapshotVersionTag(str, Enum):
    """Semantic version classification of a snapshot."""
    DRAFT      = "draft"
    RELEASE    = "release"
    STABLE     = "stable"
    DEPRECATED = "deprecated"


# ---------------------------------------------------------------------------
# KnowledgeScope — (4 scopes)
# ---------------------------------------------------------------------------
class KnowledgeScope(str, Enum):
    """Enterprise scope of a knowledge snapshot."""
    LOCAL      = "local"
    REGIONAL   = "regional"
    GLOBAL     = "global"
    ENTERPRISE = "enterprise"


# ---------------------------------------------------------------------------
# KnowledgeType — (4 types)
# ---------------------------------------------------------------------------
class KnowledgeType(str, Enum):
    """Classification of the knowledge captured by the snapshot."""
    OPERATIONAL = "operational"
    ANALYTICAL  = "analytical"
    STRATEGIC   = "strategic"
    TACTICAL    = "tactical"


# ---------------------------------------------------------------------------
# SnapshotEventType — (10 event types)
# ---------------------------------------------------------------------------
class SnapshotEventType(str, Enum):
    """Events emitted by the Knowledge Snapshot system."""
    SNAPSHOT_BUILDING  = "snapshot.building"
    SNAPSHOT_BUILT     = "snapshot.built"
    SNAPSHOT_VALIDATED = "snapshot.validated"
    SNAPSHOT_STORED    = "snapshot.stored"
    SNAPSHOT_RETRIEVED = "snapshot.retrieved"
    SNAPSHOT_CACHED    = "snapshot.cached"
    SNAPSHOT_EXPIRED   = "snapshot.expired"
    SNAPSHOT_PUBLISHED = "snapshot.published"
    SNAPSHOT_VERSIONED = "snapshot.versioned"
    SNAPSHOT_BUNDLED   = "snapshot.bundled"


# ---------------------------------------------------------------------------
# SnapshotValidationCode — (8 codes)
# ---------------------------------------------------------------------------
class SnapshotValidationCode(str, Enum):
    """Structural validation checks for a knowledge snapshot."""
    IDENTIFIER_CONSISTENCY = "IDENTIFIER_CONSISTENCY"
    VERSION_CONSISTENCY    = "VERSION_CONSISTENCY"
    KNOWLEDGE_CONSISTENCY  = "KNOWLEDGE_CONSISTENCY"
    GRAPH_CONSISTENCY      = "GRAPH_CONSISTENCY"
    EMBEDDING_CONSISTENCY  = "EMBEDDING_CONSISTENCY"
    INDEX_CONSISTENCY      = "INDEX_CONSISTENCY"
    METADATA_INTEGRITY     = "METADATA_INTEGRITY"
    SNAPSHOT_COMPLETENESS  = "SNAPSHOT_COMPLETENESS"
