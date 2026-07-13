"""iios/investment/company/integration/conflict_history.py
Thread-safe ring buffer of ConflictRecord objects per ticker.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.investment.company.integration.conflict_detector import ConflictRecord
from iios.investment.company.integration.company_state import ConflictSeverity, ConflictStatus


_DEFAULT_MAXLEN = 100   # per ticker


class ConflictHistory:
    """Maintains an audit trail of all detected conflicts per ticker."""

    def __init__(self, maxlen: int = _DEFAULT_MAXLEN) -> None:
        self._lock   = threading.RLock()
        self._maxlen = maxlen
        self._store: Dict[str, deque] = {}   # ticker → deque[ConflictRecord]

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record_all(self, ticker: str, conflicts: List[ConflictRecord]) -> None:
        """Append all *conflicts* to the ticker's history."""
        if not conflicts:
            return
        with self._lock:
            if ticker not in self._store:
                self._store[ticker] = deque(maxlen=self._maxlen)
            for c in conflicts:
                self._store[ticker].append(c)

    def record(self, conflict: ConflictRecord) -> None:
        with self._lock:
            ticker = conflict.ticker
            if ticker not in self._store:
                self._store[ticker] = deque(maxlen=self._maxlen)
            self._store[ticker].append(conflict)

    # ── Read access ───────────────────────────────────────────────────────────

    def get_history(
        self,
        ticker: str,
        n: int = 20,
        severity: Optional[ConflictSeverity] = None,
    ) -> List[ConflictRecord]:
        """Return up to *n* most-recent conflicts, optionally filtered by severity."""
        with self._lock:
            buf = self._store.get(ticker, deque())
            records = list(buf)
            if severity is not None:
                records = [r for r in records if r.severity == severity]
            return records[-n:][::-1]

    def unresolved(self, ticker: str) -> List[ConflictRecord]:
        with self._lock:
            buf = self._store.get(ticker, deque())
            return [c for c in buf if c.status == ConflictStatus.DETECTED]

    def critical_unresolved(self, ticker: str) -> List[ConflictRecord]:
        with self._lock:
            buf = self._store.get(ticker, deque())
            return [
                c for c in buf
                if c.severity == ConflictSeverity.CRITICAL
                and c.status in (ConflictStatus.DETECTED, ConflictStatus.ESCALATED)
            ]

    def count_total(self, ticker: str) -> int:
        with self._lock:
            return len(self._store.get(ticker, deque()))

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
