"""iios/integration/monitoring/availability_monitor.py"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any

from iios.integration.integration_constants import DEFAULT_MIN_AVAILABILITY_PCT


class AvailabilityMonitor:
    """
    Tracks availability (success rate) per provider using a rolling window.
    Thread-safe.
    """

    def __init__(
        self,
        min_availability: float = DEFAULT_MIN_AVAILABILITY_PCT,
        window:           int   = 100,
    ) -> None:
        self._min_availability = min_availability
        self._window           = window
        self._data:  dict[str, deque[bool]] = {}
        self._lock   = threading.RLock()

    def record(self, provider_id: str, success: bool) -> None:
        with self._lock:
            if provider_id not in self._data:
                self._data[provider_id] = deque(maxlen=self._window)
            self._data[provider_id].append(success)

    def availability(self, provider_id: str) -> float:
        with self._lock:
            vals = list(self._data.get(provider_id, []))
        if not vals:
            return 1.0
        return sum(1 for v in vals if v) / len(vals)

    def is_below_threshold(self, provider_id: str) -> bool:
        return self.availability(provider_id) < self._min_availability

    def all_provider_ids(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    def statistics(self) -> dict[str, Any]:
        result = {}
        for pid in self.all_provider_ids():
            avail = self.availability(pid)
            result[pid] = {
                "availability_pct": round(avail, 4),
                "below_threshold":  avail < self._min_availability,
            }
        return result
