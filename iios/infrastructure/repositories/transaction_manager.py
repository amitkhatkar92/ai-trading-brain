"""
iios/infrastructure/repositories/transaction_manager.py
=======================================================
Transaction management for repositories.
"""

from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional

from ..infrastructure_exceptions import TransactionError
from ..infrastructure_models import TransactionContext

__all__ = ["TransactionManager"]


class TransactionManager:
    """Manages transaction lifecycle for repository operations.

    Usage::

        tm = TransactionManager()
        with tm.transaction() as ctx:
            # perform operations
            ctx.operations.append("INSERT entity")
        # transaction auto-committed or rolled back
    """

    def __init__(self) -> None:
        self._active: dict[str, TransactionContext] = {}
        self._lock = threading.RLock()
        self._committed = 0
        self._rolled_back = 0

    @contextmanager
    def transaction(self) -> Generator[TransactionContext, None, None]:
        """Context manager providing a new transaction context."""
        ctx = TransactionContext()
        with self._lock:
            self._active[ctx.transaction_id] = ctx
        try:
            yield ctx
            if ctx.is_active:
                self._commit(ctx)
        except TransactionError:
            if ctx.is_active:
                self._rollback(ctx)
            raise
        except Exception as exc:
            if ctx.is_active:
                self._rollback(ctx)
            raise TransactionError(
                f"Transaction {ctx.transaction_id[:8]} rolled back: {exc}",
                code="INF-TXN-001",
            ) from exc
        finally:
            with self._lock:
                self._active.pop(ctx.transaction_id, None)

    def _commit(self, ctx: TransactionContext) -> None:
        ctx.committed = True
        self._committed += 1

    def _rollback(self, ctx: TransactionContext) -> None:
        ctx.rolled_back = True
        self._rolled_back += 1

    def active_transactions(self) -> list[TransactionContext]:
        with self._lock:
            return list(self._active.values())

    @property
    def committed_count(self) -> int:
        return self._committed

    @property
    def rolled_back_count(self) -> int:
        return self._rolled_back
