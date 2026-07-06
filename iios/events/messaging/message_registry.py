"""
iios/events/messaging/message_registry.py
==========================================
Registry of named message types and their schemas/validators.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

__all__ = ["MessageTypeDescriptor", "MessageRegistry", "get_message_registry", "reset_message_registry"]

_lock = threading.Lock()
_registry: Optional["MessageRegistry"] = None


@dataclass
class MessageTypeDescriptor:
    message_type: str
    description: str = ""
    schema: dict[str, Any] = field(default_factory=dict)
    owner: str = ""
    version: str = "1"
    tags: list[str] = field(default_factory=list)
    validator: Optional[Callable[[dict], bool]] = None
    deprecated: bool = False


class MessageRegistry:
    """Catalogue of all message types in the IIOS system."""

    def __init__(self) -> None:
        self._descriptors: dict[str, MessageTypeDescriptor] = {}
        self._lock = threading.RLock()

    def register(self, descriptor: MessageTypeDescriptor, allow_override: bool = True) -> None:
        with self._lock:
            self._descriptors[descriptor.message_type] = descriptor

    def get(self, message_type: str) -> Optional[MessageTypeDescriptor]:
        with self._lock:
            return self._descriptors.get(message_type)

    def has(self, message_type: str) -> bool:
        with self._lock:
            return message_type in self._descriptors

    def list_all(self) -> list[MessageTypeDescriptor]:
        with self._lock:
            return list(self._descriptors.values())

    def validate(self, message_type: str, payload: dict[str, Any]) -> bool:
        desc = self.get(message_type)
        if desc is None or desc.validator is None:
            return True
        return desc.validator(payload)

    def clear(self) -> None:
        with self._lock:
            self._descriptors.clear()

    def __len__(self) -> int:
        return len(self._descriptors)


def get_message_registry() -> MessageRegistry:
    global _registry
    with _lock:
        if _registry is None:
            _registry = MessageRegistry()
        return _registry


def reset_message_registry() -> None:
    global _registry
    with _lock:
        _registry = None
