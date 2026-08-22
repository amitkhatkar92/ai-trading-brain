"""
iios/bootstrap/lifecycle_manager.py
======================================
Lifecycle state machine for the IIOS platform.

``LifecycleManager`` owns the ``SystemState`` singleton and exposes
high-level lifecycle operations (start, pause, resume, stop, shutdown,
maintenance, recovery). Every transition is validated against the legal
transition graph defined in ``startup_state.py``.

Thread-safe: all public methods acquire the internal lock before
modifying state.

Architecture Reference: IIOS-BSS-001 §4.1 Lifecycle Model
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

from .startup_state import SystemPhase, is_valid_transition, allowed_transitions
from .system_state import SystemState, get_system_state

__all__ = ["LifecycleManager", "LifecycleHook", "LifecycleError"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

LifecycleHook = Callable[[], None]


class LifecycleError(RuntimeError):
    """Raised when a lifecycle operation cannot be performed."""

    def __init__(self, message: str, current: SystemPhase, requested: SystemPhase) -> None:
        super().__init__(message)
        self.current_phase = current
        self.requested_phase = requested


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class LifecycleManager:
    """Manages IIOS platform lifecycle with validated transitions.

    Usage::

        mgr = LifecycleManager()
        mgr.initialize()   # UNINITIALIZED → INITIALIZING → INITIALIZED
        mgr.start()        # INITIALIZED → STARTING → RUNNING
        mgr.pause()        # RUNNING → PAUSING → PAUSED
        mgr.resume()       # PAUSED → RESUMING → RUNNING
        mgr.stop()         # RUNNING → STOPPING → STOPPED
        mgr.shutdown()     # STOPPED → SHUTTING_DOWN → SHUTDOWN
    """

    def __init__(self, state: Optional[SystemState] = None) -> None:
        self._state: SystemState = state or get_system_state()
        self._lock = threading.RLock()
        self._hooks: dict[SystemPhase, list[LifecycleHook]] = {}
        self._on_error: Optional[Callable[[Exception], None]] = None

    # ─────────────────────────────────────────────────────────────────────────
    # High-level lifecycle operations
    # ─────────────────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Transition UNINITIALIZED → INITIALIZING (caller marks INITIALIZED)."""
        self._transition(
            from_phase=SystemPhase.UNINITIALIZED,
            to_phase=SystemPhase.INITIALIZING,
            reason="LifecycleManager.initialize()",
        )

    def mark_initialized(self) -> None:
        """Transition INITIALIZING → INITIALIZED (called after stages 1-10)."""
        self._transition(
            from_phase=SystemPhase.INITIALIZING,
            to_phase=SystemPhase.INITIALIZED,
            reason="Pre-startup validation complete",
        )

    def start(self) -> None:
        """Transition INITIALIZED → STARTING (caller marks RUNNING/CERTIFIED)."""
        self._require_phase(SystemPhase.INITIALIZED)
        self._transition(
            from_phase=SystemPhase.INITIALIZED,
            to_phase=SystemPhase.STARTING,
            reason="LifecycleManager.start()",
        )

    def mark_running(self) -> None:
        """Transition STARTING → RUNNING (all stages complete)."""
        self._transition(
            from_phase=SystemPhase.STARTING,
            to_phase=SystemPhase.RUNNING,
            reason="All bootstrap stages complete",
        )

    def certify(self) -> None:
        """Transition RUNNING → CERTIFIED (SYSTEM_CERTIFIED criteria met)."""
        current = self._state.current_phase
        if current not in (SystemPhase.RUNNING, SystemPhase.STARTING):
            raise LifecycleError(
                f"Cannot certify from phase {current.value}",
                current=current,
                requested=SystemPhase.CERTIFIED,
            )
        self._transition(
            from_phase=current,
            to_phase=SystemPhase.CERTIFIED,
            reason="SYSTEM_CERTIFIED: WinRate>=50%, Sharpe>0.8, MaxDD<15%",
        )

    def pause(self) -> None:
        """Transition RUNNING|CERTIFIED → PAUSING → PAUSED."""
        current = self._state.current_phase
        if current not in (SystemPhase.RUNNING, SystemPhase.CERTIFIED):
            raise LifecycleError(
                f"Cannot pause from phase {current.value}",
                current=current,
                requested=SystemPhase.PAUSED,
            )
        self._transition(from_phase=current, to_phase=SystemPhase.PAUSING, reason="pause requested")
        self._transition(from_phase=SystemPhase.PAUSING, to_phase=SystemPhase.PAUSED, reason="paused")
        logger.info("System PAUSED")

    def resume(self) -> None:
        """Transition PAUSED → RESUMING → RUNNING."""
        self._require_phase(SystemPhase.PAUSED)
        self._transition(from_phase=SystemPhase.PAUSED, to_phase=SystemPhase.RESUMING, reason="resume requested")
        self._transition(from_phase=SystemPhase.RESUMING, to_phase=SystemPhase.RUNNING, reason="resumed")
        logger.info("System RESUMED")

    def stop(self) -> None:
        """Transition active phase → STOPPING → STOPPED."""
        current = self._state.current_phase
        if not is_valid_transition(current, SystemPhase.STOPPING):
            raise LifecycleError(
                f"Cannot stop from phase {current.value}",
                current=current,
                requested=SystemPhase.STOPPED,
            )
        self._transition(from_phase=current, to_phase=SystemPhase.STOPPING, reason="stop requested")
        self._transition(from_phase=SystemPhase.STOPPING, to_phase=SystemPhase.STOPPED, reason="stopped")
        logger.info("System STOPPED")

    def shutdown(self) -> None:
        """Transition to SHUTTING_DOWN → SHUTDOWN."""
        current = self._state.current_phase
        # Allow shutdown from STOPPED, PAUSED, INITIALIZED, or after stop()
        if not is_valid_transition(current, SystemPhase.SHUTTING_DOWN):
            # Try to stop first
            if is_valid_transition(current, SystemPhase.STOPPING):
                logger.info("Auto-stopping before shutdown from phase %s", current.value)
                self._transition(from_phase=current, to_phase=SystemPhase.STOPPING, reason="pre-shutdown stop")
                self._transition(from_phase=SystemPhase.STOPPING, to_phase=SystemPhase.STOPPED, reason="pre-shutdown stopped")
                current = SystemPhase.STOPPED
            else:
                raise LifecycleError(
                    f"Cannot shutdown from phase {current.value}",
                    current=current,
                    requested=SystemPhase.SHUTDOWN,
                )
        self._transition(from_phase=current, to_phase=SystemPhase.SHUTTING_DOWN, reason="shutdown requested")
        self._transition(from_phase=SystemPhase.SHUTTING_DOWN, to_phase=SystemPhase.SHUTDOWN, reason="shutdown complete")
        logger.info("System SHUTDOWN complete")

    def enter_maintenance(self) -> None:
        """Transition RUNNING|CERTIFIED → MAINTENANCE."""
        current = self._state.current_phase
        if not is_valid_transition(current, SystemPhase.MAINTENANCE):
            raise LifecycleError(
                f"Cannot enter maintenance from phase {current.value}",
                current=current,
                requested=SystemPhase.MAINTENANCE,
            )
        self._transition(from_phase=current, to_phase=SystemPhase.MAINTENANCE, reason="maintenance mode entered")
        logger.info("System in MAINTENANCE mode")

    def exit_maintenance(self) -> None:
        """Transition MAINTENANCE → RUNNING."""
        self._require_phase(SystemPhase.MAINTENANCE)
        self._transition(
            from_phase=SystemPhase.MAINTENANCE,
            to_phase=SystemPhase.RUNNING,
            reason="maintenance complete",
        )
        logger.info("System resumed from MAINTENANCE")

    def enter_recovery(self) -> None:
        """Transition FAILED → RECOVERY."""
        self._require_phase(SystemPhase.FAILED)
        self._transition(
            from_phase=SystemPhase.FAILED,
            to_phase=SystemPhase.RECOVERY,
            reason="recovery initiated",
        )
        logger.warning("System entering RECOVERY mode")

    def mark_failed(self, reason: str = "") -> None:
        """Force-transition to FAILED from any transitioning phase."""
        current = self._state.current_phase
        if is_valid_transition(current, SystemPhase.FAILED):
            self._transition(from_phase=current, to_phase=SystemPhase.FAILED, reason=reason or "unhandled error")
        else:
            self._state.force_phase(SystemPhase.FAILED, reason=f"force-fail: {reason}")
        logger.error("System marked FAILED: %s", reason)

    # ─────────────────────────────────────────────────────────────────────────
    # State accessors
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def current_phase(self) -> SystemPhase:
        return self._state.current_phase

    @property
    def is_running(self) -> bool:
        return self._state.is_running()

    @property
    def is_operational(self) -> bool:
        return self._state.is_operational()

    @property
    def is_paused(self) -> bool:
        return self._state.is_paused()

    @property
    def is_shutting_down(self) -> bool:
        return self._state.is_shutting_down()

    def uptime_seconds(self) -> float:
        return self._state.uptime_seconds

    # ─────────────────────────────────────────────────────────────────────────
    # Hooks
    # ─────────────────────────────────────────────────────────────────────────

    def register_hook(self, phase: SystemPhase, hook: LifecycleHook) -> None:
        """Register a callback to fire when ``phase`` is entered."""
        self._hooks.setdefault(phase, []).append(hook)
        self._state.on_phase(phase, hook)

    def on_error(self, handler: Callable[[Exception], None]) -> None:
        """Register a handler called when a lifecycle exception is raised."""
        self._on_error = handler

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _transition(
        self,
        from_phase: SystemPhase,
        to_phase: SystemPhase,
        reason: str = "",
    ) -> None:
        with self._lock:
            current = self._state.current_phase
            if current != from_phase:
                # Allow idempotent "already arrived" case
                if current == to_phase:
                    return
                logger.warning(
                    "Lifecycle: expected %s but current is %s — attempting transition to %s anyway",
                    from_phase.value,
                    current.value,
                    to_phase.value,
                )
            try:
                self._state.transition_to(to_phase, reason=reason)
            except ValueError as exc:
                error = LifecycleError(str(exc), current=current, requested=to_phase)
                if self._on_error:
                    self._on_error(error)
                raise error from exc

    def _require_phase(self, required: SystemPhase) -> None:
        current = self._state.current_phase
        if current != required:
            raise LifecycleError(
                f"Operation requires phase {required.value}, but current is {current.value}",
                current=current,
                requested=required,
            )
