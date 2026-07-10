"""iios/execution/monitoring/monitoring_context.py"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Any, Generator


class _MonitoringThreadLocal(threading.local):
    """Thread-local storage for in-flight monitoring context."""

    def __init__(self) -> None:
        super().__init__()
        self.execution_id: str | None = None
        self.operation:    str | None = None
        self.broker_id:    str | None = None
        self.started_at:   float | None = None


_tl = _MonitoringThreadLocal()


class MonitoringContextState:
    """
    Thread-local execution context available to any code that runs
    inside a *monitoring_operation_context* block.
    """

    @classmethod
    def set(
        cls,
        execution_id: str,
        operation:    str = "",
        broker_id:    str = "",
    ) -> None:
        _tl.execution_id = execution_id
        _tl.operation    = operation
        _tl.broker_id    = broker_id
        _tl.started_at   = time.time()

    @classmethod
    def get_execution_id(cls) -> str | None:
        return _tl.execution_id

    @classmethod
    def get_operation(cls) -> str | None:
        return _tl.operation

    @classmethod
    def get_broker_id(cls) -> str | None:
        return _tl.broker_id

    @classmethod
    def get_started_at(cls) -> float | None:
        return _tl.started_at

    @classmethod
    def elapsed_ms(cls) -> float:
        if _tl.started_at is None:
            return 0.0
        return (time.time() - _tl.started_at) * 1_000

    @classmethod
    def clear(cls) -> None:
        _tl.execution_id = None
        _tl.operation    = None
        _tl.broker_id    = None
        _tl.started_at   = None

    @classmethod
    def to_dict(cls) -> dict[str, Any]:
        return {
            "execution_id": _tl.execution_id,
            "operation":    _tl.operation,
            "broker_id":    _tl.broker_id,
            "started_at":   _tl.started_at,
        }


@contextmanager
def monitoring_operation_context(
    execution_id: str,
    operation:    str = "",
    broker_id:    str = "",
) -> Generator[MonitoringContextState, None, None]:
    """
    Context manager that sets and clears thread-local monitoring state.

    Usage::

        with monitoring_operation_context("exec-123", "submit"):
            ...
    """
    MonitoringContextState.set(execution_id, operation, broker_id)
    try:
        yield MonitoringContextState
    finally:
        MonitoringContextState.clear()
