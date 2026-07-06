"""
iios/infrastructure/serialization/serializer_registry.py
=========================================================
Registry of named serializers.
"""

from __future__ import annotations

import threading
from typing import Any, Optional, Protocol, runtime_checkable

from ..infrastructure_exceptions import SerializationError

__all__ = ["SerializerProtocol", "SerializerRegistry", "get_serializer_registry", "reset_serializer_registry"]

_lock = threading.Lock()
_registry: Optional["SerializerRegistry"] = None


@runtime_checkable
class SerializerProtocol(Protocol):
    def serialize(self, data: Any) -> str: ...
    def deserialize(self, text: str) -> Any: ...


class SerializerRegistry:
    """Registry of named serializer instances."""

    def __init__(self) -> None:
        self._serializers: dict[str, Any] = {}
        self._lock = threading.RLock()

    def register(self, name: str, serializer: Any, allow_override: bool = False) -> None:
        with self._lock:
            if name in self._serializers and not allow_override:
                raise SerializationError(
                    f"Serializer '{name}' already registered",
                    code="INF-SER-030",
                )
            self._serializers[name] = serializer

    def get(self, name: str) -> Any:
        with self._lock:
            s = self._serializers.get(name)
        if s is None:
            raise SerializationError(
                f"Serializer '{name}' not found",
                code="INF-SER-031",
            )
        return s

    def names(self) -> list[str]:
        with self._lock:
            return list(self._serializers.keys())

    def clear(self) -> None:
        with self._lock:
            self._serializers.clear()


def get_serializer_registry() -> SerializerRegistry:
    global _registry
    with _lock:
        if _registry is None:
            _registry = SerializerRegistry()
        return _registry


def reset_serializer_registry() -> None:
    global _registry
    with _lock:
        _registry = None
