"""
iios/infrastructure/database/database_context.py
=================================================
Thread-local / context-var session context for ambient database access.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Generator, Optional

from .database_session import DatabaseSession
from .database_engine import DatabaseEngine
from .database_exceptions import SessionError

__all__ = [
    "DatabaseContext",
    "current_session",
    "push_session",
    "pop_session",
    "with_session",
]

# Thread-local stack of active sessions
_local = threading.local()


def _get_stack() -> list[DatabaseSession]:
    if not hasattr(_local, "stack"):
        _local.stack = []
    return _local.stack


def current_session() -> Optional[DatabaseSession]:
    """Return the innermost active session on the current thread, or None."""
    stack = _get_stack()
    return stack[-1] if stack else None


def push_session(session: DatabaseSession) -> None:
    _get_stack().append(session)


def pop_session() -> Optional[DatabaseSession]:
    stack = _get_stack()
    return stack.pop() if stack else None


@contextmanager
def with_session(engine: DatabaseEngine) -> Generator[DatabaseSession, None, None]:
    """Push a session onto the thread-local stack for the duration of the block.

    Usage::

        with with_session(engine) as sess:
            # sess is also available via current_session()
            Trade.find_all(current_session())
    """
    with engine.session() as sess:
        push_session(sess)
        try:
            yield sess
        finally:
            pop_session()


class DatabaseContext:
    """Ambient database context — provides the current session without passing it explicitly.

    Useful for service classes that don't want to thread sessions through every method.

    Usage::

        class TradeService:
            def __init__(self, ctx: DatabaseContext):
                self._ctx = ctx

            def get_trades(self) -> list[Trade]:
                with self._ctx.session() as sess:
                    return Trade.find_all(sess)
    """

    def __init__(self, engine: DatabaseEngine) -> None:
        self._engine = engine

    @contextmanager
    def session(self) -> Generator[DatabaseSession, None, None]:
        """Yield a new session; also pushes it to thread-local context."""
        with with_session(self._engine) as sess:
            yield sess

    @property
    def current(self) -> Optional[DatabaseSession]:
        return current_session()

    @property
    def engine(self) -> DatabaseEngine:
        return self._engine
