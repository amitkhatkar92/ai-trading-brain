"""
workflow_history.py — iios.workflow.lifecycle
----------------------------------------------
Append-only, bounded history of workflow lifecycle transitions
and state records.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY, DEFAULT_MAX_TRANSITIONS
from .workflow_state import WorkflowStateRecord
from .workflow_transition import WorkflowTransition


class WorkflowHistory:
    """
    Thread-safe, bounded, append-only history of workflow lifecycle events.

    Maintains two separate bounded buffers:
      _transitions   — WorkflowTransition records
      _state_records — WorkflowStateRecord records

    Per-session indexes allow efficient session-scoped lookup.
    """

    def __init__(
        self,
        max_transitions: int = DEFAULT_MAX_TRANSITIONS,
        max_history:     int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._max_transitions = max_transitions
        self._max_history     = max_history

        self._transitions:   Deque[WorkflowTransition]  = deque(maxlen=max_transitions)
        self._state_records: Deque[WorkflowStateRecord] = deque(maxlen=max_history)

        self._by_session_transitions:   Dict[str, List[str]] = {}
        self._by_session_state_records: Dict[str, List[str]] = {}

        self._transition_idx:   Dict[str, WorkflowTransition]  = {}
        self._state_record_idx: Dict[str, WorkflowStateRecord] = {}

        self._lock = threading.Lock()

    # ----------------------------------------------------------------
    # Write (append-only)
    # ----------------------------------------------------------------

    def record_transition(self, transition: WorkflowTransition) -> None:
        with self._lock:
            if len(self._transitions) == self._max_transitions:
                oldest = self._transitions[0]
                self._transition_idx.pop(oldest.transition_id, None)
                sl = self._by_session_transitions.get(oldest.session_id, [])
                if oldest.transition_id in sl:
                    sl.remove(oldest.transition_id)
            self._transitions.append(transition)
            self._transition_idx[transition.transition_id] = transition
            self._by_session_transitions.setdefault(
                transition.session_id, []
            ).append(transition.transition_id)

    def record_state(self, state_record: WorkflowStateRecord) -> None:
        with self._lock:
            if len(self._state_records) == self._max_history:
                oldest = self._state_records[0]
                self._state_record_idx.pop(oldest.record_id, None)
                sl = self._by_session_state_records.get(oldest.session_id, [])
                if oldest.record_id in sl:
                    sl.remove(oldest.record_id)
            self._state_records.append(state_record)
            self._state_record_idx[state_record.record_id] = state_record
            self._by_session_state_records.setdefault(
                state_record.session_id, []
            ).append(state_record.record_id)

    # ----------------------------------------------------------------
    # Read
    # ----------------------------------------------------------------

    def get_transition(
        self, transition_id: str
    ) -> Optional[WorkflowTransition]:
        with self._lock:
            return self._transition_idx.get(transition_id)

    def transitions_for_session(
        self, session_id: str
    ) -> List[WorkflowTransition]:
        with self._lock:
            ids = list(self._by_session_transitions.get(session_id, []))
        return [t for tid in ids if (t := self._transition_idx.get(tid))]

    def state_records_for_session(
        self, session_id: str
    ) -> List[WorkflowStateRecord]:
        with self._lock:
            ids = list(self._by_session_state_records.get(session_id, []))
        return [r for rid in ids if (r := self._state_record_idx.get(rid))]

    def recent_transitions(self, n: int = 20) -> List[WorkflowTransition]:
        with self._lock:
            return list(self._transitions)[-n:]

    def recent_state_records(self, n: int = 20) -> List[WorkflowStateRecord]:
        with self._lock:
            return list(self._state_records)[-n:]

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def transition_count(self) -> int:
        with self._lock:
            return len(self._transitions)

    def state_record_count(self) -> int:
        with self._lock:
            return len(self._state_records)

    def clear(self) -> None:
        with self._lock:
            self._transitions.clear()
            self._state_records.clear()
            self._transition_idx.clear()
            self._state_record_idx.clear()
            self._by_session_transitions.clear()
            self._by_session_state_records.clear()
