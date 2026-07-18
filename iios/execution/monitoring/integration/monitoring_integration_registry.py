"""iios/execution/monitoring/integration/monitoring_integration_registry.py
==================================================
IntegrationRegistry — LifecycleAwareMixin registry for tracking active
integration sessions and published snapshots.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_SESSIONS,
    REGISTRY_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    IntegrationNotRunningError,
    IntegrationRequestNotFoundError,
    IntegrationSessionNotFoundError,
)
from .monitoring_integration_response import MonitoringIntegrationResponse
from .monitoring_integration_snapshot import MonitoringIntegrationSnapshot

_log = get_logger(__name__)


class IntegrationRegistry(LifecycleAwareMixin):
    """
    Thread-safe, lifecycle-aware store for integration responses and snapshots.
    """

    def __init__(
        self,
        max_responses: int = DEFAULT_MAX_REQUESTS,
        max_snapshots: int = DEFAULT_MAX_SESSIONS,
    ) -> None:
        super().__init__()
        self._max_responses = max(1, max_responses)
        self._max_snapshots = max(1, max_snapshots)
        self._responses: Dict[str, MonitoringIntegrationResponse] = {}
        self._snapshots: Dict[str, MonitoringIntegrationSnapshot] = {}
        self._lock = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("IntegrationRegistry starting.", system_id=REGISTRY_SYSTEM_ID, version=VERSION)

    def _on_stop(self) -> None:
        with self._lock:
            r_count = len(self._responses)
            s_count = len(self._snapshots)
        _log.info(
            "IntegrationRegistry stopping.",
            system_id=REGISTRY_SYSTEM_ID,
            stored_responses=r_count,
            stored_snapshots=s_count,
        )

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise IntegrationNotRunningError()

    # ── Response CRUD ─────────────────────────────────────────────────────────

    def store_response(self, response: MonitoringIntegrationResponse) -> None:
        self._assert_running()
        with self._lock:
            if len(self._responses) >= self._max_responses:
                # Evict oldest response to make room
                oldest_key = next(iter(self._responses))
                del self._responses[oldest_key]
            self._responses[response.response_id] = response

    def get_response(self, response_id: str) -> MonitoringIntegrationResponse:
        self._assert_running()
        with self._lock:
            r = self._responses.get(response_id)
        if r is None:
            raise IntegrationRequestNotFoundError(response_id)
        return r

    def find_response(
        self, response_id: str
    ) -> Optional[MonitoringIntegrationResponse]:
        with self._lock:
            return self._responses.get(response_id)

    def all_responses(self) -> List[MonitoringIntegrationResponse]:
        with self._lock:
            return list(self._responses.values())

    def responses_for_session(
        self, session_id: str
    ) -> List[MonitoringIntegrationResponse]:
        with self._lock:
            return [r for r in self._responses.values() if r.session_id == session_id]

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    # ── Snapshot CRUD ─────────────────────────────────────────────────────────

    def store_snapshot(self, snapshot: MonitoringIntegrationSnapshot) -> None:
        self._assert_running()
        with self._lock:
            if len(self._snapshots) >= self._max_snapshots:
                oldest_key = next(iter(self._snapshots))
                del self._snapshots[oldest_key]
            self._snapshots[snapshot.snapshot_id] = snapshot

    def get_snapshot(self, snapshot_id: str) -> MonitoringIntegrationSnapshot:
        self._assert_running()
        with self._lock:
            s = self._snapshots.get(snapshot_id)
        if s is None:
            raise IntegrationSessionNotFoundError(snapshot_id)
        return s

    def find_snapshot(
        self, snapshot_id: str
    ) -> Optional[MonitoringIntegrationSnapshot]:
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def all_snapshots(self) -> List[MonitoringIntegrationSnapshot]:
        with self._lock:
            return list(self._snapshots.values())

    def snapshots_for_session(
        self, session_id: str
    ) -> List[MonitoringIntegrationSnapshot]:
        with self._lock:
            return [s for s in self._snapshots.values() if s.session_id == session_id]

    def latest_snapshot_for_session(
        self, session_id: str
    ) -> Optional[MonitoringIntegrationSnapshot]:
        snaps = self.snapshots_for_session(session_id)
        return max(snaps, key=lambda s: s.created_at) if snaps else None

    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    # ── Clear ─────────────────────────────────────────────────────────────────

    def clear(self) -> None:
        self._assert_running()
        with self._lock:
            self._responses.clear()
            self._snapshots.clear()
