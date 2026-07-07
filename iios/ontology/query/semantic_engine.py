"""
iios/ontology/query/semantic_engine.py
=======================================
Semantic reasoning engine for the IIOS ontology layer.

Responsible for:
  * Semantic similarity between types (LCA-based distance)
  * Concept expansion (BFS neighborhood)
  * Related-type discovery (shared namespace, shared parent, relationships)
  * Semantic ranking of a result set against a query term
  * Ontology-graph neighbourhood discovery
  * Detecting semantic equivalence (same canonical URI or alias)

Singleton: get_semantic_engine() / reset_semantic_engine()
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Optional

from .query_constants import (
    SemanticRelation,
    MAX_EXPAND_RADIUS,
    MAX_QUERY_DEPTH,
    SEMANTIC_DISTANCE_INFINITY,
    DEFAULT_FUZZY_THRESHOLD,
)
from .query_factory import (
    SemanticRequest,
    SemanticResult,
    SimilarType,
    get_query_factory,
)
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import OntologyTypeDef

__all__ = [
    "SemanticEngine",
    "get_semantic_engine",
    "reset_semantic_engine",
]

_LOG = logging.getLogger("iios.ontology.query.semantic")


class SemanticEngine:
    """
    Semantic reasoning engine.

    All methods are read-only against the registry and safe to call
    concurrently.
    """

    def __init__(self) -> None:
        self._similarity_count = 0
        self._expand_count     = 0
        self._rank_count       = 0
        self._lock             = threading.Lock()

    # ── High-level request API ────────────────────────────────────────────────

    def process_request(self, request: SemanticRequest) -> SemanticResult:
        t0      = time.perf_counter()
        factory = get_query_factory()

        similar      = self.find_similar(request.type_uri, top_k=request.top_k)
        neighborhood = self.expand_concept(request.type_uri, radius=request.radius)

        # Filter by relation if specified
        if request.relation is not None:
            similar = [s for s in similar if s.relation == request.relation]

        duration = (time.perf_counter() - t0) * 1_000.0
        return factory.make_semantic_result(
            request      = request,
            similar      = similar,
            neighborhood = neighborhood,
            duration_ms  = duration,
        )

    # ── Similarity ────────────────────────────────────────────────────────────

    def find_similar(
        self,
        type_uri: str,
        top_k:    int = 10,
    ) -> list[SimilarType]:
        """
        Return the *top_k* most semantically similar types to *type_uri*.

        Similarity is computed as 1 / (distance + 1).
        """
        mgr = get_registry_manager()
        td  = mgr.get_type_or_none(type_uri)
        if td is None:
            return []

        all_types = mgr.list_all_types()
        scored:   list[SimilarType] = []

        for other in all_types:
            if other.uri == type_uri:
                continue
            score, relation = self._similarity_and_relation(td, other)
            if score > 0.0:
                scored.append(SimilarType(
                    type_def = other,
                    score    = score,
                    relation = relation,
                ))

        scored.sort(key=lambda x: x.score, reverse=True)

        with self._lock:
            self._similarity_count += 1

        return scored[:top_k]

    def semantic_distance(self, uri_a: str, uri_b: str) -> float:
        """
        Compute the semantic distance between two types.

        Distance = length of path between them via their LCA in the
        inheritance tree.  Returns SEMANTIC_DISTANCE_INFINITY if they
        share no common ancestor.
        """
        if uri_a == uri_b:
            return 0.0

        mgr          = get_registry_manager()
        ancestors_a  = set(mgr.ancestors_of(uri_a, include_self=True))
        ancestors_b  = set(mgr.ancestors_of(uri_b, include_self=True))
        common       = ancestors_a & ancestors_b

        if not common:
            # Try namespace proximity as fallback
            td_a = mgr.get_type_or_none(uri_a)
            td_b = mgr.get_type_or_none(uri_b)
            if td_a and td_b and td_a.namespace_uri == td_b.namespace_uri:
                return SEMANTIC_DISTANCE_INFINITY / 2
            return SEMANTIC_DISTANCE_INFINITY

        # Find the *closest* common ancestor (minimum sum of edge distances)
        chain_a: list[str] = mgr.ancestors_of(uri_a, include_self=True)
        chain_b: list[str] = mgr.ancestors_of(uri_b, include_self=True)

        best = SEMANTIC_DISTANCE_INFINITY
        for lca in common:
            if lca in chain_a and lca in chain_b:
                dist = chain_a.index(lca) + chain_b.index(lca)
                if dist < best:
                    best = float(dist)

        return best

    def is_semantically_equivalent(self, uri_a: str, uri_b: str) -> bool:
        """
        Return True if *uri_a* and *uri_b* resolve to the same canonical URI
        (i.e. they are aliases of each other).
        """
        mgr    = get_registry_manager()
        canon_a = mgr.canonical_uri(uri_a)
        canon_b = mgr.canonical_uri(uri_b)
        if canon_a is None or canon_b is None:
            return uri_a == uri_b
        return canon_a == canon_b

    # ── Concept expansion ─────────────────────────────────────────────────────

    def expand_concept(
        self,
        type_uri: str,
        radius:   int = MAX_EXPAND_RADIUS,
    ) -> list[OntologyTypeDef]:
        """
        BFS from *type_uri* in the combined hierarchy + relationship graph,
        returning all types reachable within *radius* hops.

        The returned list excludes the starting type itself.
        """
        mgr      = get_registry_manager()
        visited  = {type_uri}
        result:  list[OntologyTypeDef] = []
        queue:   deque[tuple[str, int]] = deque([(type_uri, 0)])

        while queue:
            current_uri, depth = queue.popleft()
            if depth >= radius:
                continue

            neighbours = self._neighbours(current_uri, mgr)
            for nb_uri in neighbours:
                if nb_uri not in visited:
                    visited.add(nb_uri)
                    nb = mgr.get_type_or_none(nb_uri)
                    if nb:
                        result.append(nb)
                        queue.append((nb_uri, depth + 1))

        with self._lock:
            self._expand_count += 1

        return result

    def discover_neighborhood(
        self,
        type_uri: str,
        depth:    int = 2,
    ) -> dict:
        """
        Return a structured neighborhood view centred on *type_uri*:
        {
          "center": uri,
          "parents":     [uri, ...],
          "children":    [uri, ...],
          "siblings":    [uri, ...],
          "related":     [uri, ...],
        }
        """
        mgr = get_registry_manager()
        td  = mgr.get_type_or_none(type_uri)

        parents:  list[str] = mgr.ancestors_of(type_uri)
        children: list[str] = sorted(mgr.children_of(type_uri))
        siblings: list[str] = []

        if td and td.parent_uri:
            siblings = sorted(
                mgr.children_of(td.parent_uri) - {type_uri}
            )

        related_rels = mgr.relationships_for_source(type_uri)
        related      = list({r.target_type_uri for r in related_rels
                             if r.target_type_uri != type_uri})

        return {
            "center":   type_uri,
            "parents":  parents[:depth],
            "children": children,
            "siblings": siblings,
            "related":  related,
        }

    # ── Find related ──────────────────────────────────────────────────────────

    def find_related(
        self,
        type_uri: str,
        relation: SemanticRelation,
    ) -> list[OntologyTypeDef]:
        """
        Return types related to *type_uri* via the specified *relation*.
        """
        mgr = get_registry_manager()

        if relation == SemanticRelation.SUBTYPE_OF:
            # All descendants
            uris = mgr.descendants_of(type_uri)
            return [td for u in uris if (td := mgr.get_type_or_none(u))]

        if relation == SemanticRelation.SUPERTYPE_OF:
            # All ancestors
            uris = mgr.ancestors_of(type_uri)
            return [td for u in uris if (td := mgr.get_type_or_none(u))]

        if relation == SemanticRelation.SIBLING:
            td = mgr.get_type_or_none(type_uri)
            if td and td.parent_uri:
                sibling_uris = mgr.children_of(td.parent_uri) - {type_uri}
                return [s for u in sibling_uris if (s := mgr.get_type_or_none(u))]
            return []

        if relation == SemanticRelation.RELATED_TO:
            rels   = mgr.relationships_for_source(type_uri)
            rels  += mgr.relationships_for_target(type_uri)
            uris   = {r.target_type_uri for r in rels if r.target_type_uri != type_uri}
            uris  |= {r.source_type_uri for r in rels if r.source_type_uri != type_uri}
            return [td for u in uris if (td := mgr.get_type_or_none(u))]

        if relation == SemanticRelation.SAME_AS:
            # Semantic equivalents (aliases)
            td    = mgr.get_type_or_none(type_uri)
            if not td:
                return []
            canon = mgr.canonical_uri(type_uri)
            if canon is None:
                return []
            # All types that share the same canonical URI (aliases)
            return [
                other for other in mgr.list_all_types()
                if other.uri != type_uri
                and mgr.canonical_uri(other.uri) == canon
            ]

        return []

    # ── Semantic ranking ──────────────────────────────────────────────────────

    def semantic_rank(
        self,
        types:      list[OntologyTypeDef],
        query_term: str,
    ) -> list[OntologyTypeDef]:
        """
        Re-rank *types* by descending relevance to *query_term*.

        Scoring considers:
          1. Exact URI match (1.0)
          2. Exact name match (0.9)
          3. Name starts with query (0.7)
          4. Name contains query (0.5)
          5. Label match (0.4)
          6. Description match (0.2)
        """
        q_lower = query_term.lower()

        def score(td: OntologyTypeDef) -> float:
            name_l = td.name.lower()
            uri_l  = td.uri.lower()
            if uri_l == q_lower:
                return 1.0
            if name_l == q_lower:
                return 0.9
            if name_l.startswith(q_lower):
                return 0.7
            if q_lower in name_l:
                return 0.5
            if any(q_lower in lbl.lower() for lbl in td.labels):
                return 0.4
            if q_lower in td.description.lower():
                return 0.2
            return 0.0

        with self._lock:
            self._rank_count += 1

        return sorted(types, key=score, reverse=True)

    # ── Query suggestions ─────────────────────────────────────────────────────

    def suggest_queries(
        self,
        partial: str,
        limit:   int = 10,
    ) -> list[str]:
        """
        Return ontology URI prefixes / names that match *partial* as query
        autocompletion suggestions.
        """
        mgr     = get_registry_manager()
        partial_l = partial.lower()
        seen:   set[str] = set()
        result: list[str] = []

        for td in mgr.list_all_types():
            for candidate in [td.name, td.uri] + td.aliases:
                if candidate.lower().startswith(partial_l) and candidate not in seen:
                    seen.add(candidate)
                    result.append(candidate)
                    if len(result) >= limit:
                        return result

        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    def _neighbours(
        self,
        uri: str,
        mgr,
    ) -> set[str]:
        """
        Return the set of URIs directly reachable from *uri* via:
          * parent link
          * child links
          * relationships (source → target, target → source)
        """
        neighbours: set[str] = set()

        td = mgr.get_type_or_none(uri)
        if td:
            if td.parent_uri:
                neighbours.add(td.parent_uri)
            neighbours.update(mgr.children_of(uri))

        for rel in mgr.relationships_for_source(uri):
            if rel.target_type_uri:
                neighbours.add(rel.target_type_uri)
        for rel in mgr.relationships_for_target(uri):
            if rel.source_type_uri:
                neighbours.add(rel.source_type_uri)

        return neighbours

    def _similarity_and_relation(
        self,
        a: OntologyTypeDef,
        b: OntologyTypeDef,
    ) -> tuple[float, Optional[SemanticRelation]]:
        """
        Compute similarity score and dominant semantic relation between *a* and *b*.
        """
        mgr = get_registry_manager()

        # Direct inheritance
        if mgr.is_subtype_of(b.uri, a.uri):
            dist  = len(mgr.ancestors_of(b.uri))
            score = 1.0 / (dist + 1)
            return score, SemanticRelation.SUBTYPE_OF

        if mgr.is_subtype_of(a.uri, b.uri):
            dist  = len(mgr.ancestors_of(a.uri))
            score = 1.0 / (dist + 1)
            return score, SemanticRelation.SUPERTYPE_OF

        # Sibling (same parent)
        if a.parent_uri and a.parent_uri == b.parent_uri:
            return 0.6, SemanticRelation.SIBLING

        # Same namespace
        if a.namespace_uri == b.namespace_uri:
            return 0.3, SemanticRelation.RELATED_TO

        # Connected via relationship
        rels_a = {r.target_type_uri for r in mgr.relationships_for_source(a.uri)}
        if b.uri in rels_a:
            return 0.4, SemanticRelation.RELATED_TO

        # Shared ancestor within distance 4
        try:
            dist = self.semantic_distance(a.uri, b.uri)
            if dist < SEMANTIC_DISTANCE_INFINITY and dist <= 4:
                return max(0.1, 1.0 / (dist + 1)), SemanticRelation.RELATED_TO
        except Exception:
            pass

        return 0.0, None

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            return {
                "similarity_count": self._similarity_count,
                "expand_count":     self._expand_count,
                "rank_count":       self._rank_count,
            }


# ── Singleton ─────────────────────────────────────────────────────────────────

_sem_lock = threading.Lock()
_sem_instance: Optional[SemanticEngine] = None


def get_semantic_engine() -> SemanticEngine:
    global _sem_instance
    if _sem_instance is None:
        with _sem_lock:
            if _sem_instance is None:
                _sem_instance = SemanticEngine()
    return _sem_instance


def reset_semantic_engine() -> None:
    global _sem_instance
    with _sem_lock:
        _sem_instance = None
