"""
analytics_integration_history.py — iios.execution.analytics.integration
=========================================================================
Thread-safe bounded history stores for the Execution Analytics Integration
subsystem.

Tracks:
  * Completed :class:`AnalyticsIntegrationResponse` objects
  * Published :class:`IntegrationSnapshotRecord` objects
  * Emitted :class:`AnalyticsIntegrationEvent` objects
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional

from .analytics_integration_response import AnalyticsIntegrationResponse
from .analytics_integration_snapshot import IntegrationSnapshotRecord
from .analytics_integration_events import AnalyticsIntegrationEvent
from .constants import DEFAULT_MAX_HISTORY


class AnalyticsIntegrationHistory:
    """
    Thread-safe, bounded history for integration responses, snapshot records,
    and lifecycle events.

    All three queues have independent configurable capacities.  When a queue
    is full the oldest entry is evicted automatically (``deque(maxlen=N)``).

    Parameters
    ----------
    max_responses :  Maximum responses to retain (default 500).
    max_snapshots :  Maximum snapshot records to retain (default 100).
    max_events :     Maximum events to retain (default 500).
    """

    def __init__(
        self,
        max_responses: int = DEFAULT_MAX_HISTORY,
        max_snapshots: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock: threading.Lock = threading.Lock()

        self._responses: deque[AnalyticsIntegrationResponse] = deque(maxlen=max_responses)
        self._snapshots: deque[IntegrationSnapshotRecord]    = deque(maxlen=max_snapshots)
        self._events:    deque[AnalyticsIntegrationEvent]    = deque(maxlen=max_events)

    # ------------------------------------------------------------------
    # Record methods
    # ------------------------------------------------------------------
    def record_response(self, response: AnalyticsIntegrationResponse) -> None:
        """Append *response* to the response history."""
        with self._lock:
            self._responses.append(response)

    def record_snapshot(self, record: IntegrationSnapshotRecord) -> None:
        """Append *record* to the snapshot history."""
        with self._lock:
            self._snapshots.append(record)

    def record_event(self, event: AnalyticsIntegrationEvent) -> None:
        """Append *event* to the event history."""
        with self._lock:
            self._events.append(event)

    # ------------------------------------------------------------------
    # Query: responses
    # ------------------------------------------------------------------
    def responses(self) -> List[AnalyticsIntegrationResponse]:
        """Return all retained responses (oldest first)."""
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[AnalyticsIntegrationResponse]:
        """Return the most recently recorded response, or ``None``."""
        with self._lock:
            return self._responses[-1] if self._responses else None

    def response_count(self) -> int:
        """Number of retained responses."""
        with self._lock:
            return len(self._responses)

    def responses_for_request(self, request_id: str) -> List[AnalyticsIntegrationResponse]:
        """Return all retained responses matching *request_id*."""
        with self._lock:
            return [r for r in self._responses if r.request_id == request_id]

    def responses_for_session(self, execution_session_id: str) -> List[AnalyticsIntegrationResponse]:
        """Return all responses for *execution_session_id*."""
        with self._lock:
            return [
                r for r in self._responses
                if r.execution_session_id == execution_session_id
            ]

    # ------------------------------------------------------------------
    # Query: snapshots
    # ------------------------------------------------------------------
    def snapshots(self) -> List[IntegrationSnapshotRecord]:
        """Return all retained snapshot records (oldest first)."""
        with self._lock:
            return list(self._snapshots)

    def latest_snapshot(self) -> Optional[IntegrationSnapshotRecord]:
        """Return the most recently published snapshot record, or ``None``."""
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def snapshot_count(self) -> int:
        """Number of retained snapshot records."""
        with self._lock:
            return len(self._snapshots)

    def snapshots_for_request(self, request_id: str) -> List[IntegrationSnapshotRecord]:
        """Return snapshot records matching *request_id*."""
        with self._lock:
            return [s for s in self._snapshots if s.request_id == request_id]

    # ------------------------------------------------------------------
    # Query: events
    # ------------------------------------------------------------------
    def events(self) -> List[AnalyticsIntegrationEvent]:
        """Return all retained events (oldest first)."""
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[AnalyticsIntegrationEvent]:
        """Return the most recently emitted event, or ``None``."""
        with self._lock:
            return self._events[-1] if self._events else None

    def event_count(self) -> int:
        """Number of retained events."""
        with self._lock:
            return len(self._events)

    def events_by_type(self, event_type_value: str) -> List[AnalyticsIntegrationEvent]:
        """Return events whose ``event_type.value`` matches *event_type_value*."""
        with self._lock:
            return [e for e in self._events if e.event_type.value == event_type_value]

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------
    def clear(self) -> None:
        """Discard all retained history entries."""
        with self._lock:
            self._responses.clear()
            self._snapshots.clear()
            self._events.clear()

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"AnalyticsIntegrationHistory("
                f"responses={len(self._responses)}, "
                f"snapshots={len(self._snapshots)}, "
                f"events={len(self._events)})"
            )
