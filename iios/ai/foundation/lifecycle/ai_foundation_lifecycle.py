"""
ai_foundation_lifecycle.py — iios.ai.foundation.lifecycle
==========================================================
:class:`AILifecycleAwareMixin` — the standard lifecycle mixin for ALL
AI Platform modules (A1–A10).

This is the AI Platform equivalent of the Core Platform's
``LifecycleAwareMixin`` (``iios.investment.workflow.engine_lifecycle``).
It is defined here in A1 so that A2–A10 can inherit it without importing
from the investment domain.

Usage example (A2–A10 pattern)::

    from iios.ai.foundation.lifecycle import AILifecycleAwareMixin
    from iios.ai.foundation.lifecycle.constants import AILifecycleState

    class MyAIEngine(AILifecycleAwareMixin):
        SYSTEM_ID = "iios:ai:my_module:engine"
        VERSION   = "1.0.0"

        def _on_initialize(self) -> None:
            # module-specific setup
            ...

        def _on_start(self) -> None:
            # module-specific startup
            ...

        def _on_stop(self) -> None:
            # module-specific shutdown
            ...

A1 AI Foundation — Phase 3, Module 1
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_LIFECYCLE,
    ACTOR_SYSTEM,
    DEFAULT_MAX_EVENTS,
    VERSION,
    AILifecycleEventType,
    AILifecycleState,
    VALID_TRANSITIONS,
    ACTIVE_STATES,
    TERMINAL_STATES,
)
from .ai_foundation_events import (
    AILifecycleEvent,
    make_module_failed,
    make_module_initialized,
    make_module_paused,
    make_module_resumed,
    make_module_started,
    make_module_stopped,
)
from .exceptions import (
    AILifecycleError,
    AIInvalidTransitionError,
    AIModuleAlreadyRunningError,
    AIModuleNotRunningError,
)

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal lifecycle controller
# ---------------------------------------------------------------------------

class _AILifecycleController:
    """
    Thread-safe state machine, health tracker, and event publisher for
    a single AI module instance.

    Managed exclusively by :class:`AILifecycleAwareMixin`.  External code
    must not reference this class directly.
    """

    _MAX_EVENT_HISTORY = DEFAULT_MAX_EVENTS

    def __init__(self, module_id: str, module_version: str) -> None:
        self._module_id:      str            = module_id
        self._module_version: str            = module_version
        self._lock:           threading.Lock = threading.Lock()

        # Lifecycle state
        self._state:       AILifecycleState          = AILifecycleState.CREATED
        self._prev_state:  AILifecycleState          = AILifecycleState.CREATED

        # Health tracking
        self._start_time_mono: Optional[float] = None
        self._start_time_iso:  Optional[str]   = None
        self._restart_count:   int             = 0
        self._failure_count:   int             = 0
        self._last_error:      Optional[str]   = None
        self._last_heartbeat:  Optional[str]   = None

        # Event history and subscriber callbacks
        self._event_history: List[AILifecycleEvent]               = []
        self._callbacks:     List[Callable[[AILifecycleEvent], None]] = []

    # ── State access ──────────────────────────────────────────────────────────

    @property
    def state(self) -> AILifecycleState:
        with self._lock:
            return self._state

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._state in ACTIVE_STATES

    # ── State transitions ─────────────────────────────────────────────────────

    def transition(
        self,
        to:    AILifecycleState,
        *,
        actor: str           = ACTOR_LIFECYCLE,
        error: Optional[str] = None,
    ) -> None:
        """
        Execute a validated lifecycle state transition and emit an event.

        Raises
        ------
        AIInvalidTransitionError
            If ``to`` is not a valid next state from the current state.
        """
        with self._lock:
            from_s = self._state
            allowed = VALID_TRANSITIONS.get(from_s, frozenset())
            if to not in allowed:
                raise AIInvalidTransitionError(
                    from_state = from_s,
                    to_state   = to,
                    module_id  = self._module_id,
                )

            self._prev_state = from_s
            self._state      = to
            now_iso          = datetime.now(timezone.utc).isoformat()
            now_mono         = time.monotonic()

            # -- health field updates --
            if to == AILifecycleState.RUNNING:
                if from_s != AILifecycleState.PAUSED:
                    self._start_time_mono = now_mono
                    self._start_time_iso  = now_iso
                self._last_heartbeat = now_iso
                self._last_error     = None
            elif to == AILifecycleState.FAILED:
                self._failure_count += 1
                if error:
                    self._last_error = error
            elif to == AILifecycleState.INITIALIZED and from_s in (
                AILifecycleState.STOPPED, AILifecycleState.FAILED
            ):
                # restart
                self._restart_count += 1

            # -- event emission --
            evt = self._build_event(from_s, to, actor=actor, error=error)
            if evt is not None:
                self._record_and_dispatch(evt)

    def heartbeat(self) -> None:
        """Update the last-heartbeat timestamp (called from engine main loop)."""
        with self._lock:
            self._last_heartbeat = datetime.now(timezone.utc).isoformat()

    # ── Status snapshot ───────────────────────────────────────────────────────

    def status_dict(self) -> Dict[str, Any]:
        """Return a plain-dict health/status snapshot (no dependencies on M5)."""
        with self._lock:
            now    = time.monotonic()
            uptime = 0.0
            if self._state == AILifecycleState.RUNNING and self._start_time_mono is not None:
                uptime = round(now - self._start_time_mono, 3)
            return {
                "module_id":      self._module_id,
                "module_version": self._module_version,
                "state":          self._state.value,
                "is_running":     self._state in ACTIVE_STATES,
                "is_healthy":     self._state == AILifecycleState.RUNNING,
                "is_degraded":    self._state == AILifecycleState.PAUSED,
                "start_time":     self._start_time_iso,
                "uptime_sec":     uptime,
                "restart_count":  self._restart_count,
                "failure_count":  self._failure_count,
                "last_error":     self._last_error,
                "last_heartbeat": self._last_heartbeat,
            }

    # ── Callback management ───────────────────────────────────────────────────

    def register_callback(self, cb: Callable[[AILifecycleEvent], None]) -> None:
        with self._lock:
            if cb not in self._callbacks:
                self._callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[AILifecycleEvent], None]) -> None:
        with self._lock:
            self._callbacks = [c for c in self._callbacks if c is not cb]

    def event_history(self, n: int = 50) -> List[AILifecycleEvent]:
        with self._lock:
            return list(self._event_history[-n:])

    # ── Internals ────────────────────────────────────────────────────────────

    _EVENT_MAP: Dict[tuple, AILifecycleEventType] = {
        (AILifecycleState.CREATED,     AILifecycleState.INITIALIZED): AILifecycleEventType.MODULE_INITIALIZED,
        (AILifecycleState.INITIALIZED, AILifecycleState.RUNNING):     AILifecycleEventType.MODULE_STARTED,
        (AILifecycleState.RUNNING,     AILifecycleState.PAUSED):      AILifecycleEventType.MODULE_PAUSED,
        (AILifecycleState.PAUSED,      AILifecycleState.RUNNING):     AILifecycleEventType.MODULE_RESUMED,
        (AILifecycleState.RUNNING,     AILifecycleState.STOPPING):    AILifecycleEventType.MODULE_STOPPING,
        (AILifecycleState.PAUSED,      AILifecycleState.STOPPING):    AILifecycleEventType.MODULE_STOPPING,
        (AILifecycleState.STOPPING,    AILifecycleState.STOPPED):     AILifecycleEventType.MODULE_STOPPED,
    }

    def _build_event(
        self,
        from_s: AILifecycleState,
        to:     AILifecycleState,
        *,
        actor:  str,
        error:  Optional[str],
    ) -> Optional[AILifecycleEvent]:
        if to == AILifecycleState.FAILED:
            return make_module_failed(self._module_id, from_s, error or "", actor=actor)

        evt_type = self._EVENT_MAP.get((from_s, to))
        if evt_type is None:
            return None
        return AILifecycleEvent(
            event_type = evt_type,
            module_id  = self._module_id,
            from_state = from_s,
            to_state   = to,
            timestamp  = time.time(),
            actor      = actor,
        )

    def _record_and_dispatch(self, evt: AILifecycleEvent) -> None:
        self._event_history.append(evt)
        if len(self._event_history) > self._MAX_EVENT_HISTORY:
            self._event_history = self._event_history[-self._MAX_EVENT_HISTORY :]
        for cb in list(self._callbacks):
            try:
                cb(evt)
            except Exception:  # noqa: BLE001
                _log.exception(
                    f"[{self._module_id}] Lifecycle callback raised; ignoring."
                )


# ---------------------------------------------------------------------------
# AILifecycleAwareMixin — the standard mixin for all AI modules
# ---------------------------------------------------------------------------

class AILifecycleAwareMixin:
    """
    Standard lifecycle interface for all IIOS AI Platform modules (A1–A10).

    Inherit this mixin to gain the full lifecycle interface::

        initialize() → start() → [pause() / resume()] → stop() → restart()

    Class attributes to override
    ----------------------------
    SYSTEM_ID : str
        Machine-readable identifier for this module instance.
        Example: ``"iios:ai:model_management:engine"``
    VERSION : str
        Semantic version string of this module.
        Example: ``"1.0.0"``

    Lifecycle hooks (override in subclass)
    ---------------------------------------
    _on_initialize() — called during ``initialize()``.
    _on_start()      — called during ``start()``.
    _on_stop()       — called during ``stop()``.
    _on_pause()      — called during ``pause()``.
    _on_resume()     — called during ``resume()``.

    Properties
    ----------
    lifecycle_state   → AILifecycleState
    lifecycle_health  → Dict[str, Any]   (never shadows subclass attrs)
    is_ai_running     → bool
    """

    # Subclasses MUST override these two class attributes.
    SYSTEM_ID: str = ""
    VERSION:   str = VERSION

    # ── Lazy lifecycle controller ─────────────────────────────────────────────

    @property
    def _lc(self) -> _AILifecycleController:
        """Lazy-init lifecycle controller (avoids __init__ signature conflicts)."""
        ctrl = self.__dict__.get("_ai_lifecycle_ctrl")
        if ctrl is None:
            mid  = self.SYSTEM_ID or type(self).__name__
            ctrl = _AILifecycleController(module_id=mid, module_version=self.VERSION)
            self.__dict__["_ai_lifecycle_ctrl"] = ctrl
        return ctrl

    # ── Public lifecycle operations ───────────────────────────────────────────

    def initialize(self) -> None:
        """
        Transition CREATED → INITIALIZED.

        Calls the ``_on_initialize()`` hook after the state transition.

        Raises
        ------
        AIInvalidTransitionError
            If the current state does not permit initialization.
        """
        self._lc.transition(AILifecycleState.INITIALIZED, actor=ACTOR_SYSTEM)
        try:
            self._on_initialize()
        except Exception as exc:
            self._lc.transition(AILifecycleState.FAILED, error=str(exc))
            raise

    def start(self) -> None:
        """
        Transition INITIALIZED → RUNNING.

        Also accepts STOPPED and FAILED (restart paths).

        Raises
        ------
        AIModuleAlreadyRunningError
            If the module is already RUNNING.
        AIInvalidTransitionError
            If the current state does not permit start.
        """
        if self.lifecycle_state in ACTIVE_STATES:
            raise AIModuleAlreadyRunningError(
                module_id=self.SYSTEM_ID or type(self).__name__
            )
        # Auto-initialize if still CREATED
        if self.lifecycle_state == AILifecycleState.CREATED:
            self._lc.transition(AILifecycleState.INITIALIZED, actor=ACTOR_SYSTEM)
        # Re-initialize if STOPPED or FAILED (restart path)
        if self.lifecycle_state in (AILifecycleState.STOPPED, AILifecycleState.FAILED):
            self._lc.transition(AILifecycleState.INITIALIZED, actor=ACTOR_SYSTEM)
        try:
            self._on_start()
            self._lc.transition(AILifecycleState.RUNNING, actor=ACTOR_SYSTEM)
        except Exception as exc:
            self._lc.transition(
                AILifecycleState.FAILED,
                actor = ACTOR_SYSTEM,
                error = str(exc),
            )
            raise

    def stop(self) -> None:
        """
        Transition RUNNING/PAUSED → STOPPING → STOPPED.

        Raises
        ------
        AIModuleNotRunningError
            If the module is not in an active state.
        """
        if self.lifecycle_state not in ACTIVE_STATES:
            raise AIModuleNotRunningError(
                module_id=self.SYSTEM_ID or type(self).__name__
            )
        self._lc.transition(AILifecycleState.STOPPING, actor=ACTOR_SYSTEM)
        try:
            self._on_stop()
            self._lc.transition(AILifecycleState.STOPPED, actor=ACTOR_SYSTEM)
        except Exception as exc:
            self._lc.transition(
                AILifecycleState.FAILED,
                actor = ACTOR_SYSTEM,
                error = str(exc),
            )
            raise

    def restart(self) -> None:
        """
        Restart the module.

        From RUNNING/PAUSED: stop gracefully, then start.
        From STOPPED/FAILED: start directly.
        """
        mid = self.SYSTEM_ID or type(self).__name__
        _log.info(f"[{mid}] restarting…")
        if self.lifecycle_state in ACTIVE_STATES:
            self.stop()
        self.start()

    def pause(self) -> None:
        """
        Transition RUNNING → PAUSED.

        Raises
        ------
        AIModuleNotRunningError
            If the module is not RUNNING.
        """
        if self.lifecycle_state != AILifecycleState.RUNNING:
            raise AIModuleNotRunningError(
                module_id=self.SYSTEM_ID or type(self).__name__
            )
        try:
            self._on_pause()
            self._lc.transition(AILifecycleState.PAUSED, actor=ACTOR_SYSTEM)
        except Exception as exc:
            self._lc.transition(
                AILifecycleState.FAILED,
                actor = ACTOR_SYSTEM,
                error = str(exc),
            )
            raise

    def resume(self) -> None:
        """
        Transition PAUSED → RUNNING.

        Raises
        ------
        AIInvalidTransitionError
            If the module is not PAUSED.
        """
        if self.lifecycle_state != AILifecycleState.PAUSED:
            raise AIInvalidTransitionError(
                from_state = self.lifecycle_state,
                to_state   = AILifecycleState.RUNNING,
                module_id  = self.SYSTEM_ID or type(self).__name__,
            )
        try:
            self._on_resume()
            self._lc.transition(AILifecycleState.RUNNING, actor=ACTOR_SYSTEM)
        except Exception as exc:
            self._lc.transition(
                AILifecycleState.FAILED,
                actor = ACTOR_SYSTEM,
                error = str(exc),
            )
            raise

    # ── Supervisor-safe property accessors ───────────────────────────────────
    # Named with "lifecycle_" prefix to avoid shadowing subclass attributes.

    @property
    def lifecycle_state(self) -> AILifecycleState:
        """Current lifecycle state.  Thread-safe read."""
        return self._lc.state

    @property
    def lifecycle_health(self) -> Dict[str, Any]:
        """
        Plain-dict health snapshot.

        Never raises; always returns a valid mapping regardless of state.
        Subclasses may provide a richer ``health()`` method.
        """
        return self._lc.status_dict()

    @property
    def is_ai_running(self) -> bool:
        """``True`` iff the module is in RUNNING or PAUSED state."""
        return self._lc.is_running

    # ── Lifecycle event management ────────────────────────────────────────────

    def register_lifecycle_callback(
        self,
        callback: Callable[[AILifecycleEvent], None],
    ) -> None:
        """Register a callback invoked on every lifecycle event."""
        self._lc.register_callback(callback)

    def unregister_lifecycle_callback(
        self,
        callback: Callable[[AILifecycleEvent], None],
    ) -> None:
        """Remove a previously registered lifecycle callback."""
        self._lc.unregister_callback(callback)

    def lifecycle_event_history(self, n: int = 50) -> List[AILifecycleEvent]:
        """Return the most recent ``n`` lifecycle events (oldest first)."""
        return self._lc.event_history(n)

    def lifecycle_heartbeat(self) -> None:
        """Update the internal heartbeat timestamp."""
        self._lc.heartbeat()

    # ── Lifecycle hooks (override in subclass) ────────────────────────────────

    def _on_initialize(self) -> None:
        """Called after the INITIALIZED state transition.  Override in subclass."""

    def _on_start(self) -> None:
        """Called before the RUNNING state transition.  Override in subclass."""

    def _on_stop(self) -> None:
        """Called before the STOPPED state transition.  Override in subclass."""

    def _on_pause(self) -> None:
        """Called before the PAUSED state transition.  Override in subclass."""

    def _on_resume(self) -> None:
        """Called before the RUNNING (from PAUSED) transition.  Override in subclass."""

    # ── str / repr ────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        mid   = self.SYSTEM_ID or type(self).__name__
        state = self._lc.state.value if hasattr(self, "_ai_lifecycle_ctrl") else "CREATED"
        return f"<{type(self).__name__} id={mid!r} state={state!r}>"
