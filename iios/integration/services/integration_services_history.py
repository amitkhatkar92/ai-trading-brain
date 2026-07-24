"""
integration_services_history.py — iios.integration.services
-------------------------------------------------------------
IntegrationServicesHistory — bounded history of ConnectorRequest /
ConnectorResponse pairs for audit and diagnostics.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse
from .constants import DEFAULT_MAX_HISTORY


@dataclass(frozen=True)
class ServicesHistoryEntry:
    """An immutable history entry pairing request and response."""
    entry_id:   str
    request_id: str
    service_type: str
    success:    bool
    latency_ms: float
    retry_count: int
    recorded_at: str


@dataclass(frozen=True)
class ServicesHistoryReport:
    """Summary report of service history."""
    total_entries:   int
    successful:      int
    failed:          int
    avg_latency_ms:  float
    avg_retry_count: float
    oldest_entry_at: Optional[str]
    newest_entry_at: Optional[str]
    generated_at:    str


class IntegrationServicesHistory:
    """
    Thread-safe bounded history of service executions.

    Entries are stored as lightweight records (not full request/response).
    Bounded at max_size — oldest entries are dropped when full.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._lock:    threading.Lock       = threading.Lock()
        self._entries: Deque[ServicesHistoryEntry] = deque(maxlen=max_size)
        self._max      = max_size

    # ── Record ────────────────────────────────────────────────────────────

    def record(
        self,
        request:  ConnectorRequest,
        response: ConnectorResponse,
    ) -> ServicesHistoryEntry:
        entry = ServicesHistoryEntry(
            entry_id     = f"shist-{response.response_id[-8:]}",
            request_id   = request.request_id,
            service_type = request.service_type.value,
            success      = (response.status.value == "success"),
            latency_ms   = response.latency_ms,
            retry_count  = response.retry_count,
            recorded_at  = datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._entries.append(entry)
        return entry

    # ── Query ─────────────────────────────────────────────────────────────

    def recent(self, n: int = 20) -> List[ServicesHistoryEntry]:
        with self._lock:
            entries = list(self._entries)
        return entries[-n:]

    def by_service_type(self, service_type: str) -> List[ServicesHistoryEntry]:
        with self._lock:
            return [e for e in self._entries if e.service_type == service_type]

    def failed(self) -> List[ServicesHistoryEntry]:
        with self._lock:
            return [e for e in self._entries if not e.success]

    def report(self) -> ServicesHistoryReport:
        with self._lock:
            entries = list(self._entries)
        if not entries:
            return ServicesHistoryReport(
                total_entries=0, successful=0, failed=0,
                avg_latency_ms=0.0, avg_retry_count=0.0,
                oldest_entry_at=None, newest_entry_at=None,
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
        successful = sum(1 for e in entries if e.success)
        return ServicesHistoryReport(
            total_entries  = len(entries),
            successful     = successful,
            failed         = len(entries) - successful,
            avg_latency_ms = sum(e.latency_ms   for e in entries) / len(entries),
            avg_retry_count= sum(e.retry_count  for e in entries) / len(entries),
            oldest_entry_at= entries[0].recorded_at,
            newest_entry_at= entries[-1].recorded_at,
            generated_at   = datetime.now(timezone.utc).isoformat(),
        )

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
