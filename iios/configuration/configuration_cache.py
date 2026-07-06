"""
iios/configuration/configuration_cache.py
==========================================
Thread-safe versioned configuration cache with TTL and rollback.

``ConfigurationCache`` stores the current live configuration snapshot and
maintains a limited history of previous snapshots for rollback.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .configuration_constants import DEFAULT_CACHE_TTL_SECONDS, MAX_HISTORY_VERSIONS
from .configuration_exception import ConfigurationError

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigurationCache",
    "CacheSnapshot",
]


@dataclass
class CacheSnapshot:
    """One versioned snapshot of the full configuration."""

    version: int
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.monotonic)
    timestamp_iso: str = ""
    checksum: str = ""
    sources: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp_iso:
            self.timestamp_iso = datetime.now(timezone.utc).isoformat()
        if not self.checksum:
            self.checksum = _checksum(self.data)


class ConfigurationCache:
    """Thread-safe configuration cache with TTL, versioning, and rollback.

    Args:
        ttl_seconds: How long a snapshot is considered fresh. After this,
                     ``is_stale`` returns True. 0 or negative = never stale.
        max_history: Maximum number of historical versions to keep for rollback.
    """

    def __init__(
        self,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        max_history: int = MAX_HISTORY_VERSIONS,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_history = max_history
        self._lock = threading.RLock()
        self._current: Optional[CacheSnapshot] = None
        self._history: list[CacheSnapshot] = []        # oldest first
        self._version: int = 0
        self._change_callbacks: list[Any] = []         # Callable[[CacheSnapshot], None]

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by dotted key from the current snapshot."""
        with self._lock:
            if self._current is None:
                return default
            data = self._current.data
            for part in key.split("."):
                if not isinstance(data, dict):
                    return default
                data = data.get(part, default)
            return data

    def get_all(self) -> dict[str, Any]:
        """Return a deep copy of the current configuration snapshot."""
        with self._lock:
            if self._current is None:
                return {}
            return copy.deepcopy(self._current.data)

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    @property
    def is_stale(self) -> bool:
        """True if the current snapshot is older than ``ttl_seconds``."""
        with self._lock:
            if self._current is None:
                return True
            if self._ttl <= 0:
                return False
            return (time.monotonic() - self._current.timestamp) > self._ttl

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return self._current is None

    @property
    def history(self) -> list[CacheSnapshot]:
        """Read-only list of historical snapshots (oldest first)."""
        with self._lock:
            return list(self._history)

    @property
    def current_snapshot(self) -> Optional[CacheSnapshot]:
        with self._lock:
            return self._current

    # ------------------------------------------------------------------
    # Write API
    # ------------------------------------------------------------------

    def put(
        self,
        data: dict[str, Any],
        sources: Optional[list[str]] = None,
    ) -> CacheSnapshot:
        """Store a new snapshot and advance the version counter.

        The previous snapshot is appended to ``history`` (bounded by
        ``max_history``).
        """
        with self._lock:
            self._version += 1
            snapshot = CacheSnapshot(
                version=self._version,
                data=copy.deepcopy(data),
                sources=sources or [],
            )
            if self._current is not None:
                self._history.append(self._current)
                if len(self._history) > self._max_history:
                    self._history.pop(0)
            self._current = snapshot
            logger.debug(
                "Configuration cache updated — version=%d checksum=%s",
                self._version,
                snapshot.checksum[:8],
            )
            callbacks = list(self._change_callbacks)

        # Fire change notifications outside the lock
        for cb in callbacks:
            try:
                cb(snapshot)
            except Exception as exc:
                logger.warning("Configuration change callback raised: %s", exc)

        return snapshot

    def invalidate(self) -> None:
        """Clear the current snapshot (marks cache as stale)."""
        with self._lock:
            self._current = None
            logger.debug("Configuration cache invalidated")

    def clear(self) -> None:
        """Clear current snapshot and all history."""
        with self._lock:
            self._current = None
            self._history.clear()
            self._version = 0
            logger.debug("Configuration cache cleared")

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback(self, version: int) -> CacheSnapshot:
        """Restore a previous snapshot by version number.

        The restored snapshot is re-committed as a new version so the version
        counter always advances.

        Raises:
            ConfigurationError: if the requested version is not in history.
        """
        with self._lock:
            for snap in self._history:
                if snap.version == version:
                    logger.info("Rolling back configuration to version %d", version)
                    return self.put(snap.data, sources=snap.sources)
            raise ConfigurationError(
                f"Cannot rollback: version {version} not found in cache history "
                f"(available: {[s.version for s in self._history]})",
                code="CFG-CAC-001",
            )

    def diff(self, version_a: int, version_b: int) -> dict[str, Any]:
        """Compute the keys that differ between two versions.

        Returns a dict ``{key: (old_value, new_value)}`` for changed keys.
        """
        snap_a = self._find_version(version_a)
        snap_b = self._find_version(version_b)
        if snap_a is None:
            raise ConfigurationError(f"Version {version_a} not found", code="CFG-CAC-002")
        if snap_b is None:
            raise ConfigurationError(f"Version {version_b} not found", code="CFG-CAC-002")
        return _diff_dicts(snap_a.data, snap_b.data)

    # ------------------------------------------------------------------
    # Change notifications
    # ------------------------------------------------------------------

    def on_change(self, callback: Any) -> None:
        """Register a callback invoked whenever the cache is updated.

        Args:
            callback: ``Callable[[CacheSnapshot], None]``
        """
        with self._lock:
            self._change_callbacks.append(callback)

    def remove_change_handler(self, callback: Any) -> None:
        with self._lock:
            self._change_callbacks = [c for c in self._change_callbacks if c is not callback]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_version(self, version: int) -> Optional[CacheSnapshot]:
        with self._lock:
            if self._current and self._current.version == version:
                return self._current
            for snap in self._history:
                if snap.version == version:
                    return snap
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _checksum(data: dict[str, Any]) -> str:
    """Compute a short SHA-256 of the serialized config."""
    try:
        raw = json.dumps(data, sort_keys=True, default=str)
    except Exception:
        raw = str(data)
    return hashlib.sha256(raw.encode()).hexdigest()


def _diff_dicts(
    old: dict[str, Any],
    new: dict[str, Any],
    prefix: str = "",
) -> dict[str, tuple[Any, Any]]:
    """Recursively find differing keys between *old* and *new*."""
    diffs: dict[str, tuple[Any, Any]] = {}
    all_keys = set(old) | set(new)
    for key in all_keys:
        full_key = f"{prefix}.{key}" if prefix else key
        old_val = old.get(key)
        new_val = new.get(key)
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            diffs.update(_diff_dicts(old_val, new_val, prefix=full_key))
        elif old_val != new_val:
            diffs[full_key] = (old_val, new_val)
    return diffs
