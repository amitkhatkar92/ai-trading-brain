"""
iios/monitoring/heartbeat_manager.py
======================================
Heartbeat monitoring — detects silent failures in long-running subsystems.

Each IIOS component should call ``beat()`` periodically. If a component
misses its heartbeat within the configured timeout, it is flagged as
unhealthy and an alert callback is fired.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

from .monitoring_constants import DEFAULT_HEARTBEAT_TIMEOUT_SECONDS, HealthStatus
from .monitoring_models import HeartbeatRecord

__all__ = [
    "HeartbeatManager",
    "get_heartbeat_manager",
]

_LOG = logging.getLogger("iios.monitoring.heartbeat")
_instance_lock = threading.Lock()
_instance: Optional["HeartbeatManager"] = None


class HeartbeatManager:
    """Tracks periodic heartbeats from IIOS components.

    Args:
        default_timeout:  Seconds before a component is considered dead.
        check_interval:   How often to scan for missed heartbeats.
    """

    def __init__(
        self,
        default_timeout: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
        check_interval: float = 10.0,
    ) -> None:
        self._lock = threading.Lock()
        self._default_timeout = default_timeout
        self._check_interval = check_interval
        # component → last HeartbeatRecord
        self._last: dict[str, HeartbeatRecord] = {}
        # component → registered timeout
        self._timeouts: dict[str, float] = {}
        # component → sequence counter
        self._sequences: dict[str, int] = {}
        # Death callbacks
        self._death_callbacks: list[Callable[[str, float], None]] = []
        # Recovery callbacks
        self._recovery_callbacks: list[Callable[[str], None]] = []
        # Track which components are known dead (to fire recovery)
        self._dead: set[str] = set()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, component: str, timeout_seconds: Optional[float] = None) -> None:
        """Register a component for heartbeat monitoring."""
        with self._lock:
            self._timeouts[component] = timeout_seconds or self._default_timeout
            self._sequences[component] = 0
        _LOG.debug("Heartbeat registered: %s (timeout=%ss)", component, self._timeouts[component])

    def unregister(self, component: str) -> None:
        with self._lock:
            self._timeouts.pop(component, None)
            self._last.pop(component, None)
            self._sequences.pop(component, None)
            self._dead.discard(component)

    # ------------------------------------------------------------------
    # Heartbeat API
    # ------------------------------------------------------------------

    def beat(
        self,
        component: str,
        status: str = HealthStatus.HEALTHY.value,
        **metadata: Any,
    ) -> HeartbeatRecord:
        """Record a heartbeat from *component*."""
        with self._lock:
            seq = self._sequences.get(component, 0) + 1
            self._sequences[component] = seq
            was_dead = component in self._dead
            self._dead.discard(component)

        record = HeartbeatRecord(
            component=component,
            status=status,
            sequence=seq,
            metadata=metadata,
        )
        with self._lock:
            self._last[component] = record

        # Fire recovery if component was previously dead
        if was_dead:
            _LOG.info("Heartbeat recovered: %s (seq=%d)", component, seq)
            for cb in self._recovery_callbacks:
                try:
                    cb(component)
                except Exception:
                    pass

        return record

    # ------------------------------------------------------------------
    # Status queries
    # ------------------------------------------------------------------

    def is_alive(self, component: str) -> bool:
        """Return True if *component* is alive (received heartbeat within timeout)."""
        with self._lock:
            record = self._last.get(component)
            timeout = self._timeouts.get(component, self._default_timeout)
        if record is None:
            return False
        age = time.monotonic() - record.timestamp_mono
        return age <= timeout

    def last_beat(self, component: str) -> Optional[HeartbeatRecord]:
        with self._lock:
            return self._last.get(component)

    def age_seconds(self, component: str) -> Optional[float]:
        """Return seconds since the last heartbeat, or None if never beaten."""
        with self._lock:
            record = self._last.get(component)
        if record is None:
            return None
        return time.monotonic() - record.timestamp_mono

    def status_all(self) -> dict[str, dict[str, Any]]:
        """Return status for all registered components."""
        with self._lock:
            components = list(self._timeouts.keys())

        result = {}
        for comp in components:
            alive = self.is_alive(comp)
            age = self.age_seconds(comp)
            result[comp] = {
                "alive": alive,
                "age_seconds": round(age, 1) if age is not None else None,
                "timeout": self._timeouts.get(comp, self._default_timeout),
                "sequence": self._sequences.get(comp, 0),
            }
        return result

    @property
    def dead_components(self) -> list[str]:
        """Return list of currently dead components."""
        with self._lock:
            return list(self._dead)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_death(self, callback: Callable[[str, float], None]) -> None:
        """Register callback fired when a component stops beating.
        Signature: ``(component_name, age_seconds) -> None``
        """
        with self._lock:
            self._death_callbacks.append(callback)

    def on_recovery(self, callback: Callable[[str], None]) -> None:
        """Register callback fired when a dead component resumes beating."""
        with self._lock:
            self._recovery_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Background monitor
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background heartbeat monitor."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="heartbeat-monitor",
        )
        self._monitor_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=self._check_interval + 1)

    def _monitor_loop(self) -> None:
        while self._running:
            self._scan()
            time.sleep(self._check_interval)

    def _scan(self) -> None:
        """Scan for components that have missed their heartbeat."""
        with self._lock:
            components = list(self._timeouts.items())

        for comp, timeout in components:
            with self._lock:
                record = self._last.get(comp)
            if record is None:
                continue   # Never beaten — not yet registered as dead
            age = time.monotonic() - record.timestamp_mono
            if age > timeout:
                with self._lock:
                    newly_dead = comp not in self._dead
                    self._dead.add(comp)
                if newly_dead:
                    _LOG.warning("Heartbeat MISSED: %s (age=%.1fs, timeout=%ss)", comp, age, timeout)
                    for cb in self._death_callbacks:
                        try:
                            cb(comp, age)
                        except Exception:
                            pass


def get_heartbeat_manager() -> HeartbeatManager:
    """Return (or create) the global ``HeartbeatManager`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = HeartbeatManager()
        return _instance


def _reset_heartbeat_manager() -> None:
    global _instance
    with _instance_lock:
        if _instance is not None:
            _instance.stop()
        _instance = None
