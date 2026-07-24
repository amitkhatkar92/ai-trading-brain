"""
knowledge_integration_status.py — iios.knowledge.integration
-------------------------------------------------------------
Status tracking for the Knowledge Integration engine.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import IntegrationState, VERSION


@dataclass(frozen=True)
class KnowledgeIntegrationStatus:
    """
    Point-in-time operational status of the Knowledge Integration engine.
    """
    state:             IntegrationState
    version:           str
    uptime_seconds:    float
    integration_count: int
    last_request_id:   str
    last_snapshot_id:  str
    is_running:        bool
    is_healthy:        bool
    captured_at:       str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state":             self.state.value,
            "version":           self.version,
            "uptime_seconds":    self.uptime_seconds,
            "integration_count": self.integration_count,
            "last_request_id":   self.last_request_id,
            "last_snapshot_id":  self.last_snapshot_id,
            "is_running":        self.is_running,
            "is_healthy":        self.is_healthy,
            "captured_at":       self.captured_at,
        }


class KnowledgeIntegrationStatusTracker:
    """
    Thread-safe status tracker for the integration engine.
    """

    def __init__(self) -> None:
        self._lock             = threading.Lock()
        self._state            = IntegrationState.STOPPED
        self._started_at:      Optional[float]  = None
        self._integration_count = 0
        self._last_request_id  = ""
        self._last_snapshot_id = ""
        self._is_healthy       = False

    # ----------------------------------------------------------------
    # Mutation
    # ----------------------------------------------------------------

    def set_state(self, state: IntegrationState) -> None:
        import time
        with self._lock:
            self._state = state
            if state == IntegrationState.RUNNING and self._started_at is None:
                self._started_at = time.monotonic()
            if state == IntegrationState.STOPPED:
                self._started_at = None
            self._is_healthy = state in (
                IntegrationState.RUNNING, IntegrationState.DEGRADED
            )

    def record_request(self, request_id: str) -> None:
        with self._lock:
            self._integration_count += 1
            self._last_request_id   = request_id

    def record_snapshot(self, snapshot_id: str) -> None:
        with self._lock:
            self._last_snapshot_id = snapshot_id

    # ----------------------------------------------------------------
    # Query
    # ----------------------------------------------------------------

    def get(self) -> KnowledgeIntegrationStatus:
        import time
        with self._lock:
            uptime = (
                time.monotonic() - self._started_at
                if self._started_at is not None else 0.0
            )
            return KnowledgeIntegrationStatus(
                state             = self._state,
                version           = VERSION,
                uptime_seconds    = round(uptime, 2),
                integration_count = self._integration_count,
                last_request_id   = self._last_request_id,
                last_snapshot_id  = self._last_snapshot_id,
                is_running        = self._state == IntegrationState.RUNNING,
                is_healthy        = self._is_healthy,
                captured_at       = datetime.now(tz=timezone.utc).isoformat(),
            )
