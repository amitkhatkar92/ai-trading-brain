"""
iios/ontology/compiler/compiler_constants.py
===============================================
All enumerations, numeric limits, and string constants for the
IIOS Ontology Compiler & Loader subsystem.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    # Enumerations
    "CompilationStrategy",
    "LoadPhase",
    "DependencyKind",
    "MetadataField",
    "CompilationPass",
    "CacheStrategy",
    "IncrementalMode",
    # Numeric constants
    "MAX_PARALLEL_COMPILATIONS",
    "MAX_DEPENDENCY_DEPTH",
    "MAX_IMPORT_CHAIN",
    "COMPILATION_TIMEOUT_MS",
    "METADATA_HASH_TRUNCATE",
    "INCREMENTAL_BATCH_SIZE",
    "WARM_CACHE_MAX_SIZE",
    "PERSISTENT_CACHE_VERSION",
    # String constants
    "COMPILER_VERSION",
    "COMPILER_NAMESPACE",
    "SCHEMA_HASH_ALGORITHM",
    "METADATA_VERSION",
    "BUILTIN_COMPILE_ORDER",
]


# ── Compilation strategy ──────────────────────────────────────────────────────

class CompilationStrategy(str, Enum):
    """How the compiler should process an ontology batch."""
    SEQUENTIAL  = "sequential"   # One at a time in dependency order
    PARALLEL    = "parallel"     # Independent ontologies compile concurrently
    INCREMENTAL = "incremental"  # Only recompile changed ontologies
    LAZY        = "lazy"         # Compile on first access
    EAGER       = "eager"        # Compile all at startup


# ── Load phase ────────────────────────────────────────────────────────────────

class LoadPhase(str, Enum):
    """Phase of the load lifecycle."""
    PRE_LOAD     = "pre_load"     # Before raw document is loaded
    LOADING      = "loading"      # Raw document being loaded
    VALIDATING   = "validating"   # Schema / syntax validation
    RESOLVING    = "resolving"    # Dependency resolution
    COMPILING    = "compiling"    # Compilation pass
    POST_COMPILE = "post_compile" # Indexing / metadata generation
    CACHING      = "caching"      # Writing to cache
    REGISTERING  = "registering"  # Registering with runtime
    COMPLETE     = "complete"     # Load complete
    FAILED       = "failed"       # Load failed


# ── Dependency kind ───────────────────────────────────────────────────────────

class DependencyKind(str, Enum):
    """Type of a dependency relationship between ontologies."""
    IMPORT      = "import"       # Explicit ontology import
    INHERITANCE = "inheritance"  # Parent type from another ontology
    REFERENCE   = "reference"    # Property ref_uri pointing to another ontology
    RELATIONSHIP = "relationship" # Relationship source/target in another ontology
    ALIAS       = "alias"        # Alias resolved from another ontology


# ── Metadata field ────────────────────────────────────────────────────────────

class MetadataField(str, Enum):
    """Keys for compiler-generated runtime metadata."""
    COMPILED_AT    = "compiled_at"
    COMPILER_VER   = "compiler_version"
    SOURCE_HASH    = "source_hash"
    SCHEMA_HASH    = "schema_hash"
    DEPENDENCY_IDS = "dependency_ids"
    TYPE_COUNT     = "type_count"
    REL_COUNT      = "rel_count"
    PROP_COUNT     = "prop_count"
    BUILD_ID       = "build_id"
    WARNINGS       = "warnings"
    DURATION_MS    = "duration_ms"


# ── Compilation pass ──────────────────────────────────────────────────────────

class CompilationPass(str, Enum):
    """Named passes within the compilation pipeline."""
    PARSE         = "parse"         # Parse raw document
    VALIDATE      = "validate"      # Schema validation
    RESOLVE_DEPS  = "resolve_deps"  # Resolve imports / external refs
    RESOLVE_TYPES = "resolve_types" # Build visible-type universe
    CYCLE_CHECK   = "cycle_check"   # Circular inheritance detection
    PROP_RESOLVE  = "prop_resolve"  # Inherited property resolution
    INDEX_BUILD   = "index_build"   # Build children / alias indexes
    META_GEN      = "meta_gen"      # Generate runtime metadata
    CACHE_WRITE   = "cache_write"   # Write compiled artefact to cache


# ── Cache strategy ────────────────────────────────────────────────────────────

class CacheStrategy(str, Enum):
    """Strategy for compiled ontology caching."""
    NONE        = "none"        # No caching
    MEMORY      = "memory"      # LRU in-memory only
    PERSISTENT  = "persistent"  # On-disk JSON/pickle
    TWO_LEVEL   = "two_level"   # Memory + disk
    VERSIONED   = "versioned"   # Include version in cache key


# ── Incremental mode ──────────────────────────────────────────────────────────

class IncrementalMode(str, Enum):
    """How the incremental loader decides what to recompile."""
    HASH_BASED    = "hash_based"    # Compare source hash
    VERSION_BASED = "version_based" # Compare version string
    TIMESTAMP     = "timestamp"     # Compare mtime
    ALWAYS        = "always"        # Always recompile (force)
    NEVER         = "never"         # Use cache if present, never recompile


# ── Numeric constants ─────────────────────────────────────────────────────────

MAX_PARALLEL_COMPILATIONS: Final[int]   = 8
MAX_DEPENDENCY_DEPTH:       Final[int]   = 16
MAX_IMPORT_CHAIN:           Final[int]   = 32
COMPILATION_TIMEOUT_MS:     Final[float] = 30_000.0
METADATA_HASH_TRUNCATE:     Final[int]   = 16   # hex chars
INCREMENTAL_BATCH_SIZE:     Final[int]   = 4
WARM_CACHE_MAX_SIZE:        Final[int]   = 128
PERSISTENT_CACHE_VERSION:   Final[int]   = 1


# ── String constants ──────────────────────────────────────────────────────────

COMPILER_VERSION:      Final[str] = "2.0.0"
COMPILER_NAMESPACE:    Final[str] = "iios.ontology.compiler"
SCHEMA_HASH_ALGORITHM: Final[str] = "md5"
METADATA_VERSION:      Final[str] = "1.0"

# Built-in ontology compilation order (dependencies first)
BUILTIN_COMPILE_ORDER: Final[tuple[str, ...]] = (
    "INFORMATION_ONTOLOGY",    # no dependencies
    "ENTITY_ONTOLOGY",         # imports information
    "EVENT_ONTOLOGY",          # imports information
    "OBSERVATION_ONTOLOGY",    # imports information
    "KNOWLEDGE_ONTOLOGY",      # imports information
    "RELATIONSHIP_ONTOLOGY",   # imports entity, observation, knowledge
    "MASTER_KNOWLEDGE_ARCHITECTURE",  # imports information
)
