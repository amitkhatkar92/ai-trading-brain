"""iios/investment/market/volatility/confidence_history.py
Thread-safe ring buffer of ConfidenceScore objects.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List

from iios.investment.market.volatility.models import ConfidenceScore


class ConfidenceHistory:
    """Fixed-capacity deque of ConfidenceScore, thread-safe."""

    def __init__(self, maxlen: int = 200) -> None:
        self._buf: deque[ConfidenceScore] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, score: ConfidenceScore) -> None:
        with self._lock:
            self._buf.append(score)

    def recent(self, n: int) -> List[ConfidenceScore]:
        with self._lock:
            return list(self._buf)[-n:]

    def latest(self) -> "ConfidenceScore | None":
        with self._lock:
            return self._buf[-1] if self._buf else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)
