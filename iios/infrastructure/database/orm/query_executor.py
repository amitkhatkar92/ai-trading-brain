"""
iios/infrastructure/database/orm/query_executor.py
===================================================
Executes raw SQL with optional caching, metrics, and model hydration.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, Type, TypeVar

from .entity_mapper import EntityMapper
from ..database_session import DatabaseSession
from ..database_connection import Row
from ..performance.query_cache import QueryCache
from ..performance.metrics import DatabaseMetrics

__all__ = ["QueryExecutor"]

T = TypeVar("T")


class QueryExecutor:
    """Executes SQL queries against a session, with optional caching and metrics.

    Meant as an internal helper for BaseModel and OrmQueryBuilder; users rarely
    need to interact with this class directly.
    """

    def __init__(
        self,
        session: DatabaseSession,
        cache: Optional[QueryCache] = None,
        metrics: Optional[DatabaseMetrics] = None,
    ) -> None:
        self._session = session
        self._cache = cache
        self._metrics = metrics

    def fetch_all(
        self,
        sql: str,
        params: Sequence[Any] = (),
        tables: Optional[list[str]] = None,
        cache: bool = True,
    ) -> list[Row]:
        params_t = tuple(params)
        if cache and self._cache:
            hit = self._cache.get(sql, params_t)
            if hit is not None:
                return hit

        with (self._metrics.measure(sql) if self._metrics else _noop()):
            rows = self._session.query(sql, params_t)

        if cache and self._cache:
            self._cache.set(sql, params_t, rows, tables=tables)

        return rows

    def fetch_one(
        self,
        sql: str,
        params: Sequence[Any] = (),
    ) -> Optional[Row]:
        with (self._metrics.measure(sql) if self._metrics else _noop()):
            return self._session.query_one(sql, params)

    def fetch_scalar(
        self,
        sql: str,
        params: Sequence[Any] = (),
    ) -> Any:
        row = self.fetch_one(sql, params)
        if row is None:
            return None
        return next(iter(row.values()), None)

    def execute(
        self,
        sql: str,
        params: Sequence[Any] = (),
        invalidate_tables: Optional[list[str]] = None,
    ) -> int:
        """Execute a DML statement; optionally invalidate cached tables."""
        with (self._metrics.measure(sql) if self._metrics else _noop()):
            result = self._session.execute(sql, params)

        if invalidate_tables and self._cache:
            for table in invalidate_tables:
                self._cache.invalidate_table(table)

        return result.rowcount

    def fetch_models(
        self,
        cls: Type[T],
        sql: str,
        params: Sequence[Any] = (),
        tables: Optional[list[str]] = None,
        cache: bool = True,
    ) -> list[T]:
        rows = self.fetch_all(sql, params, tables=tables, cache=cache)
        return [EntityMapper.from_row(cls, r) for r in rows]


class _noop:
    """No-op context manager for optional metrics."""
    def __enter__(self) -> "_noop":
        return self
    def __exit__(self, *_: Any) -> bool:
        return False
