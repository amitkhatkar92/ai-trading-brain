"""
analytics_integration_registry.py — iios.execution.analytics.integration
=========================================================================
Thread-safe registry that tracks in-flight analytics integration requests.

An entry is added when a request is received and removed when the
corresponding response has been emitted (or the request is rejected).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_REGISTRY
from .analytics_integration_request import AnalyticsIntegrationRequest


# ---------------------------------------------------------------------------
# Entry state
# ---------------------------------------------------------------------------
class RegistryEntryState(str, Enum):
    """Lifecycle state of a registry entry."""
    REGISTERED  = "registered"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"
    REJECTED    = "rejected"


# ---------------------------------------------------------------------------
# Registry entry
# ---------------------------------------------------------------------------
@dataclass
class RegistryEntry:
    """
    Mutable tracking record for one in-flight analytics integration request.
    """
    request:            AnalyticsIntegrationRequest
    state:              RegistryEntryState = RegistryEntryState.REGISTERED
    analytics_session_id: str             = ""
    registered_at:      float             = field(default_factory=time.time)
    started_at:         Optional[float]   = None
    completed_at:       Optional[float]   = None
    error_message:      str               = ""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class AnalyticsIntegrationRegistry:
    """
    Thread-safe registry for in-flight analytics integration requests.

    Entries are inserted on receive, updated as the workflow progresses,
    and retained (up to *max_entries*) for history inspection.

    Parameters
    ----------
    max_entries : Maximum number of entries retained (default 200).
                  When capacity is reached the oldest *completed* entry is
                  evicted.  In-progress entries are never evicted.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_REGISTRY) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._max: int = max_entries
        self._entries: Dict[str, RegistryEntry] = {}

    # ------------------------------------------------------------------
    # Lifecycle operations
    # ------------------------------------------------------------------
    def register(self, request: AnalyticsIntegrationRequest) -> RegistryEntry:
        """
        Register a new request.

        Raises
        ------
        ValueError
            If *request_id* is already registered and still in progress.
        """
        with self._lock:
            if request.request_id in self._entries:
                existing = self._entries[request.request_id]
                if existing.state in (
                    RegistryEntryState.REGISTERED,
                    RegistryEntryState.IN_PROGRESS,
                ):
                    raise ValueError(
                        f"Request {request.request_id!r} is already in-flight"
                    )
            entry = RegistryEntry(request=request)
            self._entries[request.request_id] = entry
            self._evict_if_needed()
            return entry

    def mark_in_progress(
        self, request_id: str, analytics_session_id: str
    ) -> None:
        """
        Transition a registered entry to IN_PROGRESS.

        Called after the M1 analytics session has been created.
        """
        with self._lock:
            entry = self._entries.get(request_id)
            if entry is not None:
                entry.state = RegistryEntryState.IN_PROGRESS
                entry.analytics_session_id = analytics_session_id
                entry.started_at = time.time()

    def mark_completed(self, request_id: str) -> None:
        """Mark an entry as COMPLETED."""
        with self._lock:
            entry = self._entries.get(request_id)
            if entry is not None:
                entry.state = RegistryEntryState.COMPLETED
                entry.completed_at = time.time()

    def mark_failed(self, request_id: str, error_message: str = "") -> None:
        """Mark an entry as FAILED."""
        with self._lock:
            entry = self._entries.get(request_id)
            if entry is not None:
                entry.state = RegistryEntryState.FAILED
                entry.error_message = error_message
                entry.completed_at = time.time()

    def mark_rejected(self, request_id: str, reason: str = "") -> None:
        """Mark an entry as REJECTED."""
        with self._lock:
            entry = self._entries.get(request_id)
            if entry is not None:
                entry.state = RegistryEntryState.REJECTED
                entry.error_message = reason
                entry.completed_at = time.time()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get(self, request_id: str) -> Optional[RegistryEntry]:
        """Return the registry entry for *request_id*, or ``None``."""
        with self._lock:
            return self._entries.get(request_id)

    def active_count(self) -> int:
        """Number of requests currently in REGISTERED or IN_PROGRESS state."""
        with self._lock:
            return sum(
                1 for e in self._entries.values()
                if e.state in (
                    RegistryEntryState.REGISTERED,
                    RegistryEntryState.IN_PROGRESS,
                )
            )

    def total_count(self) -> int:
        """Total number of retained entries."""
        with self._lock:
            return len(self._entries)

    def all_active(self) -> List[RegistryEntry]:
        """Return entries that are REGISTERED or IN_PROGRESS."""
        with self._lock:
            return [
                e for e in self._entries.values()
                if e.state in (
                    RegistryEntryState.REGISTERED,
                    RegistryEntryState.IN_PROGRESS,
                )
            ]

    def all_entries(self) -> List[RegistryEntry]:
        """Return all retained entries."""
        with self._lock:
            return list(self._entries.values())

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------
    def _evict_if_needed(self) -> None:
        """Evict the oldest completed/failed/rejected entry when over capacity."""
        if len(self._entries) <= self._max:
            return
        terminal = [
            (rid, e) for rid, e in self._entries.items()
            if e.state not in (
                RegistryEntryState.REGISTERED,
                RegistryEntryState.IN_PROGRESS,
            )
        ]
        if not terminal:
            return
        # Evict the one with the oldest completed_at (or registered_at)
        oldest_rid = min(
            terminal,
            key=lambda t: (t[1].completed_at or t[1].registered_at),
        )[0]
        del self._entries[oldest_rid]

    def clear_completed(self) -> int:
        """Remove all terminal entries; return count removed."""
        with self._lock:
            terminal_ids = [
                rid for rid, e in self._entries.items()
                if e.state not in (
                    RegistryEntryState.REGISTERED,
                    RegistryEntryState.IN_PROGRESS,
                )
            ]
            for rid in terminal_ids:
                del self._entries[rid]
            return len(terminal_ids)

    def clear(self) -> None:
        """Remove ALL entries (used on subsystem reset)."""
        with self._lock:
            self._entries.clear()

    def __repr__(self) -> str:
        return (
            f"AnalyticsIntegrationRegistry("
            f"total={len(self._entries)}, "
            f"active={self.active_count()})"
        )
