"""
iios/ontology/query/query_factory.py
=====================================
Dataclass models and factory for the IIOS Ontology Query &
Semantic Resolution Engine.

All request / result objects are pure data containers with
.to_dict() support and no I/O.
"""

from __future__ import annotations

import time
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .query_constants import (
    QueryType,
    ResolutionStrategy,
    NavigationDirection,
    SortOrder,
    QueryStatus,
    SemanticRelation,
    DEFAULT_RESULT_LIMIT,
    SYSTEM_QUERY_ACTOR,
)
from ..runtime.runtime_object import (
    OntologyTypeDef,
    OntologyRelationshipDef,
    OntologyNamespace,
    OntologyProperty,
)

__all__ = [
    # Request models
    "QueryRequest",
    "ResolutionRequest",
    "NavigationRequest",
    "SearchRequest",
    "SemanticRequest",
    # Result models
    "QueryResult",
    "ResolutionResult",
    "NavigationResult",
    "SearchResult",
    "SemanticResult",
    "SimilarType",
    # Factory
    "QueryFactory",
    "get_query_factory",
    "reset_query_factory",
]


# ══════════════════════════════════════════════════════════════════════════════
#  Request models
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class QueryRequest:
    """Specification for a single ontology query operation."""
    query_type:    QueryType
    target:        str                       # URI, name, or alias
    filters:       dict[str, Any]            = field(default_factory=dict)
    options:       dict[str, Any]            = field(default_factory=dict)
    limit:         int                       = DEFAULT_RESULT_LIMIT
    sort_order:    SortOrder                 = SortOrder.RELEVANCE
    include_abstract: bool                   = True
    include_deprecated: bool                 = False
    namespace_hint: Optional[str]            = None
    query_id:      str                       = field(default_factory=lambda: str(uuid.uuid4()))
    actor:         str                       = SYSTEM_QUERY_ACTOR
    created_at:    float                     = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "query_id":          self.query_id,
            "query_type":        self.query_type.value,
            "target":            self.target,
            "filters":           self.filters,
            "options":           self.options,
            "limit":             self.limit,
            "sort_order":        self.sort_order.value,
            "include_abstract":  self.include_abstract,
            "include_deprecated": self.include_deprecated,
            "namespace_hint":    self.namespace_hint,
            "actor":             self.actor,
            "created_at":        self.created_at,
        }


@dataclass
class ResolutionRequest:
    """Specification for a single resolution operation."""
    ref:              str
    strategy:         ResolutionStrategy   = ResolutionStrategy.AUTO
    context_ontology: Optional[str]        = None   # Restrict scope to one ontology
    actor:            str                  = SYSTEM_QUERY_ACTOR
    request_id:       str                  = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "request_id":       self.request_id,
            "ref":              self.ref,
            "strategy":         self.strategy.value,
            "context_ontology": self.context_ontology,
            "actor":            self.actor,
        }


@dataclass
class NavigationRequest:
    """Specification for a hierarchy / graph traversal operation."""
    start_uri:  str
    direction:  NavigationDirection      = NavigationDirection.DOWN
    max_depth:  int                      = 16
    relation:   Optional[SemanticRelation] = None
    stop_at:    Optional[str]            = None     # Stop when this URI is reached
    actor:      str                      = SYSTEM_QUERY_ACTOR
    request_id: str                      = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "start_uri":  self.start_uri,
            "direction":  self.direction.value,
            "max_depth":  self.max_depth,
            "relation":   self.relation.value if self.relation else None,
            "stop_at":    self.stop_at,
            "actor":      self.actor,
        }


