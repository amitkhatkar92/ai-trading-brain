"""
iios/infrastructure/database/orm/base_model.py
==============================================
Base class for all IIOS ORM models (dataclass-based).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, ClassVar, Generator, List, Optional, Sequence, Type, TypeVar

from ..database_session import DatabaseSession
from ..database_connection import Row
from .specification import Specification, Always
from .entity_mapper import EntityMapper

__all__ = ["BaseModel"]

T = TypeVar("T", bound="BaseModel")


@dataclass
class BaseModel:
    """Base class for all ORM models.

    Subclass with ``@dataclass`` and define ``__tablename__`` ::

        @dataclass
        class Trade(BaseModel):
            __tablename__ = "trades"
            __primary_key__ = "id"
            __schema__ = '''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    qty    INTEGER NOT NULL DEFAULT 1
                )
            '''
            id: Optional[int] = None
            symbol: str = ""
            qty: int = 0

        # CRUD usage
        with engine.session() as sess:
            Trade.create_table(sess)
            t = Trade(symbol="RELIANCE", qty=10)
            t = t.save(sess)          # INSERT; returns instance with id set
            t.qty = 20
            t.save(sess)              # UPDATE (id is set)
            Trade.find_all(sess)      # list of Trade
    """

    __tablename__: ClassVar[str] = ""
    __primary_key__: ClassVar[str] = "id"
    __schema__: ClassVar[str] = ""          # CREATE TABLE SQL, set by subclass

    # ── Write operations ──────────────────────────────────────────────────────

    def save(self: T, session: DatabaseSession) -> T:
        """INSERT if pk is None, UPDATE otherwise."""
        pk_name = self.__class__.__primary_key__
        pk_val = getattr(self, pk_name, None)

        if pk_val is None:
            return self._insert(session)
        else:
            return self._update(session)

    def _insert(self: T, session: DatabaseSession) -> T:
        sql, columns = EntityMapper.get_insert_sql(self.__class__)
        params = [getattr(self, c) for c in columns]
        result = session.execute(sql, params)
        pk_name = self.__class__.__primary_key__
        if result.lastrowid is not None:
            object.__setattr__(self, pk_name, result.lastrowid)
        return self

    def _update(self: T, session: DatabaseSession) -> T:
        pk_name = self.__class__.__primary_key__
        pk_val = getattr(self, pk_name)
        sql, columns, pk_val = EntityMapper.get_update_sql(self.__class__, pk_val)
        params = [getattr(self, c) for c in columns] + [pk_val]
        session.execute(sql, params)
        return self

    def delete(self, session: DatabaseSession) -> bool:
        """Delete this record by primary key."""
        pk_name = self.__class__.__primary_key__
        pk_val = getattr(self, pk_name, None)
        if pk_val is None:
            return False
        sql = EntityMapper.get_delete_sql(self.__class__)
        result = session.execute(sql, (pk_val,))
        return result.rowcount > 0

    # ── Class-level queries ───────────────────────────────────────────────────

    @classmethod
    def find_by_id(cls: Type[T], session: DatabaseSession, pk: Any) -> Optional[T]:
        pk_name = cls.__primary_key__
        table = cls.__tablename__
        row = session.query_one(
            f"SELECT * FROM {table} WHERE {pk_name} = ?", (pk,)
        )
        return EntityMapper.from_row(cls, row) if row else None

    @classmethod
    def find_all(
        cls: Type[T],
        session: DatabaseSession,
        spec: Optional[Specification] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[T]:
        where_sql, params = _spec_sql(spec)
        sql = EntityMapper.get_select_sql(
            cls,
            where=where_sql or None,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        rows = session.query(sql, params)
        return [EntityMapper.from_row(cls, r) for r in rows]

    @classmethod
    def find_one(
        cls: Type[T],
        session: DatabaseSession,
        spec: Specification,
    ) -> Optional[T]:
        results = cls.find_all(session, spec=spec, limit=1)
        return results[0] if results else None

    @classmethod
    def count(
        cls: Type[T],
        session: DatabaseSession,
        spec: Optional[Specification] = None,
    ) -> int:
        table = cls.__tablename__
        where_sql, params = _spec_sql(spec)
        sql = f"SELECT COUNT(*) AS cnt FROM {table}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        row = session.query_one(sql, params)
        return int(row["cnt"]) if row else 0

    @classmethod
    def exists(
        cls: Type[T],
        session: DatabaseSession,
        spec: Specification,
    ) -> bool:
        return cls.count(session, spec=spec) > 0

    @classmethod
    def delete_all(
        cls: Type[T],
        session: DatabaseSession,
        spec: Optional[Specification] = None,
    ) -> int:
        table = cls.__tablename__
        where_sql, params = _spec_sql(spec)
        sql = f"DELETE FROM {table}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        result = session.execute(sql, params)
        return result.rowcount

    @classmethod
    def paginate(
        cls: Type[T],
        session: DatabaseSession,
        page: int = 1,
        page_size: int = 50,
        spec: Optional[Specification] = None,
        order_by: Optional[str] = None,
    ) -> tuple[list[T], int]:
        """Return (records, total_count) for a paginated result set."""
        where_sql, params = _spec_sql(spec)
        table = cls.__tablename__
        base_sql = f"SELECT * FROM {table}"
        if where_sql:
            base_sql += f" WHERE {where_sql}"
        if order_by:
            base_sql += f" ORDER BY {order_by}"
        rows, total = session.query_paginated(base_sql, params, page=page, page_size=page_size)
        return [EntityMapper.from_row(cls, r) for r in rows], total

    @classmethod
    def create_table(cls, session: DatabaseSession) -> None:
        """Run the class-level __schema__ DDL statement."""
        schema = cls.__schema__
        if schema:
            session.execute(schema)
        else:
            raise ValueError(
                f"{cls.__name__} has no __schema__ — define CREATE TABLE SQL in __schema__"
            )


# ── Helper ────────────────────────────────────────────────────────────────────

def _spec_sql(spec: Optional[Specification]) -> tuple[str, list]:
    if spec is None:
        return "", []
    return spec.to_sql()
