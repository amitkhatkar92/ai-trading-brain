"""iios/investment/market/liquidity/liquidity_history.py
Thread-safe ring buffer of LiquidityProfile objects.
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from typing import List, Optional

from iios.investment.market.liquidity.models import LiquidityProfile

logger = logging.getLogger(__name__)


class LiquidityHistory:
    """Thread-safe ring buffer of LiquidityProfile objects."""

    def __init__(self, max_size: int = 500) -> None:
        self._max_size = max_size
        self._profiles: deque[LiquidityProfile] = deque(maxlen=max_size)
        self._lock = threading.RLock()

    def record(self, profile: LiquidityProfile) -> None:
        with self._lock:
            self._profiles.append(profile)

    def recent(self, n: int = 20) -> List[LiquidityProfile]:
        with self._lock:
            return list(self._profiles)[-n:]

    def last(self) -> Optional[LiquidityProfile]:
        with self._lock:
            if not self._profiles:
                return None
            return self._profiles[-1]

    def count(self) -> int:
        with self._lock:
            return len(self._profiles)

    def avg_quality(self, n: int = 20) -> float:
        with self._lock:
            profiles = list(self._profiles)[-n:]
            if not profiles:
                return 0.0
            return sum(p.quality for p in profiles) / len(profiles)

    def avg_availability(self, n: int = 20) -> float:
        with self._lock:
            profiles = list(self._profiles)[-n:]
            if not profiles:
                return 0.0
            return sum(p.availability for p in profiles) / len(profiles)
