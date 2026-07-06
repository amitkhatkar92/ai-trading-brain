"""
iios/infrastructure/database/query_builder.py
=============================================
Simple fluent SQL query builder.
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = ["QueryBuilder"]


class QueryBuilder:
    """Fluent SQL query builder for safe parameterised queries.

    Usage::

        q = QueryBuilder("trades")
        sql, params = (
            q.select("id", "symbol", "pnl")
             .where("status = ?", "CLOSED")
             .where("pnl > ?", 0)
             .order_by("executed_at DESC")
             .limit(50)
             .build()
        )
    """

    def __init__(self, table: str) -> None:
        self._table = table
        self._columns: list[str] = []
        self._conditions: list[str] = []
        self._params: list[Any] = []
        self._order: Optional[str] = None
        self._limit_val: Optional[int] = None
        self._offset_val: Optional[int] = None

    def select(self, *columns: str) -> "QueryBuilder":
        self._columns.extend(columns)
        return self

    def where(self, condition: str, *values: Any) -> "QueryBuilder":
        self._conditions.append(condition)
        self._params.extend(values)
        return self

    def order_by(self, clause: str) -> "QueryBuilder":
        self._order = clause
        return self

    def limit(self, n: int) -> "QueryBuilder":
        self._limit_val = n
        return self

    def offset(self, n: int) -> "QueryBuilder":
        self._offset_val = n
        return self

    def build(self) -> tuple[str, tuple[Any, ...]]:
        """Build the SELECT query.

        Returns:
            A (sql_string, params_tuple) pair.
        """
        cols = ", ".join(self._columns) if self._columns else "*"
        sql = f"SELECT {cols} FROM {self._table}"
        if self._conditions:
            sql += " WHERE " + " AND ".join(self._conditions)
        if self._order:
            sql += f" ORDER BY {self._order}"
        if self._limit_val is not None:
            sql += f" LIMIT {self._limit_val}"
        if self._offset_val is not None:
            sql += f" OFFSET {self._offset_val}"
        return sql, tuple(self._params)

    def insert(self, **values: Any) -> tuple[str, tuple[Any, ...]]:
        """Build an INSERT statement from keyword arguments."""
        cols = ", ".join(values.keys())
        placeholders = ", ".join("?" * len(values))
        sql = f"INSERT INTO {self._table} ({cols}) VALUES ({placeholders})"
        return sql, tuple(values.values())

    def update(self, where_col: str, where_val: Any, **values: Any) -> tuple[str, tuple[Any, ...]]:
        """Build an UPDATE statement."""
        set_clause = ", ".join(f"{k} = ?" for k in values)
        sql = f"UPDATE {self._table} SET {set_clause} WHERE {where_col} = ?"
        return sql, (*values.values(), where_val)

    def delete(self, where_col: str, where_val: Any) -> tuple[str, tuple[Any, ...]]:
        return f"DELETE FROM {self._table} WHERE {where_col} = ?", (where_val,)
