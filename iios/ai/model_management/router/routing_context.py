"""
routing_context.py -- iios.ai.model_management.router
=======================================================
:class:`RoutingContext` — immutable specification of what a caller needs
from the router.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Optional

from ..capabilities.capability_type import ModelCapabilityType
from ..core.model_tier               import ModelTier


@dataclass(frozen=True)
class RoutingContext:
    """
    Immutable routing request.  All fields are optional — an empty context
    routes to any enabled, healthy model.
    """
    required_capabilities: FrozenSet[ModelCapabilityType] = field(default_factory=frozenset)
    preferred_tier:        Optional[ModelTier]             = None
    exclude_model_ids:     FrozenSet[str]                  = field(default_factory=frozenset)
    max_latency_ms:        Optional[int]                   = None
    session_id:            str                             = ""
    trace_id:              str                             = ""

    @classmethod
    def for_capability(cls, *capabilities: ModelCapabilityType, **kwargs) -> "RoutingContext":
        """Convenience factory requiring specific capabilities."""
        return cls(required_capabilities=frozenset(capabilities), **kwargs)
