"""
platform_registry.py — iios.ai.platform
=========================================
Thread-safe registry mapping platform_id → descriptor + gateway + phase.

F0.1 Critical Architecture Resolution — R-001 Platform Bootstrap
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple

from .platform_types import PlatformDescriptor, PlatformPhase

__all__ = ["PlatformRegistry", "PlatformRegistryError"]


class PlatformRegistryError(RuntimeError):
    """Raised on invalid :class:`PlatformRegistry` operations."""


class PlatformRegistry:
    """
    Thread-safe store of registered platforms.

    Each entry tracks:
    - a :class:`PlatformDescriptor` (immutable)
    - an optional gateway object (the live ``AILifecycleAwareMixin`` instance)
    - a mutable :class:`PlatformPhase` updated by the coordinators

    Usage::

        registry = PlatformRegistry()
        registry.register(PlatformDescriptor.create("A1:foundation"), gateway)
        registry.set_phase("A1:foundation", PlatformPhase.RUNNING)
        phase = registry.get_phase("A1:foundation")
    """

    def __init__(self) -> None:
        self._lock:        threading.RLock               = threading.RLock()
        self._descriptors: Dict[str, PlatformDescriptor] = {}
        self._gateways:    Dict[str, Any]                = {}
        self._phases:      Dict[str, PlatformPhase]      = {}

    # ── registration ──────────────────────────────────────────────────────────

    def register(
        self,
        descriptor: PlatformDescriptor,
        gateway:    Any = None,
    ) -> None:
        """Register a platform descriptor and optional gateway.

        Raises :class:`PlatformRegistryError` if the platform_id is already
        registered.
        """
        with self._lock:
            pid = descriptor.platform_id
            if pid in self._descriptors:
                raise PlatformRegistryError(
                    f"Platform already registered: {pid!r}"
                )
            self._descriptors[pid] = descriptor
            self._gateways[pid]    = gateway
            self._phases[pid]      = PlatformPhase.REGISTERED

    def deregister(self, platform_id: str) -> None:
        """Remove a platform entry.

        Raises :class:`PlatformRegistryError` if not found.
        """
        with self._lock:
            self._require(platform_id)
            del self._descriptors[platform_id]
            del self._gateways[platform_id]
            del self._phases[platform_id]

    # ── query ─────────────────────────────────────────────────────────────────

    def get_descriptor(self, platform_id: str) -> PlatformDescriptor:
        with self._lock:
            self._require(platform_id)
            return self._descriptors[platform_id]

    def get_gateway(self, platform_id: str) -> Any:
        with self._lock:
            self._require(platform_id)
            return self._gateways[platform_id]

    def get_phase(self, platform_id: str) -> PlatformPhase:
        with self._lock:
            self._require(platform_id)
            return self._phases[platform_id]

    def set_phase(self, platform_id: str, phase: PlatformPhase) -> None:
        with self._lock:
            self._require(platform_id)
            self._phases[platform_id] = phase

    def is_registered(self, platform_id: str) -> bool:
        with self._lock:
            return platform_id in self._descriptors

    def list_ids(self) -> List[str]:
        """Return all registered platform IDs in insertion order."""
        with self._lock:
            return list(self._descriptors.keys())

    def list_all(self) -> List[Tuple[PlatformDescriptor, PlatformPhase]]:
        """Return (descriptor, phase) pairs for all registered platforms."""
        with self._lock:
            return [
                (self._descriptors[pid], self._phases[pid])
                for pid in self._descriptors
            ]

    def all_phases(self) -> Dict[str, PlatformPhase]:
        """Return a snapshot dict of platform_id → phase."""
        with self._lock:
            return dict(self._phases)

    # ── internal ──────────────────────────────────────────────────────────────

    def _require(self, platform_id: str) -> None:
        if platform_id not in self._descriptors:
            raise PlatformRegistryError(
                f"Platform not registered: {platform_id!r}"
            )
