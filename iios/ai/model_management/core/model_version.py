"""
model_version.py -- iios.ai.model_management.core
===================================================
:class:`AIModelVersion` — immutable snapshot of a model at a specific version.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import FrozenSet, TYPE_CHECKING

from .model_descriptor import AIModelDescriptor

if TYPE_CHECKING:
    from ..capabilities.capability_type import ModelCapabilityType


@dataclass(frozen=True)
class AIModelVersion:
    """Immutable record of a model at a specific version point."""
    version_id:     str
    model_id:       str
    version_number: int
    descriptor:     AIModelDescriptor
    active:         bool
    created_at:     float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        model_id:    str,
        version_number: int,
        capabilities: FrozenSet["ModelCapabilityType"],
        *,
        context_window:      int   = 4_096,
        max_output_tokens:   int   = 1_024,
        parameters_billions: float = 0.0,
        active:              bool  = True,
    ) -> "AIModelVersion":
        descriptor = AIModelDescriptor.create(
            model_id,
            frozenset(capabilities),
            context_window=context_window,
            max_output_tokens=max_output_tokens,
            parameters_billions=parameters_billions,
        )
        return cls(
            version_id     = str(uuid.uuid4()),
            model_id       = model_id,
            version_number = version_number,
            descriptor     = descriptor,
            active         = active,
        )

    def with_active(self, active: bool) -> "AIModelVersion":
        """Return a copy with ``active`` changed."""
        return AIModelVersion(
            version_id     = self.version_id,
            model_id       = self.model_id,
            version_number = self.version_number,
            descriptor     = self.descriptor,
            active         = active,
            created_at     = self.created_at,
        )
