"""
iios/infrastructure/database/indexing/index_manager.py
======================================================
Manages database indexes — create, drop, list, check.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ..database_session import DatabaseSession
from ..database_constants import IndexType

__all__ = ["IndexDefinition", "IndexManager"]

_LOG = logging.getLogger("iios.database.indexing")


@dataclass
class IndexDefinition:
    """Metadata for a single database index."""
    name: str
    table: str
    columns: list[str]
    index_type: IndexType = IndexType.SECONDARY
    unique: bool = False
    partial_where: Optional[str] = None  # e.g. "active = 1"


class IndexManager:
    """Creates, drops, and introspects table indexes.

    Usage::

        mgr = IndexManager(session)

        # Create a secondary index
        mgr.create(IndexDefinition(
            name="idx_trades_symbol",
            table="trades",
            columns=["symbol"],
        ))

        # Create a unique composite index
        mgr.create(IndexDefinition(
            name="idx_trades_symbol_date",
            table="trades",
            columns=["symbol", "date"],
            unique=True,
        ))

        # List existing indexes on a table
        indexes = mgr.list_for_table("trades")

        # Drop
        mgr.drop("idx_trades_symbol")
    """

    def __init__(self, session: DatabaseSession) -> None:
        self._sess = session

    def create(self, defn: IndexDefinition, if_not_exists: bool = True) -> None:
        """Create an index from an IndexDefinition."""
        unique_kw = "UNIQUE " if defn.unique else ""
        exists_kw = "IF NOT EXISTS " if if_not_exists else ""
        columns = ", ".join(defn.columns)
        sql = (
            f"CREATE {unique_kw}INDEX {exists_kw}"
            f"{defn.name} ON {defn.table} ({columns})"
        )
        if defn.partial_where:
            sql += f" WHERE {defn.partial_where}"
        self._sess.execute(sql)
        _LOG.debug("Created index %s on %s(%s)", defn.name, defn.table, columns)

    def drop(self, name: str, if_exists: bool = True) -> None:
        """Drop an index by name."""
        exists_kw = "IF EXISTS " if if_exists else ""
        self._sess.execute(f"DROP INDEX {exists_kw}{name}")
        _LOG.debug("Dropped index %s", name)

    def exists(self, name: str) -> bool:
        """Check whether an index exists (SQLite)."""
        row = self._sess.query_one(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            (name,),
        )
        return row is not None

    def list_for_table(self, table: str) -> list[dict]:
        """Return all indexes defined on *table* (SQLite)."""
        rows = self._sess.query(
            "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name=?",
            (table,),
        )
        return list(rows)

    def list_all(self) -> list[dict]:
        """Return all user-created indexes in the database."""
        rows = self._sess.query(
            "SELECT * FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        )
        return list(rows)

    def create_many(self, definitions: list[IndexDefinition]) -> None:
        for defn in definitions:
            self.create(defn)
