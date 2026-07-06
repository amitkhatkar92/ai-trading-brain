"""
iios/infrastructure/database/orm/query_builder.py
==================================================
ORM-level fluent query builder — operates on BaseModel classes.
"""

from __future__ import annotations

from typing import Any, Optional, Type, TypeVar

from .specification import Specification
from .entity_mapper import EntityMapper
from ..database_session import DatabaseSession
from ..database_connection import Row

__all__ = ["OrmQueryBuilder"]

T = TypeVar("T")


class OrmQueryBuilder:
    """Fluent query builder scoped to a model class.

    Usage::

        trades = (
            OrmQueryBuilder(Trade, session)
            .filter(Eq("symbol", "RELIANCE") & Gt("qty", 5))
            .order_by("qty DESC")
            .limit(20)
            .all()
        )
    """

    def __init__(self, model_cls: Type[T], session: DatabaseSession) -> None:
        self._cls = model_cls
        self._session = session
        self._spec: Optional[Specification] = None
        self._order: Optional[str] = None
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._columns: str = "*"

    # ── Builder methods ───────────────────────────────────────────────────────

    def filter(self, spec: Specification) -> "OrmQueryBuilder":
        if self._spec is None:
            self._spec = spec
        else:
            self._spec = self._spec & spec
        return self

    def order_by(self, clause: str) -> "OrmQueryBuilder":
        self._order = clause
        return self

    def limit(self, n: int) -> "OrmQueryBuilder":
        self._limit = n
        return self

    def offset(self, n: int) -> "OrmQueryBuilder":
        self._offset = n
        return self

    def columns(self, *cols: str) -> "OrmQueryBuilder":
        self._columns = ", ".join(cols)
        return self

    # ── Terminal methods ──────────────────────────────────────────────────────

    def all(self) -> list[T]:
        """Return all matching rows as model instances."""
        from .base_model import BaseModel
        model_cls = self._cls
        sql, params = self._build_select()
        rows = self._session.query(sql, params)
        return [EntityMapper.from_row(model_cls, r) for r in rows]

    def one(self) -> Optional[T]:
        """Return the first matching row or None."""
        self._limit = 1
        results = self.all()
        return results[0] if results else None

    def count(self) -> int:
        table = _tablename(self._cls)
        where_sql, params = self._where_clause()
        sql = f"SELECT COUNT(*) AS cnt FROM {table}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        row = self._session.query_one(sql, params)
        return int(row["cnt"]) if row else 0

    def exists(self) -> bool:
        return self.count() > 0

    def delete(self) -> int:
        """Delete matching rows; returns affected count."""
        table = _tablename(self._cls)
        where_sql, params = self._where_clause()
        sql = f"DELETE FROM {table}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        result = self._session.execute(sql, params)
        return result.rowcount

    def paginate(self, page: int = 1, page_size: int = 50) -> tuple[list[T], int]:
        table = _tablename(self._cls)
        where_sql, params = self._where_clause()
        base_sql = f"SELECT {self._columns} FROM {table}"
        if where_sql:
            base_sql += f" WHERE {where_sql}"
        if self._order:
            base_sql += f" ORDER BY {self._order}"
        rows, total = self._session.query_paginated(base_sql, params, page=page, page_size=page_size)
        return [EntityMapper.from_row(self._cls, r) for r in rows], total

    def raw(self) -> list[Row]:
        """Return rows as plain dicts (no mapping)."""
        sql, params = self._build_select()
        return self._session.query(sql, params)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _where_clause(self) -> tuple[str, list]:
        if self._spec is None:
            return "", []
        frag, params = self._spec.to_sql()
        return frag, params

    def _build_select(self) -> tuple[str, list]:
        table = _tablename(self._cls)
        where_sql, params = self._where_clause()
        sql = f"SELECT {self._columns} FROM {table}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        if self._order:
            sql += f" ORDER BY {self._order}"
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._offset is not None:
            sql += f" OFFSET {self._offset}"
        return sql, params


def _tablename(cls: type) -> str:
    name = getattr(cls, "__tablename__", None)
    if not name:
        raise ValueError(f"{cls.__name__} has no __tablename__")
    return name
