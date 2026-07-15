"""iios/investment/workflow/engine_lifecycle.py
Unified lifecycle framework for all IIOS institutional intelligence engines.

Provides a reusable, thread-safe lifecycle abstraction that every engine
(C1–C10) can inherit.  The framework:

  • Manages a 10-state state machine with validated transitions.
  • Tracks health metrics: uptime, restart count, failure count, last error,
    last heartbeat.
  • Publishes structured LifecycleEvent objects to registered callbacks.
  • Exposes uniform methods on every engine: initialize(), start(), stop(),
    restart(), shutdown(), pause(), resume(), health(), status(), version().

Usage::

    class MyEngine(LifecycleAwareMixin):
        VERSION   = "1.0.0"
        SYSTEM_ID = "iios:my:engine"

        def _on_start(self) -> None:
            # Custom startup logic here
            ...

        def _on_stop(self) -> None:
            # Custom teardown logic here
            ...

    engine = MyEngine()
    engine.start()               # CREATED → INITIALIZED → STARTING → RUNNING
    print(engine.version())      # "1.0.0"
    print(engine.status())       # EngineState.RUNNING
    h = engine.health()          # LifecycleStatus(is_running=True, ...)
    engine.pause()               # RUNNING → PAUSED
    engine.resume()              # PAUSED  → RUNNING
    engine.stop()                # RUNNING → STOPPING → STOPPED
    engine.restart()             # STOPPED → RESTARTING → STARTING → RUNNING
    engine.shutdown()            # RUNNING → SHUTDOWN  (terminal)
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, FrozenSet, List, Optional

from iios.common.logging.logging_manager import get_logger as _get_iios_logger
from iios.common.logging.audit_logger import get_audit_logger as _get_audit_logger
from iios.common.errors.error_context import ErrorContext, bind_error_context
from iios.common.errors.error_manager import get_error_manager as _get_error_manager
from iios.common.async_exec.async_execution_manager import get_execution_manager as _get_exec_manager

_log = _get_iios_logger(__name__, engine_id="iios:lifecycle")
_audit = _get_audit_logger(__name__, engine_id="iios:lifecycle", component="engine_lifecycle")


# ── Enumerations ──────────────────────────────────────────────────────────────

class EngineState(str, Enum):
    """
    Ordered states in the engine lifecycle state machine.

    Allowed transitions:
    ┌───────────────┬──────────────────────────────────────────────────────┐
    │ From          │ To                                                   │
    ├───────────────┼──────────────────────────────────────────────────────┤
    │ CREATED       │ INITIALIZED, STARTING, SHUTDOWN                     │
    │ INITIALIZED   │ STARTING, SHUTDOWN                                  │
    │ STARTING      │ RUNNING, FAILED                                     │
    │ RUNNING       │ PAUSED, STOPPING, RESTARTING, FAILED, SHUTDOWN      │
    │ PAUSED        │ RUNNING, STOPPING, SHUTDOWN                         │
    │ STOPPING      │ STOPPED, RESTARTING, FAILED                         │
    │ STOPPED       │ STARTING, RESTARTING, SHUTDOWN                      │
    │ FAILED        │ STARTING, RESTARTING, SHUTDOWN                      │
    │ RESTARTING    │ STARTING, FAILED, SHUTDOWN                          │
    │ SHUTDOWN      │ (terminal — no transitions allowed)                 │
    └───────────────┴──────────────────────────────────────────────────────┘
    """
    CREATED     = "created"
    INITIALIZED = "initialized"
    STARTING    = "starting"
    RUNNING     = "running"
    PAUSED      = "paused"
    STOPPING    = "stopping"
    STOPPED     = "stopped"
    FAILED      = "failed"
    RESTARTING  = "restarting"
    SHUTDOWN    = "shutdown"


class LifecycleEventType(str, Enum):
    """Lifecycle event types published during state transitions."""
    ENGINE_INITIALIZED = "engine_initialized"
    ENGINE_STARTED     = "engine_started"
    ENGINE_PAUSED      = "engine_paused"
    ENGINE_RESUMED     = "engine_resumed"
    ENGINE_STOPPED     = "engine_stopped"
    ENGINE_RESTARTED   = "engine_restarted"
    ENGINE_FAILED      = "engine_failed"
    ENGINE_SHUTDOWN    = "engine_shutdown"


# ── State machine definition ──────────────────────────────────────────────────

_VALID_TRANSITIONS: Dict[EngineState, FrozenSet[EngineState]] = {
    EngineState.CREATED:     frozenset({
        EngineState.INITIALIZED,
        EngineState.STARTING,
        EngineState.SHUTDOWN,
    }),
    EngineState.INITIALIZED: frozenset({
        EngineState.STARTING,
        EngineState.SHUTDOWN,
    }),
    EngineState.STARTING:    frozenset({
        EngineState.RUNNING,
        EngineState.FAILED,
    }),
    EngineState.RUNNING:     frozenset({
        EngineState.PAUSED,
        EngineState.STOPPING,
        EngineState.RESTARTING,
        EngineState.FAILED,
        EngineState.SHUTDOWN,
    }),
    EngineState.PAUSED:      frozenset({
        EngineState.RUNNING,
        EngineState.STOPPING,
        EngineState.SHUTDOWN,
    }),
    EngineState.STOPPING:    frozenset({
        EngineState.STOPPED,
        EngineState.RESTARTING,
        EngineState.FAILED,
    }),
    EngineState.STOPPED:     frozenset({
        EngineState.STARTING,
        EngineState.RESTARTING,
        EngineState.SHUTDOWN,
    }),
    EngineState.FAILED:      frozenset({
        EngineState.STARTING,
        EngineState.RESTARTING,
        EngineState.SHUTDOWN,
    }),
    EngineState.RESTARTING:  frozenset({
        EngineState.STARTING,
        EngineState.FAILED,
        EngineState.SHUTDOWN,
    }),
    EngineState.SHUTDOWN:    frozenset(),
}


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LifecycleEvent:
    """Immutable record of a single lifecycle state transition."""
    event_type:     LifecycleEventType
    engine_id:      str
    engine_version: str
    from_state:     EngineState
    to_state:       EngineState
    timestamp:      str              # ISO-8601 UTC
    error:          Optional[str] = None
    metadata:       Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "event_type":     self.event_type.value,
            "engine_id":      self.engine_id,
            "engine_version": self.engine_version,
            "from_state":     self.from_state.value,
            "to_state":       self.to_state.value,
            "timestamp":      self.timestamp,
            "error":          self.error,
            "metadata":       self.metadata,
        }


@dataclass(frozen=True)
class LifecycleStatus:
    """Point-in-time snapshot of engine lifecycle health."""
    engine_id:      str
    engine_version: str
    state:          EngineState
    is_running:     bool
    is_healthy:     bool
    start_time:     Optional[str]  # ISO-8601 UTC; None if never started
    uptime_sec:     float          # seconds since last start; 0.0 if not running
    restart_count:  int
    failure_count:  int
    last_error:     Optional[str]
    last_heartbeat: Optional[str]  # ISO-8601 UTC; None if never set

    def to_dict(self) -> dict:
        return {
            "engine_id":      self.engine_id,
            "engine_version": self.engine_version,
            "state":          self.state.value,
            "is_running":     self.is_running,
            "is_healthy":     self.is_healthy,
            "start_time":     self.start_time,
            "uptime_sec":     self.uptime_sec,
            "restart_count":  self.restart_count,
            "failure_count":  self.failure_count,
            "last_error":     self.last_error,
            "last_heartbeat": self.last_heartbeat,
        }


# ── Exceptions ────────────────────────────────────────────────────────────────

class LifecycleError(Exception):
    """Base exception for lifecycle violations."""


class InvalidTransitionError(LifecycleError):
    """Raised on an invalid state transition attempt."""
    def __init__(
        self,
        from_state: EngineState,
        to_state:   EngineState,
        engine_id:  str = "",
    ) -> None:
        super().__init__(
            f"[{engine_id}] Invalid lifecycle transition: "
            f"{from_state.value!r} → {to_state.value!r}"
        )
        self.from_state = from_state
        self.to_state   = to_state


class EngineShutdownError(LifecycleError):
    """Raised when an operation is attempted on a shut-down engine."""


class EngineAlreadyRunningError(LifecycleError):
    """Raised when start() is called on a running engine."""


class EngineNotRunningError(LifecycleError):
    """Raised when stop() is called on a non-running engine."""


# ── Internal state-to-event mapping ──────────────────────────────────────────

_STATE_TO_EVENT: Dict[EngineState, LifecycleEventType] = {
    EngineState.INITIALIZED: LifecycleEventType.ENGINE_INITIALIZED,
    EngineState.RUNNING:     LifecycleEventType.ENGINE_STARTED,
    EngineState.PAUSED:      LifecycleEventType.ENGINE_PAUSED,
    EngineState.STOPPED:     LifecycleEventType.ENGINE_STOPPED,
    EngineState.FAILED:      LifecycleEventType.ENGINE_FAILED,
    EngineState.SHUTDOWN:    LifecycleEventType.ENGINE_SHUTDOWN,
    # ENGINE_RESUMED: emitted when PAUSED → RUNNING (see transition logic)
    # ENGINE_RESTARTED: emitted when RESTARTING → RUNNING (see transition logic)
}


# ── LifecycleController ───────────────────────────────────────────────────────

class LifecycleController:
    """
    Thread-safe lifecycle state machine, health tracker, and event publisher.

    One instance per engine.  Managed exclusively by LifecycleAwareMixin.
    External consumers use the mixin's public API rather than this class.
    """

    _MAX_EVENT_HISTORY = 200

    def __init__(self, engine_id: str, engine_version: str) -> None:
        self._engine_id:      str            = engine_id
        self._engine_version: str            = engine_version
        self._lock:           threading.RLock = threading.RLock()

        # State
        self._state:           EngineState    = EngineState.CREATED
        self._prev_state:      EngineState    = EngineState.CREATED

        # Health tracking (monotonic clock for uptime, ISO for reporting)
        self._start_time_mono: Optional[float] = None
        self._start_time_iso:  Optional[str]   = None
        self._restart_count:   int             = 0
        self._failure_count:   int             = 0
        self._last_error:      Optional[str]   = None
        self._last_heartbeat:  Optional[str]   = None

        # Event history + callbacks
        self._event_history: List[LifecycleEvent]                   = []
        self._callbacks:     List[Callable[[LifecycleEvent], None]] = []

    # ── State machine ──────────────────────────────────────────────────────────

    @property
    def state(self) -> EngineState:
        with self._lock:
            return self._state

    def transition(
        self,
        to:       EngineState,
        *,
        error:    Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Execute a validated state transition and emit a lifecycle event.

        Raises:
            EngineShutdownError:    If the engine is already shut down.
            InvalidTransitionError: If the transition is not valid.
        """
        with self._lock:
            from_s = self._state
            self._validate_transition(from_s, to)

            self._prev_state = from_s
            self._state      = to

            now_mono = time.monotonic()
            now_iso  = datetime.now(timezone.utc).isoformat()

            # --- health field updates ---
            if to == EngineState.RUNNING:
                if from_s != EngineState.PAUSED:
                    # Fresh start (not a resume)
                    self._start_time_mono = now_mono
                    self._start_time_iso  = now_iso
                self._last_heartbeat = now_iso
                self._last_error     = None

            elif to == EngineState.FAILED:
                self._failure_count += 1
                if error:
                    self._last_error = error

            elif to == EngineState.RESTARTING:
                self._restart_count += 1

            # --- event emission ---
            evt_type = self._resolve_event_type(from_s, to)
            if evt_type is not None:
                evt = LifecycleEvent(
                    event_type     = evt_type,
                    engine_id      = self._engine_id,
                    engine_version = self._engine_version,
                    from_state     = from_s,
                    to_state       = to,
                    timestamp      = now_iso,
                    error          = error,
                    metadata       = metadata,
                )
                self._record_and_dispatch(evt)

    def _validate_transition(self, from_s: EngineState, to: EngineState) -> None:
        if from_s == EngineState.SHUTDOWN:
            raise EngineShutdownError(
                f"[{self._engine_id}] Engine is permanently shut down; "
                "no further state transitions are allowed."
            )
        if to not in _VALID_TRANSITIONS[from_s]:
            raise InvalidTransitionError(from_s, to, self._engine_id)

    def _resolve_event_type(
        self, from_s: EngineState, to: EngineState
    ) -> Optional[LifecycleEventType]:
        """Determine the correct LifecycleEventType for a transition."""
        if to == EngineState.RUNNING:
            if from_s == EngineState.PAUSED:
                return LifecycleEventType.ENGINE_RESUMED
            if from_s == EngineState.STARTING and self._restart_count > 0:
                return LifecycleEventType.ENGINE_RESTARTED
        return _STATE_TO_EVENT.get(to)

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    def heartbeat(self) -> None:
        """Update the last-heartbeat timestamp (call from engine's main loop)."""
        with self._lock:
            self._last_heartbeat = datetime.now(timezone.utc).isoformat()

    # ── Health snapshot ───────────────────────────────────────────────────────

    def status(self) -> LifecycleStatus:
        """Return a point-in-time LifecycleStatus snapshot."""
        with self._lock:
            now = time.monotonic()
            uptime = 0.0
            if self._state == EngineState.RUNNING and self._start_time_mono is not None:
                uptime = round(now - self._start_time_mono, 3)
            return LifecycleStatus(
                engine_id      = self._engine_id,
                engine_version = self._engine_version,
                state          = self._state,
                is_running     = self._state == EngineState.RUNNING,
                is_healthy     = self._state in (EngineState.RUNNING, EngineState.PAUSED),
                start_time     = self._start_time_iso,
                uptime_sec     = uptime,
                restart_count  = self._restart_count,
                failure_count  = self._failure_count,
                last_error     = self._last_error,
                last_heartbeat = self._last_heartbeat,
            )

    # ── Event callbacks ───────────────────────────────────────────────────────

    def register_callback(self, cb: Callable[[LifecycleEvent], None]) -> None:
        with self._lock:
            if cb not in self._callbacks:
                self._callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[LifecycleEvent], None]) -> None:
        with self._lock:
            self._callbacks = [c for c in self._callbacks if c is not cb]

    def event_history(self, n: int = 50) -> List[LifecycleEvent]:
        with self._lock:
            return list(self._event_history[-n:])

    # ── Private helpers ───────────────────────────────────────────────────────

    def _record_and_dispatch(self, evt: LifecycleEvent) -> None:
        """Append event to history and dispatch to all registered callbacks."""
        self._event_history.append(evt)
        if len(self._event_history) > self._MAX_EVENT_HISTORY:
            self._event_history = self._event_history[-self._MAX_EVENT_HISTORY:]
        # Emit structured audit record for every lifecycle transition
        try:
            _audit.log_lifecycle_event(
                engine_id  = self._engine_id,
                from_state = evt.from_state.value if evt.from_state else "",
                to_state   = evt.to_state.value if evt.to_state else "",
                version    = self._engine_version,
            )
        except Exception:  # noqa: BLE001  — never crash the dispatch loop
            pass
        for cb in list(self._callbacks):
            try:
                cb(evt)
            except Exception:
                _log.exception(
                    f"[{self._engine_id}] Lifecycle callback raised an exception; ignoring.",
                )


