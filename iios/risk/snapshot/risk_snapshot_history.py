"""
risk_snapshot_history.py — iios.risk.snapshot
===============================================
Bounded ring-buffer history for RiskSnapshot and related events.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .risk_snapshot import RiskSnapshot


class RiskSnapshotHistory:
    """
    Thread-safe bounded ring-buffer history for snapshot artefacts.

    Four independent buffers are maintained:
    - Snapshots (published)
    - Events
    - Errors
    - Superseded snapshots

    Parameters
    ----------
    max_items :
        Maximum items retained per buffer.
    """

    def __init__(self, max_items: int = DEFAULT_MAX_HISTORY) -> None:
        self._max  = max_items
        self._lock = threading.RLock()
        self._snapshots:   Deque[RiskSnapshot] = deque(maxlen=max_items)
        self._events:      Deque[Any]          = deque(maxlen=max_items)
        self._errors:      Deque[Any]          = deque(maxlen=max_items)
        self._superseded:  Deque[RiskSnapshot] = deque(maxlen=max_items)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_snapshot(self, snapshot: RiskSnapshot) -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    def record_event(self, event: Any) -> None:
        with self._lock:
            self._events.append(event)

    def record_error(self, error: Any) -> None:
        with self._lock:
            self._errors.append(error)

    def record_superseded(self, snapshot: RiskSnapshot) -> None:
        with self._lock:
            self._superseded.append(snapshot)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def recent_snapshots(self, n: int = 10) -> List[RiskSnapshot]:
        with self._lock:
            items = list(self._snapshots)
        return items[-n:] if n < len(items) else items

    def recent_events(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n < len(items) else items

    def recent_errors(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._errors)
        return items[-n:] if n < len(items) else items

    def find_snapshot(self, snapshot_id: str) -> Optional[RiskSnapshot]:
        """Return the snapshot matching snapshot_id, or None."""
        with self._lock:
            for s in reversed(list(self._snapshots)):
                if s.snapshot_id == snapshot_id:
                    return s
        return None

    def find_by_portfolio(self, portfolio_id: str) -> List[RiskSnapshot]:
        """Return all recorded snapshots for a portfolio."""
        with self._lock:
            return [s for s in self._snapshots if s.portfolio_id == portfolio_id]

    def find_by_assessment(self, assessment_id: str) -> List[RiskSnapshot]:
        """Return all recorded snapshots for an assessment."""
        with self._lock:
            return [
                s for s in self._snapshots
                if s.risk_assessment_id == assessment_id
            ]

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "snapshots":  len(self._snapshots),
                "events":     len(self._events),
                "errors":     len(self._errors),
                "superseded": len(self._superseded),
            }

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._events.clear()
            self._errors.clear()
            self._superseded.clear()
