"""
iios/knowledge/graph/graph_constants.py
========================================
Enums, type constants, and configuration values for the Knowledge Graph Engine.
"""
from __future__ import annotations

from enum import Enum
from typing import Final


class GraphNodeType(str, Enum):
    KNOWLEDGE   = "knowledge"
    STRATEGY    = "strategy"
    SIGNAL      = "signal"
    AGENT       = "agent"
    MARKET      = "market"
    INSTRUMENT  = "instrument"
    INDICATOR   = "indicator"
    RULE        = "rule"
    CONCEPT     = "concept"
    ENTITY      = "entity"
    CLUSTER     = "cluster"
    VIRTUAL     = "virtual"
    EVENT       = "event"
    METRIC      = "metric"


class GraphEdgeType(str, Enum):
    RELATED_TO      = "related_to"
    DEPENDS_ON      = "depends_on"
    INFLUENCES      = "influences"
    SUPPORTS        = "supports"
    CONTRADICTS     = "contradicts"
    DERIVED_FROM    = "derived_from"
    PART_OF         = "part_of"
    INSTANCE_OF     = "instance_of"
    CAUSES          = "causes"
    CORRELATES_WITH = "correlates_with"
    SUPERSEDES      = "supersedes"
    IMPLEMENTS      = "implements"
    TRIGGERS        = "triggers"
    CONTAINS        = "contains"
    REFERENCES      = "references"
    SIMILAR_TO      = "similar_to"
    OPPOSITE_OF     = "opposite_of"
    PRECEDES        = "precedes"
    FOLLOWS         = "follows"
    GENERATES       = "generates"
    VALIDATES       = "validates"


class NodeStatus(str, Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DELETED  = "deleted"
    PENDING  = "pending"
    MERGED   = "merged"


class EdgeStatus(str, Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    DELETED  = "deleted"
    PENDING  = "pending"
    EXPIRED  = "expired"


class TraversalMode(str, Enum):
    BFS         = "bfs"
    DFS         = "dfs"
    DIJKSTRA    = "dijkstra"
    WEIGHTED_BFS = "weighted_bfs"


class GraphQueryOp(str, Enum):
    EQ          = "eq"
    NEQ         = "neq"
    GT          = "gt"
    GTE         = "gte"
    LT          = "lt"
    LTE         = "lte"
    IN          = "in"
    NOT_IN      = "not_in"
    CONTAINS    = "contains"
    EXISTS      = "exists"


class GraphSortOrder(str, Enum):
    ASC  = "asc"
    DESC = "desc"


class GraphEvent(str, Enum):
    NODE_CREATED   = "node.created"
    NODE_UPDATED   = "node.updated"
    NODE_DELETED   = "node.deleted"
    NODE_MERGED    = "node.merged"
    EDGE_CREATED   = "edge.created"
    EDGE_UPDATED   = "edge.updated"
    EDGE_DELETED   = "edge.deleted"
    GRAPH_CLEARED  = "graph.cleared"
    CYCLE_DETECTED = "graph.cycle_detected"


# ── Numeric constants ─────────────────────────────────────────────────────────

GRAPH_NAMESPACE:              Final[str]   = "iios.graph"
DEFAULT_EDGE_WEIGHT:          Final[float] = 0.5
DEFAULT_EDGE_CONFIDENCE:      Final[float] = 1.0
DEFAULT_PAGE_SIZE:            Final[int]   = 50
MAX_PAGE_SIZE:                Final[int]   = 1_000
MAX_TRAVERSAL_DEPTH:          Final[int]   = 100
MAX_PATH_RESULTS:             Final[int]   = 100
DEFAULT_CACHE_TTL:            Final[float] = 300.0
MAX_CLUSTER_SIZE:             Final[int]   = 10_000
GRAPH_SCHEMA_VERSION:         Final[str]   = "1.0.0"
DEFAULT_PAGERANK_DAMPING:     Final[float] = 0.85
DEFAULT_PAGERANK_ITERATIONS:  Final[int]   = 20
SYSTEM_GRAPH_ACTOR:           Final[str]   = "iios:system"
