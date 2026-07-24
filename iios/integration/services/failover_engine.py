"""
failover_engine.py — iios.integration.services
------------------------------------------------
FailoverEngine — manages a pool of connector endpoints and routes
requests to healthy targets, failing over on error.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import HealthStatus

_log = get_logger(__name__)

HealthCheckFn = Callable[[str], bool]
ExecutorFn    = Callable[[str], Any]


@dataclass
class FailoverEndpoint:
    """An endpoint in the failover pool."""
    endpoint_id:   str
    address:       str
    priority:      int       = 0       # lower = preferred
    healthy:       bool      = True
    failure_count: int       = 0
    last_used:     Optional[str] = None


@dataclass
class FailoverResult:
    """Result of a failover-aware execution."""
    success:        bool
    endpoint_used:  Optional[str]
    attempts:       int
    result:         Any
    error:          str = ""


class FailoverEngine:
    """
    Manages a pool of endpoints and provides automatic failover.

    On each ``execute()`` call, the engine selects the highest-priority
    healthy endpoint. If execution fails, the endpoint's failure_count is
    incremented and the next healthy endpoint is tried.
    """

    def __init__(self, failure_threshold: int = 3) -> None:
        self._lock             = threading.Lock()
        self._endpoints:       Dict[str, FailoverEndpoint] = {}
        self._failure_threshold = failure_threshold
        self._failovers        = 0

    # ── Endpoint management ───────────────────────────────────────────────

    def add_endpoint(
        self,
        endpoint_id: str,
        address:     str,
        priority:    int = 0,
    ) -> FailoverEndpoint:
        ep = FailoverEndpoint(endpoint_id=endpoint_id, address=address, priority=priority)
        with self._lock:
            self._endpoints[endpoint_id] = ep
        return ep

    def remove_endpoint(self, endpoint_id: str) -> bool:
        with self._lock:
            if endpoint_id in self._endpoints:
                del self._endpoints[endpoint_id]
                return True
        return False

    def mark_healthy(self, endpoint_id: str) -> None:
        with self._lock:
            ep = self._endpoints.get(endpoint_id)
            if ep:
                ep.healthy       = True
                ep.failure_count = 0

    def mark_unhealthy(self, endpoint_id: str) -> None:
        with self._lock:
            ep = self._endpoints.get(endpoint_id)
            if ep:
                ep.healthy = False

    # ── Execution ────────────────────────────────────────────────────────

    def execute(
        self,
        executor:     ExecutorFn,
        health_check: Optional[HealthCheckFn] = None,
    ) -> FailoverResult:
        """
        Try endpoints in priority order, failing over on exception.

        ``executor`` receives the endpoint address string and returns a result.
        """
        with self._lock:
            ordered = sorted(
                [ep for ep in self._endpoints.values() if ep.healthy],
                key=lambda e: e.priority,
            )

        if not ordered:
            return FailoverResult(
                success=False, endpoint_used=None, attempts=0,
                result=None, error="No healthy endpoints available",
            )

        attempts = 0
        for ep in ordered:
            attempts += 1
            try:
                if health_check and not health_check(ep.address):
                    self.mark_unhealthy(ep.endpoint_id)
                    continue
                result = executor(ep.address)
                with self._lock:
                    ep.last_used     = datetime.now(timezone.utc).isoformat()
                    ep.failure_count = 0
                return FailoverResult(
                    success=True, endpoint_used=ep.address,
                    attempts=attempts, result=result,
                )
            except Exception as exc:
                with self._lock:
                    ep.failure_count += 1
                    if ep.failure_count >= self._failure_threshold:
                        ep.healthy = False
                    self._failovers += 1
                _log.debug(
                    f"failover-engine: endpoint {ep.address!r} failed "
                    f"(count={ep.failure_count}): {exc}"
                )

        return FailoverResult(
            success=False, endpoint_used=None, attempts=attempts,
            result=None, error="All endpoints exhausted",
        )

    # ── Stats ─────────────────────────────────────────────────────────────

    def healthy_count(self) -> int:
        with self._lock:
            return sum(1 for ep in self._endpoints.values() if ep.healthy)

    def total_count(self) -> int:
        with self._lock:
            return len(self._endpoints)

    @property
    def failover_count(self) -> int:
        with self._lock:
            return self._failovers

    def health_status(self) -> HealthStatus:
        with self._lock:
            total   = len(self._endpoints)
            healthy = sum(1 for ep in self._endpoints.values() if ep.healthy)
        if total == 0:
            return HealthStatus.UNKNOWN
        ratio = healthy / total
        if ratio == 1.0:
            return HealthStatus.HEALTHY
        if ratio > 0.5:
            return HealthStatus.DEGRADED
        return HealthStatus.UNHEALTHY
