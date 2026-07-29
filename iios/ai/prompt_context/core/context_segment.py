"""
context_segment.py -- iios.ai.prompt_context.core
====================================================
:class:`ContextSegment` -- immutable unit of context content contributed
by a single source (system, user, history, retrieval, ...).

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .context_priority import ContextPriority
from .token_estimator   import estimate_tokens


@dataclass(frozen=True)
class ContextSegment:
    """Immutable piece of context content from a single source."""
    segment_id:       str
    source:           str
    content:          str
    priority:         ContextPriority = ContextPriority.NORMAL
    estimated_tokens: int             = 0
    metadata:         Dict[str, Any]  = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source:           str,
        content:          str,
        *,
        priority:         ContextPriority   = ContextPriority.NORMAL,
        estimated_tokens: Optional[int]     = None,
        **metadata: Any,
    ) -> "ContextSegment":
        tokens = estimated_tokens if estimated_tokens is not None else estimate_tokens(content)
        return cls(
            segment_id       = str(uuid.uuid4()),
            source           = source,
            content          = content,
            priority         = priority,
            estimated_tokens = tokens,
            metadata         = dict(metadata),
        )
