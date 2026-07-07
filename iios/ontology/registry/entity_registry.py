"""
iios/ontology/registry/entity_registry.py
============================================
Typed view over the master registry for entity-namespace types.
"""

from __future__ import annotations

import threading
from typing import Optional

from ..ontology_exceptions import TypeNotFoundError
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import OntologyRelationshipDef, OntologyTypeDef

__all__ = [
    "EntityRegistry",
    "get_entity_registry",
    "reset_entity_registry",
]

_NS   = "iios.entity"
_lock = threading.Lock()
_inst: Optional["EntityRegistry"] = None


class EntityRegistry:
    """Domain-scoped view of all entity types registered in the ontology."""

    @property
    def _mgr(self):
        return get_registry_manager()

    # ── Lookup ─────────────────────────────────────────────────────────────────

    def get_type(self, name_or_uri: str) -> OntologyTypeDef:
        """Return entity type by name or URI. Raises TypeNotFoundError."""
        td = self._mgr.get_type_or_none(name_or_uri)
        if td is None or not (td.namespace_uri == _NS or name_or_uri.startswith(_NS)):
            raise TypeNotFoundError(name_or_uri)
        return td

    def get_type_or_none(self, name_or_uri: str) -> Optional[OntologyTypeDef]:
        td = self._mgr.get_type_or_none(name_or_uri)
        if td is None:
            return None
        if td.namespace_uri != _NS:
            return None
        return td

    def has(self, name_or_uri: str) -> bool:
        return self.get_type_or_none(name_or_uri) is not None

    # ── Listing ────────────────────────────────────────────────────────────────

    def all_types(self) -> list[OntologyTypeDef]:
        return self._mgr.types_in_namespace(_NS)

    def concrete_types(self) -> list[OntologyTypeDef]:
        from ..ontology_constants import TypeKind
        return [t for t in self.all_types() if not t.abstract and t.kind != TypeKind.ABSTRACT]

    def abstract_types(self) -> list[OntologyTypeDef]:
        return [t for t in self.all_types() if t.abstract]

    # ── Hierarchy ──────────────────────────────────────────────────────────────

    def subtypes_of(self, name_or_uri: str, include_self: bool = False) -> list[OntologyTypeDef]:
        td = self.get_type(name_or_uri)
        desc_uris = self._mgr.descendants_of(td.uri, include_self=include_self)
        return [self._mgr.get_type_or_none(u) for u in desc_uris if self._mgr.get_type_or_none(u)]  # type: ignore[misc]

    def supertypes_of(self, name_or_uri: str) -> list[OntologyTypeDef]:
        td         = self.get_type(name_or_uri)
        ancestor_uris = self._mgr.ancestors_of(td.uri)
        return [self._mgr.get_type_or_none(u) for u in ancestor_uris if self._mgr.get_type_or_none(u)]  # type: ignore[misc]

    # ── Relationships ──────────────────────────────────────────────────────────

    def relationships_from(self, name_or_uri: str) -> list[OntologyRelationshipDef]:
        td = self.get_type(name_or_uri)
        return self._mgr.relationships_for_source(td.uri)

    def relationships_to(self, name_or_uri: str) -> list[OntologyRelationshipDef]:
        td = self.get_type(name_or_uri)
        return self._mgr.relationships_for_target(td.uri)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def count(self) -> int:
        return len(self.all_types())


def get_entity_registry() -> EntityRegistry:
    global _inst
    if _inst is None:
        with _lock:
            if _inst is None:
                _inst = EntityRegistry()
    return _inst


def reset_entity_registry() -> None:
    global _inst
    with _lock:
        _inst = None
