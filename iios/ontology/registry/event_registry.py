"""iios/ontology/registry/event_registry.py — typed view for event namespace."""
from __future__ import annotations
import threading
from typing import Optional
from ..ontology_exceptions import TypeNotFoundError
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import OntologyTypeDef

__all__ = ["EventRegistry", "get_event_registry", "reset_event_registry"]
_NS = "iios.event"
_lock = threading.Lock()
_inst: Optional["EventRegistry"] = None


class EventRegistry:
    @property
    def _mgr(self): return get_registry_manager()
    def get_type(self, name_or_uri: str) -> OntologyTypeDef:
        td = self._mgr.get_type_or_none(name_or_uri)
        if td is None: raise TypeNotFoundError(name_or_uri)
        return td
    def get_type_or_none(self, name_or_uri: str) -> Optional[OntologyTypeDef]:
        td = self._mgr.get_type_or_none(name_or_uri)
        return td if (td and td.namespace_uri == _NS) else None
    def all_types(self) -> list[OntologyTypeDef]:
        return self._mgr.types_in_namespace(_NS)
    def concrete_types(self) -> list[OntologyTypeDef]:
        return [t for t in self.all_types() if not t.abstract]
    def subtypes_of(self, name_or_uri: str) -> list[OntologyTypeDef]:
        td = self.get_type(name_or_uri)
        return [self._mgr.get_type_or_none(u) for u in self._mgr.descendants_of(td.uri) if self._mgr.get_type_or_none(u)]  # type: ignore[misc]
    def count(self) -> int:
        return len(self.all_types())


def get_event_registry() -> EventRegistry:
    global _inst
    if _inst is None:
        with _lock:
            if _inst is None:
                _inst = EventRegistry()
    return _inst


def reset_event_registry() -> None:
    global _inst
    with _lock:
        _inst = None
