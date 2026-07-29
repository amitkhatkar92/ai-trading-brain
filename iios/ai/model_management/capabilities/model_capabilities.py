"""
model_capabilities.py -- iios.ai.model_management.capabilities
================================================================
:class:`ModelCapabilities` — frozen summary of a model version's capability
set.  Provides capability discovery helpers.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, List

from .capability_type import ModelCapabilityType


@dataclass(frozen=True)
class ModelCapabilities:
    """Immutable wrapper around a capability frozenset with discovery helpers."""
    capabilities: FrozenSet[ModelCapabilityType]

    # ── Discovery ─────────────────────────────────────────────────────────────

    def supports(self, capability: ModelCapabilityType) -> bool:
        return capability in self.capabilities

    def supports_all(self, required: FrozenSet[ModelCapabilityType]) -> bool:
        return required.issubset(self.capabilities)

    def supports_any(self, candidates: FrozenSet[ModelCapabilityType]) -> bool:
        return bool(self.capabilities & candidates)

    def list_all(self) -> List[ModelCapabilityType]:
        return sorted(self.capabilities, key=lambda c: c.value)

    def __contains__(self, item: object) -> bool:
        return item in self.capabilities

    def __len__(self) -> int:
        return len(self.capabilities)
