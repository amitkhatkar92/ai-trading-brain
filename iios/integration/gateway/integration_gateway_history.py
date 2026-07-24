"""
integration_gateway_history.py — iios.integration.gateway
-----------------------------------------------------------
GatewayHistoryEntry, GatewayHistoryReport, and IntegrationGatewayHistory.

Bounded, thread-safe history of completed gateway operations.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_MAX_HISTORY,
    ENTRY_ID_PREFIX,
    GatewayOperationType,
    GatewayResponseStatus,
)

import threading


@dataclass(frozen=True)
class GatewayHistoryEntry:
    """Immutable record of a single completed gateway operation."""

    entry_id:             str
    gateway_id:           str
    request_id:           str
    operation:            GatewayOperationType
    status:               GatewayResponseStatus
    processing_time_ms:   float
    lifecycle_session_id: str
    snapshot_id:          str
    recorded_at:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id":             self.entry_id,
            "gateway_id":           self.gateway_id,
            "request_id":           self.request_id,
            "operation":            self.operation.value,
            "status":               self.status.value,
            "processing_time_ms":   self.processing_time_ms,
            "lifecycle_session_id": self.lifecycle_session_id,
            "snapshot_id":          self.snapshot_id,
            "recorded_at":          self.recorded_at,
        }


@dataclass(frozen=True)
class GatewayHistoryReport:
    """Summary of gateway history."""

    total_entries: int
    successful:    int
    failed:        int
    by_operation:  Dict[str, int]   # operation.value → count
    generated_at:  str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entries": self.total_entries,
            "successful":    self.successful,
            "failed":        self.failed,
            "by_operation":  dict(self.by_operation),
            "generated_at":  self.generated_at,
        }


class IntegrationGatewayHistory:
    """
    Bounded, thread-safe history of completed gateway operations.

    Ordered by insertion time (oldest first in deque).
    ``recent(n)`` returns the most recent *n* entries.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._entries: deque[GatewayHistoryEntry] = deque(maxlen=max_size)
        self._max_size = max_size
        self._lock = threading.Lock()

    # ─── recording ────────────────────────────────────────────────────

    def record(
        self,
        gateway_id:           str,
        request_id:           str,
        operation:            GatewayOperationType,
        status:               GatewayResponseStatus,
        processing_time_ms:   float = 0.0,
        lifecycle_session_id: str   = "",
        snapshot_id:          str   = "",
    ) -> GatewayHistoryEntry:
        """Create and store a history entry. Returns the new entry."""
        entry = GatewayHistoryEntry(
            entry_id             = f"{ENTRY_ID_PREFIX}{uuid.uuid4().hex[:12]}",
            gateway_id           = gateway_id,
            request_id           = request_id,
            operation            = operation,
            status               = status,
            processing_time_ms   = processing_time_ms,
            lifecycle_session_id = lifecycle_session_id,
            snapshot_id          = snapshot_id,
            recorded_at          = datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._entries.append(entry)
        return entry

    # ─── retrieval ────────────────────────────────────────────────────

    def recent(self, n: int = 100) -> List[GatewayHistoryEntry]:
        """Return the most recent *n* entries (newest last)."""
        with self._lock:
            entries = list(self._entries)
        return entries[-n:]

    def by_status(self, status: GatewayResponseStatus) -> List[GatewayHistoryEntry]:
        with self._lock:
            return [e for e in self._entries if e.status == status]

    def by_operation(self, operation: GatewayOperationType) -> List[GatewayHistoryEntry]:
        with self._lock:
            return [e for e in self._entries if e.operation == operation]

    def by_gateway(self, gateway_id: str) -> List[GatewayHistoryEntry]:
        with self._lock:
            return [e for e in self._entries if e.gateway_id == gateway_id]

    # ─── report ───────────────────────────────────────────────────────

    def report(self) -> GatewayHistoryReport:
        with self._lock:
            entries = list(self._entries)

        by_op: Dict[str, int] = {}
        successful = 0
        failed     = 0
        for e in entries:
            by_op[e.operation.value] = by_op.get(e.operation.value, 0) + 1
            if e.status == GatewayResponseStatus.SUCCESS:
                successful += 1
            elif e.status in (GatewayResponseStatus.FAILED, GatewayResponseStatus.REJECTED):
                failed += 1

        return GatewayHistoryReport(
            total_entries = len(entries),
            successful    = successful,
            failed        = failed,
            by_operation  = by_op,
            generated_at  = datetime.now(timezone.utc).isoformat(),
        )

    # ─── management ───────────────────────────────────────────────────

    def clear(self) -> int:
        with self._lock:
            n = len(self._entries)
            self._entries.clear()
            return n

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    @property
    def max_size(self) -> int:
        return self._max_size
