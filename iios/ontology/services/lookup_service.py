"""
iios/ontology/services/lookup_service.py
==========================================
Fast lookup service — single entry point for all type/relationship/
namespace resolution, including cross-document lookups.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from ..ontology_exceptions import TypeNotFoundError
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import (
    OntologyNamespace,
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
)

__all__ = [
    "LookupService",
    "get_lookup_service",
    "reset_lookup_service",
]

_LOG  = logging.getLogger("iios.ontology.services.lookup")
_lock = threading.Lock()
_svc: Optional["LookupService"] = None


class LookupService:
    """
    Unified lookup façade over the master registry.

    All callers should prefer this service over directly accessing
    the registry manager — it handles alias resolution, case-insensitive
    matching, and provides sensible defaults.
    """

    @property
    def _mgr(self):
        return get_registry_manager()

    # ── Type lookup ────────────────────────────────────────────────────────────

    def type(self, ref: str) -> OntologyTypeDef:
        """Resolve *ref* (URI, name, or alias) to a type definition."""
        td = self._mgr.get_type_or_none(ref)
        if td is None:
            raise TypeNotFoundError(ref)
        return td

    def type_or_none(self, ref: str) -> Optional[OntologyTypeDef]:
        return self._mgr.get_type_or_none(ref)

    def exists(self, ref: str) -> bool:
        return self._mgr.has_type(ref)

    def canonical_uri(self, ref: str) -> Optional[str]:
        return self._mgr.canonical_uri(ref)

    # ── Property lookup ────────────────────────────────────────────────────────

    def properties_of(self, ref: str) -> dict[str, OntologyProperty]:
        """All properties (own + inherited) for a type."""
        td = self.type(ref)
        return self._mgr.all_properties_of(td.uri)

    def property(self, type_ref: str, prop_name: str) -> Optional[OntologyProperty]:
        """Look up a single property on a type (checks own + inherited)."""
        props = self.properties_of(type_ref)
        return props.get(prop_name)

    # ── Namespace lookup ───────────────────────────────────────────────────────

    def namespace(self, uri: str) -> OntologyNamespace:
        return self._mgr.get_namespace(uri)

    def namespace_or_none(self, uri: str) -> Optional[OntologyNamespace]:
        return self._mgr.get_namespace_or_none(uri)

    def types_in_namespace(self, ns_uri: str) -> list[OntologyTypeDef]:
        return self._mgr.types_in_namespace(ns_uri)

    # ── Relationship lookup ────────────────────────────────────────────────────

    def relationship(self, uri: str) -> Optional[OntologyRelationshipDef]:
        return self._mgr.get_relationship(uri)

    def relationships_from(self, type_ref: str) -> list[OntologyRelationshipDef]:
        td = self.type(type_ref)
        return self._mgr.relationships_for_source(td.uri)

    def relationships_to(self, type_ref: str) -> list[OntologyRelationshipDef]:
        td = self.type(type_ref)
        return self._mgr.relationships_for_target(td.uri)

    # ── Inheritance checks ─────────────────────────────────────────────────────

    def is_subtype_of(self, candidate: str, base: str) -> bool:
        """True if *candidate* IS *base* or inherits from it."""
        return self._mgr.is_subtype_of(candidate, base)

    def common_ancestor(
        self,
        uri_a: str,
        uri_b: str,
    ) -> Optional[str]:
        """
        Return the URI of the nearest common ancestor of *uri_a* and *uri_b*,
        or None if they share no ancestor.
        """
        ancestors_a = set(self._mgr.ancestors_of(uri_a, include_self=True))
        for anc in self._mgr.ancestors_of(uri_b, include_self=True):
            if anc in ancestors_a:
                return anc
        return None

    # ── Global search ──────────────────────────────────────────────────────────

    def search(self, query: str, max_results: int = 50) -> list[OntologyTypeDef]:
        return self._mgr.search_types(query, max_results=max_results)


def get_lookup_service() -> LookupService:
    global _svc
    if _svc is None:
        with _lock:
            if _svc is None:
                _svc = LookupService()
    return _svc


def reset_lookup_service() -> None:
    global _svc
    with _lock:
        _svc = None
