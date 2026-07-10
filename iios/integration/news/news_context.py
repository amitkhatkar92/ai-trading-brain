"""iios/integration/news/news_context.py

Thread-local context for the news pipeline.

Provides per-thread state (provider_id, subject, operation) analogous to
the market_data_context in the market data framework.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator


@dataclass
class NewsContextState:
    provider_id: str  = ""
    subject:     str  = ""
    operation:   str  = ""
    started_at:  float = field(default_factory=time.time)
    metadata:    dict[str, Any] = field(default_factory=dict)

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000


_local = threading.local()


def _get_state() -> NewsContextState:
    if not hasattr(_local, "state"):
        _local.state = NewsContextState()
    return _local.state


class NewsContext:
    """
    Thread-local context for the news processing pipeline.

    Usage:
        NewsContext.set(provider_id="paper_news", subject="AAPL", operation="fetch")
        ...
        state = NewsContext.get()
        print(state.elapsed_ms())
    """

    @staticmethod
    def set(provider_id: str = "", subject: str = "", operation: str = "") -> None:
        s = _get_state()
        s.provider_id = provider_id
        s.subject     = subject
        s.operation   = operation
        s.started_at  = time.time()

    @staticmethod
    def get() -> NewsContextState:
        return _get_state()

    @staticmethod
    def clear() -> None:
        _local.state = NewsContextState()

    @staticmethod
    @contextmanager
    def scope(provider_id: str, subject: str, operation: str) -> Generator[NewsContextState, None, None]:
        """Context manager that sets and clears the thread-local context."""
        NewsContext.set(provider_id=provider_id, subject=subject, operation=operation)
        try:
            yield _get_state()
        finally:
            NewsContext.clear()
