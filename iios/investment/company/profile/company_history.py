"""iios/investment/company/profile/company_history.py
Thread-safe per-company ring buffer of CompanySnapshot objects.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any

from iios.investment.company.company_constants import DEFAULT_SNAPSHOT_HISTORY
from iios.investment.company.profile.company_snapshot import CompanySnapshot


class CompanyHistory:
    """
    Stores a bounded history of CompanySnapshot objects per company.
    Each company has its own ring buffer of depth ``max_per_company``.
    """

    def __init__(self, max_per_company: int = DEFAULT_SNAPSHOT_HISTORY) -> None:
        self._lock:           threading.RLock                        = threading.RLock()
        self._max_per_company: int                                   = max_per_company
        self._store:          dict[str, deque[CompanySnapshot]]      = {}

    def add(self, company_id: str, snapshot: CompanySnapshot) -> None:
        with self._lock:
            buf = self._store.setdefault(company_id, deque(maxlen=self._max_per_company))
            buf.append(snapshot)

    def get_latest(self, company_id: str) -> CompanySnapshot | None:
        with self._lock:
            buf = self._store.get(company_id)
            if not buf:
                return None
            return buf[-1]

    def get_recent(self, company_id: str, n: int = 10) -> list[CompanySnapshot]:
        with self._lock:
            buf = self._store.get(company_id)
            if not buf:
                return []
            items = list(buf)
            return items[-n:] if len(items) >= n else items

    def all_companies(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def count(self, company_id: str) -> int:
        with self._lock:
            return len(self._store.get(company_id, []))

    def total_snapshots(self) -> int:
        with self._lock:
            return sum(len(b) for b in self._store.values())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "companies":        len(self._store),
                "total_snapshots":  self.total_snapshots(),
                "max_per_company":  self._max_per_company,
            }
