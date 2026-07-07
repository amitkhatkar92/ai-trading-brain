"""
iios/observation/collectors/collector_context.py
================================================
Thread-local execution context for active collector runs.

Tracks which collector is currently running in the calling thread,
enabling structured logging and audit trail without passing context
objects through every call.
"""
from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

from .collector_constants import SYSTEM_COLLECTOR

__all__ = [
    "CollectorContext",
    "get_collector_context",
    "reset_collector_context",
    "collector_operation",
    "current_collector_name",
    "current_run_id",
    "current_batch_id",
]

_lock = threading.Lock()
_ctx: Optional["CollectorContext"] = None


class CollectorContext:
    """Thread-local context for the active collector run."""

    def __init__(self) -> None:
        self._local = threading.local()

    @property
    def collector_name(self) -> str:
        return getattr(self._local, "collector_name", SYSTEM_COLLECTOR)

    @collector_name.setter
    def collector_name(self, v: str) -> None:
        self._local.collector_name = v

    @property
    def run_id(self) -> Optional[str]:
        return getattr(self._local, "run_id", None)

    @run_id.setter
    def run_id(self, v: Optional[str]) -> None:
        self._local.run_id = v

    @property
    def batch_id(self) -> Optional[str]:
        return getattr(self._local, "batch_id", None)

    @batch_id.setter
    def batch_id(self, v: Optional[str]) -> None:
        self._local.batch_id = v

    @contextmanager
    def running(
        self,
        collector_name: str,
        run_id:         Optional[str] = None,
        batch_id:       Optional[str] = None,
    ) -> Generator[None, None, None]:
        prev_name  = self.collector_name
        prev_run   = self.run_id
        prev_batch = self.batch_id
        self.collector_name = collector_name
        self.run_id         = run_id or str(uuid.uuid4())
        self.batch_id       = batch_id
        try:
            yield
        finally:
            self.collector_name = prev_name
            self.run_id         = prev_run
            self.batch_id       = prev_batch


def get_collector_context() -> CollectorContext:
    global _ctx
    if _ctx is None:
        with _lock:
            if _ctx is None:
                _ctx = CollectorContext()
    return _ctx


def reset_collector_context() -> None:
    global _ctx
    with _lock:
        _ctx = None


@contextmanager
def collector_operation(
    collector_name: str,
    run_id:         Optional[str] = None,
    batch_id:       Optional[str] = None,
) -> Generator[None, None, None]:
    """Context manager shorthand for ``get_collector_context().running(...)``."""
    with get_collector_context().running(collector_name, run_id, batch_id):
        yield


def current_collector_name() -> str:
    return get_collector_context().collector_name


def current_run_id() -> Optional[str]:
    return get_collector_context().run_id


def current_batch_id() -> Optional[str]:
    return get_collector_context().batch_id
