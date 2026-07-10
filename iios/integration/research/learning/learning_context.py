"""learning_context.py — Thread-local execution context for the Learning Framework."""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from typing import Generator, Optional


_local = threading.local()


class _LearningContext:
    """Read-only snapshot of the current thread's learning context."""

    __slots__ = ("operation", "job_id", "model_id", "experiment_id", "request_id", "_started_at")

    def __init__(
        self,
        operation:     str,
        job_id:        Optional[str],
        model_id:      Optional[str],
        experiment_id: Optional[str],
        request_id:    Optional[str],
        started_at:    float,
    ) -> None:
        self.operation     = operation
        self.job_id        = job_id
        self.model_id      = model_id
        self.experiment_id = experiment_id
        self.request_id    = request_id
        self._started_at   = started_at

    def elapsed_ms(self) -> float:
        return (time.time() - self._started_at) * 1_000


def set_context(
    operation:     str,
    *,
    job_id:        Optional[str] = None,
    model_id:      Optional[str] = None,
    experiment_id: Optional[str] = None,
    request_id:    Optional[str] = None,
) -> None:
    _local._ctx = _LearningContext(
        operation     = operation,
        job_id        = job_id,
        model_id      = model_id,
        experiment_id = experiment_id,
        request_id    = request_id or f"req_{uuid.uuid4().hex[:8]}",
        started_at    = time.time(),
    )


def get_context() -> Optional[_LearningContext]:
    return getattr(_local, "_ctx", None)


def clear_context() -> None:
    _local._ctx = None


@contextmanager
def scope(
    operation:     str,
    *,
    job_id:        Optional[str] = None,
    model_id:      Optional[str] = None,
    experiment_id: Optional[str] = None,
) -> Generator[_LearningContext, None, None]:
    set_context(operation, job_id=job_id, model_id=model_id, experiment_id=experiment_id)
    ctx = get_context()
    try:
        yield ctx  # type: ignore[misc]
    finally:
        clear_context()
