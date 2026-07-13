"""iios/investment/company/valuation/assumption_manager.py
Store and retrieve historical assumption sets per ticker.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from iios.investment.company.valuation.valuation_assumptions import ValuationAssumptions


@dataclass
class AssumptionRecord:
    ticker:      str
    recorded_at: datetime
    assumptions: ValuationAssumptions
    source:      str = "default"  # "default" | "calibrated" | "override"


class AssumptionManager:
    """
    Thread-safe per-ticker assumption history.
    Stores the last N assumption sets used for each ticker.
    """

    def __init__(self, max_per_ticker: int = 10) -> None:
        self._lock  = threading.RLock()
        self._store: Dict[str, Deque[AssumptionRecord]] = {}
        self._max   = max_per_ticker

    def store(
        self,
        ticker:      str,
        assumptions: ValuationAssumptions,
        source:      str = "default",
    ) -> None:
        record = AssumptionRecord(
            ticker      = ticker,
            recorded_at = datetime.now(timezone.utc),
            assumptions = assumptions,
            source      = source,
        )
        with self._lock:
            q = self._store.setdefault(ticker, deque(maxlen=self._max))
            q.append(record)

    def get_latest(self, ticker: str) -> Optional[ValuationAssumptions]:
        with self._lock:
            q = self._store.get(ticker)
            if q:
                return q[-1].assumptions
            return None

    def get_history(self, ticker: str, n: int = 5) -> List[AssumptionRecord]:
        with self._lock:
            q = self._store.get(ticker)
            if not q:
                return []
            return list(q)[-n:]

    def was_calibrated(self, ticker: str) -> bool:
        """Returns True if at least one calibrated assumption set has been recorded."""
        with self._lock:
            q = self._store.get(ticker)
            if not q:
                return False
            return any(r.source == "calibrated" for r in q)

    def all_tickers(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
