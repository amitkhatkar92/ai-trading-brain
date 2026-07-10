"""iios/integration/history/history_context.py

Thread-local context for the historical data pipeline.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator


@dataclass
class HistoryContextState:
    operation:   str   = ""
    dataset_id:  str   = ""
    session_id:  str   = ""
    started_at:  float = field(default_factory=time.time)
    metadata:    dict[str, Any] = field(default_factory=dict)

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000


_local = threading.local()


def _get_state() -> HistoryContextState:
    if not hasattr(_local, "state"):
        _local.state = HistoryContextState()
    return _local.state


class HistoryContext:
    """Thread-local context for the historical data framework."""

    @staticmethod
    def set(
        operation:  str = "",
        dataset_id: str = "",
        session_id: str = "",
    ) -> None:
        s = _get_state()
        s.operation  = operation
        s.dataset_id = dataset_id
        s.session_id = session_id
        s.started_at = time.time()

    @staticmethod
    def get() -> HistoryContextState:
        return _get_state()

    @staticmethod
    def clear() -> None:
        _local.state = HistoryContextState()

    @staticmethod
    @contextmanager
    def scope(
        operation:  str,
        dataset_id: str = "",
        session_id: str = "",
    ) -> Generator[HistoryContextState, None, None]:
        HistoryContext.set(operation=operation, dataset_id=dataset_id, session_id=session_id)
        try:
            yield _get_state()
        finally:
            HistoryContext.clear()