@dataclass
class SearchRequest:
    """Specification for a text / semantic search operation."""
    query_term:     str
    namespace_hint: Optional[str]    = None
    max_results:    int              = DEFAULT_RESULT_LIMIT
    include_abstract: bool           = True
    include_deprecated: bool         = False
    fuzzy_threshold: float           = 0.5
    actor:          str              = SYSTEM_QUERY_ACTOR
    request_id:     str              = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "request_id":      self.request_id,
            "query_term":      self.query_term,
            "namespace_hint":  self.namespace_hint,
            "max_results":     self.max_results,
            "fuzzy_threshold": self.fuzzy_threshold,
            "actor":           self.actor,
        }


@dataclass
class SemanticRequest:
    """Specification for a semantic expansion / similarity operation."""
    type_uri:    str
    relation:    Optional[SemanticRelation] = None
    top_k:       int                        = 10
    radius:      int                        = 3
    actor:       str                        = SYSTEM_QUERY_ACTOR
    request_id:  str                        = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "type_uri":   self.type_uri,
            "relation":   self.relation.value if self.relation else None,
            "top_k":      self.top_k,
            "radius":     self.radius,
            "actor":      self.actor,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Result models
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class QueryResult:
    """Generic result from any QueryRequest execution."""
    request:    QueryRequest
    types:      list[OntologyTypeDef]   = field(default_factory=list)
    status:     QueryStatus             = QueryStatus.COMPLETED
    duration_ms: float                  = 0.0
    from_cache:  bool                   = False
    truncated:   bool                   = False
    metadata:    dict[str, Any]         = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.types)

    def first(self) -> Optional[OntologyTypeDef]:
        return self.types[0] if self.types else None

    def uris(self) -> list[str]:
        return [t.uri for t in self.types]

    def to_dict(self) -> dict:
        return {
            "query_id":   self.request.query_id,
            "query_type": self.request.query_type.value,
            "target":     self.request.target,
            "count":      self.count,
            "status":     self.status.value,
            "duration_ms": round(self.duration_ms, 3),
            "from_cache": self.from_cache,
            "truncated":  self.truncated,
            "uris":       self.uris(),
            "metadata":   self.metadata,
        }


@dataclass
class ResolutionResult:
    """Result of a ResolutionRequest."""
    request:        ResolutionRequest
    resolved:       Optional[OntologyTypeDef]  = None
    canonical_uri:  Optional[str]              = None
    resolution_path: list[str]                 = field(default_factory=list)
    strategy_used:  Optional[ResolutionStrategy] = None
    duration_ms:    float                      = 0.0
    from_cache:     bool                       = False

    @property
    def succeeded(self) -> bool:
        return self.resolved is not None

    def to_dict(self) -> dict:
        return {
            "request_id":      self.request.request_id,
            "ref":             self.request.ref,
            "succeeded":       self.succeeded,
            "canonical_uri":   self.canonical_uri,
            "resolution_path": self.resolution_path,
            "strategy_used":   self.strategy_used.value if self.strategy_used else None,
            "duration_ms":     round(self.duration_ms, 3),
            "from_cache":      self.from_cache,
        }


@dataclass
class NavigationResult:
    """Result of a NavigationRequest traversal."""
    request:     NavigationRequest
    path:        list[str]            = field(default_factory=list)  # Ordered URI sequence
    visited:     list[OntologyTypeDef] = field(default_factory=list)
    depth:       int                  = 0
    duration_ms: float                = 0.0
    truncated:   bool                 = False

    def to_dict(self) -> dict:
        return {
            "request_id":  self.request.request_id,
            "start_uri":   self.request.start_uri,
            "direction":   self.request.direction.value,
            "path":        self.path,
            "depth":       self.depth,
            "count":       len(self.visited),
            "duration_ms": round(self.duration_ms, 3),
            "truncated":   self.truncated,
        }


@dataclass
class SimilarType:
    """A type + similarity score from a semantic similarity search."""
    type_def:   OntologyTypeDef
    score:      float           # 0.0 = unrelated, 1.0 = identical
    relation:   Optional[SemanticRelation] = None

    def to_dict(self) -> dict:
        return {
            "uri":      self.type_def.uri,
            "name":     self.type_def.name,
            "score":    round(self.score, 4),
            "relation": self.relation.value if self.relation else None,
        }


