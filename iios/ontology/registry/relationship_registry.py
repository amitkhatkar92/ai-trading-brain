"""iios/ontology/registry/relationship_registry.py — typed view for relationship namespace."""
from __future__ import annotations
import threading
from typing import Optional
from ..ontology_exceptions import TypeNotFoundError
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import OntologyRelationshipDef, OntologyTypeDef

__all__ = ["RelationshipRegistry", "get_relationship_registry", "reset_relationship_registry"]
_NS = "iios.relationship"
_lock = threading.Lock()
_inst: Optional["RelationshipRegistry"] = None


class RelationshipRegistry:
    @property
    def _mgr(self): return get_registry_manager()
    def all_relationships(self) -> list[OntologyRelationshipDef]:
        return [r for r in self._mgr.list_relationships() if r.namespace_uri == _NS]
    def get(self, uri: str) -> Optional[OntologyRelationshipDef]:
        return self._mgr.get_relationship(uri)
    def from_source(self, source_uri: str) -> list[OntologyRelationshipDef]:
        return self._mgr.relationships_for_source(source_uri)
    def to_target(self, target_uri: str) -> list[OntologyRelationshipDef]:
        return self._mgr.relationships_for_target(target_uri)
    def count(self) -> int:
        return len(self.all_relationships())


def get_relationship_registry() -> RelationshipRegistry:
    global _inst
    if _inst is None:
        with _lock:
            if _inst is None:
                _inst = RelationshipRegistry()
    return _inst


def reset_relationship_registry() -> None:
    global _inst
    with _lock:
        _inst = None
