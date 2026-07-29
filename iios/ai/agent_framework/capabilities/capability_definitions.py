"""
capability_definitions.py -- iios.ai.agent_framework.capabilities
===================================================================
:class:`CapabilityDefinition` — formal schema for one capability type.
:class:`CapabilityRegistry`   — class-level registry of all known definitions.

Pre-registers the eight built-in capability types on module import.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Dict, List, Optional

from ..core.agent_capabilities import CapabilityType
from ..exceptions               import AICapabilityNotFoundError


@dataclass(frozen=True)
class CapabilityDefinition:
    """Formal description of one capability type used by the framework."""

    capability_type: CapabilityType
    name:            str
    description:     str
    input_schema:    Optional[str]   # JSON Schema string or None
    output_schema:   Optional[str]   # JSON Schema string or None
    version:         str


class CapabilityRegistry:
    """
    Class-level registry of :class:`CapabilityDefinition` objects.

    All built-in capability types are pre-registered at module import.
    Extend at runtime via :meth:`register`.
    """

    _definitions: ClassVar[Dict[CapabilityType, CapabilityDefinition]] = {}

    @classmethod
    def register(cls, definition: CapabilityDefinition) -> None:
        """Register or replace a :class:`CapabilityDefinition`."""
        cls._definitions[definition.capability_type] = definition

    @classmethod
    def get(cls, capability_type: CapabilityType) -> CapabilityDefinition:
        """Return the definition for *capability_type*.  Raises if absent."""
        defn = cls._definitions.get(capability_type)
        if defn is None:
            raise AICapabilityNotFoundError(capability_type.value)
        return defn

    @classmethod
    def list_all(cls) -> List[CapabilityDefinition]:
        """Return all registered definitions."""
        return list(cls._definitions.values())

    @classmethod
    def is_registered(cls, capability_type: CapabilityType) -> bool:
        return capability_type in cls._definitions

    @classmethod
    def count(cls) -> int:
        return len(cls._definitions)


# ---------------------------------------------------------------------------
# Built-in capability definitions — pre-registered at module import
# ---------------------------------------------------------------------------

_BUILTIN_DEFINITIONS = [
    CapabilityDefinition(
        capability_type = CapabilityType.ANALYSIS,
        name            = "Analysis",
        description     = "Analyse structured and unstructured data to extract insights.",
        input_schema    = None,
        output_schema   = None,
        version         = "1.0.0",
    ),
    CapabilityDefinition(
        capability_type = CapabilityType.PLANNING,
        name            = "Planning",
        description     = "Decompose objectives into ordered action plans.",
        input_schema    = None,
        output_schema   = None,
        version         = "1.0.0",
    ),
    CapabilityDefinition(
        capability_type = CapabilityType.REASONING,
        name            = "Reasoning",
        description     = "Apply logical or probabilistic inference over domain knowledge.",
        input_schema    = None,
        output_schema   = None,
        version         = "1.0.0",
    ),
    CapabilityDefinition(
        capability_type = CapabilityType.CLASSIFICATION,
        name            = "Classification",
        description     = "Assign items to predefined or learned categories.",
        input_schema    = None,
        output_schema   = None,
        version         = "1.0.0",
    ),
    CapabilityDefinition(
        capability_type = CapabilityType.RESEARCH,
        name            = "Research",
        description     = "Retrieve, synthesise, and summarise relevant information.",
        input_schema    = None,
        output_schema   = None,
        version         = "1.0.0",
    ),
    CapabilityDefinition(
        capability_type = CapabilityType.RECOMMENDATION,
        name            = "Recommendation",
        description     = "Propose ranked options or actions based on evidence.",
        input_schema    = None,
        output_schema   = None,
        version         = "1.0.0",
    ),
    CapabilityDefinition(
        capability_type = CapabilityType.SUMMARIZATION,
        name            = "Summarization",
        description     = "Condense content to its essential points.",
        input_schema    = None,
        output_schema   = None,
        version         = "1.0.0",
    ),
    CapabilityDefinition(
        capability_type = CapabilityType.PREDICTION,
        name            = "Prediction",
        description     = "Forecast future values or outcomes from historical data.",
        input_schema    = None,
        output_schema   = None,
        version         = "1.0.0",
    ),
    CapabilityDefinition(
        capability_type = CapabilityType.CUSTOM,
        name            = "Custom",
        description     = "Extension point for domain-specific capabilities.",
        input_schema    = None,
        output_schema   = None,
        version         = "1.0.0",
    ),
]

for _defn in _BUILTIN_DEFINITIONS:
    CapabilityRegistry.register(_defn)
