"""iios/execution/monitoring/metrics/metrics_response.py
==================================================
MetricsResponse — immutable result of a metrics computation.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION


@dataclass(frozen=True)
class MetricsResponse:
    """
    Immutable result from a MetricsRequest computation.

    Contains the computed metric values and any errors that occurred
    during partial computation.
    """

    response_id:           str
    request_id:            str
    session_id:            str
    metrics:               Dict[str, float]
    window_metrics:        Dict[str, Dict[str, float]]
    calculation_duration_ms: float
    calculated_at:         float
    errors:                Tuple[str, ...]  = ()
    framework_version:     str              = VERSION

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def metric_count(self) -> int:
        return len(self.metrics)

    @property
    def is_complete(self) -> bool:
        return not self.has_errors

    def get(self, metric_key: str, default: float = 0.0) -> float:
        return self.metrics.get(metric_key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":             self.response_id,
            "request_id":              self.request_id,
            "session_id":              self.session_id,
            "metrics":                 dict(self.metrics),
            "window_metrics":          {k: dict(v) for k, v in self.window_metrics.items()},
            "calculation_duration_ms": self.calculation_duration_ms,
            "calculated_at":           self.calculated_at,
            "errors":                  list(self.errors),
            "framework_version":       self.framework_version,
        }


def make_metrics_response(
    request_id:  str,
    session_id:  str,
    metrics:     Dict[str, float],
    *,
    window_metrics:          Optional[Dict[str, Dict[str, float]]] = None,
    calculation_duration_ms: float                                  = 0.0,
    errors:                  Optional[Tuple[str, ...]]              = None,
) -> MetricsResponse:
    return MetricsResponse(
        response_id=str(uuid.uuid4()),
        request_id=request_id,
        session_id=session_id,
        metrics=metrics,
        window_metrics=window_metrics or {},
        calculation_duration_ms=calculation_duration_ms,
        calculated_at=time.time(),
        errors=errors or (),
    )
