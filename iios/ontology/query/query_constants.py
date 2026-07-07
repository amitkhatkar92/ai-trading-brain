"""
iios/ontology/query/query_constants.py
=======================================
Enumerations and constants for the IIOS Ontology Query &
Semantic Resolution Engine.

Error-code prefix: QRY-
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    # Enumerations
    "QueryType",
    "ResolutionStrategy",
    "NavigationDirection",
    "SortOrder",
    "QueryStatus",
    "SemanticRelation",
    "IndexHint",
    # Numeric constants
    "MAX_QUERY_DEPTH",
    "DEFAULT_FUZZY_THRESHOLD",
    "MAX_FUZZY_CANDIDATES",
    "MAX_EXPAND_RADIUS",
    "QUERY_TIMEOUT_MS",
    "QUERY_CACHE_TTL_SECONDS",
    "QUERY_CACHE_MAX_SIZE",
    "MAX_NAMED_QUERIES",
    "DEFAULT_RESULT_LIMIT",
    "MAX_RESOLUTION_DEPTH",
    "SEMANTIC_DISTANCE_INFINITY",
    # String constants
    "QUERY_ENGINE_VERSION",
    "SYSTEM_QUERY_ACTOR",
    # Built-in named query IDs
    "QID_ALL_TYPES",
    "QID_ENTITY_TYPES",
    "QID_ABSTRACT_TYPES",
    "QID_CONCRETE_TYPES",
    "QID_ALL_RELATIONSHIPS",
    "QID_ALL_NAMESPACES",
]


# ── Query type ─────────────────────────────────────────────────────────────────

class QueryType(str, Enum):
    """The kind of semantic query being executed."""
    TYPE_LOOKUP       = "type_lookup"       # Resolve a type by URI/name/alias
    RELATIONSHIP_LOOKUP = "relationship_lookup"  # Resolve a relationship
    HIERARCHY         = "hierarchy"         # Full subtree from a root
    ANCESTORS         = "ancestors"         # Walk up the inheritance chain
    DESCENDANTS       = "descendants"       # All recursive children
    CHILDREN          = "children"          # Direct children only
    PARENT            = "parent"            # Single parent
    SEARCH            = "search"            # Text/substring search
    SEMANTIC          = "semantic"          # Semantic similarity/expansion
    REFERENCE         = "reference"         # Cross-reference lookup
    METADATA          = "metadata"          # Property / metadata query
    CROSS_REFERENCE   = "cross_reference"   # Cross-ontology reference
    NAMED             = "named"             # Execute a named/stored query
    NEIGHBORHOOD      = "neighborhood"      # BFS around a concept


# ── Resolution strategy ────────────────────────────────────────────────────────

class ResolutionStrategy(str, Enum):
    """Strategy used to resolve a reference to a canonical type."""
    EXACT       = "exact"       # Direct URI match only
    ALIAS       = "alias"       # Check alias index
    CANONICAL   = "canonical"   # Resolve via canonical_uri mapping
    FUZZY       = "fuzzy"       # Substring / edit-distance match
    INHERITANCE = "inheritance" # Walk up inheritance chain
    HIERARCHICAL = "hierarchical" # Any name in the subtree
    AUTO        = "auto"        # Try each strategy in order until resolved


# ── Navigation direction ───────────────────────────────────────────────────────

class NavigationDirection(str, Enum):
    """Direction of hierarchy / graph traversal."""
    UP     = "up"      # Follow parent_uri links (toward root)
    DOWN   = "down"    # Follow children links (toward leaves)
    BOTH   = "both"    # Bidirectional BFS
    LATERAL = "lateral" # Same-namespace peers (siblings)


# ── Sort order ─────────────────────────────────────────────────────────────────

class SortOrder(str, Enum):
    """How to order results from a query or search."""
    RELEVANCE        = "relevance"        # Score-based (highest first)
    ALPHABETICAL     = "alphabetical"     # name A → Z
    ALPHABETICAL_DESC = "alphabetical_desc"
    HIERARCHY_DEPTH  = "hierarchy_depth"  # Shallowest first
    NAMESPACE        = "namespace"        # By namespace URI
    NATURAL          = "natural"          # Registry insertion order


# ── Query status ───────────────────────────────────────────────────────────────

class QueryStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CACHED    = "cached"
    TIMEOUT   = "timeout"


# ── Semantic relation ──────────────────────────────────────────────────────────

class SemanticRelation(str, Enum):
    """Named semantic relation between two types."""
    SAME_AS      = "same_as"       # Aliases / synonyms
    SUBTYPE_OF   = "subtype_of"    # Direct or transitive child
    SUPERTYPE_OF = "supertype_of"  # Direct or transitive parent
    RELATED_TO   = "related_to"    # Connected via any relationship
    INVERSE_OF   = "inverse_of"    # Inverse relationship pair
    PART_OF      = "part_of"       # Compositional membership
    SIBLING      = "sibling"       # Same direct parent


# ── Index hint ─────────────────────────────────────────────────────────────────

class IndexHint(str, Enum):
    """Optimizer hints for index usage."""
    USE_URI_INDEX       = "use_uri_index"
    USE_ALIAS_INDEX     = "use_alias_index"
    USE_NAMESPACE_INDEX = "use_namespace_index"
    USE_LABEL_INDEX     = "use_label_index"
    FULL_SCAN           = "full_scan"
    HIERARCHY_INDEX     = "hierarchy_index"


# ── Numeric constants ─────────────────────────────────────────────────────────

MAX_QUERY_DEPTH:        Final[int]   = 64
DEFAULT_FUZZY_THRESHOLD: Final[float] = 0.5
MAX_FUZZY_CANDIDATES:   Final[int]   = 256
MAX_EXPAND_RADIUS:      Final[int]   = 8
QUERY_TIMEOUT_MS:       Final[float] = 10_000.0
QUERY_CACHE_TTL_SECONDS: Final[int]  = 300    # 5 minutes
QUERY_CACHE_MAX_SIZE:   Final[int]   = 1_024
MAX_NAMED_QUERIES:      Final[int]   = 512
DEFAULT_RESULT_LIMIT:   Final[int]   = 100
MAX_RESOLUTION_DEPTH:   Final[int]   = 32
SEMANTIC_DISTANCE_INFINITY: Final[float] = 999.0


# ── String constants ──────────────────────────────────────────────────────────

QUERY_ENGINE_VERSION: Final[str] = "1.0.0"
SYSTEM_QUERY_ACTOR:   Final[str] = "iios:query:system"


# ── Built-in named query IDs ──────────────────────────────────────────────────

QID_ALL_TYPES:          Final[str] = "builtin.all_types"
QID_ENTITY_TYPES:       Final[str] = "builtin.entity_types"
QID_ABSTRACT_TYPES:     Final[str] = "builtin.abstract_types"
QID_CONCRETE_TYPES:     Final[str] = "builtin.concrete_types"
QID_ALL_RELATIONSHIPS:  Final[str] = "builtin.all_relationships"
QID_ALL_NAMESPACES:     Final[str] = "builtin.all_namespaces"
