"""iios/integration/core/data_event.py

Integration events emitted to the internal event bus.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.integration_constants import IntegrationEventType


@dataclass
class IntegrationEvent:
    """An event emitted by the integration layer."""

    event_type:  IntegrationEventType = IntegrationEventType.ENGINE_STARTED
    provider_id: str                  = ""
    pipeline_id: str                  = ""
    payload:     dict[str, Any]       = field(default_factory=dict)
    source:      str                  = "integration"
    event_id:    str                  = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:   float                = field(default_factory=time.time)
    metadata:    dict[str, Any]       = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "provider_id": self.provider_id,
            "pipeline_id": self.pipeline_id,
            "payload":     self.payload,
            "source":      self.source,
            "timestamp":   self.timestamp,
            "metadata":    self.metadata,
        }
