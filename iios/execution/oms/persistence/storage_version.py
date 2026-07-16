"""iios/execution/oms/persistence/storage_version.py
==================================================
StorageVersion and VersionHistory — record and schema versioning.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator

from iios.execution.oms.persistence.constants import SCHEMA_VERSION, VersionType


@dataclass(frozen=True)
class StorageVersion:
    """
    Immutable entry in a record's version history.

    Captures what changed, when, and by whom.
    """
    version_id:      str   = field(default_factory=lambda: str(uuid.uuid4()))
    record_id:       str   = ""
    version_type:    VersionType = VersionType.RECORD
    version_number:  int   = 1
    schema_version:  str   = SCHEMA_VERSION
    recorded_at:     float = field(default_factory=time.time)
    author:          str   = "iios:system"
    change_summary:  str   = ""
    metadata:        dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id":     self.version_id,
            "record_id":      self.record_id,
            "version_type":   self.version_type.value,
            "version_number": self.version_number,
            "schema_version": self.schema_version,
            "recorded_at":    self.recorded_at,
            "author":         self.author,
            "change_summary": self.change_summary,
        }


class VersionHistory:
    """
    Thread-safe, append-only list of StorageVersion entries for a single record.
    """

    __slots__ = ("_record_id", "_entries", "_lock")

    def __init__(self, record_id: str) -> None:
        self._record_id = record_id
        self._entries:  list[StorageVersion] = []
        self._lock      = threading.RLock()

    def append(self, version: StorageVersion) -> None:
        with self._lock:
            self._entries.append(version)

    def all(self) -> list[StorageVersion]:
        with self._lock:
            return list(self._entries)

    def latest(self) -> StorageVersion | None:
        with self._lock:
            return self._entries[-1] if self._entries else None

    def at_version(self, version_number: int) -> StorageVersion | None:
        with self._lock:
            for v in reversed(self._entries):
                if v.version_number == version_number:
                    return v
        return None

    def by_type(self, version_type: VersionType) -> list[StorageVersion]:
        with self._lock:
            return [v for v in self._entries if v.version_type == version_type]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    @property
    def current_version(self) -> int:
        with self._lock:
            if not self._entries:
                return 0
            return self._entries[-1].version_number

    def __iter__(self) -> Iterator[StorageVersion]:
        with self._lock:
            snapshot = list(self._entries)
        return iter(snapshot)

    def __len__(self) -> int:
        return self.count

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":       self._record_id,
            "count":           self.count,
            "current_version": self.current_version,
        }
