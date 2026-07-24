"""
database_connector_engine.py — iios.integration.services
----------------------------------------------------------
DatabaseConnectorEngine — provider-independent database connector interface.

MUST NOT import: sqlalchemy, pymysql, psycopg2, sqlite3, or any DB driver.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse

_log = get_logger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Abstract Interface
# ════════════════════════════════════════════════════════════════════════


class BaseDatabaseConnector(ABC):
    """Abstract database connector — implementors inject the DB driver."""

    @abstractmethod
    def query(
        self,
        sql:        str,
        params:     Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30_000,
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT and return rows as dicts."""

    @abstractmethod
    def execute(
        self,
        sql:        str,
        params:     Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30_000,
    ) -> int:
        """Execute DML (INSERT/UPDATE/DELETE) and return affected row count."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the database is reachable."""


class SimulatedDatabaseConnector(BaseDatabaseConnector):
    """In-process database simulation — no DB I/O."""

    def query(
        self,
        sql:        str,
        params:     Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30_000,
    ) -> List[Dict[str, Any]]:
        return [{"simulated": True, "sql": sql, "row": 0}]

    def execute(
        self,
        sql:        str,
        params:     Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30_000,
    ) -> int:
        return 1

    def health_check(self) -> bool:
        return True


# ════════════════════════════════════════════════════════════════════════
# Engine
# ════════════════════════════════════════════════════════════════════════


class DatabaseConnectorEngine:
    """
    Manages database connector instances and routes requests.

    Named connections are registered by connection_id and can be reused
    across multiple requests.
    """

    def __init__(self) -> None:
        self._lock        = threading.Lock()
        self._connections: Dict[str, BaseDatabaseConnector] = {}
        self._queries     = 0
        self._mutations   = 0
        self._errors      = 0

    def register_connection(
        self,
        connection_id: str,
        connector:     Optional[BaseDatabaseConnector] = None,
    ) -> None:
        conn = connector or SimulatedDatabaseConnector()
        with self._lock:
            self._connections[connection_id] = conn
        _log.debug(f"db-engine: registered connection {connection_id!r}")

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        try:
            cfg           = request.connector_config
            connection_id = cfg.get("db_connection_id", "default")
            sql           = cfg.get("db_sql", "SELECT 1")
            operation     = cfg.get("db_operation", "query").lower()

            with self._lock:
                conn = self._connections.get(connection_id)
                if conn is None:
                    conn = SimulatedDatabaseConnector()
                    self._connections[connection_id] = conn

            if operation == "execute":
                rows_affected = conn.execute(
                    sql=sql, params=request.payload, timeout_ms=request.timeout_ms
                )
                data = {"rows_affected": rows_affected, "sql": sql}
                with self._lock:
                    self._mutations += 1
            else:
                rows = conn.query(
                    sql=sql, params=request.payload, timeout_ms=request.timeout_ms
                )
                data = {"rows": rows, "count": len(rows), "sql": sql}
                with self._lock:
                    self._queries += 1

            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.success(
                request.request_id, data=data, latency_ms=latency_ms,
                adapter_id="database-connector-engine", transport="database_wire",
            )
        except Exception as exc:
            with self._lock:
                self._errors += 1
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="database-connector-engine", transport="database_wire",
            )

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "connections": len(self._connections),
                "queries":     self._queries,
                "mutations":   self._mutations,
                "errors":      self._errors,
            }
