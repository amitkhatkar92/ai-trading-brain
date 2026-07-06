"""
iios/infrastructure/repositories/unit_of_work.py
=================================================
Unit of Work pattern — groups repository operations into an atomic unit.
"""

from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional

from ..infrastructure_exceptions import UnitOfWorkError
from ..infrastructure_models import TransactionContext

__all__ = ["UnitOfWork", "InMemoryUnitOfWork"]


class UnitOfWork(Exception):
    """Marker exception for rolling back a unit of work."""


class InMemoryUnitOfWork:
    """In-memory Unit of Work for coordinating repository operations.

    Usage::

        uow = InMemoryUnitOfWork()
        with uow.begin() as ctx:
            repo.save(entity)          # operations collected
            uow.commit()               # commits tracked changes
        # on exception: automatic rollback
    """

    def __init__(self) -> None:
        self._context: Optional[TransactionContext] = None
        self._committed_callbacks: list[Callable[[], None]] = []
        self._rollback_callbacks: list[Callable[[], None]] = []
        self._operations: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    @contextmanager
    def begin(self) -> Generator["InMemoryUnitOfWork", None, None]:
        """Context manager that creates a transaction and auto-rolls back on failure."""
        with self._lock:
            if self._context is not None and self._context.is_active:
                raise UnitOfWorkError(
                    "UnitOfWork already active; nested UoW not supported",
                    code="INF-UOW-001",
                )
            self._context = TransactionContext()
            self._operations = []
            self._committed_callbacks = []
            self._rollback_callbacks = []

        try:
            yield self
            # Auto-commit if no explicit commit/rollback was called
            if self._context is not None and self._context.is_active:
                self.commit()
        except UnitOfWorkError:
            raise
        except Exception as exc:
            self.rollback()
            raise UnitOfWorkError(
                f"UnitOfWork rolled back due to: {exc}",
                code="INF-UOW-002",
            ) from exc

    def commit(self) -> None:
        with self._lock:
            if self._context is None or not self._context.is_active:
                raise UnitOfWorkError("No active UnitOfWork to commit", code="INF-UOW-003")
            self._context.committed = True
            for cb in self._committed_callbacks:
                try:
                    cb()
                except Exception:
                    pass

    def rollback(self) -> None:
        with self._lock:
            if self._context is None:
                return
            self._context.rolled_back = True
            for cb in self._rollback_callbacks:
                try:
                    cb()
                except Exception:
                    pass
            self._operations = []

    def record(self, operation: dict[str, Any]) -> None:
        """Track a repository operation in the current UoW."""
        with self._lock:
            if self._context is not None and self._context.is_active:
                self._context.operations.append(str(operation))
            self._operations.append(operation)

    def on_commit(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked after successful commit."""
        self._committed_callbacks.append(callback)

    def on_rollback(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked after rollback."""
        self._rollback_callbacks.append(callback)

    @property
    def is_active(self) -> bool:
        return self._context is not None and self._context.is_active

    @property
    def context(self) -> Optional[TransactionContext]:
        return self._context

    @property
    def pending_operations(self) -> list[dict[str, Any]]:
        return list(self._operations)
