"""
iios/bootstrap/system_state.py
================================
Thread-safe global system state singleton.

``SystemState`` holds the authoritative current phase of the IIOS platform
and a snapshot of the most recent ``StartupContext``. All components that
need to know whether the platform is running, paused, or shutting down
read from here.

Architecture Reference: IIOS-BSS-001 §2.3 System State
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .startup_state import SystemPhase, is_valid_transition

__all__ = ["SystemState", "get_system_state"]

logger = logging.getLogger(__name__)


@dataclass
class _PhaseRecord:
    """Audit record of a single phase transition."""

    from_phase: SystemPhase
    to_phase: SystemPhase
    timestamp: float = field(default_factory=time.monotonic)
    reason: str = ""


class SystemState:
    """Thread-safe singleton holding the global IIOS lifecycle phase.

    Usage::

        state = get_system_state()
        state.transition_to(SystemPhase.INITIALIZING, reason="BootstrapEngine start")
        print(state.current_phase)
    """

    _instance: Optional[SystemState] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> SystemState:
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._init()
                cls._instance = instance
            return cls._instance

    def _init(self) -> None:
        self._phase: SystemPhase = SystemPhase.UNINITIALIZED
        self._phase_lock: threading.RLock = threading.RLock()
        self._history: list[_PhaseRecord] = []
        self._start_time: float = time.monotonic()
        self._startup_context: Optional[Any] = None   # StartupContext, typed Any to avoid circular
        self._metadata: dict[str, Any] = {}
        self._phase_callbacks: dict[SystemPhase, list[Any]] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # Phase access
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def current_phase(self) -> SystemPhase:
        with self._phase_lock:
            return self._phase

    def transition_to(self, new_phase: SystemPhase, reason: str = "") -> None:
        """Atomically transition to ``new_phase``.

        Raises:
            ValueError: If the transition is not permitted.
        """
        with self._phase_lock:
            old_phase = self._phase
            if old_phase == new_phase:
                return  # idempotent
            if not is_valid_transition(old_phase, new_phase):
                raise ValueError(
                    f"Invalid lifecycle transition: {old_phase.value} → {new_phase.value}"
                )
            self._phase = new_phase
            record = _PhaseRecord(from_phase=old_phase, to_phase=new_phase, reason=reason)
            self._history.append(record)
            logger.info(
                "Phase transition: %s → %s%s",
                old_phase.value,
                new_phase.value,
                f" ({reason})" if reason else "",
            )
            self._fire_callbacks(new_phase)

    def force_phase(self, phase: SystemPhase, reason: str = "forced") -> None:
        """Bypass transition validation and force a phase.

        Use only in recovery/test scenarios.
        """
        with self._phase_lock:
            old = self._phase
            self._phase = phase
            self._history.append(_PhaseRecord(from_phase=old, to_phase=phase, reason=reason))
            logger.warning("Phase FORCED: %s → %s (%s)", old.value, phase.value, reason)

    # ─────────────────────────────────────────────────────────────────────────
    # Convenience checks
    # ─────────────────────────────────────────────────────────────────────────

    def is_running(self) -> bool:
        return self.current_phase in (SystemPhase.RUNNING, SystemPhase.CERTIFIED)

    def is_operational(self) -> bool:
        return self.current_phase.is_active

    def is_shutting_down(self) -> bool:
        return self.current_phase in (SystemPhase.SHUTTING_DOWN, SystemPhase.SHUTDOWN)

    def is_failed(self) -> bool:
        return self.current_phase == SystemPhase.FAILED

    def is_paused(self) -> bool:
        return self.current_phase == SystemPhase.PAUSED

    # ─────────────────────────────────────────────────────────────────────────
    # History
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def phase_history(self) -> list[_PhaseRecord]:
        with self._phase_lock:
            return list(self._history)

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time

    # ─────────────────────────────────────────────────────────────────────────
    # Startup context reference
    # ─────────────────────────────────────────────────────────────────────────

    def set_startup_context(self, context: Any) -> None:
        self._startup_context = context

    def get_startup_context(self) -> Optional[Any]:
        return self._startup_context

    # ─────────────────────────────────────────────────────────────────────────
    # Generic metadata
    # ─────────────────────────────────────────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        self._metadata[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._metadata.get(key, default)

    # ─────────────────────────────────────────────────────────────────────────
    # Phase callbacks
    # ─────────────────────────────────────────────────────────────────────────

    def on_phase(self, phase: SystemPhase, callback: Any) -> None:
        """Register a zero-argument callable to fire when ``phase`` is entered."""
        self._phase_callbacks.setdefault(phase, []).append(callback)

    def _fire_callbacks(self, phase: SystemPhase) -> None:
        for cb in self._phase_callbacks.get(phase, []):
            try:
                cb()
            except Exception:  # noqa: BLE001
                logger.exception("Phase callback raised for phase=%s", phase.value)

    # ─────────────────────────────────────────────────────────────────────────
    # Reset (test / recovery only)
    # ─────────────────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset state to UNINITIALIZED. Only for tests and recovery."""
        with self._phase_lock:
            self._phase = SystemPhase.UNINITIALIZED
            self._history.clear()
            self._startup_context = None
            self._metadata.clear()
            self._phase_callbacks.clear()
            logger.warning("SystemState RESET to UNINITIALIZED")

    def __repr__(self) -> str:
        return f"SystemState(phase={self.current_phase.value}, uptime={self.uptime_seconds:.1f}s)"


def get_system_state() -> SystemState:
    """Return the global ``SystemState`` singleton.

    This is the authoritative factory function — never instantiate
    ``SystemState`` directly.
    """
    return SystemState()
