"""
iios/ontology/query/resolution_engine.py
==========================================
Semantic resolution engine for the IIOS ontology layer.

Responsible for:
  * Resolving a string reference (URI / alias / name) to a canonical type
  * Walking the full inheritance chain for a type
  * Merging inherited properties across the chain
  * Resolving relationship definitions by URI or name
  * Fuzzy-matching type names for "did you mean?" lookups
  * Resolving property cross-references (REF properties)

Singleton: get_resolution_engine() / reset_resolution_engine()
"""

from __future__ import annotations

import difflib
import logging
import threading
import time
from typing import Optional

from .query_constants import (
    ResolutionStrategy,
    MAX_RESOLUTION_DEPTH,
    DEFAULT_FUZZY_THRESHOLD,
    MAX_FUZZY_CANDIDATES,
    SYSTEM_QUERY_ACTOR,
)
from .query_exceptions import (
    AliasResolutionError,
    CircularResolutionError,
    InheritanceResolutionError,
    ReferenceResolutionError,
    ResolutionError,
)
from .query_context import get_query_context
from .query_factory import ResolutionRequest, ResolutionResult, get_query_factory
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import (
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
)

__all__ = [
    "ResolutionEngine",
    "get_resolution_engine",
    "reset_resolution_engine",
]

_LOG = logging.getLogger("iios.ontology.query.resolution")


