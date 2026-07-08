"""iios/decision_governance/monitoring/decision_monitor.py

DecisionMonitor: optional background thread for continuous metric sampling.
"""
from __future__ import annotations

import threading
import time
from typing import Callable


MetricSampler = Callable[[], dict]


class DecisionMonitor:
    """
    Lightweight background monitor that periodically invokes a sampler
    function and accumulates snapshots.

    By design this monitor is dependency-free — the sampler callable
    is injected at construction time.
    """

    def __init__(
        self,
        sampler:           MetricSampler,
        interval_seconds:  float = 30.0,
        max_snapshots:     int   = 100,
    ) -> None:
        self._sampler    = sampler
        self._interval   = interval_seconds
        self._max        = max_snapshots
        self._snapshots: list[dict]         = []
        self._lock:       threading.RLock   = threading.RLock()
        self._thread:     threading.Thread | None = None
        self._stop_event: threading.Event   = threading.Event()
        self._running:    bool              = False

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._stop_event.clear()
        self._thread  = threading.Thread(target=self._run, daemon=True, name="DecisionMonitor")
        self._running = True
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 1)
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # ── internal ──────────────────────────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop_event.wait(timeout=self._interval):
            try:
                snapshot = self._sampler()
                snapshot["sampled_at"] = time.time()
                with self._lock:
                    self._snapshots.append(snapshot)
                    if len(self._snapshots) > self._max:
                        self._snapshots = self._snapshots[-self._max:]
            except Exception:  # noqa: BLE001
                pass
        self._running = False

    # ── snapshots ─────────────────────────────────────────────────────────────

    def latest(self) -> dict:
        with self._lock:
            return dict(self._snapshots[-1]) if self._snapshots else {}

    def history(self, n: int = 10) -> list[dict]:
        with self._lock:
            return list(self._snapshots[-n:])

    def sample_once(self) -> dict:
        """Force a single sample without the background thread."""
        snapshot = self._sampler()
        snapshot["sampled_at"] = time.time()
        with self._lock:
            self._snapshots.append(snapshot)
        return snapshot
