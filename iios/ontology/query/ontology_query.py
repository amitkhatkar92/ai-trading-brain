"""
iios/ontology/query/ontology_query.py
=======================================
Query builder and executor for ontology type lookups.

Usage::

    from iios.ontology.query import OntologyQuery, OntologyQueryEngine

    results = (
        OntologyQuery()
        .in_namespace("iios.observation")
        .subtype_of("iios.observation.Observation")
        .has_label("market")
        .not_abstract()
        .build()
        .execute()
    )
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from ..ontology_constants import MAX_QUERY_RESULTS, QueryOperator
from ..ontology_exceptions import OntologyQueryError
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import OntologyTypeDef

__all__ = [
    "OntologyFilter",
    "OntologyQuery",
    "OntologyQueryResult",
    "OntologyQueryEngine",
    "get_query_engine",
    "reset_query_engine",
]

_LOG  = logging.getLogger("iios.ontology.query")
_lock = threading.Lock()
_engine: Optional["OntologyQueryEngine"] = None


# ── Filter ─────────────────────────────────────────────────────────────────────

@dataclass
class OntologyFilter:
    """A single filter condition on a type field."""
    operator: QueryOperator
    field:    str
    value:    object

    def matches(self, td: OntologyTypeDef, mgr) -> bool:
        op  = self.operator
        val = self.value

        if op == QueryOperator.EQ:
            return getattr(td, self.field, None) == val
        if op == QueryOperator.NEQ:
            return getattr(td, self.field, None) != val
        if op == QueryOperator.CONTAINS:
            attr = getattr(td, self.field, "")
            if isinstance(attr, str):
                return str(val).lower() in attr.lower()
            if isinstance(attr, list):
                return val in attr
            return False
        if op == QueryOperator.STARTS:
            attr = getattr(td, self.field, "")
            return isinstance(attr, str) and attr.lower().startswith(str(val).lower())
        if op == QueryOperator.IN:
            attr = getattr(td, self.field, None)
            return attr in (val if isinstance(val, (list, set, tuple)) else [val])
        if op == QueryOperator.HAS_PROP:
            return str(val) in td.properties
        if op == QueryOperator.SUBTYPE_OF:
            return mgr.is_subtype_of(td.uri, str(val))
        if op == QueryOperator.SUPERTYPE_OF:
            return mgr.is_subtype_of(str(val), td.uri)
        return False


# ── Query builder ──────────────────────────────────────────────────────────────

class OntologyQuery:
    """Fluent builder for ontology type queries."""

    def __init__(self) -> None:
        self._filters:    list[OntologyFilter] = []
        self._namespaces: list[str]            = []
        self._max_results: int                  = MAX_QUERY_RESULTS
        self._include_abstract: bool            = True
        self._include_deprecated: bool          = False

    # ── Filter methods ─────────────────────────────────────────────────────────

    def in_namespace(self, ns_uri: str) -> "OntologyQuery":
        self._namespaces.append(ns_uri)
        return self

    def subtype_of(self, base_uri: str) -> "OntologyQuery":
        self._filters.append(OntologyFilter(QueryOperator.SUBTYPE_OF, "uri", base_uri))
        return self

    def supertype_of(self, child_uri: str) -> "OntologyQuery":
        self._filters.append(OntologyFilter(QueryOperator.SUPERTYPE_OF, "uri", child_uri))
        return self

    def has_label(self, label: str) -> "OntologyQuery":
        self._filters.append(OntologyFilter(QueryOperator.CONTAINS, "labels", label))
        return self

    def has_tag(self, tag: str) -> "OntologyQuery":
        self._filters.append(OntologyFilter(QueryOperator.CONTAINS, "tags", tag))
        return self

    def has_property(self, prop_name: str) -> "OntologyQuery":
        self._filters.append(OntologyFilter(QueryOperator.HAS_PROP, "properties", prop_name))
        return self

    def named(self, name: str) -> "OntologyQuery":
        self._filters.append(OntologyFilter(QueryOperator.EQ, "name", name))
        return self

    def name_contains(self, substring: str) -> "OntologyQuery":
        self._filters.append(OntologyFilter(QueryOperator.CONTAINS, "name", substring))
        return self

    def uri_starts_with(self, prefix: str) -> "OntologyQuery":
        self._filters.append(OntologyFilter(QueryOperator.STARTS, "uri", prefix))
        return self

    def not_abstract(self) -> "OntologyQuery":
        self._include_abstract = False
        return self

    def include_deprecated(self) -> "OntologyQuery":
        self._include_deprecated = True
        return self

    def limit(self, n: int) -> "OntologyQuery":
        self._max_results = max(1, n)
        return self

    # ── Execute ────────────────────────────────────────────────────────────────

    def build(self) -> "OntologyQuery":
        """Return self — execute via .execute() or pass to query engine."""
        return self

    def execute(self) -> "OntologyQueryResult":
        return get_query_engine().execute(self)


# ── Query result ───────────────────────────────────────────────────────────────

@dataclass
class OntologyQueryResult:
    types:        list[OntologyTypeDef]
    total_found:  int
    duration_ms:  float
    truncated:    bool = False

    def __len__(self) -> int:
        return len(self.types)

    def __iter__(self):
        return iter(self.types)

    def first(self) -> Optional[OntologyTypeDef]:
        return self.types[0] if self.types else None

    def to_dict(self) -> dict:
        return {
            "count":       len(self.types),
            "total_found": self.total_found,
            "duration_ms": round(self.duration_ms, 3),
            "truncated":   self.truncated,
            "uris":        [t.uri for t in self.types],
        }


# ── Query engine ───────────────────────────────────────────────────────────────

class OntologyQueryEngine:
    """Executes OntologyQuery objects against the live registry."""

    def __init__(self) -> None:
        self._query_count = 0

    @property
    def _mgr(self):
        return get_registry_manager()

    def execute(self, query: OntologyQuery) -> OntologyQueryResult:
        t0 = time.perf_counter()
        self._query_count += 1

        try:
            # Candidate pool
            if query._namespaces:
                candidates: list[OntologyTypeDef] = []
                for ns in query._namespaces:
                    candidates.extend(self._mgr.types_in_namespace(ns))
            else:
                candidates = self._mgr.list_all_types()

            # Pre-filters (fast)
            if not query._include_abstract:
                candidates = [t for t in candidates if not t.abstract]
            if not query._include_deprecated:
                candidates = [t for t in candidates if not t.deprecated]

            # Apply dynamic filters
            filtered: list[OntologyTypeDef] = []
            for td in candidates:
                if all(f.matches(td, self._mgr) for f in query._filters):
                    filtered.append(td)

            total    = len(filtered)
            truncated = total > query._max_results
            filtered  = filtered[:query._max_results]
            duration  = (time.perf_counter() - t0) * 1_000.0

            return OntologyQueryResult(
                types       = filtered,
                total_found = total,
                duration_ms = duration,
                truncated   = truncated,
            )
        except Exception as exc:
            raise OntologyQueryError(f"Query execution failed: {exc}") from exc

    def stats(self) -> dict:
        return {"query_count": self._query_count}


def get_query_engine() -> OntologyQueryEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = OntologyQueryEngine()
    return _engine


def reset_query_engine() -> None:
    global _engine
    with _lock:
        _engine = None
