"""iios/execution/monitoring/metrics/metrics_request.py
==================================================
MetricsRequest — immutable request for a metrics computation.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import MetricType, WindowSize


@dataclass(frozen=True)
class MetricsRequest:
    """
    Immutable request for a metrics computation.

    Specifies which metrics to compute, for which session,
    over which time window.
    """

    request_id:   str
    session_id:   str
    metric_types: Tuple[MetricType, ...]
    window_size:  WindowSize

    from_timestamp: Optional[float] = None
    to_timestamp:   Optional[float] = None
    requested_at:   float           = field(default_factory=time.time)
    metadata:       Dict[str, Any]  = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def has_time_range(self) -> bool:
        return self.from_timestamp is not None or self.to_timestamp is not None

    @property
    def metric_count(self) -> int:
        return len(self.metric_types)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "session_id":     self.session_id,
            "metric_types":   [m.value for m in self.metric_types],
            "window_size":    self.window_size.value,
            "from_timestamp": self.from_timestamp,
            "to_timestamp":   self.to_timestamp,
            "requested_at":   self.requested_at,
        }


def make_metrics_request(
    session_id:   str,
    metric_types: Tuple[MetricType, ...],
    *,
    window_size:    WindowSize     = WindowSize.FIVE_MINUTES,
    from_timestamp: Optional[float] = None,
    to_timestamp:   Optional[float] = None,
    metadata:       Optional[Dict[str, Any]] = None,
) -> MetricsRequest:
    return MetricsRequest(
        request_id=str(uuid.uuid4()),
        session_id=session_id,
        metric_types=metric_types,
        window_size=window_size,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        metadata=metadata or {},
    )
