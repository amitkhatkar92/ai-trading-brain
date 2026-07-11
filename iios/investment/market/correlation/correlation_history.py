"""iios/investment/market/correlation/correlation_history.py
Thread-safe ring buffer for CorrelationIntelligenceSnapshot objects.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional

from iios.investment.market.correlation.models import CorrelationIntelligenceSnapshot


class CorrelationHistory:
    def __init__(self, maxlen: int = 500) -> None:
        self._buf:  deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, snap: CorrelationIntelligenceSnapshot) -> None:
        with self._lock:
            self._buf.append(snap)

    def recent(self, n: int) -> List[CorrelationIntelligenceSnapshot]:
        with self._lock:
            return list(self._buf)[-n:]

    def latest(self) -> Optional[CorrelationIntelligenceSnapshot]:
        with self._lock:
            return self._buf[-1] if self._buf else None

    def all(self) -> List[CorrelationIntelligenceSnapshot]:
        with self._lock:
            return list(self._buf)

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)
