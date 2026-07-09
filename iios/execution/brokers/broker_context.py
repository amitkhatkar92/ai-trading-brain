"""iios/execution/brokers/broker_context.py"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator


class BrokerContextState:
    """Thread-local context for the current broker operation."""

    _local = threading.local()

    @classmethod
    def set(
        cls,
        broker_id:   str,
        operation:   str = "",
        request_id:  str = "",
        trace_id:    str = "",
        metadata:    dict[str, Any] | None = None,
    ) -> None:
        cls._local.broker_id   = broker_id
        cls._local.operation   = operation
        cls._local.request_id  = request_id or str(uuid.uuid4())
        cls._local.trace_id    = trace_id   or str(uuid.uuid4())
        cls._local.metadata    = metadata or {}
        cls._local.started_at  = time.time()

    @classmethod
    def get_broker_id(cls) -> str:
        return getattr(cls._local, "broker_id", "")

    @classmethod
    def get_operation(cls) -> str:
        return getattr(cls._local, "operation", "")

    @classmethod
    def get_request_id(cls) -> str:
        return getattr(cls._local, "request_id", "")

    @classmethod
    def get_trace_id(cls) -> str:
        return getattr(cls._local, "trace_id", "")

    @classmethod
    def get_elapsed_ms(cls) -> float:
        started = getattr(cls._local, "started_at", None)
        if started is None:
            return 0.0
        return (time.time() - started) * 1_000

    @classmethod
    def clear(cls) -> None:
        cls._local.__dict__.clear()

    @classmethod
    def snapshot(cls) -> dict[str, Any]:
        return {
            "broker_id":  cls.get_broker_id(),
            "operation":  cls.get_operation(),
            "request_id": cls.get_request_id(),
            "trace_id":   cls.get_trace_id(),
            "elapsed_ms": cls.get_elapsed_ms(),
        }


@contextmanager
def broker_operation_context(
    broker_id: str,
    operation: str,
    metadata:  dict[str, Any] | None = None,
) -> Generator[BrokerContextState, None, None]:
    """Context manager that sets and clears broker operation context."""
    BrokerContextState.set(
        broker_id=broker_id, operation=operation, metadata=metadata
    )
    try:
        yield BrokerContextState
    finally:
        BrokerContextState.clear()
