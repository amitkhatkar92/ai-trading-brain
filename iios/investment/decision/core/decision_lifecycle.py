"""iios/investment/decision/core/decision_lifecycle.py
DecisionLifecycle — records phase timestamps and validates state machine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.core.decision_constants import (
    VALID_TRANSITIONS,
    DecisionStatus,
)
from iios.investment.decision.core.decision_state import (
    DecisionState,
    InvalidTransitionError,
)


@dataclass
class PhaseRecord:
    """One recorded phase transition with duration."""
    from_status: DecisionStatus
    to_status:   DecisionStatus
    occurred_at: datetime
    duration_ms: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_status": self.from_status.value,
            "to_status":   self.to_status.value,
            "occurred_at": self.occurred_at.isoformat(),
            "duration_ms": round(self.duration_ms, 2) if self.duration_ms else None,
        }


class DecisionLifecycle:
    """
    Records and validates all phase transitions for one decision.
    Thread-safe: can be shared between async tasks.
    """

    def __init__(self, decision_id: str) -> None:
        import threading
        self._lock        = threading.RLock()
        self.decision_id  = decision_id
        self._phases:     List[PhaseRecord] = []
        self._last_ts:    datetime          = datetime.now(timezone.utc)

    def record_transition(
        self,
        from_status: DecisionStatus,
        to_status:   DecisionStatus,
    ) -> PhaseRecord:
        """Validate and record a state transition. Raises InvalidTransitionError."""
        allowed = VALID_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise InvalidTransitionError(
                f"Lifecycle violation: {from_status.value!r} → {to_status.value!r} "
                f"is not a valid transition."
            )
        now      = datetime.now(timezone.utc)
        duration = (now - self._last_ts).total_seconds() * 1000.0

        record = PhaseRecord(
            from_status=from_status,
            to_status=to_status,
            occurred_at=now,
            duration_ms=duration,
        )
        with self._lock:
            self._phases.append(record)
            self._last_ts = now

        return record

    def all_phases(self) -> List[PhaseRecord]:
        with self._lock:
            return list(self._phases)

    def total_duration_ms(self) -> Optional[float]:
        with self._lock:
            if not self._phases:
                return None
            return sum(
                p.duration_ms or 0.0 for p in self._phases
            )

    def is_valid_next(
        self,
        current: DecisionStatus,
        next_:   DecisionStatus,
    ) -> bool:
        return next_ in VALID_TRANSITIONS.get(current, set())

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "decision_id":       self.decision_id,
                "phase_count":       len(self._phases),
                "total_duration_ms": self.total_duration_ms(),
                "phases":            [p.to_dict() for p in self._phases],
            }
