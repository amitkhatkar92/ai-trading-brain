"""
iios/knowledge/graph/__init__.py
========================================
Knowledge Graph Engine (Wave 3 extension) + the original KnowledgeGraph reference
implementation (used internally by KnowledgeManager/KnowledgeEngine).
"""
from __future__ import annotations

# ── Original reference graph (keep for KnowledgeManager compatibility) ────────
from .knowledge_graph import KnowledgeGraph, get_knowledge_graph, reset_knowledge_graph

# ── Constants + exceptions ────────────────────────────────────────────────────
from .graph_constants import (
    GraphNodeType, GraphEdgeType, NodeStatus, EdgeStatus,
    TraversalMode, GraphSortOrder, GraphQueryOp, GraphEvent,
    GRAPH_NAMESPACE, DEFAULT_EDGE_WEIGHT, DEFAULT_EDGE_CONFIDENCE,
    GRAPH_SCHEMA_VERSION, SYSTEM_GRAPH_ACTOR,
)
from .graph_exceptions import (
    GraphError, GraphNodeNotFoundError, GraphNodeAlreadyExistsError,
    GraphEdgeNotFoundError, GraphEdgeAlreadyExistsError,
    GraphPathNotFoundError, GraphCycleError, GraphValidationError,
    GraphIntegrityError, GraphStorageError, GraphTraversalError,
    GraphAnalyticsError, GraphEngineError, GraphRegistryError,
    GraphSubgraphError, GraphMergeError, GraphAccessDeniedError,
)

# ── Models ────────────────────────────────────────────────────────────────────
from .models import (
    GraphMetadata, GraphNode, GraphEdge, GraphPath, PathStep,
    GraphCluster, GraphSubgraph, GraphStatistics, NodeStatistics, ImpactResult,
)

# ── Storage ───────────────────────────────────────────────────────────────────
from .storage import (
    NodeFilter, EdgeFilter, PageRequest, NodeQuery, EdgeQuery, GraphPageResult,
    GraphStorage,    get_graph_storage,    reset_graph_storage,
    GraphCache,      get_graph_cache,      reset_graph_cache,
    GraphIndex,      get_graph_index,      reset_graph_index,
    GraphRepository, get_graph_repository, reset_graph_repository,
)

# ── Engine + façade ───────────────────────────────────────────────────────────
from .graph_context  import (
    GraphContext, get_graph_context, reset_graph_context,
    current_graph_actor, current_graph_operation_id, graph_operation,
)
from .graph_factory  import GraphFactory,  get_graph_factory
from .graph_engine   import GraphEngine,   get_graph_engine,   reset_graph_engine
from .graph_manager  import GraphManager,  get_graph_manager,  reset_graph_manager
from .graph_registry import GraphRegistry, get_graph_registry, reset_graph_registry

__all__ = [
    # legacy
    "KnowledgeGraph", "get_knowledge_graph", "reset_knowledge_graph",
    # constants
    "GraphNodeType", "GraphEdgeType", "NodeStatus", "EdgeStatus",
    "TraversalMode", "GraphSortOrder", "GraphQueryOp", "GraphEvent",
    "GRAPH_NAMESPACE", "DEFAULT_EDGE_WEIGHT", "DEFAULT_EDGE_CONFIDENCE",
    "GRAPH_SCHEMA_VERSION", "SYSTEM_GRAPH_ACTOR",
    # exceptions
    "GraphError", "GraphNodeNotFoundError", "GraphNodeAlreadyExistsError",
    "GraphEdgeNotFoundError", "GraphEdgeAlreadyExistsError",
    "GraphPathNotFoundError", "GraphCycleError", "GraphValidationError",
    "GraphIntegrityError", "GraphStorageError", "GraphTraversalError",
    "GraphAnalyticsError", "GraphEngineError", "GraphRegistryError",
    "GraphSubgraphError", "GraphMergeError", "GraphAccessDeniedError",
    # models
    "GraphMetadata", "GraphNode", "GraphEdge", "GraphPath", "PathStep",
    "GraphCluster", "GraphSubgraph", "GraphStatistics", "NodeStatistics", "ImpactResult",
    # storage
    "NodeFilter", "EdgeFilter", "PageRequest", "NodeQuery", "EdgeQuery", "GraphPageResult",
    "GraphStorage",    "get_graph_storage",    "reset_graph_storage",
    "GraphCache",      "get_graph_cache",      "reset_graph_cache",
    "GraphIndex",      "get_graph_index",      "reset_graph_index",
    "GraphRepository", "get_graph_repository", "reset_graph_repository",
    # engine
    "GraphContext", "get_graph_context", "reset_graph_context",
    "current_graph_actor", "current_graph_operation_id", "graph_operation",
    "GraphFactory",  "get_graph_factory",
    "GraphEngine",   "get_graph_engine",   "reset_graph_engine",
    "GraphManager",  "get_graph_manager",  "reset_graph_manager",
    "GraphRegistry", "get_graph_registry", "reset_graph_registry",
]
