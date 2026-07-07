"""
iios/observation/collectors/collector_registry.py
=================================================
CollectorRegistry — thread-safe singleton registry of all collector instances.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from typing import Optional

from .base_collector         import BaseCollector
from .collector_constants    import CollectorCategory, CollectorStatus
from .collector_exceptions   import CollectorAlreadyRegisteredError, CollectorNotFoundError

__all__ = ["CollectorRegistry", "get_collector_registry", "reset_collector_registry"]

_LOG  = logging.getLogger("iios.collector.registry")
_lock = threading.Lock()
_reg: Optional["CollectorRegistry"] = None


class CollectorRegistry:
    """Global registry of all BaseCollector instances."""

    def __init__(self) -> None:
        self._lock:       threading.RLock              = threading.RLock()
        self._collectors: dict[str, BaseCollector]     = {}

    def register(self, collector: BaseCollector, overwrite: bool = False) -> None:
        with self._lock:
            if collector.name in self._collectors and not overwrite:
                raise CollectorAlreadyRegisteredError(collector.name)
            self._collectors[collector.name] = collector
            _LOG.debug("Registered: %s", collector.name)

    def unregister(self, name: str) -> None:
        with self._lock:
            if name not in self._collectors:
                raise CollectorNotFoundError(name)
            del self._collectors[name]

    def get(self, name: str) -> BaseCollector:
        with self._lock:
            if name not in self._collectors:
                raise CollectorNotFoundError(name)
            return self._collectors[name]

    def get_or_none(self, name: str) -> Optional[BaseCollector]:
        with self._lock:
            return self._collectors.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._collectors

    def all(self) -> list[BaseCollector]:
        with self._lock:
            return list(self._collectors.values())

    def by_category(self, category: CollectorCategory) -> list[BaseCollector]:
        with self._lock:
            return [c for c in self._collectors.values()
                    if c.config.category == category]

    def by_status(self, status: CollectorStatus) -> list[BaseCollector]:
        with self._lock:
            return [c for c in self._collectors.values() if c.status == status]

    def enabled(self) -> list[BaseCollector]:
        with self._lock:
            return [c for c in self._collectors.values() if c.config.enabled]

    def names(self) -> list[str]:
        with self._lock:
            return list(self._collectors)

    def count(self) -> int:
        with self._lock:
            return len(self._collectors)

    def status_summary(self) -> dict[str, str]:
        with self._lock:
            return {n: c.status.value for n, c in self._collectors.items()}

    def clear(self) -> None:
        with self._lock:
            self._collectors.clear()

    def __len__(self) -> int:
        return self.count()

    def __iter__(self) -> Iterator[BaseCollector]:
        with self._lock:
            return iter(list(self._collectors.values()))

    def __contains__(self, name: str) -> bool:
        return self.has(name)


def get_collector_registry() -> CollectorRegistry:
    global _reg
    if _reg is None:
        with _lock:
            if _reg is None:
                _reg = CollectorRegistry()
    return _reg


def reset_collector_registry() -> None:
    global _reg
    with _lock:
        _reg = None
