"""iios/execution/monitoring/metrics/metrics_snapshot.py
==================================================
MetricsSnapshot — immutable point-in-time snapshot of all computed metrics.

This is the primary output of the Metrics Framework.
Downstream subsystems (M4 Alert Framework, analytics, dashboards)
consume this object exclusively.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION


@dataclass(frozen=True)
class MetricsSnapshot:
    """
    Immutable, versioned, self-describing snapshot of all current metrics.

    Fields
    ------
    snapshot_id:
        Globally unique ID for this snapshot.
    snapshot_version:
        Monotonic version per session_id.  Starts at 1.
    session_id:
        Session this snapshot belongs to.
    portfolio_id:
        Owning portfolio.
    strategy_id:
        Originating strategy, if available.
    gateway_id:
        Associated gateway, if available.
    metrics:
        Dict of metric_type.value → computed float value (session-wide).
    window_metrics:
        Dict of window_size.value → Dict[metric_type.value → float].
    point_counts:
        Dict of metric_type.value → number of raw data points used.
    created_at:
        Wall-time of snapshot creation.
    framework_version:
        Framework version string for compatibility checks.
    """

    snapshot_id:       str
    snapshot_version:  int
    session_id:        str
    portfolio_id:      str
    metrics:           Dict[str, float]
    window_metrics:    Dict[str, Dict[str, float]]
    point_counts:      Dict[str, int]
    created_at:        float
    framework_version: str

    # Optional correlation
    strategy_id: Optional[str] = None
    gateway_id:  Optional[str] = None

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def metric_count(self) -> int:
        return len(self.metrics)

    @property
    def total_points(self) -> int:
        return sum(self.point_counts.values())

    @property
    def has_window_metrics(self) -> bool:
        return bool(self.window_metrics)

    def get(self, metric_key: str, default: float = 0.0) -> float:
        return self.metrics.get(metric_key, default)

    def get_window(
        self, window: str, metric_key: str, default: float = 0.0
    ) -> float:
        return self.window_metrics.get(window, {}).get(metric_key, default)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "snapshot_version":  self.snapshot_version,
            "session_id":        self.session_id,
            "portfolio_id":      self.portfolio_id,
            "strategy_id":       self.strategy_id,
            "gateway_id":        self.gateway_id,
            "metrics":           dict(self.metrics),
            "window_metrics":    {k: dict(v) for k, v in self.window_metrics.items()},
            "point_counts":      dict(self.point_counts),
            "total_points":      self.total_points,
            "created_at":        self.created_at,
            "framework_version": self.framework_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    # ── Equality / ordering ───────────────────────────────────────────────────

    def is_newer_than(self, other: "MetricsSnapshot") -> bool:
        if self.session_id != other.session_id:
            return self.created_at > other.created_at
        return self.snapshot_version > other.snapshot_version


def make_metrics_snapshot(
    session_id:   str,
    portfolio_id: str,
    metrics:      Dict[str, float],
    *,
    snapshot_version: int = 1,
    window_metrics:   Optional[Dict[str, Dict[str, float]]] = None,
    point_counts:     Optional[Dict[str, int]]              = None,
    strategy_id:      Optional[str]                         = None,
    gateway_id:       Optional[str]                         = None,
) -> MetricsSnapshot:
    return MetricsSnapshot(
        snapshot_id=str(uuid.uuid4()),
        snapshot_version=snapshot_version,
        session_id=session_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        gateway_id=gateway_id,
        metrics=metrics,
        window_metrics=window_metrics or {},
        point_counts=point_counts or {},
        created_at=time.time(),
        framework_version=VERSION,
    )
