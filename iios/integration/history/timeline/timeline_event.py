"""iios/integration/history/timeline/timeline_event.py

One discrete event on the historical timeline.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_constants import HistoricalDataType


@dataclass
class TimelineEvent:
    """
    Immutable event placed on the timeline.

    The ``data`` dict carries the event payload; its schema is defined by
    the originating data source.
    """

    event_id:   str                = field(default_factory=lambda: str(uuid.uuid4()))
    timeline_id: str               = ""
    timestamp:  float              = 0.0        # simulated event time
    data_type:  HistoricalDataType = HistoricalDataType.CUSTOM
    subject:    str                = ""         # ticker, country, system, …
    source:     str                = ""         # which subsystem emitted this
    data:       dict[str, Any]     = field(default_factory=dict)
    priority:   int                = 0          # higher = processed first at same ts
    tags:       list[str]          = field(default_factory=list)
    created_at: float              = field(default_factory=time.time)
    metadata:   dict[str, Any]     = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":  self.event_id,
            "timeline_id": self.timeline_id,
            "timestamp": self.timestamp,
            "data_type": self.data_type.value,
            "subject":   self.subject,
            "source":    self.source,
            "priority":  self.priority,
        }
