"""iios/investment/market/breadth/divergence_history.py
Thread-safe ring buffer of DivergenceSignal lists.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional

from iios.investment.market.breadth.models import DivergenceSignal


class DivergenceHistory:
    def __init__(self, maxlen: int = 200) -> None:
        self._buf: deque[List[DivergenceSignal]] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, signals: List[DivergenceSignal]) -> None:
        with self._lock:
            self._buf.append(list(signals))

    def recent(self, n: int) -> List[List[DivergenceSignal]]:
        with self._lock:
            return list(self._buf)[-n:]

    def latest(self) -> Optional[List[DivergenceSignal]]:
        with self._lock:
            return self._buf[-1] if self._buf else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)
