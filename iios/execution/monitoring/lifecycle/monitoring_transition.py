"""iios/execution/monitoring/lifecycle/monitoring_transition.py
==================================================
MonitoringTransition — immutable record of a single state transition
for a monitoring session.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ACTOR_LIFECYCLE, MonitoringState


@dataclass(frozen=True)
class MonitoringTransition:
    """Immutable record of a single lifecycle state transition."""

    transition_id: str
    session_id:    str
    from_state:    MonitoringState
    to_state:      MonitoringState
    actor:         str
    occurred_at:   float
    reason:        str = ""
    metadata:      Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "session_id":    self.session_id,
            "from_state":    self.from_state.value,
            "to_state":      self.to_state.value,
            "actor":         self.actor,
            "occurred_at":   self.occurred_at,
            "reason":        self.reason,
        }


def make_monitoring_transition(
    session_id: str,
    from_state: MonitoringState,
    to_state:   MonitoringState,
    *,
    actor:    str = ACTOR_LIFECYCLE,
    reason:   str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> MonitoringTransition:
    return MonitoringTransition(
        transition_id=str(uuid.uuid4()),
        session_id=session_id,
        from_state=from_state,
        to_state=to_state,
        actor=actor,
        occurred_at=time.time(),
        reason=reason,
        metadata=metadata or {},
    )
