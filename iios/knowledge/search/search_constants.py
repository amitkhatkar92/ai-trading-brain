"""
iios/knowledge/search/search_constants.py
==========================================
All enumerations and constants for the Knowledge Indexing & Search Engine.
"""
from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    "SearchType", "SearchIndexType", "RankingStrategy", "SearchSortOrder",
    "SearchQueryOp", "ItemType", "SearchEvent",
    "SEARCH_NAMESPACE", "SYSTEM_SEARCH_ACTOR",
    "DEFAULT_SEARCH_PAGE_SIZE", "MAX_SEARCH_PAGE_SIZE", "DEFAULT_MAX_RESULTS",
    "SEARCH_CACHE_TTL", "SEARCH_CACHE_MAX_SIZE",
    "DEFAULT_FUZZY_THRESHOLD", "MIN_TOKEN_LENGTH", "MAX_QUERY_TEXT_LENGTH",
    "SEARCH_SCHEMA_VERSION",
    "TITLE_BOOST", "TAG_BOOST", "CONTENT_BOOST",
    "EXACT_TITLE_BONUS", "ALL_TOKENS_BONUS", "RECENCY_DECAY_DAYS",
]


class SearchType(str, Enum):
    """Available search modalities."""
    ID_LOOKUP        = "id_lookup"
    EXACT_MATCH      = "exact_match"
    KEYWORD          = "keyword"
    METADATA         = "metadata"
    TAG              = "tag"
    ONTOLOGY         = "ontology"
    RELATIONSHIP     = "relationship"
    GRAPH_TRAVERSAL  = "graph_traversal"
    HYBRID           = "hybrid"
    SEMANTIC         = "semantic"


class SearchIndexType(str, Enum):
    """Types of indexes maintained by the engine."""
    PRIMARY   = "primary"    # item_id → UnifiedSearchResult
    KEYWORD   = "keyword"    # token → set[item_id]
    TAG       = "tag"        # tag → set[item_id]
    METADATA  = "metadata"   # field:value → set[item_id]
    ONTOLOGY  = "ontology"   # type/domain key → set[item_id]
    GRAPH     = "graph"      # graph-node specific index
    COMPOSITE = "composite"  # multi-field compound index
    TEMPORAL  = "temporal"   # time-range index


class RankingStrategy(str, Enum):
    """How results are ranked after retrieval."""
    RELEVANCE             = "relevance"
    CONFIDENCE            = "confidence"
    RECENCY               = "recency"
    IMPORTANCE            = "importance"
    RELATIONSHIP_STRENGTH = "relationship_strength"
    HYBRID                = "hybrid"
    CUSTOM                = "custom"


class SearchSortOrder(str, Enum):
    ASC  = "asc"
    DESC = "desc"


class SearchQueryOp(str, Enum):
    """Boolean / structural query operators for multi-token search."""
    AND      = "and"
    OR       = "or"
    NOT      = "not"
    PHRASE   = "phrase"
    WILDCARD = "wildcard"
    FUZZY    = "fuzzy"
    RANGE    = "range"


class ItemType(str, Enum):
    """Types of items stored in the search indexes."""
    KNOWLEDGE  = "knowledge"
    GRAPH_NODE = "graph_node"
    GRAPH_EDGE = "graph_edge"


class SearchEvent(str, Enum):
    SEARCH_EXECUTED  = "search.executed"
    INDEX_BUILT      = "index.built"
    INDEX_UPDATED    = "index.updated"
    CACHE_HIT        = "cache.hit"
    CACHE_MISS       = "cache.miss"
    ITEM_INDEXED     = "item.indexed"
    ITEM_DEINDEXED   = "item.deindexed"
    INDEX_OPTIMIZED  = "index.optimized"


# ── String constants ───────────────────────────────────────────────────────────

SEARCH_NAMESPACE:       Final[str]   = "iios.search"
SYSTEM_SEARCH_ACTOR:    Final[str]   = "iios:system"
SEARCH_SCHEMA_VERSION:  Final[str]   = "1.0.0"

# ── Pagination & limits ────────────────────────────────────────────────────────

DEFAULT_SEARCH_PAGE_SIZE: Final[int]  = 50
MAX_SEARCH_PAGE_SIZE:     Final[int]  = 1000
DEFAULT_MAX_RESULTS:      Final[int]  = 100
MAX_QUERY_TEXT_LENGTH:    Final[int]  = 2000

# ── Cache ──────────────────────────────────────────────────────────────────────

SEARCH_CACHE_TTL:       Final[float] = 60.0
SEARCH_CACHE_MAX_SIZE:  Final[int]   = 500

# ── Tokenization ──────────────────────────────────────────────────────────────

MIN_TOKEN_LENGTH:         Final[int]   = 2
DEFAULT_FUZZY_THRESHOLD:  Final[float] = 0.75

# ── Scoring boosts ────────────────────────────────────────────────────────────

TITLE_BOOST:        Final[float] = 2.5
TAG_BOOST:          Final[float] = 1.5
CONTENT_BOOST:      Final[float] = 1.0
EXACT_TITLE_BONUS:  Final[float] = 3.0
ALL_TOKENS_BONUS:   Final[float] = 1.5
RECENCY_DECAY_DAYS: Final[float] = 30.0
