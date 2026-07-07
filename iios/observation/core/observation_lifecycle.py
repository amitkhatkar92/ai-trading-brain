"""
iios/observation/core/observation_lifecycle.py
==============================================
Lifecycle utilities: allowed transitions, guards, and helpers.
"""

from __future__ import annotations

from typing import Optional

from ..observation_constants import ObservationStatus, LifecycleEvent
from ..observation_exceptions import ObservationLifecycleError
from ..models.observation import Observation, _TRANSITIONS

__all__ = [
    "can_transition",
    "assert_transition",
    "lifecycle_event_for",
    "terminal_statuses",
    "active_statuses",
]

# ── Set helpers ────────────────────────────────────────────────────────────────

def terminal_statuses() -> frozenset[ObservationStatus]:
    return frozenset({
        ObservationStatus.ACCEPTED,
        ObservationStatus.REJECTED,
        ObservationStatus.ARCHIVED,
        ObservationStatus.EXPIRED,
        ObservationStatus.DELETED,
    })


def active_statuses() -> frozenset[ObservationStatus]:
    return frozenset({
        ObservationStatus.CREATED,
        ObservationStatus.COLLECTED,
        ObservationStatus.VALIDATING,
        ObservationStatus.VALIDATED,
        ObservationStatus.CLASSIFYING,
        ObservationStatus.CLASSIFIED,
        ObservationStatus.ENRICHING,
        ObservationStatus.ENRICHED,
    })


# ── Transition helpers ────────────────────────────────────────────────────────

def can_transition(current: ObservationStatus, target: ObservationStatus) -> bool:
    return target in _TRANSITIONS.get(current, frozenset())


def assert_transition(
    current: ObservationStatus,
    target:  ObservationStatus,
    obs_id:  str = "",
) -> None:
    if not can_transition(current, target):
        raise ObservationLifecycleError(
            f"Illegal lifecycle transition {current.value!r} → {target.value!r}"
            + (f" for observation '{obs_id[:16]}'" if obs_id else ""),
            code="OBS-030",
        )


# ── LifecycleEvent mapping ────────────────────────────────────────────────────

_STATUS_EVENT: dict[ObservationStatus, LifecycleEvent] = {
    ObservationStatus.CREATED:   LifecycleEvent.CREATED,
    ObservationStatus.COLLECTED: LifecycleEvent.COLLECTED,
    ObservationStatus.VALIDATED: LifecycleEvent.VALIDATED,
    ObservationStatus.CLASSIFIED:LifecycleEvent.CLASSIFIED,
    ObservationStatus.ENRICHED:  LifecycleEvent.ENRICHED,
    ObservationStatus.ACCEPTED:  LifecycleEvent.ACCEPTED,
    ObservationStatus.REJECTED:  LifecycleEvent.REJECTED,
    ObservationStatus.ARCHIVED:  LifecycleEvent.ARCHIVED,
    ObservationStatus.EXPIRED:   LifecycleEvent.EXPIRED,
    ObservationStatus.DELETED:   LifecycleEvent.DELETED,
}


def lifecycle_event_for(status: ObservationStatus) -> Optional[LifecycleEvent]:
    return _STATUS_EVENT.get(status)
