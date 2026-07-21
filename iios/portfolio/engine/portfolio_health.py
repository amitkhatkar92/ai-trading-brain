"""
portfolio_health.py — iios.portfolio.engine
============================================
Subsystem health tracking for the Portfolio Engine.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SubsystemHealthRecord:
    """
    Immutable health record for a single subsystem.

    Fields
    ------
    name :          Subsystem identifier.
    is_available :  True if the subsystem is responding normally.
    last_checked :  Wall-clock time of the last health check.
    latency_ms :    Last observed latency in milliseconds.
    error :         Non-empty if the subsystem reported an error.
    """
    name:          str
    is_available:  bool
    last_checked:  float = field(default_factory=time.time)
    latency_ms:    float = 0.0
    error:         str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":         self.name,
            "is_available": self.is_available,
            "last_checked": self.last_checked,
            "latency_ms":   self.latency_ms,
            "error":        self.error,
        }


class PortfolioEngineHealth:
    """
    Tracks and reports subsystem availability for the Portfolio Engine.

    Maintains a live register of named subsystems and their latest
    :class:`SubsystemHealthRecord`.

    Built-in subsystem names:
    - ``lifecycle``
    - ``scheduler``
    - ``dispatcher``
    - ``registry``
    - ``validator``

    Usage
    -----
    ::

        health = PortfolioEngineHealth()
        health.report("lifecycle", is_available=True, latency_ms=1.2)
        if health.is_healthy():
            ...
    """

    _CORE_SUBSYSTEMS = ("lifecycle", "scheduler", "dispatcher", "registry", "validator")

    def __init__(self) -> None:
        self._lock      = threading.Lock()
        self._records:  Dict[str, SubsystemHealthRecord] = {}
        # Initialise all core subsystems as available
        for name in self._CORE_SUBSYSTEMS:
            self._records[name] = SubsystemHealthRecord(
                name         = name,
                is_available = True,
            )

    def report(
        self,
        name:         str,
        *,
        is_available: bool  = True,
        latency_ms:   float = 0.0,
        error:        str   = "",
    ) -> None:
        """Record a health observation for a named subsystem."""
        with self._lock:
            self._records[name] = SubsystemHealthRecord(
                name         = name,
                is_available = is_available,
                latency_ms   = latency_ms,
                error        = error,
            )

    def get(self, name: str) -> Optional[SubsystemHealthRecord]:
        with self._lock:
            return self._records.get(name)

    def is_healthy(self) -> bool:
        """Return True iff all registered subsystems are available."""
        with self._lock:
            return all(r.is_available for r in self._records.values())

    def unavailable_subsystems(self) -> list:
        with self._lock:
            return [name for name, r in self._records.items() if not r.is_available]

    def subsystem_availability(self) -> Dict[str, bool]:
        with self._lock:
            return {name: r.is_available for name, r in self._records.items()}

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_healthy":   all(r.is_available for r in self._records.values()),
                "subsystems":   {name: r.to_dict() for name, r in self._records.items()},
                "checked_at":   time.time(),
            }
