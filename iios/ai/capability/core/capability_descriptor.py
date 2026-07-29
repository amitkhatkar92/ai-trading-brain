"""
capability_descriptor.py -- iios.ai.capability.core
=====================================================
:class:`CapabilityDescriptor` — the central definition object for any
capability registered in the Enterprise Capability Platform.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional

from .capability_metadata import CapabilityMetadata, CapabilityVersion
from .capability_types    import CapabilityCategory, CapabilityStatus, CapabilityType


@dataclass(frozen=True)
class CapabilityDescriptor:
    """
    Immutable, provider-independent description of a single capability.

    The descriptor acts as the registry entry; actual execution logic is
    injected via :class:`~iios.ai.capability.engine.CapabilityExecutor`.
    """

    descriptor_id:    str
    capability_type:  CapabilityType
    category:         CapabilityCategory
    name:             str
    version:          CapabilityVersion
    metadata:         CapabilityMetadata
    status:           CapabilityStatus
    requires_auth:    bool
    timeout_seconds:  float
    max_retries:      int
    input_schema:     FrozenSet[str]   # required input parameter names
    output_schema:    FrozenSet[str]   # expected output field names

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name:            str,
        capability_type: CapabilityType               = CapabilityType.TOOL,
        category:        CapabilityCategory           = CapabilityCategory.CUSTOM,
        version:         Optional[CapabilityVersion]  = None,
        description:     str                          = "",
        author:          str                          = "",
        tags:            Optional[FrozenSet[str]]     = None,
        requires_auth:   bool                         = True,
        timeout_seconds: float                        = 30.0,
        max_retries:     int                          = 0,
        input_schema:    Optional[FrozenSet[str]]     = None,
        output_schema:   Optional[FrozenSet[str]]     = None,
        status:          CapabilityStatus             = CapabilityStatus.ACTIVE,
    ) -> "CapabilityDescriptor":
        return cls(
            descriptor_id   = str(uuid.uuid4()),
            capability_type = capability_type,
            category        = category,
            name            = name,
            version         = version if version is not None else CapabilityVersion.create(),
            metadata        = CapabilityMetadata.create(name, description, author, tags),
            status          = status,
            requires_auth   = requires_auth,
            timeout_seconds = timeout_seconds,
            max_retries     = max_retries,
            input_schema    = input_schema  if input_schema  is not None else frozenset(),
            output_schema   = output_schema if output_schema is not None else frozenset(),
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def is_executable(self) -> bool:
        """True when the capability is in ACTIVE status."""
        return self.status.is_executable()

    def with_status(self, status: CapabilityStatus) -> "CapabilityDescriptor":
        """Return a new descriptor with an updated status (bypass frozen)."""
        import dataclasses
        return dataclasses.replace(self, status=status)
