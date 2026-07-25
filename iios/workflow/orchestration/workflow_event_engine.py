"""
workflow_event_engine.py — iios.workflow.orchestration
-------------------------------------------------------
WorkflowEventEngine — manages event-driven step triggers.

Steps with StepType.EVENT or StepType.WAIT block until an external
event is signalled.  The engine stores pending events and allows
external code to fire them.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .exceptions import WorkflowTimeoutError

_log = get_logger(__name__)


class WorkflowEventEngine:
    """
    Event-driven step trigger engine.

    External code signals events by name; waiting threads unblock.
    Thread-safe.
    """

    def __init__(self) -> None:
        self._events:  Dict[str, threading.Event] = {}
        self._payloads: Dict[str, Any]            = {}
        self._lock     = threading.Lock()

    # ── Publishing ─────────────────────────────────────────────────────────────

    def signal(self, event_name: str, payload: Any = None) -> None:
        """Signal an event, unblocking any step waiting for it."""
        with self._lock:
            ev = self._events.setdefault(event_name, threading.Event())
            self._payloads[event_name] = payload
            ev.set()
        _log.debug(f"EventEngine: signalled event={event_name!r}")

    def reset(self, event_name: str) -> None:
        """Clear an event so steps can wait for it again."""
        with self._lock:
            ev = self._events.get(event_name)
            if ev:
                ev.clear()
                self._payloads.pop(event_name, None)

    # ── Waiting ────────────────────────────────────────────────────────────────

    def wait_for(
        self,
        event_name:      str,
        timeout_seconds: float = 60.0,
    ) -> Any:
        """
        Block until event_name is signalled, or raise WorkflowTimeoutError.

        Returns:
            The payload provided when the event was signalled.
        """
        with self._lock:
            ev = self._events.setdefault(event_name, threading.Event())

        signalled = ev.wait(timeout=timeout_seconds)
        if not signalled:
            raise WorkflowTimeoutError(
                f"Timed out waiting for event {event_name!r} "
                f"after {timeout_seconds:.1f}s"
            )
        with self._lock:
            return self._payloads.get(event_name)

    def is_signalled(self, event_name: str) -> bool:
        with self._lock:
            ev = self._events.get(event_name)
            return ev.is_set() if ev else False

    # ── Introspection ─────────────────────────────────────────────────────────

    def pending_events(self) -> Dict[str, bool]:
        with self._lock:
            return {name: ev.is_set() for name, ev in self._events.items()}

    def clear_all(self) -> None:
        with self._lock:
            self._events.clear()
            self._payloads.clear()
