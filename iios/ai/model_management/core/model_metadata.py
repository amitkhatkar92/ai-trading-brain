"""
model_metadata.py -- iios.ai.model_management.core
=====================================================
:class:`ModelMetadata` — immutable identity record for an AI model.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Tuple

from .model_category import ModelCategory
from .model_tier      import ModelTier


@dataclass(frozen=True)
class ModelMetadata:
    """Immutable identity / classification record for a registered AI model."""
    model_id:    str
    name:        str
    category:    ModelCategory
    tier:        ModelTier
    provider_id: str            = ""
    description: str            = ""
    tags:        Tuple[str, ...] = field(default_factory=tuple)
    owner:       str            = ""
    created_at:  float          = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        name:        str,
        category:    ModelCategory,
        *,
        tier:        ModelTier        = ModelTier.STANDARD,
        provider_id: str              = "",
        description: str              = "",
        tags:        Tuple[str, ...]  = (),
        owner:       str              = "",
        model_id:    str              = "",
    ) -> "ModelMetadata":
        return cls(
            model_id    = model_id or str(uuid.uuid4()),
            name        = name,
            category    = category,
            tier        = tier,
            provider_id = provider_id,
            description = description,
            tags        = tuple(tags),
            owner       = owner,
        )
