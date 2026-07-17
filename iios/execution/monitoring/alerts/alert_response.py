"""iios/execution/monitoring/alerts/alert_response.py
==================================================
AlertResponse — immutable result of an alert evaluation cycle.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION


@dataclass(frozen=True)
class AlertResponse:
    """
    Immutable result of an alert evaluation request.

    Contains IDs of all alerts generated, suppressed, and any
    evaluation errors encountered.
    """

    response_id:            str
    request_id:             str
    session_id:             str
    alerts_generated:       Tuple[str, ...]  # alert_ids of new alerts
    alerts_suppressed:      Tuple[str, ...]  # alert_ids suppressed (duplicate)
    evaluation_duration_ms: float
    evaluated_at:           float
    errors:                 Tuple[str, ...]
    framework_version:      str

    @property
    def generated_count(self) -> int:
        return len(self.alerts_generated)

    @property
    def suppressed_count(self) -> int:
        return len(self.alerts_suppressed)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def has_alerts(self) -> bool:
        return bool(self.alerts_generated)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":            self.response_id,
            "request_id":             self.request_id,
            "session_id":             self.session_id,
            "alerts_generated":       list(self.alerts_generated),
            "alerts_suppressed":      list(self.alerts_suppressed),
            "evaluation_duration_ms": self.evaluation_duration_ms,
            "evaluated_at":           self.evaluated_at,
            "errors":                 list(self.errors),
            "framework_version":      self.framework_version,
        }


def make_alert_response(
    request_id:        str,
    session_id:        str,
    alerts_generated:  Tuple[str, ...],
    *,
    alerts_suppressed:      Tuple[str, ...]    = (),
    evaluation_duration_ms: float              = 0.0,
    errors:                 Tuple[str, ...]    = (),
    response_id:            Optional[str]      = None,
    evaluated_at:           Optional[float]    = None,
) -> AlertResponse:
    """Factory for AlertResponse."""
    return AlertResponse(
        response_id            = response_id or str(uuid.uuid4()),
        request_id             = request_id,
        session_id             = session_id,
        alerts_generated       = alerts_generated,
        alerts_suppressed      = alerts_suppressed,
        evaluation_duration_ms = evaluation_duration_ms,
        evaluated_at           = evaluated_at if evaluated_at is not None else time.time(),
        errors                 = errors,
        framework_version      = VERSION,
    )
