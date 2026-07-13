"""iios/investment/company/opportunity/priority_monitor.py
Monitors priority changes and generates priority-level alerts.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from iios.investment.company.opportunity.opportunity_profile import (
    AlertSeverity, OpportunityAlert, OpportunityPriority,
)


class PriorityMonitor:
    """
    Tracks priority levels across all tickers and detects significant changes.
    Thread-safe for concurrent updates.
    """

    def __init__(self) -> None:
        self._lock     = threading.RLock()
        self._priority: Dict[str, OpportunityPriority] = {}
        self._history:  Dict[str, List[Tuple[OpportunityPriority, datetime]]] = {}

    def update(
        self,
        ticker:   str,
        priority: OpportunityPriority,
    ) -> Optional[OpportunityAlert]:
        """
        Record a new priority for *ticker*.
        Returns an alert if a material priority change is detected, else None.
        """
        with self._lock:
            prev = self._priority.get(ticker)
            self._priority[ticker] = priority
            if ticker not in self._history:
                self._history[ticker] = []
            self._history[ticker].append((priority, datetime.now(timezone.utc)))
            # Trim history
            if len(self._history[ticker]) > 50:
                self._history[ticker] = self._history[ticker][-50:]

            return self._check_priority_change(ticker, prev, priority)

    def get_priority(self, ticker: str) -> Optional[OpportunityPriority]:
        with self._lock:
            return self._priority.get(ticker)

    def get_tickers_by_priority(self, priority: OpportunityPriority) -> List[str]:
        with self._lock:
            return [t for t, p in self._priority.items() if p == priority]

    def critical_tickers(self) -> List[str]:
        return self.get_tickers_by_priority(OpportunityPriority.CRITICAL)

    def high_tickers(self) -> List[str]:
        return self.get_tickers_by_priority(OpportunityPriority.HIGH)

    def get_priority_history(
        self, ticker: str
    ) -> List[Tuple[OpportunityPriority, datetime]]:
        with self._lock:
            return list(self._history.get(ticker, []))[-10:]

    # ── Private ───────────────────────────────────────────────────────────────

    _PRIORITY_ORDER = {
        OpportunityPriority.WATCHLIST: 0,
        OpportunityPriority.LOW:       1,
        OpportunityPriority.MEDIUM:    2,
        OpportunityPriority.HIGH:      3,
        OpportunityPriority.CRITICAL:  4,
    }

    @classmethod
    def _check_priority_change(
        cls,
        ticker: str,
        prev:   Optional[OpportunityPriority],
        curr:   OpportunityPriority,
    ) -> Optional[OpportunityAlert]:
        if prev is None or prev == curr:
            return None
        prev_ord = cls._PRIORITY_ORDER.get(prev, 0)
        curr_ord = cls._PRIORITY_ORDER.get(curr, 0)
        delta    = curr_ord - prev_ord
        if delta >= 2:
            return OpportunityAlert(
                message=(
                    f"{ticker}: Priority elevated from {prev.value} → {curr.value} "
                    "— materially improved signal"
                ),
                severity=AlertSeverity.INFO,
                source="priority_monitor",
                generated_at=datetime.now(timezone.utc),
            )
        if delta <= -2:
            return OpportunityAlert(
                message=(
                    f"{ticker}: Priority downgraded from {prev.value} → {curr.value} "
                    "— signal weakening"
                ),
                severity=AlertSeverity.MEDIUM,
                source="priority_monitor",
                generated_at=datetime.now(timezone.utc),
            )
        return None
