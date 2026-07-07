"""
iios/ontology/ontology_constants.py
=====================================
All enumerations, numeric limits, and string constants for the
IIOS Ontology Runtime Layer.

The Ontology Runtime Layer is the semantic foundation of IIOS:
every type, relationship, event, and concept used anywhere in the
system is defined here and resolved at runtime.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    # Enumerations
    "OntologyStatus",
    "OntologyCategory",
    "TypeKind",
    "Cardinality",
    "DataType",
    "LoadStrategy",
    "CompileStatus",
    "RegistryScope",
    "QueryOperator",
    "HierarchyDirection",
    # Numeric constants
    "MAX_INHERITANCE_DEPTH",
    "MAX_TYPE_PROPERTIES",
    "MAX_NAMESPACE_TYPES",
    "MAX_COMPILED_CACHE_SIZE",
    "DEFAULT_ONTOLOGY_VERSION",
    "MAX_QUERY_RESULTS",
    "COMPILE_TIMEOUT_MS",
    "LOAD_TIMEOUT_MS",
    # String constants
    "ONTOLOGY_NAMESPACE",
    "SYSTEM_ONTOLOGY_URI",
    "BASE_NAMESPACE_URI",
    "BUILTIN_NAMESPACE_URI",
    "SCHEMA_VERSION",
    "SYSTEM_ACTOR",
    # Built-in ontology names
    "ONT_MASTER",
    "ONT_INFORMATION",
    "ONT_ENTITY",
    "ONT_RELATIONSHIP",
    "ONT_EVENT",
    "ONT_OBSERVATION",
    "ONT_KNOWLEDGE",
    "BUILTIN_ONTOLOGY_NAMES",
]


# ── Ontology lifecycle status ──────────────────────────────────────────────────

class OntologyStatus(str, Enum):
    """Lifecycle status of an ontology document or compiled artefact."""
    UNLOADED   = "unloaded"    # Not yet loaded
    LOADING    = "loading"     # Load in progress
    LOADED     = "loaded"      # Raw document loaded, not yet compiled
    COMPILING  = "compiling"   # Compilation in progress
    COMPILED   = "compiled"    # Compiled and indexed, ready for use
    ACTIVE     = "active"      # Registered and serving queries
    DEPRECATED = "deprecated"  # Superseded by a newer version
    ERROR      = "error"       # Load or compile failed


# ── Ontology category ──────────────────────────────────────────────────────────

class OntologyCategory(str, Enum):
    """Broad functional category of an ontology document."""
    ARCHITECTURE   = "architecture"   # Master architecture definitions
    INFORMATION    = "information"    # Base information types
    ENTITY         = "entity"         # Domain entity types
    RELATIONSHIP   = "relationship"   # Relationship type definitions
    EVENT          = "event"          # Event type definitions
    OBSERVATION    = "observation"    # Observation layer types
    KNOWLEDGE      = "knowledge"      # Knowledge engine types
    MARKET         = "market"         # Market-specific types
    RISK           = "risk"           # Risk and constraint types
    EXECUTION      = "execution"      # Execution layer types
    EXTENSION      = "extension"      # User or plugin extensions
    CUSTOM         = "custom"         # Uncategorised custom types


# ── Type kind ─────────────────────────────────────────────────────────────────

class TypeKind(str, Enum):
    """The kind of an ontology type definition."""
    ABSTRACT    = "abstract"    # Cannot be instantiated; meant for inheritance
    CONCRETE    = "concrete"    # Can be instantiated directly
    MIXIN       = "mixin"       # Provides reusable properties; no own instances
    ENUM        = "enum"        # Enumerated value set
    PRIMITIVE   = "primitive"   # Scalar type (string, int, float, bool)
    ALIAS       = "alias"       # Alias pointing to another type


# ── Cardinality ───────────────────────────────────────────────────────────────

class Cardinality(str, Enum):
    """Cardinality of a relationship."""
    ONE_TO_ONE   = "one-to-one"
    ONE_TO_MANY  = "one-to-many"
    MANY_TO_ONE  = "many-to-one"
    MANY_TO_MANY = "many-to-many"


# ── Data types ────────────────────────────────────────────────────────────────

class DataType(str, Enum):
    """Primitive data types for ontology properties."""
    STRING   = "string"
    INT      = "int"
    FLOAT    = "float"
    BOOL     = "bool"
    DATETIME = "datetime"
    DATE     = "date"
    UUID     = "uuid"
    LIST     = "list"
    DICT     = "dict"
    ANY      = "any"
    REF      = "ref"       # Reference to another ontology type


# ── Load strategy ─────────────────────────────────────────────────────────────

class LoadStrategy(str, Enum):
    """Strategy for loading ontology documents."""
    EAGER       = "eager"       # Load at engine startup
    LAZY        = "lazy"        # Load on first access
    ON_DEMAND   = "on_demand"   # Load only when explicitly requested
    INCREMENTAL = "incremental" # Load types incrementally as needed


# ── Compile status ────────────────────────────────────────────────────────────

class CompileStatus(str, Enum):
    """Outcome of an ontology compilation step."""
    SUCCESS  = "success"
    PARTIAL  = "partial"    # Compiled with non-fatal warnings
    FAILURE  = "failure"    # Compilation failed


# ── Registry scope ────────────────────────────────────────────────────────────

class RegistryScope(str, Enum):
    """Scope of a registry lookup."""
    LOCAL    = "local"      # Only within one namespace
    GLOBAL   = "global"     # Across all namespaces
    BUILTIN  = "builtin"    # Only built-in IIOS types


# ── Query operator ────────────────────────────────────────────────────────────

class QueryOperator(str, Enum):
    """Filter operators for ontology queries."""
    EQ         = "eq"
    NEQ        = "neq"
    CONTAINS   = "contains"
    STARTS     = "starts_with"
    IN         = "in"
    SUBTYPE_OF = "subtype_of"
    SUPERTYPE_OF = "supertype_of"
    HAS_PROP   = "has_property"


# ── Hierarchy direction ───────────────────────────────────────────────────────

class HierarchyDirection(str, Enum):
    UP   = "up"     # From child → ancestors
    DOWN = "down"   # From parent → descendants
    BOTH = "both"   # Full subtree


# ── Numeric constants ─────────────────────────────────────────────────────────

MAX_INHERITANCE_DEPTH:    Final[int]   = 32
MAX_TYPE_PROPERTIES:      Final[int]   = 256
MAX_NAMESPACE_TYPES:      Final[int]   = 4_096
MAX_COMPILED_CACHE_SIZE:  Final[int]   = 64
MAX_QUERY_RESULTS:        Final[int]   = 1_000
COMPILE_TIMEOUT_MS:       Final[float] = 10_000.0
LOAD_TIMEOUT_MS:          Final[float] = 30_000.0


# ── String constants ──────────────────────────────────────────────────────────

DEFAULT_ONTOLOGY_VERSION: Final[str] = "1.0.0"
ONTOLOGY_NAMESPACE:       Final[str] = "iios.ontology"
SYSTEM_ONTOLOGY_URI:      Final[str] = "iios.ontology.system"
BASE_NAMESPACE_URI:       Final[str] = "iios.base"
BUILTIN_NAMESPACE_URI:    Final[str] = "iios.builtin"
SCHEMA_VERSION:           Final[str] = "1.0"
SYSTEM_ACTOR:             Final[str] = "iios:ontology:system"


# ── Built-in ontology names ───────────────────────────────────────────────────

ONT_MASTER:       Final[str] = "MASTER_KNOWLEDGE_ARCHITECTURE"
ONT_INFORMATION:  Final[str] = "INFORMATION_ONTOLOGY"
ONT_ENTITY:       Final[str] = "ENTITY_ONTOLOGY"
ONT_RELATIONSHIP: Final[str] = "RELATIONSHIP_ONTOLOGY"
ONT_EVENT:        Final[str] = "EVENT_ONTOLOGY"
ONT_OBSERVATION:  Final[str] = "OBSERVATION_ONTOLOGY"
ONT_KNOWLEDGE:    Final[str] = "KNOWLEDGE_ONTOLOGY"

BUILTIN_ONTOLOGY_NAMES: Final[tuple[str, ...]] = (
    ONT_MASTER,
    ONT_INFORMATION,
    ONT_ENTITY,
    ONT_RELATIONSHIP,
    ONT_EVENT,
    ONT_OBSERVATION,
    ONT_KNOWLEDGE,
)
