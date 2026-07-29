"""
context_metadata.py -- iios.ai.prompt_context.core
=====================================================
:class:`ContextMetadata` -- immutable descriptor for an assembled
context (identity, ownership, token budget).

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ContextMetadata:
    """Immutable metadata describing an assembled context's origin and budget."""
    context_id:  str
    session_id:  str
    module_id:   str
    trace_id:    str
    max_tokens:  int   = 8_192
    created_at:  float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        session_id: str,
        module_id:  str,
        *,
        trace_id:   str            = "",
        max_tokens: int            = 8_192,
        context_id: Optional[str]  = None,
    ) -> "ContextMetadata":
        return cls(
            context_id = context_id or str(uuid.uuid4()),
            session_id = session_id,
            module_id  = module_id,
            trace_id   = trace_id or str(uuid.uuid4()),
            max_tokens = max_tokens,
            created_at = time.time(),
        )
