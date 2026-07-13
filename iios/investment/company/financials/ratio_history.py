"""iios/investment/company/financials/ratio_history.py
Historical ratio store — keeps N periods of computed ratios per company.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

_DEFAULT_MAX_PERIODS = 40   # ~10 years annual or ~40 quarters


@dataclass
class RatioPeriodSnapshot:
    """All computed ratios for one period."""
    period_label: str
    end_date:     str
    ratios:       Dict[str, Optional[float]]
    period_type:  str = "annual"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_label": self.period_label,
            "end_date":     self.end_date,
            "period_type":  self.period_type,
            "ratios":       self.ratios,
        }


class RatioHistory:
    """Thread-safe history of ratio snapshots per company.

    Supports:
    - get_latest()      → most recent snapshot
    - get_history(n)    → last n snapshots
    - get_ratio_series(name) → time-series of one ratio
    - push()            → add a new period snapshot
    """

    def __init__(self, max_periods: int = _DEFAULT_MAX_PERIODS) -> None:
        self._lock: threading.RLock = threading.RLock()
        self._store: Dict[str, Deque[RatioPeriodSnapshot]] = {}
        self._max   = max_periods

    def push(
        self,
        ticker:  str,
        snapshot: RatioPeriodSnapshot,
    ) -> None:
        with self._lock:
            if ticker not in self._store:
                self._store[ticker] = deque(maxlen=self._max)
            # Avoid duplicate periods
            dq = self._store[ticker]
            if dq and dq[-1].period_label == snapshot.period_label:
                dq[-1] = snapshot   # overwrite same period
            else:
                dq.append(snapshot)

    def get_latest(self, ticker: str) -> Optional[RatioPeriodSnapshot]:
        with self._lock:
            dq = self._store.get(ticker)
            if not dq:
                return None
            return dq[-1]

    def get_history(self, ticker: str, n: int = 8) -> List[RatioPeriodSnapshot]:
        with self._lock:
            dq = self._store.get(ticker, deque())
            return list(dq)[-n:]

    def get_ratio_series(
        self,
        ticker: str,
        ratio_name: str,
        n: int = 8,
    ) -> List[Tuple[str, Optional[float]]]:
        """Return [(period_label, value), ...] for the last n periods."""
        history = self.get_history(ticker, n)
        return [(s.period_label, s.ratios.get(ratio_name)) for s in history]

    def all_tickers(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def period_count(self, ticker: str) -> int:
        with self._lock:
            return len(self._store.get(ticker, []))
