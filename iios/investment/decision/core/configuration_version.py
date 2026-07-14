"""iios/investment/decision/core/configuration_version.py
ConfigurationVersion — tracks versioned snapshots of configuration data.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ConfigSnapshot:
    """Immutable snapshot of a configuration at one point in time."""
    snapshot_id:   str
    version:       int
    config_data:   Dict[str, Any]
    author:        str
    change_note:   str
    created_at:    datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "version":     self.version,
            "config_data": self.config_data,
            "author":      self.author,
            "change_note": self.change_note,
            "created_at":  self.created_at.isoformat(),
        }


class ConfigurationVersion:
    """
    Thread-safe versioned history of configuration snapshots.
    Supports rollback to any previous version.
    """

    def __init__(self, initial_data: Dict[str, Any], author: str = "system") -> None:
        self._lock     = threading.RLock()
        self._history: List[ConfigSnapshot] = []
        self._version  = 0
        self._commit(initial_data, author, "initial configuration")

    def _commit(self, data: Dict[str, Any], author: str, note: str) -> ConfigSnapshot:
        self._version += 1
        snap = ConfigSnapshot(
            snapshot_id=str(uuid.uuid4()),
            version=self._version,
            config_data=dict(data),
            author=author,
            change_note=note,
            created_at=datetime.now(timezone.utc),
        )
        self._history.append(snap)
        return snap

    def commit(self, data: Dict[str, Any], author: str = "system", note: str = "") -> ConfigSnapshot:
        with self._lock:
            return self._commit(data, author, note)

    @property
    def current(self) -> ConfigSnapshot:
        with self._lock:
            return self._history[-1]

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def get_version(self, version: int) -> Optional[ConfigSnapshot]:
        with self._lock:
            for snap in self._history:
                if snap.version == version:
                    return snap
            return None

    def history(self) -> List[ConfigSnapshot]:
        with self._lock:
            return list(self._history)

    def rollback(self, version: int, author: str = "system") -> Optional[ConfigSnapshot]:
        """Roll back to a previous version by creating a new snapshot with old data."""
        with self._lock:
            snap = self.get_version(version)
            if snap is None:
                return None
            return self._commit(
                snap.config_data,
                author,
                f"rollback to version {version}",
            )