# ── LifecycleAwareMixin ────────────────────────────────────────────────────────

class LifecycleAwareMixin:
    """
    Uniform lifecycle interface for all IIOS institutional engines (C1–C10).

    Inherit this mixin to gain the full lifecycle interface:
        initialize() → start() → [pause()/resume()] → stop() → restart() → shutdown()

    Override hooks in subclasses for engine-specific logic:
        _on_initialize()   — called inside initialize()
        _on_start()        — called inside start() before RUNNING state
        _on_stop()         — called inside stop() before STOPPED state
        _on_pause()        — called inside pause() before PAUSED state
        _on_resume()       — called inside resume() before RUNNING state
        _on_shutdown()     — called inside shutdown() before SHUTDOWN state

    Subclasses that already define start()/stop() MUST call super().start() /
    super().stop() at the BEGINNING of their overrides to keep lifecycle state
    tracking in sync.

    Supervisor-safe accessors that always return lifecycle types:
        lifecycle_state()  — always returns EngineState (never shadowed)
        lifecycle_health() — always returns LifecycleStatus (never shadowed)
    """

    # Class-level defaults; override at engine class level
    VERSION:   str = "0.0.0"
    SYSTEM_ID: str = ""

    # ── Lazy lifecycle controller ─────────────────────────────────────────────

    @property
    def _lc(self) -> LifecycleController:
        """Lazy-init lifecycle controller (avoids __init__ signature conflicts)."""
        ctrl = self.__dict__.get("_lifecycle_ctrl")
        if ctrl is None:
            ctrl = LifecycleController(
                engine_id      = self.SYSTEM_ID or type(self).__name__,
                engine_version = self.VERSION,
            )
            self.__dict__["_lifecycle_ctrl"] = ctrl
        return ctrl

    # ── Core lifecycle operations ─────────────────────────────────────────────

    def initialize(self) -> None:
        """
        Transition CREATED → INITIALIZED.

        Subclasses with parameterized initialize() should keep their own
        signature and call ``self._lc.transition(EngineState.INITIALIZED)``
        after their custom logic, or call ``super().initialize()`` if the
        no-arg version is acceptable.
        """
        self._lc.transition(EngineState.INITIALIZED)
        self._on_initialize()

    def start(self) -> None:
        """
        Transition to RUNNING.

        From CREATED:     CREATED → INITIALIZED → STARTING → RUNNING
        From INITIALIZED: INITIALIZED → STARTING → RUNNING
        From STOPPED:     STOPPED → STARTING → RUNNING
        From FAILED:      FAILED  → STARTING → RUNNING

        Raises:
            EngineAlreadyRunningError: if already RUNNING.
            InvalidTransitionError:   if current state does not permit start.
        """
        lc    = self._lc
        state = lc.state

        if state == EngineState.RUNNING:
            raise EngineAlreadyRunningError(
                f"[{self.SYSTEM_ID or type(self).__name__}] Engine is already running."
            )
        if state == EngineState.CREATED:
            # Auto-initialize before starting
            lc.transition(EngineState.INITIALIZED)
        lc.transition(EngineState.STARTING)
        _start_ctx = ErrorContext(
            engine_id = self.SYSTEM_ID or type(self).__name__,
            stage     = "start",
            operation = "_on_start",
        )
        try:
            with bind_error_context(_start_ctx):
                _engine_id = self.SYSTEM_ID or type(self).__name__
                _get_exec_manager().execute_sync(
                    self._on_start,
                    timeout_sec = 60.0,
                    operation   = "engine.start",
                    engine_id   = _engine_id,
                )
            lc.transition(EngineState.RUNNING)
        except Exception as exc:
            _get_error_manager().report_failure(self.SYSTEM_ID or type(self).__name__, exc)
            lc.transition(EngineState.FAILED, error=str(exc))
            raise

    def stop(self) -> None:
        """
        Transition RUNNING/PAUSED → STOPPING → STOPPED.

        Raises:
            EngineNotRunningError: if the engine is not RUNNING or PAUSED.
        """
        lc    = self._lc
        state = lc.state

        if state not in (EngineState.RUNNING, EngineState.PAUSED):
            raise EngineNotRunningError(
                f"[{self.SYSTEM_ID or type(self).__name__}] "
                f"Cannot stop engine in state {state.value!r}."
            )
        lc.transition(EngineState.STOPPING)
        _err_ctx = ErrorContext(
            engine_id = self.SYSTEM_ID or type(self).__name__,
            stage     = "stop",
            operation = "_on_stop",
        )
        try:
            with bind_error_context(_err_ctx):
                _engine_id = self.SYSTEM_ID or type(self).__name__
                _get_exec_manager().execute_sync(
                    self._on_stop,
                    timeout_sec = 30.0,
                    operation   = "engine.stop",
                    engine_id   = _engine_id,
                )
            lc.transition(EngineState.STOPPED)
        except Exception as exc:
            _get_error_manager().report_failure(self.SYSTEM_ID or type(self).__name__, exc)
            lc.transition(EngineState.FAILED, error=str(exc))
            raise

    def restart(self) -> None:
        """
        Restart the engine.

        From RUNNING/PAUSED: stop gracefully, then start again.
        From STOPPED/FAILED: start again directly.

        State path (if running):
            RUNNING → STOPPING → RESTARTING → STARTING → RUNNING

        State path (if stopped/failed):
            STOPPED/FAILED → RESTARTING → STARTING → RUNNING
        """
        lc    = self._lc
        state = lc.state

        if state in (EngineState.RUNNING, EngineState.PAUSED):
            lc.transition(EngineState.STOPPING)
            try:
                self._on_stop()
            except Exception:
                _log.exception(
                    f"[{self.SYSTEM_ID or type(self).__name__}] _on_stop raised during restart; continuing.",
                )
            lc.transition(EngineState.RESTARTING)
        elif state in (EngineState.STOPPED, EngineState.FAILED):
            lc.transition(EngineState.RESTARTING)
        else:
            raise LifecycleError(
                f"[{self.SYSTEM_ID or type(self).__name__}] "
                f"Cannot restart from state {state.value!r}."
            )

        lc.transition(EngineState.STARTING)
        try:
            self._on_start()
            lc.transition(EngineState.RUNNING)
        except Exception as exc:
            lc.transition(EngineState.FAILED, error=str(exc))
            raise

    def pause(self) -> None:
        """
        Transition RUNNING → PAUSED.

        Raises:
            LifecycleError: if the engine is not RUNNING.
        """
        lc = self._lc
        if lc.state != EngineState.RUNNING:
            raise LifecycleError(
                f"[{self.SYSTEM_ID or type(self).__name__}] "
                f"Cannot pause engine in state {lc.state.value!r}."
            )
        self._on_pause()
        lc.transition(EngineState.PAUSED)

    def resume(self) -> None:
        """
        Transition PAUSED → RUNNING.

        Raises:
            LifecycleError: if the engine is not PAUSED.
        """
        lc = self._lc
        if lc.state != EngineState.PAUSED:
            raise LifecycleError(
                f"[{self.SYSTEM_ID or type(self).__name__}] "
                f"Cannot resume engine in state {lc.state.value!r}."
            )
        self._on_resume()
        lc.transition(EngineState.RUNNING)

    def shutdown(self) -> None:
        """
        Permanently shut down the engine (terminal state).

        Idempotent: calling shutdown() on an already shut-down engine is safe.
        If RUNNING or PAUSED, the engine is gracefully stopped first.
        """
        lc    = self._lc
        state = lc.state

        if state == EngineState.SHUTDOWN:
            return  # already shut down; idempotent

        if state in (EngineState.RUNNING, EngineState.PAUSED):
            try:
                self._on_stop()
            except Exception:
                _log.exception(
                    f"[{self.SYSTEM_ID or type(self).__name__}] _on_stop raised during shutdown; continuing.",
                )
        self._on_shutdown()
        lc.transition(EngineState.SHUTDOWN)

    # ── Health / status ───────────────────────────────────────────────────────

    def health(self) -> LifecycleStatus:
        """
        Return a LifecycleStatus snapshot.

        Engines that already define health() for domain-specific purposes
        will shadow this method.  Use lifecycle_health() for guaranteed
        lifecycle-typed access.
        """
        return self._lc.status()

    def status(self) -> EngineState:
        """
        Return the current EngineState.

        Engines that already define status() for domain-specific purposes
        will shadow this method.  Use lifecycle_state() for guaranteed
        EngineState-typed access.
        """
        return self._lc.state

    def version(self) -> str:
        """Return the engine version string (from the class-level VERSION attribute)."""
        return self.VERSION

    # ── Supervisor-safe lifecycle accessors ───────────────────────────────────

    def lifecycle_state(self) -> EngineState:
        """
        Always returns the current EngineState.

        Unlike status(), this method is never shadowed by subclasses, making
        it safe for supervisors and the workflow orchestrator to call uniformly
        across all engine types.
        """
        return self._lc.state

    def lifecycle_health(self) -> LifecycleStatus:
        """
        Always returns a LifecycleStatus snapshot.

        Unlike health(), this method is never shadowed by subclasses, making
        it safe for supervisors and the workflow orchestrator to call uniformly
        across all engine types.
        """
        return self._lc.status()

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    def lifecycle_heartbeat(self) -> None:
        """Update the last-heartbeat timestamp in the lifecycle controller."""
        self._lc.heartbeat()

    # ── Event subscription ────────────────────────────────────────────────────

    def register_lifecycle_callback(
        self, cb: Callable[[LifecycleEvent], None]
    ) -> None:
        """Register a callback that receives LifecycleEvent objects."""
        self._lc.register_callback(cb)

    def unregister_lifecycle_callback(
        self, cb: Callable[[LifecycleEvent], None]
    ) -> None:
        """Remove a previously registered lifecycle callback."""
        self._lc.unregister_callback(cb)

    def lifecycle_event_history(self, n: int = 50) -> List[LifecycleEvent]:
        """Return the most recent *n* lifecycle events (newest-last)."""
        return self._lc.event_history(n)

    # ── Hooks (override in subclass) ──────────────────────────────────────────

    def _on_initialize(self) -> None:
        """Called inside initialize().  Override for custom initialization."""

    def _on_start(self) -> None:
        """Called inside start() and restart() before RUNNING state is set."""

    def _on_stop(self) -> None:
        """Called inside stop(), restart(), and shutdown() before STOPPED state."""

    def _on_pause(self) -> None:
        """Called inside pause() before PAUSED state is set."""

    def _on_resume(self) -> None:
        """Called inside resume() before RUNNING state is set."""

    def _on_shutdown(self) -> None:
        """Called inside shutdown() before SHUTDOWN state is set."""
