"""
iios/knowledge/versioning/version_context.py
============================================
Thread-local versioning context — tracks the current actor and operation
ID for the duration of a versioning operation.

Usage::

    from iios.knowledge.versioning.version_context import (
        get_version_context,
        version_operation,
        current_version_actor,
    )

    ctx = get_version_context()
    with version_operation(actor="user:alice", operation_id="op-123"):
        ve = get_version_engine()
        ve.create_version(record, VersionBump.MINOR, author=current_version_actor())
"""

from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

from .version_constants import SYSTEM_VERSIONING_ACTOR

__all__ = [
    "VersionContext",
    "get_version_context",
    "reset_version_context",
    "version_operation",
    "current_version_actor",
    "current_version_operation_id",
]

_lock = threading.Lock()
_ctx: Optional["VersionContext"] = None


class VersionContext:
    """Thread-local context that tracks the current versioning actor and
    operation identifier."""

    def __init__(self) -> None:
        self._local = threading.local()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def actor(self) -> str:
        return getattr(self._local, "actor", SYSTEM_VERSIONING_ACTOR)

    @actor.setter
    def actor(self, value: str) -> None:
        self._local.actor = value

    @property
    def operation_id(self) -> Optional[str]:
        return getattr(self._local, "operation_id", None)

    @operation_id.setter
    def operation_id(self, value: Optional[str]) -> None:
        self._local.operation_id = value

    # ── Context manager ───────────────────────────────────────────────────────

    @contextmanager
    def operation(
        self,
        actor:        Optional[str] = None,
        operation_id: Optional[str] = None,
    ) -> Generator[None, None, None]:
        prev_actor = self.actor
        prev_op    = self.operation_id
        self.actor        = actor or SYSTEM_VERSIONING_ACTOR
        self.operation_id = operation_id or str(uuid.uuid4())
        try:
            yield
        finally:
            self.actor        = prev_actor
            self.operation_id = prev_op


# ── Module-level helpers ──────────────────────────────────────────────────────

def get_version_context() -> VersionContext:
    global _ctx
    if _ctx is None:
        with _lock:
            if _ctx is None:
                _ctx = VersionContext()
    return _ctx


def reset_version_context() -> None:
    global _ctx
    with _lock:
        _ctx = None


@contextmanager
def version_operation(
    actor:        Optional[str] = None,
    operation_id: Optional[str] = None,
) -> Generator[None, None, None]:
    """Convenience context manager for versioning operations."""
    with get_version_context().operation(actor=actor, operation_id=operation_id):
        yield


def current_version_actor() -> str:
    return get_version_context().actor


def current_version_operation_id() -> Optional[str]:
    return get_version_context().operation_id
