"""iios/investment/portfolio/integration/conflict_history.py

Bounded per-portfolio log of detected conflicts and their resolutions.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List

from iios.investment.portfolio.integration.conflict_detector import DetectedConflict
from iios.investment.portfolio.integration.conflict_resolution import ConflictResolutionResult


class ConflictHistory:
    """Thread-safe bounded history of conflicts and resolutions per portfolio."""

    def __init__(self, max_per_portfolio: int = 200) -> None:
        self._max         = max_per_portfolio
        self._lock        = threading.RLock()
        self._conflicts:   Dict[str, deque] = {}
        self._resolutions: Dict[str, deque] = {}

    def add_conflict(self, conflict: DetectedConflict) -> None:
        with self._lock:
            pid = conflict.portfolio_id
            if pid not in self._conflicts:
                self._conflicts[pid] = deque(maxlen=self._max)
            self._conflicts[pid].appendleft(conflict)

    def add_resolution(
        self,
        portfolio_id: str,
        resolution:   ConflictResolutionResult,
    ) -> None:
        with self._lock:
            if portfolio_id not in self._resolutions:
                self._resolutions[portfolio_id] = deque(maxlen=self._max)
            self._resolutions[portfolio_id].appendleft(resolution)

    def recent_conflicts(
        self,
        portfolio_id: str,
        n: int = 20,
    ) -> List[DetectedConflict]:
        with self._lock:
            return list(self._conflicts.get(portfolio_id, deque()))[:n]

    def recent_resolutions(
        self,
        portfolio_id: str,
        n: int = 20,
    ) -> List[ConflictResolutionResult]:
        with self._lock:
            return list(self._resolutions.get(portfolio_id, deque()))[:n]

    def all_portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._conflicts.keys())
