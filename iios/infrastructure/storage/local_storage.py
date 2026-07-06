"""
iios/infrastructure/storage/local_storage.py
============================================
Local filesystem storage backend.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import threading
import time
from typing import Any, Optional

from ..infrastructure_exceptions import StorageError
from ..infrastructure_models import StorageMetadata

__all__ = ["LocalStorage"]


class LocalStorage:
    """Stores arbitrary binary data in a local directory.

    Usage::

        store = LocalStorage("/app/data/cache")
        store.write("quotes/RELIANCE", b"raw bytes")
        data = store.read("quotes/RELIANCE")
    """

    def __init__(self, root: str = "data/storage") -> None:
        self._root = pathlib.Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def write(self, key: str, data: bytes, *, overwrite: bool = True) -> StorageMetadata:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if path.exists() and not overwrite:
                raise StorageError(
                    f"Key '{key}' already exists",
                    code="INF-STOR-001",
                    context={"key": key},
                )
            path.write_bytes(data)
        checksum = hashlib.sha256(data).hexdigest()
        now = time.time()
        meta = StorageMetadata(
            key=key,
            size_bytes=len(data),
            created_at=now,
            updated_at=now,
            checksum=checksum,
        )
        return meta

    def read(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise StorageError(
                f"Key '{key}' not found",
                code="INF-STOR-002",
                context={"key": key},
            )
        return path.read_bytes()

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def list(self, prefix: str = "") -> list[str]:
        base = self._root / prefix if prefix else self._root
        if not base.exists():
            return []
        return [
            str(p.relative_to(self._root)).replace("\\", "/")
            for p in base.rglob("*")
            if p.is_file()
        ]

    def metadata(self, key: str) -> StorageMetadata:
        path = self._path(key)
        if not path.exists():
            raise StorageError(f"Key '{key}' not found", code="INF-STOR-002")
        stat = path.stat()
        data = path.read_bytes()
        return StorageMetadata(
            key=key,
            size_bytes=stat.st_size,
            created_at=stat.st_ctime,
            updated_at=stat.st_mtime,
            checksum=hashlib.sha256(data).hexdigest(),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _path(self, key: str) -> pathlib.Path:
        # Prevent path traversal
        resolved = (self._root / key).resolve()
        if not str(resolved).startswith(str(self._root.resolve())):
            raise StorageError(
                f"Invalid key (path traversal detected): {key!r}",
                code="INF-STOR-003",
            )
        return resolved

    @property
    def root(self) -> pathlib.Path:
        return self._root
