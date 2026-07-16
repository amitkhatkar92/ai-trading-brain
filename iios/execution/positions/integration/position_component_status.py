"""iios/execution/positions/integration/position_component_status.py
==================================================
ComponentStatus — per-component operational status record.

Immutable value object capturing point-in-time status of a
registered integration component.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class ComponentStatus:
    """
    Immutable snapshot of a single component's operational status.

    Attributes
    ----------
    component_name
        Canonical component identifier (e.g. ``"position_engine"``).
    is_registered
        Whether the component is registered in the ComponentRegistry.
    is_running
        Whether the component lifecycle state is RUNNING.
    is_healthy
        Whether the last health check passed.
    lifecycle_state
        The component's ``EngineState.value`` string at capture time.
    last_checked_at
        Unix timestamp of when this status was captured.
    message
        Optional human-readable note (empty if no issues).
    """

    component_name:  str
    is_registered:   bool
    is_running:      bool
    is_healthy:      bool
    lifecycle_state: str
    last_checked_at: float = field(default_factory=time.time)
    message:         str   = ""

    @property
    def is_ok(self) -> bool:
        """``True`` when the component is registered, running, and healthy."""
        return self.is_registered and self.is_running and self.is_healthy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name":  self.component_name,
            "is_registered":   self.is_registered,
            "is_running":      self.is_running,
            "is_healthy":      self.is_healthy,
            "lifecycle_state": self.lifecycle_state,
            "last_checked_at": self.last_checked_at,
            "message":         self.message,
            "is_ok":           self.is_ok,
        }
