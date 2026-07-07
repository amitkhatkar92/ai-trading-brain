"""
iios/knowledge/search/search_registry.py
==========================================
Lazy-resolution registry of all Knowledge Indexing & Search Engine components.
"""
from __future__ import annotations

import threading
from typing import Any, Optional, Type

from .search_exceptions import SearchRegistryError

__all__ = ["SearchRegistry", "get_search_registry", "reset_search_registry"]

_lock:      threading.Lock              = threading.Lock()
_registry:  Optional["SearchRegistry"] = None


class SearchRegistry:
    """Registry for all search engine components with lazy resolution."""

    def __init__(self) -> None:
        self._lock:       threading.RLock    = threading.RLock()
        self._components: dict[str, Any]     = {}
        self._factories:  dict[str, Any]     = {}
        self._auto_register_defaults()

    def _auto_register_defaults(self) -> None:
        # All imports are local to avoid circular imports at module-load time
        from .index_manager    import get_index_manager
        from .index_builder    import get_index_builder
        from .index_registry   import get_index_registry
        from .index_statistics import get_search_stats
        from .index_optimizer  import get_index_optimizer
        from .query_parser     import get_query_parser
        from .query_builder    import get_query_builder
        from .query_validator  import get_query_validator
        from .query_optimizer  import get_query_optimizer
        from .query_executor   import get_query_executor
        from .search_engine    import get_search_engine
        from .search_context   import get_search_context
        from .search_factory   import get_search_factory
        from .search_manager   import get_search_manager

        self._factories.update({
            "index_manager":   get_index_manager,
            "index_builder":   get_index_builder,
            "index_registry":  get_index_registry,
            "stats":           get_search_stats,
            "index_optimizer": get_index_optimizer,
            "query_parser":    get_query_parser,
            "query_builder":   get_query_builder,
            "query_validator": get_query_validator,
            "query_optimizer": get_query_optimizer,
            "query_executor":  get_query_executor,
            "search_engine":   get_search_engine,
            "search_context":  get_search_context,
            "search_factory":  get_search_factory,
            "search_manager":  get_search_manager,
        })

    def register(self, name: str, component: Any, override: bool = True) -> None:
        with self._lock:
            if not override and name in self._components:
                raise SearchRegistryError(
                    f"Component '{name}' already registered", code="SR-001",
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
        raise SearchRegistryError(f"Component '{name}' not found", code="SR-002")

    def resolve_typed(self, name: str, expected_type: Type) -> Any:
        component = self.resolve(name)
        if not isinstance(component, expected_type):
            raise SearchRegistryError(
                f"Component '{name}': expected {expected_type.__name__}, "
                f"got {type(component).__name__}",
                code="SR-003",
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


def get_search_registry() -> SearchRegistry:
    global _registry
    with _lock:
        if _registry is None:
            _registry = SearchRegistry()
        return _registry


def reset_search_registry() -> None:
    global _registry
    with _lock:
        _registry = None
