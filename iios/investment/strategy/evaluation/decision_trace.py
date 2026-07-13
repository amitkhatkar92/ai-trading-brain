"""iios/investment/strategy/evaluation/decision_trace.py
Decision trace: timestamped record of every evaluation decision made.
Provides full auditability — every score change is traceable.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TraceEntry:
    timestamp: datetime
    component: str        # which sub-engine produced this entry
    event:     str        # human-readable event description
    value:     Any        # the value/score at this moment
    context:   Dict[str, Any] = field(default_factory=dict)


class DecisionTrace:
    """Ordered, append-only log of evaluation decisions."""

    def __init__(self, strategy_id: str, evaluation_id: str) -> None:
        self.strategy_id = strategy_id
        self.evaluation_id = evaluation_id
        self._entries: List[TraceEntry] = []
        self._lock = threading.Lock()

    def record(
        self,
        component: str,
        event: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = TraceEntry(
            timestamp=datetime.now(timezone.utc),
            component=component,
            event=event,
            value=value,
            context=context or {},
        )
        with self._lock:
            self._entries.append(entry)

    def entries(self) -> List[TraceEntry]:
        with self._lock:
            return list(self._entries)

    def to_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "ts":        e.timestamp.isoformat(),
                "component": e.component,
                "event":     e.event,
                "value":     e.value,
                "context":   e.context,
            }
            for e in self.entries()
        ]