@dataclass
class SearchResult:
    """Result of a SearchRequest."""
    request:     SearchRequest
    matches:     list[tuple[OntologyTypeDef, float]]  = field(default_factory=list)  # (type, score)
    duration_ms: float                                 = 0.0
    from_cache:  bool                                  = False

    @property
    def count(self) -> int:
        return len(self.matches)

    def types(self) -> list[OntologyTypeDef]:
        return [t for t, _ in self.matches]

    def to_dict(self) -> dict:
        return {
            "request_id":  self.request.request_id,
            "query_term":  self.request.query_term,
            "count":       self.count,
            "duration_ms": round(self.duration_ms, 3),
            "from_cache":  self.from_cache,
            "matches": [
                {"uri": t.uri, "name": t.name, "score": round(s, 4)}
                for t, s in self.matches
            ],
        }


@dataclass
class SemanticResult:
    """Result of a SemanticRequest expansion / neighborhood discovery."""
    request:     SemanticRequest
    similar:     list[SimilarType]  = field(default_factory=list)
    neighborhood: list[OntologyTypeDef] = field(default_factory=list)
    duration_ms: float              = 0.0

    def to_dict(self) -> dict:
        return {
            "request_id":   self.request.request_id,
            "type_uri":     self.request.type_uri,
            "similar_count": len(self.similar),
            "similar":      [s.to_dict() for s in self.similar],
            "neighborhood_count": len(self.neighborhood),
            "neighborhood": [t.uri for t in self.neighborhood],
            "duration_ms":  round(self.duration_ms, 3),
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Factory
# ══════════════════════════════════════════════════════════════════════════════

class QueryFactory:
    """Convenience constructors for all query/result objects."""

    # ── Requests ──────────────────────────────────────────────────────────────

    def make_query(
        self,
        query_type: QueryType,
        target:     str,
        *,
        limit:         int           = DEFAULT_RESULT_LIMIT,
        sort_order:    SortOrder     = SortOrder.RELEVANCE,
        include_abstract: bool       = True,
        include_deprecated: bool     = False,
        namespace_hint: Optional[str] = None,
        filters:       dict[str, Any] | None = None,
        options:       dict[str, Any] | None = None,
        actor:         str           = SYSTEM_QUERY_ACTOR,
    ) -> QueryRequest:
        return QueryRequest(
            query_type        = query_type,
            target            = target,
            filters           = filters or {},
            options           = options or {},
            limit             = limit,
            sort_order        = sort_order,
            include_abstract  = include_abstract,
            include_deprecated = include_deprecated,
            namespace_hint    = namespace_hint,
            actor             = actor,
        )

    def make_resolution(
        self,
        ref:              str,
        strategy:         ResolutionStrategy = ResolutionStrategy.AUTO,
        context_ontology: Optional[str]      = None,
        actor:            str                = SYSTEM_QUERY_ACTOR,
    ) -> ResolutionRequest:
        return ResolutionRequest(
            ref              = ref,
            strategy         = strategy,
            context_ontology = context_ontology,
            actor            = actor,
        )

    def make_navigation(
        self,
        start_uri:  str,
        direction:  NavigationDirection    = NavigationDirection.DOWN,
        max_depth:  int                    = 16,
        relation:   Optional[SemanticRelation] = None,
        stop_at:    Optional[str]          = None,
        actor:      str                    = SYSTEM_QUERY_ACTOR,
    ) -> NavigationRequest:
        return NavigationRequest(
            start_uri = start_uri,
            direction = direction,
            max_depth = max_depth,
            relation  = relation,
            stop_at   = stop_at,
            actor     = actor,
        )

    def make_search(
        self,
        query_term:      str,
        namespace_hint:  Optional[str] = None,
        max_results:     int           = DEFAULT_RESULT_LIMIT,
        fuzzy_threshold: float         = 0.5,
        actor:           str           = SYSTEM_QUERY_ACTOR,
    ) -> SearchRequest:
        return SearchRequest(
            query_term      = query_term,
            namespace_hint  = namespace_hint,
            max_results     = max_results,
            fuzzy_threshold = fuzzy_threshold,
            actor           = actor,
        )

    def make_semantic(
        self,
        type_uri: str,
        relation: Optional[SemanticRelation] = None,
        top_k:    int                        = 10,
        radius:   int                        = 3,
        actor:    str                        = SYSTEM_QUERY_ACTOR,
    ) -> SemanticRequest:
        return SemanticRequest(
            type_uri = type_uri,
            relation = relation,
            top_k    = top_k,
            radius   = radius,
            actor    = actor,
        )

    # ── Results ───────────────────────────────────────────────────────────────

    def make_query_result(
        self,
        request:     QueryRequest,
        types:       list[OntologyTypeDef] | None = None,
        status:      QueryStatus                  = QueryStatus.COMPLETED,
        duration_ms: float                        = 0.0,
        from_cache:  bool                         = False,
        truncated:   bool                         = False,
        metadata:    dict[str, Any] | None        = None,
    ) -> QueryResult:
        return QueryResult(
            request     = request,
            types       = types or [],
            status      = status,
            duration_ms = duration_ms,
            from_cache  = from_cache,
            truncated   = truncated,
            metadata    = metadata or {},
        )

    def make_resolution_result(
        self,
        request:         ResolutionRequest,
        resolved:        Optional[OntologyTypeDef]     = None,
        canonical_uri:   Optional[str]                 = None,
        resolution_path: list[str] | None              = None,
        strategy_used:   Optional[ResolutionStrategy]  = None,
        duration_ms:     float                         = 0.0,
        from_cache:      bool                          = False,
    ) -> ResolutionResult:
        return ResolutionResult(
            request         = request,
            resolved        = resolved,
            canonical_uri   = canonical_uri,
            resolution_path = resolution_path or [],
            strategy_used   = strategy_used,
            duration_ms     = duration_ms,
            from_cache      = from_cache,
        )

    def make_navigation_result(
        self,
        request:     NavigationRequest,
        path:        list[str] | None              = None,
        visited:     list[OntologyTypeDef] | None  = None,
        depth:       int                           = 0,
        duration_ms: float                         = 0.0,
        truncated:   bool                          = False,
    ) -> NavigationResult:
        return NavigationResult(
            request     = request,
            path        = path or [],
            visited     = visited or [],
            depth       = depth,
            duration_ms = duration_ms,
            truncated   = truncated,
        )

    def make_search_result(
        self,
        request:     SearchRequest,
        matches:     list[tuple[OntologyTypeDef, float]] | None = None,
        duration_ms: float                                      = 0.0,
        from_cache:  bool                                       = False,
    ) -> SearchResult:
        return SearchResult(
            request     = request,
            matches     = matches or [],
            duration_ms = duration_ms,
            from_cache  = from_cache,
        )

    def make_semantic_result(
        self,
        request:      SemanticRequest,
        similar:      list[SimilarType] | None              = None,
        neighborhood: list[OntologyTypeDef] | None          = None,
        duration_ms:  float                                  = 0.0,
    ) -> SemanticResult:
        return SemanticResult(
            request      = request,
            similar      = similar or [],
            neighborhood = neighborhood or [],
            duration_ms  = duration_ms,
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_factory_lock = threading.Lock()
_factory_instance: Optional[QueryFactory] = None


def get_query_factory() -> QueryFactory:
    global _factory_instance
    if _factory_instance is None:
        with _factory_lock:
            if _factory_instance is None:
                _factory_instance = QueryFactory()
    return _factory_instance


def reset_query_factory() -> None:
    global _factory_instance
    with _factory_lock:
        _factory_instance = None
