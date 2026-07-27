"""
context_metadata.py -- iios.ai.foundation.context
===================================================
Immutable metadata for an :class:`AIContext`.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ContextMetadata:
    """
    Immutable descriptor for one AI context assembly.

    Fields
    ------
    context_id :       Unique context identifier.
    session_id :       Originating session.
    module_id :        Module that built this context.
    trace_id :         Distributed trace identifier.
    capability :       Required AI capability.
    max_tokens :       Hard token budget for this context.
    created_at :       Wall-clock creation time.
    source_labels :    Ordered list of content source labels added.
    compression_applied : Whether context was compressed to fit budget.
    tags :             Caller-supplied string key-value tags.
    """
    context_id:           str
    session_id:           str
    module_id:            str
    trace_id:             str
    capability:           str
    max_tokens:           int
    created_at:           float
    source_labels:        tuple[str, ...]     = field(default_factory=tuple)
    compression_applied:  bool                = False
    tags:                 Dict[str, str]      = field(default_factory=dict)
    schema:               str                 = SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        session_id: str,
        module_id:  str,
        *,
        trace_id:   str  = "",
        capability: str  = "completion",
        max_tokens: int  = 8_192,
        **tags: str,
    ) -> "ContextMetadata":
        return cls(
            context_id  = str(uuid.uuid4()),
            session_id  = session_id,
            module_id   = module_id,
            trace_id    = trace_id or str(uuid.uuid4()),
            capability  = capability,
            max_tokens  = max_tokens,
            created_at  = time.time(),
            tags        = dict(tags),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":          self.context_id,
            "session_id":          self.session_id,
            "module_id":           self.module_id,
            "trace_id":            self.trace_id,
            "capability":          self.capability,
            "max_tokens":          self.max_tokens,
            "created_at":          self.created_at,
            "source_labels":       list(self.source_labels),
            "compression_applied": self.compression_applied,
            "tags":                self.tags,
        }
