"""
iios/infrastructure/database/database_manager.py
=================================================
Main high-level façade for the IIOS Database Framework.

Combines registry, factory, migrations, audit, and context management.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any, Generator, Optional

from .database_config import DatabaseConfig
from .database_constants import DatabaseEngine as EngineType
from .database_engine import DatabaseEngine
from .database_factory import DatabaseFactory
from .database_registry import DatabaseRegistry, get_database_registry
from .database_session import DatabaseSession
from .database_context import DatabaseContext, with_session
from .database_exceptions import EngineNotFoundError, DatabaseError

__all__ = ["DatabaseManager", "get_database_manager", "reset_database_manager"]

_LOG = logging.getLogger("iios.database.manager")
_mgr_lock = threading.Lock()
_manager: Optional["DatabaseManager"] = None


class DatabaseManager:
    """Unified entry-point for all database operations in IIOS.

    Usage::

        mgr = get_database_manager()

        # Register an engine
        mgr.configure("trades", DatabaseConfig(
            engine=DatabaseEngine.SQLITE,
            url="data/trades.db",
        ))

        # Use sessions
        with mgr.session("trades") as sess:
            rows = sess.query("SELECT * FROM trades")

        # Quick one-shot query
        rows = mgr.query("trades", "SELECT * FROM trades WHERE symbol=?", ("RELIANCE",))
    """

    def __init__(self) -> None:
        self._registry = get_database_registry()
        self._lock = threading.RLock()
        self._initialized = False

    # ── Engine management ─────────────────────────────────────────────────────

    def configure(
        self,
        name: str,
        config: DatabaseConfig,
        *,
        as_default: bool = False,
        allow_override: bool = False,
    ) -> DatabaseEngine:
        """Create and register an engine from a DatabaseConfig."""
        engine = DatabaseFactory.create(config)
        self._registry.register(name, engine, as_default=as_default, allow_override=allow_override)
        _LOG.info("Registered database engine '%s' (%s → %s)", name, config.engine.value, config.url)
        return engine

    def register(
        self,
        name: str,
        engine: DatabaseEngine,
        *,
        as_default: bool = False,
        allow_override: bool = False,
    ) -> None:
        """Register a pre-built engine."""
        self._registry.register(name, engine, as_default=as_default, allow_override=allow_override)

    def engine(self, name: str = "default") -> DatabaseEngine:
        """Return a named engine (or the default if name=='default')."""
        if name == "default":
            return self._registry.default()
        return self._registry.get(name)

    def close(self, name: str) -> bool:
        """Close and unregister a named engine."""
        return self._registry.unregister(name, close=True)

    def close_all(self) -> None:
        """Close all registered engines."""
        self._registry.close_all()

    def names(self) -> list[str]:
        return self._registry.names()

    def has(self, name: str) -> bool:
        return self._registry.has(name)

    # ── Session access ────────────────────────────────────────────────────────

    @contextmanager
    def session(self, engine_name: str = "default") -> Generator[DatabaseSession, None, None]:
        """Yield a transactional session for the named engine."""
        eng = self.engine(engine_name)
        with eng.session() as sess:
            yield sess

    def context(self, engine_name: str = "default") -> DatabaseContext:
        """Return a DatabaseContext for ambient session access."""
        return DatabaseContext(self.engine(engine_name))

    # ── One-shot query helpers ────────────────────────────────────────────────

    def execute(
        self,
        engine_name: str,
        sql: str,
        params: tuple = (),
    ) -> int:
        """Execute a DML statement; returns rowcount."""
        with self.session(engine_name) as sess:
            result = sess.execute(sql, params)
            return result.rowcount

    def query(
        self,
        engine_name: str,
        sql: str,
        params: tuple = (),
        cache: bool = True,
    ) -> list[dict]:
        """Execute a SELECT and return all rows."""
        return self.engine(engine_name).query(sql, params, cache=cache)

    def query_one(
        self,
        engine_name: str,
        sql: str,
        params: tuple = (),
    ) -> Optional[dict]:
        return self.engine(engine_name).query_one(sql, params)

    # ── Table utilities ───────────────────────────────────────────────────────

    def table_exists(self, engine_name: str, table_name: str) -> bool:
        return self.engine(engine_name).table_exists(table_name)

    # ── Performance stats ─────────────────────────────────────────────────────

    def metrics(self, engine_name: str = "default") -> dict[str, Any]:
        return self.engine(engine_name).metrics.report()

    # ── Convenience factory methods ────────────────────────────────────────────

    def in_memory(self, name: str = "test") -> DatabaseEngine:
        """Create and register an in-memory SQLite engine (for tests)."""
        engine = DatabaseFactory.in_memory(name=name)
        self._registry.register(name, engine, allow_override=True)
        return engine

    def sqlite(
        self,
        path: str,
        name: str = "default",
        *,
        as_default: bool = True,
    ) -> DatabaseEngine:
        """Create and register a file-based SQLite engine."""
        engine = DatabaseFactory.sqlite(path=path, name=name)
        self._registry.register(name, engine, as_default=as_default, allow_override=True)
        return engine


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------


def get_database_manager() -> DatabaseManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = DatabaseManager()
        return _manager


def reset_database_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.close_all()
        _manager = None
