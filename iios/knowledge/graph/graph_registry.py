"""
iios/knowledge/graph/graph_registry.py
"""
from __future__ import annotations

import threading
from typing import Any, Optional, Type

from .graph_exceptions import GraphRegistryError

__all__ = ["GraphRegistry", "get_graph_registry", "reset_graph_registry"]

_lock:      threading.Lock             = threading.Lock()
_registry:  Optional["GraphRegistry"] = None


class GraphRegistry:
    """Lazy-resolution registry of all Knowledge Graph Engine components."""

    def __init__(self) -> None:
        self._lock:       threading.RLock    = threading.RLock()
        self._components: dict[str, Any]     = {}
        self._factories:  dict[str, Any]     = {}
        self._auto_register_defaults()

    def _auto_register_defaults(self) -> None:
        # All imports are local to avoid circular imports at module-load time
        from .storage.graph_storage    import get_graph_storage
        from .storage.graph_cache      import get_graph_cache
        from .storage.graph_index      import get_graph_index
        from .storage.graph_repository import get_graph_repository
        from .graph_engine             import get_graph_engine
        from .graph_factory            import get_graph_factory
        from .graph_context            import get_graph_context
        from .graph_manager            import get_graph_manager

        self._factories.update({
            "storage":    get_graph_storage,
            "cache":      get_graph_cache,
            "index":      get_graph_index,
            "repository": get_graph_repository,
            "engine":     get_graph_engine,
            "factory":    get_graph_factory,
            "context":    get_graph_context,
            "manager":    get_graph_manager,
        })

    def register(self, name: str, component: Any, override: bool = True) -> None:
        with self._lock:
            if not override and name in self._components:
                raise GraphRegistryError(
                    f"Component '{name}' already registered", code="GRY-001",
                )
            self._components[name] = component

    def resolve(self, name: str) -> Any:
        with self._lock:
            if name in self._components:
                return self._components[name]
            factory = self._factories.get(name)
        if factory:
            component = factory()
            with self._lock:
                self._components[name] = component
            return component
        raise GraphRegistryError(f"Component '{name}' not found", code="GRY-002")

    def resolve_typed(self, name: str, expected_type: Type) -> Any:
        component = self.resolve(name)
        if not isinstance(component, expected_type):
            raise GraphRegistryError(
                f"Component '{name}': expected {expected_type.__name__}, "
                f"got {type(component).__name__}",
                code="GRY-003",
            )
        return component

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._components or name in self._factories

    def list_registered(self) -> list[str]:
        with self._lock:
            return sorted(self._components.keys() | self._factories.keys())

    def unregister(self, name: str) -> None:
        with self._lock:
            self._components.pop(name, None)

    def reset(self) -> None:
        with self._lock:
            self._components.clear()


def get_graph_registry() -> GraphRegistry:
    global _registry
    with _lock:
        if _registry is None:
            _registry = GraphRegistry()
        return _registry


def reset_graph_registry() -> None:
    global _registry
    with _lock:
        _registry = None
