"""
iios/infrastructure/storage/compressed_storage.py
==================================================
Compressed storage (gzip) built on LocalStorage.
"""

from __future__ import annotations

import gzip
from typing import Any

from .local_storage import LocalStorage
from ..infrastructure_models import StorageMetadata

__all__ = ["CompressedStorage"]


class CompressedStorage:
    """Transparently compresses/decompresses data with gzip."""

    def __init__(
        self,
        root: str = "data/storage/compressed",
        compresslevel: int = 6,
    ) -> None:
        self._store = LocalStorage(root)
        self._level = compresslevel

    def write(self, key: str, data: bytes, *, overwrite: bool = True) -> StorageMetadata:
        compressed = gzip.compress(data, compresslevel=self._level)
        return self._store.write(key + ".gz", compressed, overwrite=overwrite)

    def read(self, key: str) -> bytes:
        compressed = self._store.read(key + ".gz")
        return gzip.decompress(compressed)

    def delete(self, key: str) -> bool:
        return self._store.delete(key + ".gz")

    def exists(self, key: str) -> bool:
        return self._store.exists(key + ".gz")

    def list(self, prefix: str = "") -> list[str]:
        keys = self._store.list(prefix)
        return [k[:-3] if k.endswith(".gz") else k for k in keys]
