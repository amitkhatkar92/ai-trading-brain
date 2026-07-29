"""
capability_registry.py -- iios.ai.capability.registry
=======================================================
:class:`CapabilityRegistry` — thread-safe CRUD + discovery store.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import threading
from typing import Dict, FrozenSet, List, Optional

from ..core.capability_descriptor import CapabilityDescriptor
from ..core.capability_types      import CapabilityCategory, CapabilityStatus, CapabilityType
from ..exceptions.capability_exceptions import (
    AICapabilityAlreadyExistsError,
    AICapabilityNotFoundError,
)


class CapabilityRegistry:
    """
    Thread-safe store for :class:`CapabilityDescriptor` objects.

    Supports CRUD, enable/disable, and discovery by type/category/tags.
    """

    def __init__(self) -> None:
        self._lock:        threading.Lock                          = threading.Lock()
        self._store:       Dict[str, CapabilityDescriptor]         = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, descriptor: CapabilityDescriptor) -> None:
        """Register a capability descriptor.

        Raises :class:`AICapabilityAlreadyExistsError` on duplicate *descriptor_id*.
        """
        with self._lock:
            if descriptor.descriptor_id in self._store:
                raise AICapabilityAlreadyExistsError(
                    f"Capability '{descriptor.descriptor_id}' is already registered"
                )
            self._store[descriptor.descriptor_id] = descriptor

    def deregister(self, capability_id: str) -> None:
        """Remove a capability from the registry."""
        with self._lock:
            if capability_id not in self._store:
                raise AICapabilityNotFoundError(
                    f"Capability '{capability_id}' not found"
                )
            del self._store[capability_id]

    def get(self, capability_id: str) -> CapabilityDescriptor:
        """Return descriptor by ID; raises if not found."""
        with self._lock:
            d = self._store.get(capability_id)
        if d is None:
            raise AICapabilityNotFoundError(
                f"Capability '{capability_id}' not found"
            )
        return d

    def get_optional(self, capability_id: str) -> Optional[CapabilityDescriptor]:
        with self._lock:
            return self._store.get(capability_id)

    # ── enable / disable ─────────────────────────────────────────────────────

    def enable(self, capability_id: str) -> None:
        """Set capability status to ACTIVE."""
        with self._lock:
            d = self._store.get(capability_id)
            if d is None:
                raise AICapabilityNotFoundError(f"Capability '{capability_id}' not found")
            self._store[capability_id] = d.with_status(CapabilityStatus.ACTIVE)

    def disable(self, capability_id: str) -> None:
        """Set capability status to DISABLED."""
        with self._lock:
            d = self._store.get(capability_id)
            if d is None:
                raise AICapabilityNotFoundError(f"Capability '{capability_id}' not found")
            self._store[capability_id] = d.with_status(CapabilityStatus.DISABLED)

    # ── discovery ─────────────────────────────────────────────────────────────

    def discover(
        self,
        capability_type: Optional[CapabilityType]     = None,
        category:        Optional[CapabilityCategory] = None,
        tags:            Optional[FrozenSet[str]]      = None,
        active_only:     bool                          = False,
    ) -> List[CapabilityDescriptor]:
        """Return capabilities matching all provided filters."""
        with self._lock:
            results = list(self._store.values())

        if capability_type is not None:
            results = [d for d in results if d.capability_type == capability_type]
        if category is not None:
            results = [d for d in results if d.category == category]
        if tags is not None and len(tags) > 0:
            results = [d for d in results if tags.issubset(d.metadata.tags)]
        if active_only:
            results = [d for d in results if d.is_executable()]

        return results

    def list_all(self) -> List[CapabilityDescriptor]:
        with self._lock:
            return list(self._store.values())

    def list_active(self) -> List[CapabilityDescriptor]:
        return self.discover(active_only=True)

    def count(self) -> int:
        with self._lock:
            return len(self._store)
