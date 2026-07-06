"""
iios/infrastructure/database/database_factory.py
=================================================
Factory for creating DatabaseEngine instances from config.
"""

from __future__ import annotations

from typing import Any, Optional

from .database_config import DatabaseConfig, PoolConfig, CacheConfig
from .database_constants import DatabaseEngine as EngineType
from .database_engine import DatabaseEngine
from .database_exceptions import ConfigurationError, UnsupportedEngineError

__all__ = ["DatabaseFactory"]

_SUPPORTED = {e.value for e in EngineType}


class DatabaseFactory:
    """Creates and validates ``DatabaseEngine`` instances from config.

    Usage::

        engine = DatabaseFactory.create(
            DatabaseConfig(name="trades", engine=DatabaseEngine.SQLITE, url="data/trades.db")
        )

        # Quick helper for in-memory SQLite (tests/dev):
        engine = DatabaseFactory.in_memory(name="test")
    """

    @staticmethod
    def create(config: DatabaseConfig) -> DatabaseEngine:
        """Create a DatabaseEngine from a DatabaseConfig."""
        DatabaseFactory._validate(config)
        return DatabaseEngine(config)

    @staticmethod
    def sqlite(
        path: str,
        name: str = "default",
        pool_size: int = 5,
        cache_ttl: float = 60.0,
        wal: bool = True,
        echo: bool = False,
    ) -> DatabaseEngine:
        """Shortcut: create a SQLite DatabaseEngine."""
        cfg = DatabaseConfig(
            name=name,
            engine=EngineType.SQLITE,
            url=path,
            wal_mode=wal,
            echo=echo,
            pool=PoolConfig(size=pool_size),
            cache=CacheConfig(ttl=cache_ttl),
        )
        return DatabaseEngine(cfg)

    @staticmethod
    def in_memory(name: str = "test", echo: bool = False) -> DatabaseEngine:
        """Create an in-memory SQLite engine (useful for tests)."""
        cfg = DatabaseConfig(
            name=name,
            engine=EngineType.SQLITE,
            url=":memory:",
            echo=echo,
            pool=PoolConfig(size=1),
            cache=CacheConfig(enabled=False),
            audit=__import__("iios.infrastructure.database.database_config", fromlist=["AuditConfig"]).AuditConfig(enabled=False),
        )
        return DatabaseEngine(cfg)

    @staticmethod
    def postgresql(
        host: str,
        database: str,
        username: str = "",
        password: str = "",
        port: int = 5432,
        name: str = "pg_default",
        pool_size: int = 10,
    ) -> DatabaseEngine:
        """Shortcut: create a PostgreSQL DatabaseEngine."""
        cfg = DatabaseConfig(
            name=name,
            engine=EngineType.POSTGRESQL,
            url=f"{host}:{port}",
            username=username,
            password=password,
            database=database,
            pool=PoolConfig(size=pool_size),
        )
        return DatabaseEngine(cfg)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DatabaseEngine:
        """Create a DatabaseEngine from a plain dict (e.g. loaded from YAML)."""
        try:
            engine_str = data.pop("engine", "sqlite").lower()
            engine = EngineType(engine_str)
        except ValueError:
            raise UnsupportedEngineError(engine_str)

        cfg = DatabaseConfig(engine=engine, **{k: v for k, v in data.items() if not isinstance(v, dict)})

        if "pool" in data:
            cfg.pool = PoolConfig(**data["pool"])
        if "cache" in data:
            cfg.cache = CacheConfig(**data["cache"])

        return DatabaseEngine(cfg)

    @staticmethod
    def _validate(config: DatabaseConfig) -> None:
        if not config.url and config.engine == EngineType.SQLITE:
            raise ConfigurationError(
                "SQLite requires a 'url' (file path or ':memory:')",
                code="DB-CFG-002",
            )
        if config.pool.size < 1:
            raise ConfigurationError(
                "pool.size must be >= 1",
                code="DB-CFG-003",
            )
        if config.pool.timeout <= 0:
            raise ConfigurationError(
                "pool.timeout must be > 0",
                code="DB-CFG-004",
            )
