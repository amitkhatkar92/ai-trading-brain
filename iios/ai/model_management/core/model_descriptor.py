"""
model_descriptor.py -- iios.ai.model_management.core
======================================================
:class:`AIModelDescriptor` — immutable description of a model version's
technical capabilities and constraints.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import FrozenSet, TYPE_CHECKING

if TYPE_CHECKING:
    from ..capabilities.capability_type import ModelCapabilityType


@dataclass(frozen=True)
class AIModelDescriptor:
    """
    Immutable specification of what an AI model version can do.

    ``capabilities`` is a frozenset of :class:`ModelCapabilityType` values
    so it is hashable and safe to use in sets/dict-keys.
    """
    descriptor_id:        str
    model_id:             str
    capabilities:         FrozenSet["ModelCapabilityType"]
    context_window:       int   = 4_096
    max_output_tokens:    int   = 1_024
    parameters_billions:  float = 0.0   # abstract size hint — provider-independent

    @classmethod
    def create(
        cls,
        model_id:            str,
        capabilities:        FrozenSet["ModelCapabilityType"],
        *,
        context_window:      int   = 4_096,
        max_output_tokens:   int   = 1_024,
        parameters_billions: float = 0.0,
    ) -> "AIModelDescriptor":
        return cls(
            descriptor_id       = str(uuid.uuid4()),
            model_id            = model_id,
            capabilities        = frozenset(capabilities),
            context_window      = context_window,
            max_output_tokens   = max_output_tokens,
            parameters_billions = parameters_billions,
        )
