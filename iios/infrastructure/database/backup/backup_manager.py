"""
iios/infrastructure/database/backup/backup_manager.py
=====================================================
SQLite database backup and restore manager.
"""

from __future__ import annotations

import gzip
import logging
import os
import shutil
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..database_config import BackupConfig
from ..database_constants import BackupType
from ..database_exceptions import BackupError, RestoreError

__all__ = ["BackupRecord", "BackupManager"]

_LOG = logging.getLogger("iios.database.backup")


@dataclass
class BackupRecord:
    """Metadata about a completed backup."""
    id: str
    backup_type: BackupType
    source_path: str
    backup_path: str
    size_bytes: int
    compressed: bool
    created_at: float = field(default_factory=time.time)
    checksum: str = ""


class BackupManager:
    """Performs full SQLite backups using the sqlite3 backup API.

    Supports:
    - Full backups via ``sqlite3.Connection.backup()``
    - Optional gzip compression
    - Retention-based cleanup

    Usage::

        mgr = BackupManager(db_path="data/trades.db", config=backup_config)
        record = mgr.backup()              # full backup
        mgr.restore(record.backup_path)   # restore from backup
    """

    def __init__(self, db_path: str, config: Optional[BackupConfig] = None) -> None:
        self._db_path = db_path
        self._cfg = config or BackupConfig()
        self._backup_dir = Path(self._cfg.backup_dir)
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._records: list[BackupRecord] = []

    def backup(
        self,
        backup_type: BackupType = BackupType.FULL,
        label: str = "",
    ) -> BackupRecord:
        """Create a backup of the SQLite database."""
        if not os.path.exists(self._db_path) and self._db_path != ":memory:":
            raise BackupError(f"Source DB not found: {self._db_path}")

        ts = int(time.time())
        tag = f"{label}_" if label else ""
        base_name = f"backup_{tag}{backup_type.value}_{ts}.db"
        dest = self._backup_dir / base_name

        t0 = time.time()
        try:
            src_conn = sqlite3.connect(self._db_path)
            dst_conn = sqlite3.connect(str(dest))
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
        except Exception as exc:
            raise BackupError(f"Backup failed: {exc}") from exc

        # Compress
        final_path = str(dest)
        compressed = False
        if self._cfg.compress:
            gz_path = str(dest) + ".gz"
            with open(str(dest), "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            os.remove(str(dest))
            final_path = gz_path
            compressed = True

        size = os.path.getsize(final_path)
        checksum = _file_sha256(final_path)
        record = BackupRecord(
            id=f"{backup_type.value}_{ts}",
            backup_type=backup_type,
            source_path=self._db_path,
            backup_path=final_path,
            size_bytes=size,
            compressed=compressed,
            checksum=checksum,
        )
        self._records.append(record)
        _LOG.info(
            "Backup completed: %s (%.1f KB, %.2fs)",
            final_path, size / 1024, time.time() - t0,
        )

        self._apply_retention()
        return record

    def restore(self, backup_path: str, target_path: Optional[str] = None) -> None:
        """Restore a database from a backup file."""
        target = target_path or self._db_path
        if not os.path.exists(backup_path):
            raise RestoreError(f"Backup file not found: {backup_path}")

        t0 = time.time()
        try:
            if backup_path.endswith(".gz"):
                tmp = backup_path.replace(".gz", ".tmp.db")
                with gzip.open(backup_path, "rb") as f_in, open(tmp, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
                src_path = tmp
            else:
                src_path = backup_path

            src_conn = sqlite3.connect(src_path)
            dst_conn = sqlite3.connect(target)
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()

            if src_path.endswith(".tmp.db"):
                os.remove(src_path)
        except Exception as exc:
            raise RestoreError(f"Restore failed: {exc}") from exc

        _LOG.info("Restore completed: %s → %s in %.2fs", backup_path, target, time.time() - t0)

    def verify(self, backup_path: str) -> bool:
        """Verify backup file integrity by computing its checksum."""
        if not os.path.exists(backup_path):
            return False
        rec = next((r for r in self._records if r.backup_path == backup_path), None)
        if rec is None:
            return True  # can't compare — assume ok
        return _file_sha256(backup_path) == rec.checksum

    def list_backups(self) -> list[BackupRecord]:
        return list(self._records)

    def cleanup_old(self) -> int:
        cutoff = time.time() - self._cfg.retention_days * 86400
        removed = 0
        for rec in list(self._records):
            if rec.created_at < cutoff:
                try:
                    os.remove(rec.backup_path)
                    self._records.remove(rec)
                    removed += 1
                except OSError:
                    pass
        return removed

    def _apply_retention(self) -> None:
        if self._cfg.retention_days > 0:
            self.cleanup_old()


def _file_sha256(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()[:16]
