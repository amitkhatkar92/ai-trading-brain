"""iios/investment/market/breadth/breadth_history.py
Thread-safe ring buffer of BreadthIntelligenceSnapshot.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from iios.investment.market.breadth.models import BreadthIntelligenceSnapshot


class BreadthHistory:
    def __init__(self, maxlen: int = 500) -> None:
        self._buf: deque["BreadthIntelligenceSnapshot"] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, snap: "BreadthIntelligenceSnapshot") -> None:
        with self._lock:
            self._buf.append(snap)

    def recent(self, n: int) -> "List[BreadthIntelligenceSnapshot]":
        with self._lock:
            return list(self._buf)[-n:]

    def latest(self) -> "Optional[BreadthIntelligenceSnapshot]":
        with self._lock:
            return self._buf[-1] if self._buf else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)
