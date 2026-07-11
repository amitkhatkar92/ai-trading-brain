"""iios/investment/market/breadth/metric_registry.py
Thread-safe registry of BreadthMetric instances.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.market.breadth.breadth_metric import BreadthMetric


class MetricRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metrics: Dict[str, BreadthMetric] = {}

    def register(self, metric: BreadthMetric) -> None:
        with self._lock:
            self._metrics[metric.name] = metric

    def unregister(self, name: str) -> None:
        with self._lock:
            self._metrics.pop(name, None)

    def get(self, name: str) -> Optional[BreadthMetric]:
        with self._lock:
            return self._metrics.get(name)

    def all(self) -> List[BreadthMetric]:
        with self._lock:
            return list(self._metrics.values())

    def names(self) -> List[str]:
        with self._lock:
            return list(self._metrics.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._metrics)
