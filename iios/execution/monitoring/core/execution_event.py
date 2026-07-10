"""iios/execution/monitoring/core/execution_event.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import ExecutionEventType


@dataclass
class ExecutionEvent:
    """
    Immutable system event published during the execution lifecycle.

    Events are the primary mechanism for propagating state changes
    across the monitoring engine without tight coupling.
    """

    event_type:   ExecutionEventType
    event_id:     str              = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str              = ""
    order_id:     str              = ""
    plan_id:      str              = ""
    broker_id:    str              = ""
    symbol:       str              = ""
    source:       str              = ""   # component that published the event
    payload:      dict[str, Any]   = field(default_factory=dict)
    timestamp:    float            = field(default_factory=time.time)
    metadata:     dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "execution_id": self.execution_id,
            "order_id":    self.order_id,
            "plan_id":     self.plan_id,
            "broker_id":   self.broker_id,
            "symbol":      self.symbol,
            "source":      self.source,
            "payload":     self.payload,
            "timestamp":   self.timestamp,
            "metadata":    self.metadata,
        }
