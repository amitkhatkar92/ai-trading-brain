"""
iios/infrastructure/dependency_injection/lifecycle_scope.py
============================================================
Scoped container for per-request / per-cycle service instances.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional

from ..infrastructure_exceptions import LifecycleScopeError

__all__ = ["LifecycleScope", "ScopeContext", "current_scope"]

_scope_local = threading.local()


class ScopeContext:
    """Holds scoped service instances for the duration of one scope.

    Typically used as a context manager::

        with ScopeContext() as scope:
            svc = scope.get_or_create("my_service", factory)
    """

    def __init__(self, scope_id: str = "") -> None:
        import uuid
        self._id = scope_id or str(uuid.uuid4())
        self._instances: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._closed = False

    @property
    def scope_id(self) -> str:
        return self._id

    @property
    def is_closed(self) -> bool:
        return self._closed

    def get_or_create(self, key: str, factory: Callable[[], Any]) -> Any:
        """Return cached instance or create via *factory*."""
        if self._closed:
            raise LifecycleScopeError(
                f"Cannot resolve '{key}' — scope {self._id} is already closed",
                code="INF-DI-002",
            )
        with self._lock:
            if key not in self._instances:
                self._instances[key] = factory()
            return self._instances[key]

    def get(self, key: str) -> Optional[Any]:
        return self._instances.get(key)

    def register(self, key: str, instance: Any) -> None:
        with self._lock:
            self._instances[key] = instance

    def close(self) -> None:
        self._closed = True
        self._instances.clear()

    def __enter__(self) -> "ScopeContext":
        _push_scope(self)
        return self

    def __exit__(self, *_: Any) -> None:
        _pop_scope()
        self.close()

    def __len__(self) -> int:
        return len(self._instances)


# ---------------------------------------------------------------------------
# Thread-local scope stack
# ---------------------------------------------------------------------------


def _push_scope(scope: ScopeContext) -> None:
    stack = getattr(_scope_local, "stack", None)
    if stack is None:
        _scope_local.stack = []
    _scope_local.stack.append(scope)


def _pop_scope() -> Optional[ScopeContext]:
    stack = getattr(_scope_local, "stack", [])
    return stack.pop() if stack else None


def current_scope() -> Optional[ScopeContext]:
    """Return the innermost active scope on the current thread, or None."""
    stack = getattr(_scope_local, "stack", [])
    return stack[-1] if stack else None


@contextmanager
def LifecycleScope(scope_id: str = "") -> Generator[ScopeContext, None, None]:
    """Context manager that creates and activates a ``ScopeContext``."""
    scope = ScopeContext(scope_id)
    with scope:
        yield scope
