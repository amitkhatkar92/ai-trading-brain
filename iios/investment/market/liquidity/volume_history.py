"""iios/investment/market/liquidity/volume_history.py
Thread-safe ring buffer of VolumeBar objects.
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from typing import List, Optional

from iios.investment.market.liquidity.models import VolumeBar

logger = logging.getLogger(__name__)


class VolumeHistory:
    """Thread-safe ring buffer of VolumeBar objects."""

    def __init__(self, max_size: int = 500) -> None:
        self._max_size = max_size
        self._bars: deque[VolumeBar] = deque(maxlen=max_size)
        self._lock = threading.RLock()

    def record(self, vbar: VolumeBar) -> None:
        with self._lock:
            self._bars.append(vbar)

    def recent(self, n: int = 20) -> List[VolumeBar]:
        with self._lock:
            return list(self._bars)[-n:]

    def last(self) -> Optional[VolumeBar]:
        with self._lock:
            if not self._bars:
                return None
            return self._bars[-1]

    def count(self) -> int:
        with self._lock:
            return len(self._bars)

    def up_volume_last_n(self, n: int) -> float:
        with self._lock:
            bars = list(self._bars)[-n:]
            return sum(b.volume for b in bars if b.is_up)

    def down_volume_last_n(self, n: int) -> float:
        with self._lock:
            bars = list(self._bars)[-n:]
            return sum(b.volume for b in bars if not b.is_up)
