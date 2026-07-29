"""
prompt_metadata.py -- iios.ai.prompt_context.core
====================================================
:class:`PromptMetadata` -- immutable descriptor for a registered prompt
template (identity, category, description, tags, owner).

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .prompt_category import PromptCategory


@dataclass(frozen=True)
class PromptMetadata:
    """Immutable metadata describing a prompt template's identity."""
    prompt_id:   str
    name:        str
    category:    PromptCategory
    description: str            = ""
    tags:        Tuple[str, ...] = field(default_factory=tuple)
    owner:       str            = ""
    created_at:  float          = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        name:        str,
        category:    PromptCategory,
        *,
        description: str                = "",
        tags:        Tuple[str, ...]     = (),
        owner:       str                = "",
        prompt_id:   Optional[str]       = None,
    ) -> "PromptMetadata":
        return cls(
            prompt_id   = prompt_id or str(uuid.uuid4()),
            name        = name,
            category    = category,
            description = description,
            tags        = tuple(tags),
            owner       = owner,
            created_at  = time.time(),
        )
