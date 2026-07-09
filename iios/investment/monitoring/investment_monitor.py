"""iios/investment/monitoring/investment_monitor.py
Lightweight background sampler for investment engine metrics.
"""
from __future__ import annotations

import threading
import time
from typing import Callable

MetricSampler = Callable[[], dict]


class InvestmentMonitor:
    """Periodically samples a metric callable and stores snapshots."""

    def __init__(
        self,
        sampler:          MetricSampler,
        interval_seconds: float = 30.0,
        max_snapshots:    int   = 100,
    ) -> None:
        self._sampler   = sampler
        self._interval  = interval_seconds
        self._max       = max_snapshots
        self._snapshots: list[dict]        = []
        self._lock:      threading.RLock   = threading.RLock()
        self._thread:    threading.Thread | None = None
        self._stop:      threading.Event   = threading.Event()
        self._running:   bool              = False

    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._thread  = threading.Thread(
            target=self._run, daemon=True, name="InvestmentMonitor"
        )
        self._running = True
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 1)
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def sample_once(self) -> dict:
        snap = self._sampler()
        snap["sampled_at"] = time.time()
        with self._lock:
            self._snapshots.append(snap)
            if len(self._snapshots) > self._max:
                self._snapshots = self._snapshots[-self._max:]
        return snap

    def latest(self) -> dict:
        with self._lock:
            return dict(self._snapshots[-1]) if self._snapshots else {}

    def history(self, n: int = 10) -> list[dict]:
        with self._lock:
            return list(self._snapshots[-n:])

    def _run(self) -> None:
        while not self._stop.wait(timeout=self._interval):
            try:
                self.sample_once()
            except Exception:  # noqa: BLE001
                pass
        self._running = False
