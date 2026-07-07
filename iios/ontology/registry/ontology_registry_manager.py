"""
iios/ontology/registry/ontology_registry_manager.py
======================================================
Master registry coordinator.  All compiled ontologies are registered
here after compilation.  Provides the single entry point for:
  - Type lookup by URI / name / alias
  - Namespace lookup
  - Relationship lookup
  - Hierarchy traversal
  - Cross-ontology queries
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from ..ontology_constants import RegistryScope
from ..ontology_exceptions import (
    NamespaceAlreadyExistsError,
    NamespaceNotFoundError,
    TypeAlreadyExistsError,
    TypeNotFoundError,
)
from ..runtime.runtime_object import (
    CompiledOntology,
    OntologyNamespace,
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
)

__all__ = [
    "OntologyRegistryManager",
    "get_registry_manager",
    "reset_registry_manager",
]

_LOG  = logging.getLogger("iios.ontology.registry")
_lock = threading.Lock()
_manager: Optional["OntologyRegistryManager"] = None


class OntologyRegistryManager:
    """
    Thread-safe master registry for all compiled ontology artefacts.

    Data structures:
    - _namespaces:     namespace_uri → OntologyNamespace
    - _types:          type_uri → OntologyTypeDef  (canonical index)
    - _aliases:        alias / short name → canonical type URI
    - _relationships:  rel_uri → OntologyRelationshipDef
    - _children:       parent_uri → set of direct child URIs
    - _compiled:       ontology_name → CompiledOntology
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

        self._namespaces:    dict[str, OntologyNamespace]        = {}
        self._types:         dict[str, OntologyTypeDef]          = {}
        self._aliases:       dict[str, str]                      = {}
        self._relationships: dict[str, OntologyRelationshipDef]  = {}
        self._children:      dict[str, set[str]]                 = {}
        self._compiled:      dict[str, CompiledOntology]         = {}
        # Reverse: type URI → source ontology name
        self._type_source:   dict[str, str]                      = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register_compiled(
        self,
        compiled:  CompiledOntology,
        overwrite: bool = True,
    ) -> None:
        """Register all artefacts from a CompiledOntology."""
        with self._lock:
            name = compiled.name
            self._compiled[name] = compiled

            # Namespace
            ns_uri = compiled.namespace_uri
            ns     = compiled.document.namespace
            if ns_uri not in self._namespaces:
                self._namespaces[ns_uri] = ns

            # Types
            for uri, typedef in compiled.types.items():
                self._types[uri]       = typedef
                self._type_source[uri] = name

            # Aliases
            for alias, canonical in compiled.alias_index.items():
                if alias not in self._aliases or overwrite:
                    self._aliases[alias] = canonical

            # Relationships
            for uri, reldef in compiled.relationships.items():
                self._relationships[uri] = reldef

            # Children (merge)
            for parent_uri, child_set in compiled.children.items():
                existing = self._children.setdefault(parent_uri, set())
                existing.update(child_set)

            _LOG.debug(
                "Registered ontology %r: %d types, %d relationships",
                name, len(compiled.types), len(compiled.relationships),
            )

    # ── Type lookup ────────────────────────────────────────────────────────────

    def get_type(self, uri: str) -> OntologyTypeDef:
        """Resolve *uri* (or alias) to a type definition. Raises TypeNotFoundError."""
        with self._lock:
            result = self._resolve_type(uri)
        if result is None:
            raise TypeNotFoundError(uri)
        return result

    def get_type_or_none(self, uri: str) -> Optional[OntologyTypeDef]:
        with self._lock:
            return self._resolve_type(uri)

    def has_type(self, uri: str) -> bool:
        with self._lock:
            return self._resolve_type(uri) is not None

    def _resolve_type(self, ref: str) -> Optional[OntologyTypeDef]:
        """Internal — no lock; caller must hold self._lock."""
        direct = self._types.get(ref)
        if direct:
            return direct
        canonical = self._aliases.get(ref)
        if canonical:
            return self._types.get(canonical)
        return None

    def canonical_uri(self, ref: str) -> Optional[str]:
        """Return the canonical URI for an alias or URI. None if not found."""
        with self._lock:
            if ref in self._types:
                return ref
            return self._aliases.get(ref)

    # ── Namespace lookup ───────────────────────────────────────────────────────

    def get_namespace(self, uri: str) -> OntologyNamespace:
        with self._lock:
            ns = self._namespaces.get(uri)
        if ns is None:
            raise NamespaceNotFoundError(uri)
        return ns

    def get_namespace_or_none(self, uri: str) -> Optional[OntologyNamespace]:
        with self._lock:
            return self._namespaces.get(uri)

    def list_namespaces(self) -> list[OntologyNamespace]:
        with self._lock:
            return list(self._namespaces.values())

    def types_in_namespace(self, namespace_uri: str) -> list[OntologyTypeDef]:
        with self._lock:
            return [t for t in self._types.values() if t.namespace_uri == namespace_uri]

    # ── Relationship lookup ────────────────────────────────────────────────────

    def get_relationship(self, uri: str) -> Optional[OntologyRelationshipDef]:
        with self._lock:
            return self._relationships.get(uri)

    def relationships_for_source(
        self,
        source_type_uri: str,
    ) -> list[OntologyRelationshipDef]:
        """All relationships whose source matches *source_type_uri*."""
        with self._lock:
            return [
                r for r in self._relationships.values()
                if r.source_type_uri == source_type_uri
            ]

    def relationships_for_target(
        self,
        target_type_uri: str,
    ) -> list[OntologyRelationshipDef]:
        """All relationships whose target matches *target_type_uri*."""
        with self._lock:
            return [
                r for r in self._relationships.values()
                if r.target_type_uri == target_type_uri
            ]

    def list_relationships(self) -> list[OntologyRelationshipDef]:
        with self._lock:
            return list(self._relationships.values())

    # ── Hierarchy ─────────────────────────────────────────────────────────────

    def children_of(self, uri: str) -> set[str]:
        """Direct children URIs."""
        with self._lock:
            return set(self._children.get(uri, set()))

    def descendants_of(self, uri: str, include_self: bool = False) -> set[str]:
        """All descendant URIs (BFS)."""
        with self._lock:
            result: set[str] = set()
            if include_self:
                result.add(uri)
            queue = list(self._children.get(uri, set()))
            while queue:
                child = queue.pop()
                if child not in result:
                    result.add(child)
                    queue.extend(self._children.get(child, set()))
            return result

    def ancestors_of(self, uri: str, include_self: bool = False) -> list[str]:
        """Walk up the parent chain and return ancestor URIs (nearest first)."""
        with self._lock:
            result: list[str] = []
            if include_self:
                result.append(uri)
            current = uri
            for _ in range(64):
                td = self._types.get(current)
                if td is None or td.parent_uri is None:
                    break
                result.append(td.parent_uri)
                current = td.parent_uri
            return result

    def is_subtype_of(self, candidate_uri: str, base_uri: str) -> bool:
        """Return True if *candidate_uri* is *base_uri* or a descendant of it."""
        if candidate_uri == base_uri:
            return True
        return candidate_uri in self.descendants_of(base_uri)

    # ── Properties ────────────────────────────────────────────────────────────

    def all_properties_of(self, uri: str) -> dict[str, OntologyProperty]:
        """
        Return merged properties (own + inherited) for a type URI.
        Falls back to own properties if the compiled index is unavailable.
        """
        with self._lock:
            source_name = self._type_source.get(uri)
            if source_name:
                compiled = self._compiled.get(source_name)
                if compiled:
                    idx = compiled.property_index.get(uri)
                    if idx is not None:
                        return dict(idx)
            # Fallback: own properties only
            td = self._types.get(uri)
            if td:
                return dict(td.properties)
            return {}

    # ── Global queries ─────────────────────────────────────────────────────────

    def search_types(
        self,
        query:     str,
        scope:     RegistryScope = RegistryScope.GLOBAL,
        max_results: int          = 100,
    ) -> list[OntologyTypeDef]:
        """
        Simple substring search over type names, URIs, labels, and aliases.
        Case-insensitive.
        """
        q = query.lower()
        with self._lock:
            results: list[OntologyTypeDef] = []
            for td in self._types.values():
                if (
                    q in td.name.lower()
                    or q in td.uri.lower()
                    or any(q in lbl.lower() for lbl in td.labels)
                    or any(q in alias.lower() for alias in td.aliases)
                    or q in td.description.lower()
                ):
                    results.append(td)
                    if len(results) >= max_results:
                        break
            return results

    def list_all_types(self) -> list[OntologyTypeDef]:
        with self._lock:
            return list(self._types.values())

    def all_type_uris(self) -> list[str]:
        with self._lock:
            return list(self._types.keys())

    # ── Compiled ontology access ───────────────────────────────────────────────

    def get_compiled(self, name: str) -> Optional[CompiledOntology]:
        with self._lock:
            return self._compiled.get(name)

    def all_compiled(self) -> list[CompiledOntology]:
        with self._lock:
            return list(self._compiled.values())

    def compiled_names(self) -> list[str]:
        with self._lock:
            return list(self._compiled.keys())

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_types":         len(self._types),
                "total_relationships": len(self._relationships),
                "total_namespaces":    len(self._namespaces),
                "total_aliases":       len(self._aliases),
                "compiled_ontologies": len(self._compiled),
            }

    def clear(self) -> None:
        with self._lock:
            self._namespaces.clear()
            self._types.clear()
            self._aliases.clear()
            self._relationships.clear()
            self._children.clear()
            self._compiled.clear()
            self._type_source.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_registry_manager() -> OntologyRegistryManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = OntologyRegistryManager()
    return _manager


def reset_registry_manager() -> None:
    global _manager
    with _lock:
        _manager = None
