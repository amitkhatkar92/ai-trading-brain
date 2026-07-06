"""
iios/infrastructure/storage/json_storage.py
============================================
JSON storage built on top of LocalStorage.
"""

from __future__ import annotations

import json
from typing import Any

from .local_storage import LocalStorage
from ..infrastructure_exceptions import StorageError

__all__ = ["JsonStorage"]


class JsonStorage:
    """Stores Python objects as JSON files."""

    def __init__(self, root: str = "data/storage/json") -> None:
        self._store = LocalStorage(root)

    def write(self, key: str, obj: Any, **kwargs: Any) -> None:
        try:
            data = json.dumps(obj, default=str).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise StorageError(f"JSON serialization failed: {exc}", code="INF-STOR-010") from exc
        self._store.write(key + ".json", data, **kwargs)

    def read(self, key: str) -> Any:
        raw = self._store.read(key + ".json")
        return json.loads(raw.decode("utf-8"))

    def delete(self, key: str) -> bool:
        return self._store.delete(key + ".json")

    def exists(self, key: str) -> bool:
        return self._store.exists(key + ".json")

    def list(self, prefix: str = "") -> list[str]:
        keys = self._store.list(prefix)
        return [k[:-5] if k.endswith(".json") else k for k in keys]