class ResolutionEngine:
    """
    Semantic resolution engine.

    All resolution methods are safe to call concurrently — they take
    only local state (registry reads) and never mutate shared structures.
    """

    def __init__(self) -> None:
        self._resolve_count       = 0
        self._inheritance_count   = 0
        self._fuzzy_count         = 0
        self._lock                = threading.Lock()

    # ── High-level request API ────────────────────────────────────────────────

    def resolve_request(self, request: ResolutionRequest) -> ResolutionResult:
        """Execute a ResolutionRequest and return a ResolutionResult."""
        t0 = time.perf_counter()
        ctx = get_query_context()
        factory = get_query_factory()

        with ctx.resolution(request.ref, request.strategy):
            resolved, canonical, path, strategy_used = self._resolve(
                request.ref,
                request.strategy,
            )

        duration = (time.perf_counter() - t0) * 1_000.0
        return factory.make_resolution_result(
            request         = request,
            resolved        = resolved,
            canonical_uri   = canonical,
            resolution_path = path,
            strategy_used   = strategy_used,
            duration_ms     = duration,
        )

    # ── Core resolution ───────────────────────────────────────────────────────

    def resolve(
        self,
        ref:      str,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> Optional[OntologyTypeDef]:
        """
        Resolve *ref* to a type using *strategy*.
        Returns None if unresolvable (does not raise).
        """
        resolved, _, _, _ = self._resolve(ref, strategy)
        with self._lock:
            self._resolve_count += 1
        return resolved

    def resolve_or_raise(
        self,
        ref:      str,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> OntologyTypeDef:
        """Like resolve() but raises ResolutionError if not found."""
        result = self.resolve(ref, strategy)
        if result is None:
            raise ResolutionError(
                f"Cannot resolve {ref!r} using strategy {strategy.value}",
                code="QRY-020",
            )
        return result

    def resolve_alias(self, alias: str) -> Optional[str]:
        """
        Return the canonical URI for *alias*, or None if not registered.
        """
        mgr = get_registry_manager()
        return mgr.canonical_uri(alias)

    def resolve_canonical(self, ref: str) -> Optional[str]:
        """Return the canonical URI for *ref* (URI or alias)."""
        mgr = get_registry_manager()
        return mgr.canonical_uri(ref)

    # ── Inheritance chain ─────────────────────────────────────────────────────

    def resolve_inheritance_chain(
        self,
        type_uri:   str,
        max_depth:  int = MAX_RESOLUTION_DEPTH,
    ) -> list[OntologyTypeDef]:
        """
        Return the full ancestry list for *type_uri*, ordered from
        the type itself up to the root:

            [type, parent, grandparent, ..., root]

        Raises CircularResolutionError if a cycle is detected.
        """
        mgr  = get_registry_manager()
        seen: set[str]         = set()
        chain: list[str]       = []
        current                = type_uri

        for depth in range(max_depth + 1):
            if current in seen:
                raise CircularResolutionError(chain + [current])
            td = mgr.get_type_or_none(current)
            if td is None:
                break
            seen.add(current)
            chain.append(current)
            if td.parent_uri is None:
                break
            current = td.parent_uri
        else:
            raise InheritanceResolutionError(
                type_uri,
                f"Exceeded max depth {max_depth}",
            )

        with self._lock:
            self._inheritance_count += 1

        return [mgr.get_type_or_none(u) for u in chain if mgr.get_type_or_none(u) is not None]  # type: ignore[misc]

    def resolve_all_properties(
        self,
        type_uri: str,
    ) -> dict[str, OntologyProperty]:
        """
        Return fully merged property map for *type_uri*, including all
        inherited properties (child overrides parent).
        """
        mgr   = get_registry_manager()
        chain = self.resolve_inheritance_chain(type_uri)
        # Root-first, so child properties naturally override parent ones
        merged: dict[str, OntologyProperty] = {}
        for ancestor in reversed(chain):
            merged.update(ancestor.properties)
        return merged

    # ── Relationship resolution ───────────────────────────────────────────────

    def resolve_relationship(
        self,
        ref: str,
    ) -> Optional[OntologyRelationshipDef]:
        """
        Resolve *ref* to a relationship definition.
        *ref* may be a full URI or a relationship name (case-insensitive).
        """
        mgr = get_registry_manager()
        # Direct URI match
        rel = mgr.get_relationship(ref)
        if rel:
            return rel
        # Name match (case-insensitive)
        ref_lower = ref.lower()
        for r in mgr.list_relationships():
            if r.name.lower() == ref_lower:
                return r
        return None

    # ── Label-based resolution ────────────────────────────────────────────────

    def resolve_by_label(
        self,
        label:          str,
        namespace_hint: Optional[str] = None,
    ) -> list[OntologyTypeDef]:
        """
        Return all types that carry *label* in their labels list.
        Optionally restricted to *namespace_hint*.
        """
        mgr     = get_registry_manager()
        label_l = label.lower()

        if namespace_hint:
            candidates = mgr.types_in_namespace(namespace_hint)
        else:
            candidates = mgr.list_all_types()

        return [
            td for td in candidates
            if any(label_l in lbl.lower() for lbl in td.labels)
        ]

    # ── Fuzzy resolution ──────────────────────────────────────────────────────

    def resolve_fuzzy(
        self,
        query:     str,
        threshold: float                  = DEFAULT_FUZZY_THRESHOLD,
        top_k:     int                    = MAX_FUZZY_CANDIDATES,
        namespace: Optional[str]          = None,
    ) -> list[tuple[OntologyTypeDef, float]]:
        """
        Fuzzy-match *query* against all type names and URIs.

        Returns a list of (TypeDef, score) sorted by score descending.
        Score is in [0.0, 1.0]; only entries ≥ *threshold* are included.
        """
        mgr = get_registry_manager()
        if namespace:
            candidates = mgr.types_in_namespace(namespace)
        else:
            candidates = mgr.list_all_types()

        query_l = query.lower()
        scored:  list[tuple[OntologyTypeDef, float]] = []

        for td in candidates:
            score = self._fuzzy_score(query_l, td)
            if score >= threshold:
                scored.append((td, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        with self._lock:
            self._fuzzy_count += 1

        return scored[:top_k]

    # ── Reference property resolution ────────────────────────────────────────

    def resolve_property_ref(
        self,
        prop: OntologyProperty,
    ) -> Optional[OntologyTypeDef]:
        """
        If *prop* is a REF-type property, resolve its ref_uri to a type.
        Returns None if prop has no ref_uri or the ref is unresolvable.
        """
        if not prop.ref_uri:
            return None
        return get_registry_manager().get_type_or_none(prop.ref_uri)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _resolve(
        self,
        ref:      str,
        strategy: ResolutionStrategy,
    ) -> tuple[Optional[OntologyTypeDef], Optional[str], list[str], Optional[ResolutionStrategy]]:
        """
        Core resolution loop.
        Returns (resolved, canonical_uri, resolution_path, strategy_used).
        """
        mgr = get_registry_manager()

        if strategy == ResolutionStrategy.AUTO:
            # Try each strategy in cost order
            for s in (
                ResolutionStrategy.EXACT,
                ResolutionStrategy.ALIAS,
                ResolutionStrategy.CANONICAL,
            ):
                td, canon, path, used = self._resolve(ref, s)
                if td is not None:
                    return td, canon, path, used
            return None, None, [], None

        if strategy == ResolutionStrategy.EXACT:
            td = mgr.get_type_or_none(ref)
            if td:
                return td, td.uri, [ref], ResolutionStrategy.EXACT
            return None, None, [], None

        if strategy == ResolutionStrategy.ALIAS:
            canon = mgr.canonical_uri(ref)
            if canon and canon != ref:
                td = mgr.get_type_or_none(canon)
                if td:
                    return td, canon, [ref, canon], ResolutionStrategy.ALIAS
            return None, None, [], None

        if strategy == ResolutionStrategy.CANONICAL:
            canon = mgr.canonical_uri(ref)
            if canon:
                td = mgr.get_type_or_none(canon)
                if td:
                    return td, canon, [ref, canon], ResolutionStrategy.CANONICAL
            return None, None, [], None

        if strategy == ResolutionStrategy.FUZZY:
            matches = self.resolve_fuzzy(ref, threshold=DEFAULT_FUZZY_THRESHOLD, top_k=1)
            if matches:
                td, score = matches[0]
                return td, td.uri, [ref, td.uri], ResolutionStrategy.FUZZY
            return None, None, [], None

        if strategy == ResolutionStrategy.INHERITANCE:
            # Walk up from each type whose name starts with ref
            for td in mgr.list_all_types():
                if td.name.lower() == ref.lower():
                    return td, td.uri, [ref, td.uri], ResolutionStrategy.INHERITANCE
            return None, None, [], None

        if strategy == ResolutionStrategy.HIERARCHICAL:
            # Search anywhere in the hierarchy tree
            td = mgr.get_type_or_none(ref)
            if td:
                return td, td.uri, [ref], ResolutionStrategy.HIERARCHICAL
            return None, None, [], None

        return None, None, [], None

    @staticmethod
    def _fuzzy_score(query_l: str, td: OntologyTypeDef) -> float:
        """Compute highest similarity score across name, URI, labels, aliases."""
        candidates = [td.name.lower(), td.uri.lower()]
        candidates.extend(lbl.lower() for lbl in td.labels)
        candidates.extend(a.lower() for a in td.aliases)

        best = 0.0
        for candidate in candidates:
            ratio = difflib.SequenceMatcher(None, query_l, candidate).ratio()
            if ratio > best:
                best = ratio
        return best

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            return {
                "resolve_count":     self._resolve_count,
                "inheritance_count": self._inheritance_count,
                "fuzzy_count":       self._fuzzy_count,
            }


# ── Singleton ─────────────────────────────────────────────────────────────────

_res_lock = threading.Lock()
_res_instance: Optional[ResolutionEngine] = None


def get_resolution_engine() -> ResolutionEngine:
    global _res_instance
    if _res_instance is None:
        with _res_lock:
            if _res_instance is None:
                _res_instance = ResolutionEngine()
    return _res_instance


def reset_resolution_engine() -> None:
    global _res_instance
    with _res_lock:
        _res_instance = None
