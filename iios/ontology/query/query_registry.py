"""
iios/ontology/query/query_registry.py
======================================
Named-query registry.

Stores reusable, pre-defined queries identified by a stable string ID.
Built-in named queries for standard IIOS lookup patterns are registered
automatically on first use.

Singleton: get_query_registry() / reset_query_registry()
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .query_constants import (
    QueryType,
    QueryStatus,
    SortOrder,
    MAX_NAMED_QUERIES,
    QID_ALL_TYPES,
    QID_ENTITY_TYPES,
    QID_ABSTRACT_TYPES,
    QID_CONCRETE_TYPES,
    QID_ALL_RELATIONSHIPS,
    QID_ALL_NAMESPACES,
    SYSTEM_QUERY_ACTOR,
)
from .query_exceptions import (
    DuplicateNamedQueryError,
    UnknownNamedQueryError,
    NamedQueryError,
)
from .query_factory import QueryRequest, get_query_factory

__all__ = [
    "NamedQuery",
    "QueryRegistry",
    "get_query_registry",
    "reset_query_registry",
]


# ── Named query definition ────────────────────────────────────────────────────

@dataclass
class NamedQuery:
    """
    A stored, reusable query specification.

    *builder* is an optional callable that overrides the stored request when
    executed with runtime parameters.
    """
    query_id:    str
    name:        str
    description: str
    query_type:  QueryType
    default_target: str           = ""
    parameters:  dict[str, Any]   = field(default_factory=dict)
    builder:     Optional[Callable[..., QueryRequest]] = field(default=None, repr=False)
    tags:        list[str]        = field(default_factory=list)
    builtin:     bool             = False

    def build(self, **overrides: Any) -> QueryRequest:
        """
        Materialise a QueryRequest.

        If *builder* is set, call it with **overrides.
        Otherwise build from stored target / parameters merged with overrides.
        """
        if self.builder is not None:
            return self.builder(**overrides)

        factory = get_query_factory()
        target  = overrides.pop("target", self.default_target)
        merged  = {**self.parameters, **overrides}
        return factory.make_query(
            query_type     = self.query_type,
            target         = target,
            filters        = merged.get("filters", {}),
            options        = merged.get("options", {}),
            limit          = merged.get("limit", 100),
            sort_order     = merged.get("sort_order", SortOrder.RELEVANCE),
            namespace_hint = merged.get("namespace_hint"),
            actor          = merged.get("actor", SYSTEM_QUERY_ACTOR),
        )

    def to_dict(self) -> dict:
        return {
            "query_id":       self.query_id,
            "name":           self.name,
            "description":    self.description,
            "query_type":     self.query_type.value,
            "default_target": self.default_target,
            "parameters":     self.parameters,
            "tags":           self.tags,
            "builtin":        self.builtin,
        }


# ── Registry ──────────────────────────────────────────────────────────────────

class QueryRegistry:
    """
    Stores and retrieves NamedQuery definitions.

    Thread-safe via an internal RLock.
    """

    def __init__(self) -> None:
        self._queries: dict[str, NamedQuery] = {}
        self._lock    = threading.RLock()
        self._register_builtins()

    # ── Registration ─────────────────────────────────────────────────────────

    def register(
        self,
        query_id:       str,
        name:           str,
        description:    str,
        query_type:     QueryType,
        default_target: str              = "",
        parameters:     dict[str, Any] | None = None,
        builder:        Optional[Callable[..., QueryRequest]] = None,
        tags:           list[str] | None = None,
        overwrite:      bool             = False,
    ) -> NamedQuery:
        with self._lock:
            if query_id in self._queries and not overwrite:
                raise DuplicateNamedQueryError(query_id)
            if len(self._queries) >= MAX_NAMED_QUERIES and query_id not in self._queries:
                raise NamedQueryError(
                    f"Named query registry is full ({MAX_NAMED_QUERIES})",
                    code="QRY-060",
                )
            nq = NamedQuery(
                query_id       = query_id,
                name           = name,
                description    = description,
                query_type     = query_type,
                default_target = default_target,
                parameters     = parameters or {},
                builder        = builder,
                tags           = tags or [],
                builtin        = False,
            )
            self._queries[query_id] = nq
            return nq

    def unregister(self, query_id: str) -> bool:
        with self._lock:
            if query_id in self._queries:
                nq = self._queries[query_id]
                if nq.builtin:
                    raise NamedQueryError(
                        f"Cannot unregister built-in query {query_id!r}",
                        code="QRY-060",
                    )
                del self._queries[query_id]
                return True
            return False

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(self, query_id: str) -> NamedQuery:
        with self._lock:
            nq = self._queries.get(query_id)
            if nq is None:
                raise UnknownNamedQueryError(query_id)
            return nq

    def has(self, query_id: str) -> bool:
        with self._lock:
            return query_id in self._queries

    def get_by_tag(self, tag: str) -> list[NamedQuery]:
        with self._lock:
            return [nq for nq in self._queries.values() if tag in nq.tags]

    def get_by_type(self, query_type: QueryType) -> list[NamedQuery]:
        with self._lock:
            return [
                nq for nq in self._queries.values()
                if nq.query_type == query_type
            ]

    def all_ids(self) -> list[str]:
        with self._lock:
            return list(self._queries.keys())

    def all_queries(self) -> list[NamedQuery]:
        with self._lock:
            return list(self._queries.values())

    def builtin_queries(self) -> list[NamedQuery]:
        with self._lock:
            return [nq for nq in self._queries.values() if nq.builtin]

    # ── Execute convenience ───────────────────────────────────────────────────

    def build_request(self, query_id: str, **overrides: Any) -> QueryRequest:
        """Retrieve named query and materialise a QueryRequest."""
        return self.get(query_id).build(**overrides)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            total    = len(self._queries)
            builtins = sum(1 for nq in self._queries.values() if nq.builtin)
            return {
                "total":    total,
                "builtins": builtins,
                "custom":   total - builtins,
            }

    def clear_custom(self) -> int:
        """Remove all non-builtin queries. Returns count removed."""
        with self._lock:
            custom = [
                qid for qid, nq in self._queries.items()
                if not nq.builtin
            ]
            for qid in custom:
                del self._queries[qid]
            return len(custom)

    # ── Built-in registration ─────────────────────────────────────────────────

    def _register_builtins(self) -> None:
        factory = get_query_factory()

        def _make(qid: str, name: str, desc: str, qt: QueryType, target: str = "", **kw: Any) -> None:
            nq = NamedQuery(
                query_id       = qid,
                name           = name,
                description    = desc,
                query_type     = qt,
                default_target = target,
                parameters     = kw,
                builtin        = True,
            )
            self._queries[qid] = nq

        _make(
            QID_ALL_TYPES,
            name        = "All Types",
            desc        = "Returns every registered type across all ontologies.",
            qt          = QueryType.TYPE_LOOKUP,
            target      = "",
        )
        _make(
            QID_ENTITY_TYPES,
            name        = "Entity Types",
            desc        = "Returns all types in the entity ontology.",
            qt          = QueryType.TYPE_LOOKUP,
            target      = "",
            namespace_hint = "iios.entity",
        )
        _make(
            QID_ABSTRACT_TYPES,
            name        = "Abstract Types",
            desc        = "Returns all abstract (non-instantiable) types.",
            qt          = QueryType.TYPE_LOOKUP,
            target      = "",
        )
        _make(
            QID_CONCRETE_TYPES,
            name        = "Concrete Types",
            desc        = "Returns all concrete (instantiable) types.",
            qt          = QueryType.TYPE_LOOKUP,
            target      = "",
        )
        _make(
            QID_ALL_RELATIONSHIPS,
            name        = "All Relationships",
            desc        = "Returns every registered relationship definition.",
            qt          = QueryType.RELATIONSHIP_LOOKUP,
            target      = "",
        )
        _make(
            QID_ALL_NAMESPACES,
            name        = "All Namespaces",
            desc        = "Returns every registered namespace.",
            qt          = QueryType.METADATA,
            target      = "",
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_reg_lock = threading.Lock()
_reg_instance: Optional[QueryRegistry] = None


def get_query_registry() -> QueryRegistry:
    global _reg_instance
    if _reg_instance is None:
        with _reg_lock:
            if _reg_instance is None:
                _reg_instance = QueryRegistry()
    return _reg_instance


def reset_query_registry() -> None:
    global _reg_instance
    with _reg_lock:
        _reg_instance = None
