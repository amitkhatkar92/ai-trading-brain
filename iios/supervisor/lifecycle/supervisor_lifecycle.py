"""
supervisor_lifecycle.py — iios.supervisor.lifecycle
----------------------------------------------------
Primary public interface of the AI Supervisor Lifecycle subsystem.

:class:`SupervisorLifecycle` is the ONLY interface external callers use to
manage supervisor session lifecycle.

Responsibilities
----------------
* Session creation
* State-transition orchestration (initialize → discover → validate → ready →
  supervise → monitor → pause → resume → complete → fail → archive)
* Event dispatch to registered listeners
* History and statistics accumulation
* Structural integrity validation

Non-Responsibilities (intentional exclusions)
---------------------------------------------
* AI reasoning
* Governance policy evaluation
* Decision making
* Optimization
* Execution routing

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.errors.exceptions import IIOSError
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_LIFECYCLE,
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_TRANSITIONS,
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    SupervisorPriority,
    SupervisorScope,
    SupervisorState,
    SupervisorType,
)
from .exceptions import (
    SupervisorLifecycleError,
    SupervisorLifecycleNotRunningError,
    SupervisorSessionNotFoundError,
    SupervisorValidationError,
)
from .supervisor_events import (
    SupervisorEvent,
    make_supervisor_archived,
    make_supervisor_completed,
    make_supervisor_created,
    make_supervisor_failed,
    make_supervisor_initialized,
    make_supervisor_monitoring_started,
    make_supervisor_paused,
    make_supervisor_resumed,
    make_supervisor_started,
    make_supervisor_validated,
)
from .supervisor_factory import SupervisorFactory
from .supervisor_history import SupervisorHistory
from .supervisor_registry import SupervisorRegistry
from .supervisor_session import SupervisorSession
from .supervisor_statistics import SupervisorStatistics
from .supervisor_validation import SupervisorValidationResult, SupervisorValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class SupervisorLifecycle(LifecycleAwareMixin):
    """
    Institutional AI supervisor lifecycle engine.

    This is the ONLY public interface external callers should use.

    Parameters
    ----------
    max_active_sessions :   Maximum concurrent in-flight sessions.
    max_archived_sessions : Maximum archived sessions kept in memory.
    max_history :           Maximum lifecycle events retained.
    max_transitions :       Maximum transition records retained.

    Examples
    --------
    ::

        lc = SupervisorLifecycle()
        lc.start()
        session = lc.create("sup-001")
        lc.initialize(session.session_id)
        lc.discover(session.session_id)
        lc.validate_session(session.session_id)
        lc.mark_ready(session.session_id)
        lc.start_supervising(session.session_id)
        lc.start_monitoring(session.session_id)
        lc.complete(session.session_id)
        lc.archive(session.session_id)
        lc.stop()
    """

    def __init__(
        self,
        max_active_sessions:   int = DEFAULT_MAX_SESSIONS,
        max_archived_sessions: int = DEFAULT_MAX_ARCHIVED,
        max_history:           int = DEFAULT_MAX_HISTORY,
        max_transitions:       int = DEFAULT_MAX_TRANSITIONS,
    ) -> None:
        super().__init__()
        self._factory   = SupervisorFactory()
        self._registry  = SupervisorRegistry(
            max_active_sessions   = max_active_sessions,
            max_archived_sessions = max_archived_sessions,
        )
        self._history   = SupervisorHistory(
            max_events      = max_history,
            max_transitions = max_transitions,
        )
        self._stats      = SupervisorStatistics()
        self._validator  = SupervisorValidator()
        self._listeners: List[Callable[[SupervisorEvent], None]] = []
        self._listener_lock = threading.Lock()

    # ==================================================================
    # LifecycleAwareMixin hooks
    # ==================================================================

    def _on_start(self) -> None:
        _log.info(
            f"SupervisorLifecycle starting — {LIFECYCLE_SYSTEM_ID}",
        )
        _audit.log_lifecycle_event(
            engine_id  = LIFECYCLE_SYSTEM_ID,
            from_state = "STOPPED",
            to_state   = "RUNNING",
            version    = VERSION,
            actor      = ACTOR_LIFECYCLE,
        )

    def _on_stop(self) -> None:
        _log.info(
            f"SupervisorLifecycle stopping — {LIFECYCLE_SYSTEM_ID}",
        )
        _audit.log_lifecycle_event(
            engine_id  = LIFECYCLE_SYSTEM_ID,
            from_state = "RUNNING",
            to_state   = "STOPPED",
            version    = VERSION,
            actor      = ACTOR_LIFECYCLE,
        )

    # ==================================================================
    # Guard
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise SupervisorLifecycleNotRunningError()

    # ==================================================================
    # Session creation
    # ==================================================================

    def create(
        self,
        supervisor_id: str,
        *,
        session_id:          Optional[str]            = None,
        workflow_id:         str                       = "",
        supervisor_scope:    SupervisorScope           = SupervisorScope.SYSTEM,
        supervisor_type:     SupervisorType            = SupervisorType.CUSTOM,
        supervisor_priority: SupervisorPriority        = SupervisorPriority.MEDIUM,
        supervisor_version:  int                       = 1,
        metadata:            Optional[Dict[str, Any]]  = None,
        actor:               str                       = ACTOR_LIFECYCLE,
    ) -> SupervisorSession:
        """
        Create a new supervisor session in CREATED state.

        Parameters
        ----------
        supervisor_id :       Supervised entity identifier.
        session_id :          Optional explicit session ID.
        workflow_id :         Workflow routing context.
        supervisor_scope :    Institutional scope.
        supervisor_type :     Classification of the supervisor.
        supervisor_priority : Priority level.
        supervisor_version :  Initial version counter.
        metadata :            Supplementary metadata.
        actor :               Requesting actor identifier.

        Returns
        -------
        SupervisorSession
        """
        self._assert_running()
        session = self._factory.create(
            supervisor_id,
            session_id          = session_id,
            workflow_id         = workflow_id,
            supervisor_scope    = supervisor_scope,
            supervisor_type     = supervisor_type,
            supervisor_priority = supervisor_priority,
            supervisor_version  = supervisor_version,
            metadata            = metadata,
        )
        self._registry.add(session)
        self._stats.record_session_created()
        event = make_supervisor_created(
            session.session_id,
            session.supervisor_id,
            session.workflow_id,
            payload={"actor": actor},
        )
        self._history.record_event(event)
        self._dispatch(event)
        _log.debug(
            f"Supervisor session created: {session.session_id} \u2192 "
            f"{supervisor_id}/{workflow_id or 'n/a'}"
        )
        return session

    # ==================================================================
    # State-transition methods
    # ==================================================================

    def initialize(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorSession:
        """Transition a CREATED session to INITIALIZING."""
        return self._transition(
            session_id, SupervisorState.INITIALIZING,
            actor=actor, reason=reason,
            event_fn=make_supervisor_initialized,
        )

    def discover(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorSession:
        """Transition an INITIALIZING (or VALIDATING) session to DISCOVERING."""
        return self._transition(
            session_id, SupervisorState.DISCOVERING,
            actor=actor, reason=reason,
            event_fn=None,
        )

    def validate_session(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorSession:
        """Transition a DISCOVERING session to VALIDATING."""
        return self._transition(
            session_id, SupervisorState.VALIDATING,
            actor=actor, reason=reason,
            event_fn=make_supervisor_validated,
        )

    def mark_ready(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorSession:
        """Transition a VALIDATING session to READY."""
        return self._transition(
            session_id, SupervisorState.READY,
            actor=actor, reason=reason,
            event_fn=None,
        )

    def start_supervising(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorSession:
        """Transition a READY, MONITORING, or RESUMING session to SUPERVISING."""
        return self._transition(
            session_id, SupervisorState.SUPERVISING,
            actor=actor, reason=reason,
            event_fn=make_supervisor_started,
        )

    def start_monitoring(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorSession:
        """Transition a SUPERVISING or RESUMING session to MONITORING."""
        return self._transition(
            session_id, SupervisorState.MONITORING,
            actor=actor, reason=reason,
            event_fn=make_supervisor_monitoring_started,
        )

    def pause(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorSession:
        """Transition an active session (READY/SUPERVISING/MONITORING) to PAUSED."""
        return self._transition(
            session_id, SupervisorState.PAUSED,
            actor=actor, reason=reason,
            event_fn=make_supervisor_paused,
        )

    def resume(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorSession:
        """Transition a PAUSED session to RESUMING."""
        return self._transition(
            session_id, SupervisorState.RESUMING,
            actor=actor, reason=reason,
            event_fn=make_supervisor_resumed,
        )

    def complete(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorSession:
        """Transition a SUPERVISING or MONITORING session to COMPLETED."""
        return self._transition(
            session_id, SupervisorState.COMPLETED,
            actor=actor, reason=reason,
            event_fn=make_supervisor_completed,
        )

    def fail(
        self,
        session_id: str,
        *,
        reason: str = "",
        actor:  str = ACTOR_LIFECYCLE,
    ) -> SupervisorSession:
        """Transition to FAILED and record the failure reason."""
        session = self._registry.get_active(session_id)
        session.mark_failed(reason=reason, actor=actor)
        self._stats.record_session_failed()
        self._stats.record_transition()
        transition = session.transitions[-1]
        self._history.record_transition(transition)
        event = make_supervisor_failed(
            session.session_id,
            session.supervisor_id,
            session.workflow_id,
            payload={"actor": actor, "reason": reason},
        )
        self._history.record_event(event)
        self._dispatch(event)
        _log.debug(f"Supervisor session failed: {session_id} \u2014 {reason}")
        return session

    def archive(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorSession:
        """Transition a COMPLETED or FAILED session to ARCHIVED."""
        session = self._registry.get_active(session_id)
        session.transition_to(SupervisorState.ARCHIVED, actor=actor, reason=reason)
        self._registry.archive(session_id)
        self._stats.record_session_archived()
        self._stats.record_transition()
        transition = session.transitions[-1]
        self._history.record_transition(transition)
        event = make_supervisor_archived(
            session.session_id,
            session.supervisor_id,
            session.workflow_id,
            payload={"actor": actor},
        )
        self._history.record_event(event)
        self._dispatch(event)
        _log.debug(f"Supervisor session archived: {session_id}")
        return session

    # ==================================================================
    # Query
    # ==================================================================

    def get_session(self, session_id: str) -> SupervisorSession:
        """Return a session by ID (active or archived)."""
        return self._registry.get(session_id)

    def find_session(self, session_id: str) -> Optional[SupervisorSession]:
        """Return a session by ID or None."""
        return self._registry.find(session_id)

    def active_sessions(self) -> List[SupervisorSession]:
        """Return all active sessions."""
        return self._registry.active_sessions()

    def sessions_by_state(self, state: SupervisorState) -> List[SupervisorSession]:
        """Return active sessions in the given state."""
        return self._registry.sessions_by_state(state)

    def sessions_by_type(self, supervisor_type: SupervisorType) -> List[SupervisorSession]:
        """Return active sessions of the given supervisor type."""
        return self._registry.sessions_by_type(supervisor_type)

    def sessions_by_scope(self, supervisor_scope: SupervisorScope) -> List[SupervisorSession]:
        """Return active sessions with the given scope."""
        return self._registry.sessions_by_scope(supervisor_scope)

    def sessions_by_workflow(self, workflow_id: str) -> List[SupervisorSession]:
        """Return active sessions for the given workflow_id."""
        return self._registry.sessions_by_workflow(workflow_id)

    # ==================================================================
    # Validation
    # ==================================================================

    def validate(self, session_id: str) -> SupervisorValidationResult:
        """Validate structural integrity of a session."""
        session = self._registry.get(session_id)
        return self._validator.validate(session)

    # ==================================================================
    # Statistics / History
    # ==================================================================

    def statistics(self) -> Dict[str, Any]:
        """Return a snapshot of lifecycle statistics."""
        return self._stats.snapshot()

    def events(self) -> List[SupervisorEvent]:
        """Return all retained lifecycle events."""
        return self._history.events()   # type: ignore[return-value]

    def recent_events(self, n: int = 20) -> List[SupervisorEvent]:
        """Return the *n* most recent lifecycle events."""
        all_events = self._history.events()
        return all_events[-n:] if n < len(all_events) else all_events

    def transitions(self) -> List:
        """Return all retained transition records."""
        return self._history.transitions()

    # ==================================================================
    # Listeners
    # ==================================================================

    def add_listener(self, fn: Callable[[SupervisorEvent], None]) -> None:
        """Register a callable to receive lifecycle events."""
        with self._listener_lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[SupervisorEvent], None]) -> None:
        """De-register a listener."""
        with self._listener_lock:
            self._listeners = [l for l in self._listeners if l != fn]

    def _dispatch(self, event: SupervisorEvent) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception as exc:
                _log.warning(f"SupervisorLifecycle listener error: {exc}")

    # ==================================================================
    # Internal transition helper
    # ==================================================================

    def _transition(
        self,
        session_id: str,
        to_state:   SupervisorState,
        *,
        actor:    str,
        reason:   str,
        event_fn: Optional[Callable],
    ) -> SupervisorSession:
        session    = self._registry.get_active(session_id)
        transition = session.transition_to(to_state, actor=actor, reason=reason)
        self._stats.record_transition()
        self._history.record_transition(transition)

        if event_fn is not None:
            event = event_fn(
                session.session_id,
                session.supervisor_id,
                session.workflow_id,
                payload={"actor": actor, "reason": reason},
            )
            self._history.record_event(event)
            self._dispatch(event)

        # Record terminal statistics
        if to_state == SupervisorState.COMPLETED:
            duration = session.duration_s or 0.0
            self._stats.record_session_completed(duration_s=duration)

        _log.debug(f"Supervisor session {session_id}: \u2192 {to_state.value}")
        return session
