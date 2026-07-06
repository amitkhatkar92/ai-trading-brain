"""
iios/infrastructure/database/orm/entity_mapper.py
==================================================
Maps between dataclass model instances and database rows.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Optional, Type, TypeVar

from ..database_connection import Row

__all__ = ["EntityMapper"]

T = TypeVar("T")


class EntityMapper:
    """Maps BaseModel dataclass instances to/from SQL rows.

    Works with any dataclass whose fields correspond to database columns.
    Does not require a specific base class — duck-typed on ``__tablename__``
    and ``__primary_key__`` class-vars.
    """

    @staticmethod
    def to_row(entity: Any) -> Row:
        """Convert a dataclass instance to a dict of column→value."""
        if not dataclasses.is_dataclass(entity):
            raise TypeError(f"{type(entity).__name__} is not a dataclass")
        return {f.name: getattr(entity, f.name) for f in dataclasses.fields(entity)}

    @staticmethod
    def from_row(cls: Type[T], row: Row) -> T:
        """Construct an instance of *cls* from a database row dict."""
        if not dataclasses.is_dataclass(cls):
            raise TypeError(f"{cls.__name__} is not a dataclass")
        fields = {f.name for f in dataclasses.fields(cls)}
        kwargs = {k: v for k, v in row.items() if k in fields}
        return cls(**kwargs)

    @staticmethod
    def get_columns(cls: type) -> list[str]:
        """Return all field names as column names."""
        if not dataclasses.is_dataclass(cls):
            raise TypeError(f"{cls.__name__} is not a dataclass")
        return [f.name for f in dataclasses.fields(cls)]

    @staticmethod
    def get_insert_sql(cls: type, exclude_pk_if_none: bool = True) -> tuple[str, list[str]]:
        """Return (INSERT SQL template, ordered_column_names).

        Excludes the primary key if its value is None (auto-increment).
        """
        table = _tablename(cls)
        pk = _pk(cls)
        columns = EntityMapper.get_columns(cls)
        if exclude_pk_if_none:
            columns = [c for c in columns if c != pk]
        placeholders = ", ".join("?" * len(columns))
        col_list = ", ".join(columns)
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
        return sql, columns

    @staticmethod
    def get_update_sql(cls: type, pk_value: Any) -> tuple[str, list[str], Any]:
        """Return (UPDATE SQL template, ordered_column_names, pk_value).

        Excludes the primary key from SET clause.
        """
        table = _tablename(cls)
        pk = _pk(cls)
        columns = [c for c in EntityMapper.get_columns(cls) if c != pk]
        set_clause = ", ".join(f"{c} = ?" for c in columns)
        sql = f"UPDATE {table} SET {set_clause} WHERE {pk} = ?"
        return sql, columns, pk_value

    @staticmethod
    def get_delete_sql(cls: type) -> str:
        table = _tablename(cls)
        pk = _pk(cls)
        return f"DELETE FROM {table} WHERE {pk} = ?"

    @staticmethod
    def get_select_sql(
        cls: type,
        where: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        table = _tablename(cls)
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {limit}"
        if offset is not None:
            sql += f" OFFSET {offset}"
        return sql


def _tablename(cls: type) -> str:
    name = getattr(cls, "__tablename__", None)
    if not name:
        raise ValueError(f"{cls.__name__} has no __tablename__")
    return name


def _pk(cls: type) -> str:
    return getattr(cls, "__primary_key__", "id")
