"""
skill_interface.py -- iios.ai.capability.skills
=================================================
Interfaces for provider-independent enterprise skills.

Defines:
  - SkillCategory   — enumeration of skill domains
  - SkillDescriptor — immutable skill definition
  - BaseSkill       — abstract interface every skill must implement
  - SkillRegistry   — thread-safe store for skill instances

Skill categories
----------------
CALCULATION, FORMATTING, PARSING, GENERATION, PROCESSING,
VISUALIZATION, TRANSLATION, SUMMARIZATION, CLASSIFICATION, CUSTOM

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional

from ..exceptions.capability_exceptions import AISkillNotFoundError


class SkillCategory(str, Enum):
    """Domain category of a skill."""
    CALCULATION    = "calculation"
    FORMATTING     = "formatting"
    PARSING        = "parsing"
    GENERATION     = "generation"
    PROCESSING     = "processing"
    VISUALIZATION  = "visualization"
    TRANSLATION    = "translation"
    SUMMARIZATION  = "summarization"
    CLASSIFICATION = "classification"
    CUSTOM         = "custom"


@dataclass(frozen=True)
class SkillDescriptor:
    """Immutable, provider-independent description of a skill."""

    skill_id:     str
    name:         str
    category:     SkillCategory
    version:      str
    description:  str
    input_schema:  FrozenSet[str]   # required input parameter names
    output_schema: FrozenSet[str]   # expected output field names

    @classmethod
    def create(
        cls,
        name:          str,
        category:      SkillCategory    = SkillCategory.CUSTOM,
        version:       str              = "1.0.0",
        description:   str              = "",
        input_schema:  Optional[FrozenSet[str]] = None,
        output_schema: Optional[FrozenSet[str]] = None,
    ) -> "SkillDescriptor":
        return cls(
            skill_id      = str(uuid.uuid4()),
            name          = name,
            category      = category,
            version       = version,
            description   = description,
            input_schema  = input_schema  if input_schema  is not None else frozenset(),
            output_schema = output_schema if output_schema is not None else frozenset(),
        )


class BaseSkill(ABC):
    """
    Abstract base class for all enterprise skills.

    All skills are provider-independent interfaces.  The platform calls only
    :meth:`execute` and :meth:`validate_input`; implementations must not
    touch live external services.
    """

    @property
    @abstractmethod
    def skill_id(self) -> str:
        """Unique skill identifier (must match :attr:`SkillDescriptor.skill_id`)."""

    @property
    @abstractmethod
    def skill_descriptor(self) -> SkillDescriptor:
        """Descriptor for this skill instance."""

    @abstractmethod
    def validate_input(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate that *parameters* satisfy the skill's input schema.

        Return True if valid, False otherwise.  Must not raise.
        """

    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> Any:
        """
        Execute the skill with *parameters*.

        Return the skill's output.  Raise :class:`AISkillExecutionError` on failure.
        """


class SkillRegistry:
    """Thread-safe registry of :class:`BaseSkill` instances."""

    def __init__(self) -> None:
        self._lock:  threading.Lock             = threading.Lock()
        self._store: Dict[str, BaseSkill]        = {}

    def register(self, skill: BaseSkill) -> None:
        with self._lock:
            self._store[skill.skill_id] = skill

    def deregister(self, skill_id: str) -> None:
        with self._lock:
            if skill_id not in self._store:
                raise AISkillNotFoundError(f"Skill '{skill_id}' not found")
            del self._store[skill_id]

    def get(self, skill_id: str) -> BaseSkill:
        with self._lock:
            s = self._store.get(skill_id)
        if s is None:
            raise AISkillNotFoundError(f"Skill '{skill_id}' not found")
        return s

    def get_optional(self, skill_id: str) -> Optional[BaseSkill]:
        with self._lock:
            return self._store.get(skill_id)

    def list_skills(
        self,
        category: Optional[SkillCategory] = None,
    ) -> List[BaseSkill]:
        with self._lock:
            skills = list(self._store.values())
        if category is not None:
            skills = [s for s in skills if s.skill_descriptor.category == category]
        return skills

    def count(self) -> int:
        with self._lock:
            return len(self._store)
