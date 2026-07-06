"""
iios/infrastructure/storage/binary_storage.py
=============================================
Raw binary storage — thin alias over LocalStorage with typed helpers.
"""

from __future__ import annotations

from .local_storage import LocalStorage
from ..infrastructure_models import StorageMetadata

__all__ = ["BinaryStorage"]


class BinaryStorage:
    """Stores raw binary blobs."""

    def __init__(self, root: str = "data/storage/binary") -> None:
        self._store = LocalStorage(root)

    def write(self, key: str, data: bytes, *, overwrite: bool = True) -> StorageMetadata:
        return self._store.write(key, data, overwrite=overwrite)

    def read(self, key: str) -> bytes:
        return self._store.read(key)

    def delete(self, key: str) -> bool:
        return self._store.delete(key)

    def exists(self, key: str) -> bool:
        return self._store.exists(key)

    def list(self, prefix: str = "") -> list[str]:
        return self._store.list(prefix)
