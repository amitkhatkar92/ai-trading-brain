"""iios/ontology/registry/observation_registry.py — typed view for observation namespace."""
from __future__ import annotations
import threading
from typing import Optional
from ..ontology_exceptions import TypeNotFoundError
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import OntologyTypeDef, OntologyProperty

__all__ = ["ObservationRegistry", "get_observation_registry", "reset_observation_registry"]
_NS = "iios.observation"
_lock = threading.Lock()
_inst: Optional["ObservationRegistry"] = None


class ObservationRegistry:
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
    def all_properties_of(self, name_or_uri: str) -> dict[str, OntologyProperty]:
        td = self.get_type(name_or_uri)
        return self._mgr.all_properties_of(td.uri)
    def count(self) -> int:
        return len(self.all_types())
    def root_type(self) -> Optional[OntologyTypeDef]:
        return self._mgr.get_type_or_none(f"{_NS}.Observation")


def get_observation_registry() -> ObservationRegistry:
    global _inst
    if _inst is None:
        with _lock:
            if _inst is None:
                _inst = ObservationRegistry()
    return _inst


def reset_observation_registry() -> None:
    global _inst
    with _lock:
        _inst = None
