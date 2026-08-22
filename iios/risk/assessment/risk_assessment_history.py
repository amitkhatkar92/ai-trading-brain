"""
risk_assessment_history.py — iios.risk.assessment
===================================================
Bounded in-memory history store for the Risk Assessment Framework.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY


class RiskAssessmentHistory:
    """
    Thread-safe bounded ring-buffer for assessment artefacts.

    Four independent deques are maintained:
    - Events
    - Requests
    - Reports (completed assessments)
    - Errors

    Parameters
    ----------
    max_items :
        Maximum items retained per buffer.
        Defaults to :data:`~.constants.DEFAULT_MAX_HISTORY`.
    """

    def __init__(self, max_items: int = DEFAULT_MAX_HISTORY) -> None:
        self._max  = max_items
        self._lock = threading.RLock()
        self._events:   Deque[Any] = deque(maxlen=max_items)
        self._requests: Deque[Any] = deque(maxlen=max_items)
        self._reports:  Deque[Any] = deque(maxlen=max_items)
        self._errors:   Deque[Any] = deque(maxlen=max_items)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_event(self, event: Any) -> None:
        with self._lock:
            self._events.append(event)

    def record_request(self, request: Any) -> None:
        with self._lock:
            self._requests.append(request)

    def record_report(self, report: Any) -> None:
        with self._lock:
            self._reports.append(report)

    def record_error(self, error: Any) -> None:
        with self._lock:
            self._errors.append(error)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def recent_events(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n < len(items) else items

    def recent_requests(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._requests)
        return items[-n:] if n < len(items) else items

    def recent_reports(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._reports)
        return items[-n:] if n < len(items) else items

    def recent_errors(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._errors)
        return items[-n:] if n < len(items) else items

    def find_report(self, assessment_id: str) -> Optional[Any]:
        """Return most recent report for the given assessment_id, or None."""
        with self._lock:
            for report in reversed(list(self._reports)):
                if getattr(report, "assessment_id", None) == assessment_id:
                    return report
        return None

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "events":   len(self._events),
                "requests": len(self._requests),
                "reports":  len(self._reports),
                "errors":   len(self._errors),
            }

    def clear(self) -> None:
        """Clear all history buffers (thread-safe)."""
        with self._lock:
            self._events.clear()
            self._requests.clear()
            self._reports.clear()
            self._errors.clear()
