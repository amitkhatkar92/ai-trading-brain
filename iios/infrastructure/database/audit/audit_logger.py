"""
iios/infrastructure/database/audit/audit_logger.py
===================================================
Records INSERT/UPDATE/DELETE/schema changes to _iios_audit table.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from ..database_session import DatabaseSession
from ..database_constants import AuditAction, DEFAULT_AUDIT_TABLE

__all__ = ["AuditEntry", "AuditLogger"]

_LOG = logging.getLogger("iios.database.audit")

_TABLE = DEFAULT_AUDIT_TABLE
_DDL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL DEFAULT '',
    table_name  TEXT    NOT NULL DEFAULT '',
    action      TEXT    NOT NULL,
    pk_value    TEXT,
    old_value   TEXT,
    new_value   TEXT,
    sql_text    TEXT,
    duration_ms REAL    DEFAULT 0,
    timestamp   REAL    NOT NULL
)
"""


@dataclass
class AuditEntry:
    action: str
    table_name: str = ""
    pk_value: Optional[str] = None
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    sql_text: str = ""
    duration_ms: float = 0.0
    session_id: str = ""
    timestamp: float = 0.0
    id: Optional[int] = None


class AuditLogger:
    """Writes audit entries to the _iios_audit table.

    Designed to be called from DatabaseSession's audit callback::

        audit_logger = AuditLogger(session)
        audit_logger.ensure_table()

        # log an INSERT event
        audit_logger.log(AuditEntry(
            action=AuditAction.INSERT.value,
            table_name="trades",
            new_value={"symbol": "RELIANCE", "qty": 10},
        ))
    """

    def __init__(self, session: DatabaseSession) -> None:
        self._sess = session

    def ensure_table(self) -> None:
        self._sess.execute(_DDL)

    def log(self, entry: AuditEntry) -> None:
        if not entry.timestamp:
            entry.timestamp = time.time()
        try:
            self._sess.execute(
                f"INSERT INTO {_TABLE} "
                "(session_id, table_name, action, pk_value, old_value, new_value, sql_text, duration_ms, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry.session_id,
                    entry.table_name,
                    entry.action,
                    entry.pk_value,
                    _json(entry.old_value),
                    _json(entry.new_value),
                    entry.sql_text[:1000] if entry.sql_text else "",
                    entry.duration_ms,
                    entry.timestamp,
                ),
            )
        except Exception as exc:
            _LOG.error("Audit log write failed: %s", exc)

    def query(
        self,
        table_name: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        where_parts, params = [], []
        if table_name:
            where_parts.append("table_name = ?")
            params.append(table_name)
        if action:
            where_parts.append("action = ?")
            params.append(action)
        sql = f"SELECT * FROM {_TABLE}"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self._sess.query(sql, params)
        return [_row_to_entry(r) for r in rows]

    def purge_old(self, retain_days: int = 90) -> int:
        cutoff = time.time() - retain_days * 86400
        result = self._sess.execute(
            f"DELETE FROM {_TABLE} WHERE timestamp < ?", (cutoff,)
        )
        return result.rowcount


def _json(val: Any) -> Optional[str]:
    if val is None:
        return None
    try:
        return json.dumps(val, default=str)
    except Exception:
        return str(val)


def _row_to_entry(row: dict) -> AuditEntry:
    old_val = row.get("old_value")
    new_val = row.get("new_value")
    return AuditEntry(
        id=row.get("id"),
        session_id=row.get("session_id", ""),
        table_name=row.get("table_name", ""),
        action=row.get("action", ""),
        pk_value=row.get("pk_value"),
        old_value=json.loads(old_val) if old_val else None,
        new_value=json.loads(new_val) if new_val else None,
        sql_text=row.get("sql_text", ""),
        duration_ms=row.get("duration_ms", 0.0),
        timestamp=row.get("timestamp", 0.0),
    )
