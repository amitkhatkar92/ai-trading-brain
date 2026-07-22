"""
portfolio_snapshot_history.py — iios.portfolio.snapshot
========================================================
Per-portfolio version history with bounded deques.

History tracks all snapshot versions received for each portfolio,
capped at ``max_versions_per_portfolio`` (default 100).  Versions are
stored in insertion (chronological) order.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY_PER_PF
from .portfolio_snapshot import PortfolioSnapshot


class PortfolioSnapshotHistory:
    """
    Thread-safe, bounded version history for PortfolioSnapshot objects.

    Parameters
    ----------
    max_versions_per_portfolio : int
        Maximum snapshot versions to retain per portfolio.
        Oldest versions are dropped first when the deque is full.
    """

    def __init__(
        self, max_versions_per_portfolio: int = DEFAULT_MAX_HISTORY_PER_PF
    ) -> None:
        if max_versions_per_portfolio < 1:
            max_versions_per_portfolio = 1
        self._max_versions = max_versions_per_portfolio
        self._lock = threading.Lock()
        # portfolio_id → deque[PortfolioSnapshot]
        self._history: Dict[str, deque] = {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(self, snapshot: PortfolioSnapshot) -> None:
        """Record a snapshot version in the history for its portfolio."""
        pid = snapshot.portfolio_id
        with self._lock:
            if pid not in self._history:
                self._history[pid] = deque(maxlen=self._max_versions)
            self._history[pid].append(snapshot)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_versions(
        self, portfolio_id: str, limit: int = 0
    ) -> List[PortfolioSnapshot]:
        """
        Return snapshot versions for a portfolio in chronological order.

        Parameters
        ----------
        portfolio_id : str
        limit :        int — 0 means return all retained versions.
        """
        with self._lock:
            dq = self._history.get(portfolio_id)
            if dq is None:
                return []
            versions = list(dq)
        if limit > 0:
            return versions[-limit:]
        return versions

    def get_version(
        self, portfolio_id: str, snapshot_version: int
    ) -> Optional[PortfolioSnapshot]:
        """Return the specific version number for a portfolio, or None."""
        with self._lock:
            dq = self._history.get(portfolio_id)
            if dq is None:
                return None
            versions = list(dq)
        for snap in versions:
            if snap.snapshot_version == snapshot_version:
                return snap
        return None

    def latest(self, portfolio_id: str) -> Optional[PortfolioSnapshot]:
        """Return the most-recently recorded snapshot for a portfolio."""
        with self._lock:
            dq = self._history.get(portfolio_id)
            if not dq:
                return None
            return dq[-1]

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def version_count(self, portfolio_id: str) -> int:
        with self._lock:
            dq = self._history.get(portfolio_id)
            return len(dq) if dq else 0

    def portfolio_count(self) -> int:
        with self._lock:
            return len(self._history)

    def has_portfolio(self, portfolio_id: str) -> bool:
        with self._lock:
            return portfolio_id in self._history

    def clear(self) -> None:
        with self._lock:
            self._history.clear()

    def clear_portfolio(self, portfolio_id: str) -> bool:
        with self._lock:
            if portfolio_id in self._history:
                del self._history[portfolio_id]
                return True
            return False
