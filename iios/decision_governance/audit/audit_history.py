"""iios/decision_governance/audit/audit_history.py

Thread-safe in-memory audit event history with per-decision indexing.
"""
from __future__ import annotations

import threading

from iios.decision_governance.governance_constants import MAX_AUDIT_EVENTS
from iios.decision_governance.governance_exceptions import (
    AuditAlreadyExistsError,
    AuditNotFoundError,
    AuditReplayError,
)
from iios.decision_governance.audit.audit_event import AuditEvent


class AuditHistory:
    """
    Stores AuditEvents and provides retrieval + replay + comparison.

    All operations are thread-safe via an internal RLock.
    """

    def __init__(self, max_events: int = MAX_AUDIT_EVENTS) -> None:
        self._lock:          threading.RLock               = threading.RLock()
        self._events:        dict[str, AuditEvent]         = {}  # event_id → AuditEvent
        self._by_decision:   dict[str, list[str]]          = {}  # decision_id → [event_id]
        self._max:           int                           = max_events

    # ── write ─────────────────────────────────────────────────────────────────

    def record(self, event: AuditEvent) -> None:
        with self._lock:
            if event.event_id in self._events:
                raise AuditAlreadyExistsError(event.event_id)
            if len(self._events) >= self._max:
                # evict oldest event (FIFO)
                oldest_id = next(iter(self._events))
                old_event = self._events.pop(oldest_id)
                bucket = self._by_decision.get(old_event.decision_id, [])
                if oldest_id in bucket:
                    bucket.remove(oldest_id)

            self._events[event.event_id] = event
            self._by_decision.setdefault(event.decision_id, []).append(event.event_id)

    # ── read ──────────────────────────────────────────────────────────────────

    def get(self, event_id: str) -> AuditEvent:
        with self._lock:
            ev = self._events.get(event_id)
        if ev is None:
            raise AuditNotFoundError(event_id)
        return ev

    def by_decision(self, decision_id: str) -> list[AuditEvent]:
        with self._lock:
            ids = list(self._by_decision.get(decision_id, []))
            return [self._events[eid] for eid in ids if eid in self._events]

    def all_events(self) -> list[AuditEvent]:
        with self._lock:
            return list(self._events.values())

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    # ── replay ────────────────────────────────────────────────────────────────

    def replay(self, decision_id: str) -> list[AuditEvent]:
        """Return all events for a decision in chronological order."""
        events = self.by_decision(decision_id)
        if not events:
            raise AuditReplayError(decision_id)
        return sorted(events, key=lambda e: e.timestamp)

    # ── compare ───────────────────────────────────────────────────────────────

    def compare(
        self, decision_id_a: str, decision_id_b: str
    ) -> dict:
        """Compare audit trails of two decisions. Returns diff summary."""
        events_a = sorted(self.by_decision(decision_id_a), key=lambda e: e.timestamp)
        events_b = sorted(self.by_decision(decision_id_b), key=lambda e: e.timestamp)

        types_a = [e.event_type.value for e in events_a]
        types_b = [e.event_type.value for e in events_b]
        shared  = set(types_a) & set(types_b)

        return {
            "decision_id_a":   decision_id_a,
            "decision_id_b":   decision_id_b,
            "event_count_a":   len(events_a),
            "event_count_b":   len(events_b),
            "event_types_a":   types_a,
            "event_types_b":   types_b,
            "shared_types":    sorted(shared),
            "unique_to_a":     sorted(set(types_a) - set(types_b)),
            "unique_to_b":     sorted(set(types_b) - set(types_a)),
        }
