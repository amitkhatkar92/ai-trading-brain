"""
autonomous_governance_history.py — iios.supervisor.governance
--------------------------------------------------------------
Bounded history store for autonomous governance artefacts.

Thread-safe.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List

from .constants import DEFAULT_MAX_HISTORY


class AutonomousGovernanceHistory:
    """
    Thread-safe bounded history store.

    Maintains separate bounded deques for:
    - Governance requests
    - Governance summaries
    - Governance events
    - Audit entries
    """

    def __init__(
        self,
        max_requests:  int = DEFAULT_MAX_HISTORY,
        max_summaries: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY,
        max_audits:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._requests:  Deque[Any] = deque(maxlen=max_requests)
        self._summaries: Deque[Any] = deque(maxlen=max_summaries)
        self._events:    Deque[Any] = deque(maxlen=max_events)
        self._audits:    Deque[Any] = deque(maxlen=max_audits)

    # ------------------------------------------------------------------
    # Recorders
    # ------------------------------------------------------------------

    def record_request(self, request: Any) -> None:
        with self._lock:
            self._requests.append(request)

    def record_summary(self, summary: Any) -> None:
        with self._lock:
            self._summaries.append(summary)

    def record_event(self, event: Any) -> None:
        with self._lock:
            self._events.append(event)

    def record_audit(self, audit: Any) -> None:
        with self._lock:
            self._audits.append(audit)

    # ------------------------------------------------------------------
    # Retrievers
    # ------------------------------------------------------------------

    def recent_requests(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._requests)
        return items[-n:]

    def recent_summaries(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._summaries)
        return items[-n:]

    def recent_events(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._events)
        return items[-n:]

    def recent_audits(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._audits)
        return items[-n:]

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    def summary_count(self) -> int:
        with self._lock:
            return len(self._summaries)

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def audit_count(self) -> int:
        with self._lock:
            return len(self._audits)

    def counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "requests":  len(self._requests),
                "summaries": len(self._summaries),
                "events":    len(self._events),
                "audits":    len(self._audits),
            }

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._summaries.clear()
            self._events.clear()
            self._audits.clear()
