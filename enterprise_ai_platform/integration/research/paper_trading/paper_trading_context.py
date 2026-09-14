"""paper_trading_context.py — Thread-local execution context for the Paper Trading Framework."""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Generator, Optional


_local = threading.local()


class _PaperTradingContext:
    """Read-only view of the current thread's paper trading context."""

    __slots__ = ("operation", "session_id", "account_id", "request_id", "_started_at")

    def __init__(
        self,
        operation:  str,
        session_id: Optional[str],
        account_id: Optional[str],
        request_id: Optional[str],
        started_at: float,
    ) -> None:
        self.operation  = operation
        self.session_id = session_id
        self.account_id = account_id
        self.request_id = request_id
        self._started_at = started_at

    def elapsed_ms(self) -> float:
        return (time.time() - self._started_at) * 1_000


def set_context(
    operation:  str,
    *,
    session_id: Optional[str] = None,
    account_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """Attach paper trading context to the current thread."""
    _local._ctx = _PaperTradingContext(
        operation  = operation,
        session_id = session_id,
        account_id = account_id,
        request_id = request_id or f"req_{uuid.uuid4().hex[:8]}",
        started_at = time.time(),
    )


def get_context() -> Optional[_PaperTradingContext]:
    """Return the current thread's paper trading context, or None."""
    return getattr(_local, "_ctx", None)


def clear_context() -> None:
    """Remove paper trading context from the current thread."""
    _local._ctx = None


@contextmanager
def scope(
    operation:  str,
    *,
    session_id: Optional[str] = None,
    account_id: Optional[str] = None,
) -> Generator[_PaperTradingContext, None, None]:
    """Context manager that sets and clears the paper trading context."""
    set_context(operation, session_id=session_id, account_id=account_id)
    ctx = get_context()
    try:
        yield ctx  # type: ignore[misc]
    finally:
        clear_context()
