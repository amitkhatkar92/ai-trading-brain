"""
iios/infrastructure/dependency_injection/container.py
======================================================
IIOS Dependency Injection Container.

Supports:
  - Singleton, Scoped, Transient lifecycle scopes
  - Constructor injection via type-hint inspection
  - Automatic dependency resolution
  - Lazy loading
  - Decorator-based registration (@container.singleton etc.)
"""

from __future__ import annotations

import inspect
import threading
import time
from typing import Any, Callable, Optional, Type, TypeVar

from ..infrastructure_constants import LifecycleScope
from ..infrastructure_exceptions import (
    DIError,
    ServiceNotFoundError,
    ServiceAlreadyRegisteredError,
    LifecycleScopeError,
)
from ..infrastructure_models import ServiceDescriptor, ResolvedService
from .dependency_graph import DependencyGraph
from .lifecycle_scope import current_scope
from .provider import (
    Provider,
    SingletonProvider,
    TransientProvider,
    InstanceProvider,
    LazyProvider,
)
from .service_registry import ServiceRegistry

__all__ = ["Container", "get_container", "reset_container"]

T = TypeVar("T")

_container_lock = threading.Lock()
_container: Optional["Container"] = None


class Container:
    """IIOS Inversion-of-Control container.

    Usage::

        c = Container()

        # Register
        c.singleton("my_service", MyService)
        c.transient("db_conn", DatabaseConnection)

        # Resolve
        svc = c.resolve("my_service")
        svc = c.resolve(MyService)       # also works with types

        # Decorators
        @c.singleton("config")
        class Config: ...
    """

    def __init__(self) -> None:
        self._registry = ServiceRegistry()
        self._providers: dict[str, Provider] = {}
        self._graph = DependencyGraph()
        self._lock = threading.RLock()
        self._build_count = 0

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def _key(self, key_or_type: Any) -> str:
        if isinstance(key_or_type, str):
            return key_or_type
        if inspect.isclass(key_or_type):
            return f"{key_or_type.__module__}.{key_or_type.__qualname__}"
        raise DIError(f"Service key must be a str or class, got {type(key_or_type)!r}")

    def singleton(
        self,
        key: Any,
        implementation: Optional[Any] = None,
        *,
        allow_override: bool = False,
    ) -> Any:
        """Register a singleton service (or use as a decorator)."""
        k = self._key(key)
        if implementation is None:
            # Used as decorator: @container.singleton("key")
            def decorator(cls: Any) -> Any:
                self._bind(k, cls, LifecycleScope.SINGLETON, allow_override)
                return cls
            return decorator
        self._bind(k, implementation, LifecycleScope.SINGLETON, allow_override)
        return self

    def transient(
        self,
        key: Any,
        implementation: Optional[Any] = None,
        *,
        allow_override: bool = False,
    ) -> Any:
        """Register a transient service (new instance per resolve)."""
        k = self._key(key)
        if implementation is None:
            def decorator(cls: Any) -> Any:
                self._bind(k, cls, LifecycleScope.TRANSIENT, allow_override)
                return cls
            return decorator
        self._bind(k, implementation, LifecycleScope.TRANSIENT, allow_override)
        return self

    def scoped(
        self,
        key: Any,
        implementation: Optional[Any] = None,
        *,
        allow_override: bool = False,
    ) -> Any:
        """Register a scoped service (one per active scope)."""
        k = self._key(key)
        if implementation is None:
            def decorator(cls: Any) -> Any:
                self._bind(k, cls, LifecycleScope.SCOPED, allow_override)
                return cls
            return decorator
        self._bind(k, implementation, LifecycleScope.SCOPED, allow_override)
        return self

    def instance(self, key: Any, obj: Any, *, allow_override: bool = False) -> "Container":
        """Register a pre-built singleton instance."""
        k = self._key(key)
        descriptor = self._registry.register_instance(k, obj, allow_override=allow_override)
        with self._lock:
            self._providers[k] = InstanceProvider(obj)
            self._graph.add_node(k)
        return self

    def lazy(
        self,
        key: Any,
        factory: Callable[[], Any],
        *,
        allow_override: bool = False,
    ) -> "Container":
        """Register a lazy singleton (constructed on first access)."""
        k = self._key(key)
        descriptor = self._registry.register(
            k,
            factory,
            scope=LifecycleScope.SINGLETON.value,
            allow_override=allow_override,
        )
        with self._lock:
            self._providers[k] = LazyProvider(factory)
            self._graph.add_node(k)
        return self

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(self, key: Any) -> Any:
        """Resolve and return a service instance."""
        k = self._key(key)
        t_start = time.monotonic()

        with self._lock:
            provider = self._providers.get(k)
            if provider is None:
                raise ServiceNotFoundError(
                    f"No service registered for '{k}'",
                    code="INF-DI-004",
                    context={"key": k},
                )
            descriptor = self._registry.get(k)

        # Scoped lifecycle — delegate to active scope
        if descriptor.scope == LifecycleScope.SCOPED.value:
            scope = current_scope()
            if scope is None:
                raise LifecycleScopeError(
                    f"Cannot resolve scoped service '{k}' outside a scope context",
                    code="INF-DI-002",
                )
            return scope.get_or_create(k, provider.get)

        instance = provider.get()
        self._build_count += 1
        return instance

    def resolve_all(self, tag: str) -> list[Any]:
        """Resolve all services tagged with *tag*."""
        descriptors = self._registry.by_tag(tag)
        return [self.resolve(d.service_key) for d in descriptors]

    def try_resolve(self, key: Any) -> Optional[Any]:
        """Attempt to resolve; return None if not registered."""
        try:
            return self.resolve(key)
        except ServiceNotFoundError:
            return None

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def is_registered(self, key: Any) -> bool:
        return self._registry.has(self._key(key))

    def registered_keys(self) -> list[str]:
        return self._registry.keys()

    def resolution_order(self) -> list[str]:
        return self._graph.resolution_order()

    def has_cycle(self) -> bool:
        return self._graph.has_cycle()

    @property
    def build_count(self) -> int:
        return self._build_count

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all registrations and cached instances."""
        with self._lock:
            for provider in self._providers.values():
                provider.reset()
            self._providers.clear()
            self._registry.clear()
            self._graph = DependencyGraph()
            self._build_count = 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _bind(
        self,
        key: str,
        implementation: Any,
        scope: LifecycleScope,
        allow_override: bool,
    ) -> None:
        """Register implementation and create the appropriate provider."""
        descriptor = self._registry.register(
            key,
            implementation,
            scope=scope.value,
            allow_override=allow_override,
        )

        factory = self._make_factory(implementation)

        with self._lock:
            if scope == LifecycleScope.SINGLETON:
                self._providers[key] = SingletonProvider(factory)
            else:
                self._providers[key] = TransientProvider(factory)
            self._graph.add_node(key)

    def _make_factory(self, implementation: Any) -> Callable[[], Any]:
        """Create a zero-arg factory that auto-injects constructor args."""
        import typing
        if callable(implementation) and not inspect.isclass(implementation):
            # Plain callable / factory function
            return implementation

        # Class — inspect __init__ for type-hinted parameters
        try:
            sig = inspect.signature(implementation.__init__)
        except (ValueError, TypeError):
            return implementation

        params = [
            p for name, p in sig.parameters.items()
            if name != "self" and p.default is inspect.Parameter.empty
        ]

        if not params:
            return implementation

        # Resolve string annotations (caused by `from __future__ import annotations`)
        try:
            hints = typing.get_type_hints(implementation.__init__)
        except Exception:
            hints = {}

        def auto_factory() -> Any:
            kwargs: dict[str, Any] = {}
            for p in params:
                # Prefer fully-resolved type hint over raw annotation
                ann = hints.get(p.name, p.annotation)
                if ann is inspect.Parameter.empty or isinstance(ann, str):
                    continue
                try:
                    dep_key = self._key(ann)
                except DIError:
                    continue
                if self._registry.has(dep_key):
                    kwargs[p.name] = self.resolve(dep_key)
            return implementation(**kwargs)

        return auto_factory


# ---------------------------------------------------------------------------
# Global singleton container
# ---------------------------------------------------------------------------


def get_container() -> Container:
    """Return (or create) the global DI container."""
    global _container
    with _container_lock:
        if _container is None:
            _container = Container()
        return _container


def reset_container() -> None:
    """Reset the global container (for testing)."""
    global _container
    with _container_lock:
        if _container is not None:
            _container.reset()
        _container = None
