"""
iios/observation/observation_context.py
=======================================
Thread-local context for the Observation Engine.

Tracks the current actor, operation ID, and batch ID for the duration
of an observation processing call.
"""

from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

from .observation_constants import SYSTEM_OBSERVER

__all__ = [
    "ObservationContext",
    "get_observation_context",
    "reset_observation_context",
    "observation_operation",
    "current_obs_actor",
    "current_obs_operation_id",
    "current_obs_batch_id",
]

_lock = threading.Lock()
_ctx: Optional["ObservationContext"] = None


class ObservationContext:
    """Thread-local context for observation operations."""

    def __init__(self) -> None:
        self._local = threading.local()

    @property
    def actor(self) -> str:
        return getattr(self._local, "actor", SYSTEM_OBSERVER)

    @actor.setter
    def actor(self, value: str) -> None:
        self._local.actor = value

    @property
    def operation_id(self) -> Optional[str]:
        return getattr(self._local, "operation_id", None)

    @operation_id.setter
    def operation_id(self, value: Optional[str]) -> None:
        self._local.operation_id = value

    @property
    def batch_id(self) -> Optional[str]:
        return getattr(self._local, "batch_id", None)

    @batch_id.setter
    def batch_id(self, value: Optional[str]) -> None:
        self._local.batch_id = value

    @contextmanager
    def operation(
        self,
        actor:        Optional[str] = None,
        operation_id: Optional[str] = None,
        batch_id:     Optional[str] = None,
    ) -> Generator[None, None, None]:
        prev_actor = self.actor
        prev_op    = self.operation_id
        prev_batch = self.batch_id
        self.actor        = actor        or SYSTEM_OBSERVER
        self.operation_id = operation_id or str(uuid.uuid4())
        self.batch_id     = batch_id
        try:
            yield
        finally:
            self.actor        = prev_actor
            self.operation_id = prev_op
            self.batch_id     = prev_batch


def get_observation_context() -> ObservationContext:
    global _ctx
    if _ctx is None:
        with _lock:
            if _ctx is None:
                _ctx = ObservationContext()
    return _ctx


def reset_observation_context() -> None:
    global _ctx
    with _lock:
        _ctx = None


@contextmanager
def observation_operation(
    actor:        Optional[str] = None,
    operation_id: Optional[str] = None,
    batch_id:     Optional[str] = None,
) -> Generator[None, None, None]:
    with get_observation_context().operation(
        actor=actor, operation_id=operation_id, batch_id=batch_id
    ):
        yield


def current_obs_actor() -> str:
    return get_observation_context().actor


def current_obs_operation_id() -> Optional[str]:
    return get_observation_context().operation_id


def current_obs_batch_id() -> Optional[str]:
    return get_observation_context().batch_id
