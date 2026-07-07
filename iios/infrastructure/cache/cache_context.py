"""
iios/infrastructure/cache/cache_context.py
==========================================
Thread-local cache execution context: current region, batch accumulation,
and read-through loader registry.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Generator, Optional

from .cache_constants import DEFAULT_REGION

__all__ = [
    "CacheContext",
    "get_cache_context",
    "current_region",
    "set_region",
    "cache_region",
]

_local = threading.local()
_singleton_lock = threading.Lock()
_context: Optional["CacheContext"] = None


@dataclass
class _PendingWrite:
    key: str
    value: Any
    region: str
    ttl: Optional[float]
    tags: set[str]


class CacheContext:
    """Per-thread context for cache operations.

    Usage::

        ctx = get_cache_context()
        ctx.set_region("quotes")

        with cache_region("trades"):
            # current_region() == "trades" here
            ...
        # current_region() restored to "quotes"
    """

    # ── Region stack (thread-local) ──────────────────────────────────────────

    def push_region(self, region: str) -> None:
        stack = self._region_stack
        stack.append(region)
        _local.__dict__["_region_stack"] = stack

    def pop_region(self) -> str:
        stack = self._region_stack
        if stack:
            popped = stack.pop()
            _local.__dict__["_region_stack"] = stack
            return popped
        return DEFAULT_REGION

    def current_region(self) -> str:
        stack = self._region_stack
        return stack[-1] if stack else DEFAULT_REGION

    def set_region(self, region: str) -> None:
        stack = self._region_stack
        if stack:
            stack[-1] = region
        else:
            stack.append(region)
        _local.__dict__["_region_stack"] = stack

    @property
    def _region_stack(self) -> list[str]:
        if "_region_stack" not in _local.__dict__:
            _local.__dict__["_region_stack"] = []
        return _local.__dict__["_region_stack"]

    # ── Batch mode (pending writes) ──────────────────────────────────────────

    def enter_batch(self) -> None:
        _local.__dict__["_batch_mode"] = True
        _local.__dict__.setdefault("_pending_writes", [])

    def exit_batch(self) -> list[_PendingWrite]:
        _local.__dict__["_batch_mode"] = False
        writes = _local.__dict__.pop("_pending_writes", [])
        return writes

    def is_batch_mode(self) -> bool:
        return _local.__dict__.get("_batch_mode", False)

    def add_pending_write(self, write: _PendingWrite) -> None:
        _local.__dict__.setdefault("_pending_writes", []).append(write)

    def pending_writes(self) -> list[_PendingWrite]:
        return _local.__dict__.get("_pending_writes", [])

    # ── Read-through loaders ─────────────────────────────────────────────────

    def __init__(self) -> None:
        self._loaders: dict[str, Callable[[str], Any]] = {}
        self._loaders_lock = threading.Lock()

    def register_loader(self, region: str, loader: Callable[[str], Any]) -> None:
        with self._loaders_lock:
            self._loaders[region] = loader

    def get_loader(self, region: str) -> Optional[Callable[[str], Any]]:
        with self._loaders_lock:
            return self._loaders.get(region)

    def reset(self) -> None:
        _local.__dict__.clear()
        with self._loaders_lock:
            self._loaders.clear()


# ── Module-level convenience functions ──────────────────────────────────────

def get_cache_context() -> CacheContext:
    global _context
    with _singleton_lock:
        if _context is None:
            _context = CacheContext()
        return _context


def current_region() -> str:
    return get_cache_context().current_region()


def set_region(region: str) -> None:
    get_cache_context().set_region(region)


@contextmanager
def cache_region(region: str) -> Generator[None, None, None]:
    """Context manager that sets the active cache region for the current thread."""
    ctx = get_cache_context()
    ctx.push_region(region)
    try:
        yield
    finally:
        ctx.pop_region()


def reset_cache_context() -> None:
    global _context
    with _singleton_lock:
        if _context is not None:
            _context.reset()
        _context = None
