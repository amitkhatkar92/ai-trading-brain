"""
iios/knowledge/graph/graph_exceptions.py
==========================================
Exception hierarchy for the Knowledge Graph Engine.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "GraphError",
    "GraphNodeNotFoundError",
    "GraphNodeAlreadyExistsError",
    "GraphEdgeNotFoundError",
    "GraphEdgeAlreadyExistsError",
    "GraphPathNotFoundError",
    "GraphCycleError",
    "GraphValidationError",
    "GraphIntegrityError",
    "GraphStorageError",
    "GraphQueryError",
    "GraphTraversalError",
    "GraphAnalyticsError",
    "GraphEngineError",
    "GraphEngineNotInitializedError",
    "GraphRegistryError",
    "GraphSubgraphError",
    "GraphMergeError",
    "GraphAccessDeniedError",
]


class GraphError(Exception):
    def __init__(self, message: str = "", code: str = "", context: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.context: dict[str, Any] = context if isinstance(context, dict) else {}


class GraphNodeNotFoundError(GraphError):       pass
class GraphNodeAlreadyExistsError(GraphError):  pass
class GraphEdgeNotFoundError(GraphError):       pass
class GraphEdgeAlreadyExistsError(GraphError):  pass
class GraphPathNotFoundError(GraphError):       pass
class GraphCycleError(GraphError):              pass
class GraphIntegrityError(GraphError):          pass
class GraphStorageError(GraphError):            pass
class GraphQueryError(GraphError):              pass
class GraphTraversalError(GraphError):          pass
class GraphAnalyticsError(GraphError):          pass
class GraphEngineError(GraphError):             pass
class GraphEngineNotInitializedError(GraphError): pass
class GraphRegistryError(GraphError):           pass
class GraphSubgraphError(GraphError):           pass
class GraphMergeError(GraphError):              pass
class GraphAccessDeniedError(GraphError):       pass


class GraphValidationError(GraphError):
    def __init__(self, message: str = "", violations: Any = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.violations: list[str] = list(violations or [])
