"""iios/investment/company/earnings/earnings_history.py
Thread-safe per-company ring buffer of EarningsReport objects.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport

_DEFAULT_MAX = 24   # 24 annual periods or quarterly mix


@dataclass
class CompanyEarningsStore:
    ticker: str
    reports: Deque[EarningsReport] = field(default_factory=lambda: deque(maxlen=_DEFAULT_MAX))
    ttm_report: Optional[EarningsReport] = None   # latest TTM, stored separately


class EarningsHistory:
    """Stores and retrieves EarningsReport objects per company."""

    def __init__(self, max_periods: int = _DEFAULT_MAX) -> None:
        self._lock: threading.RLock = threading.RLock()
        self._store: Dict[str, CompanyEarningsStore] = {}
        self._max = max_periods

    def push(self, ticker: str, report: EarningsReport) -> None:
        with self._lock:
            store = self._get_or_create(ticker)
            if report.period_type == "ttm":
                store.ttm_report = report
                return
            # Replace if same period already present
            dq = store.reports
            for i, existing in enumerate(list(dq)):
                if existing.period_label == report.period_label:
                    dq[i] = report
                    return
            dq.append(report)

    def get_latest(self, ticker: str) -> Optional[EarningsReport]:
        with self._lock:
            store = self._store.get(ticker)
            if store is None:
                return None
            if store.ttm_report is not None:
                return store.ttm_report
            if store.reports:
                return store.reports[-1]
            return None

    def get_history(self, ticker: str, n: int = 10, exclude_ttm: bool = True) -> List[EarningsReport]:
        with self._lock:
            store = self._store.get(ticker)
            if store is None:
                return []
            return list(store.reports)[-n:]

    def get_ttm(self, ticker: str) -> Optional[EarningsReport]:
        with self._lock:
            store = self._store.get(ticker)
            return store.ttm_report if store else None

    def period_count(self, ticker: str) -> int:
        with self._lock:
            store = self._store.get(ticker)
            return len(store.reports) if store else 0

    def all_tickers(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def _get_or_create(self, ticker: str) -> CompanyEarningsStore:
        if ticker not in self._store:
            self._store[ticker] = CompanyEarningsStore(
                ticker=ticker,
                reports=deque(maxlen=self._max),
            )
        return self._store[ticker]

    def series(
        self,
        ticker: str,
        field_name: str,
        n: int = 10,
    ) -> List[Optional[float]]:
        """Return a time-ordered list of values for one field."""
        history = self.get_history(ticker, n)
        return [getattr(r, field_name, None) for r in history]
