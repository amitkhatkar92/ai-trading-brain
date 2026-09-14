"""governance_context.py — Thread-local execution context for the Governance Framework."""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from typing import Generator, Optional


_local = threading.local()


class _GovernanceContext:
    """Read-only snapshot of the current thread's governance context."""

    __slots__ = ("operation", "project_id", "artifact_id", "approval_id",
                 "actor", "request_id", "_started_at")

    def __init__(
        self,
        operation:   str,
        project_id:  Optional[str],
        artifact_id: Optional[str],
        approval_id: Optional[str],
        actor:       Optional[str],
        request_id:  Optional[str],
        started_at:  float,
    ) -> None:
        self.operation   = operation
        self.project_id  = project_id
        self.artifact_id = artifact_id
        self.approval_id = approval_id
        self.actor       = actor
        self.request_id  = request_id
        self._started_at = started_at

    def elapsed_ms(self) -> float:
        return (time.time() - self._started_at) * 1_000


def set_context(
    operation:   str,
    *,
    project_id:  Optional[str] = None,
    artifact_id: Optional[str] = None,
    approval_id: Optional[str] = None,
    actor:       Optional[str] = None,
    request_id:  Optional[str] = None,
) -> None:
    _local._ctx = _GovernanceContext(
        operation   = operation,
        project_id  = project_id,
        artifact_id = artifact_id,
        approval_id = approval_id,
        actor       = actor,
        request_id  = request_id or f"gv_{uuid.uuid4().hex[:8]}",
        started_at  = time.time(),
    )


def get_context() -> _GovernanceContext:
    ctx = getattr(_local, "_ctx", None)
    if ctx is None:
        # Return an empty context so callers never need to null-check
        ctx = _GovernanceContext(
            operation   = None,
            project_id  = None,
            artifact_id = None,
            approval_id = None,
            actor       = None,
            request_id  = f"gv_{uuid.uuid4().hex[:8]}",
            started_at  = time.time(),
        )
    return ctx


def clear_context() -> None:
    _local._ctx = None


@contextmanager
def scope(
    operation:   str,
    *,
    project_id:  Optional[str] = None,
    artifact_id: Optional[str] = None,
    actor:       Optional[str] = None,
) -> Generator[_GovernanceContext, None, None]:
    set_context(operation, project_id=project_id, artifact_id=artifact_id, actor=actor)
    ctx = get_context()
    try:
        yield ctx  # type: ignore[misc]
    finally:
        clear_context()
