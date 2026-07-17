"""iios/execution/monitoring/metrics/metrics_events.py
==================================================
MetricsEvent — domain events emitted by the Metrics Framework.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ENGINE_SYSTEM_ID, VERSION, MetricsEventType


@dataclass(frozen=True)
class MetricsEvent:
    """Immutable domain event emitted during metrics lifecycle."""

    event_id:    str
    event_type:  MetricsEventType
    session_id:  str
    actor:       str
    occurred_at: float
    version:     str
    reason:      str           = ""
    metadata:    Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "session_id":  self.session_id,
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "reason":      self.reason,
        }


# ── Factory helper ────────────────────────────────────────────────────────────

def _make_event(
    event_type: MetricsEventType,
    session_id: str,
    *,
    actor:    str = ENGINE_SYSTEM_ID,
    reason:   str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> MetricsEvent:
    return MetricsEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        session_id=session_id,
        actor=actor,
        occurred_at=time.time(),
        version=VERSION,
        reason=reason,
        metadata=metadata or {},
    )


# ── Named factory functions ───────────────────────────────────────────────────

def make_metrics_collected(session_id: str, **kw) -> MetricsEvent:
    return _make_event(MetricsEventType.METRICS_COLLECTED, session_id, **kw)


def make_metrics_calculated(session_id: str, **kw) -> MetricsEvent:
    return _make_event(MetricsEventType.METRICS_CALCULATED, session_id, **kw)


def make_metrics_aggregated(session_id: str, **kw) -> MetricsEvent:
    return _make_event(MetricsEventType.METRICS_AGGREGATED, session_id, **kw)


def make_metrics_published(session_id: str, **kw) -> MetricsEvent:
    return _make_event(MetricsEventType.METRICS_PUBLISHED, session_id, **kw)


def make_calculation_failed(session_id: str, reason: str = "", **kw) -> MetricsEvent:
    return _make_event(
        MetricsEventType.CALCULATION_FAILED, session_id, reason=reason, **kw
    )


def make_aggregation_completed(session_id: str, **kw) -> MetricsEvent:
    return _make_event(MetricsEventType.AGGREGATION_COMPLETED, session_id, **kw)
