"""
ai_foundation_session.py — iios.ai.foundation.lifecycle
========================================================
AI Foundation session domain object.

An AIFoundationSession represents a single bounded context for one
AI operation or agent run within the foundation lifecycle.

A1 AI Foundation — Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import AILifecycleState, SCHEMA_VERSION, VERSION


@dataclass
class AIFoundationSession:
    """
    Mutable session object representing one AI operation context.

    Held internally by the lifecycle registry.  Not exposed outside M1.
    """
    session_id:   str
    module_id:    str
    created_at:   float
    state:        AILifecycleState = AILifecycleState.CREATED
    updated_at:   float            = field(default_factory=time.time)
    metadata:     Dict[str, Any]   = field(default_factory=dict)
    error:        Optional[str]    = None
    version:      str              = VERSION
    schema:       str              = SCHEMA_VERSION

    @classmethod
    def create(cls, module_id: str, **metadata: Any) -> "AIFoundationSession":
        """Create a new session for the given module."""
        now = time.time()
        return cls(
            session_id = str(uuid.uuid4()),
            module_id  = module_id,
            created_at = now,
            updated_at = now,
            metadata   = dict(metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "module_id":  self.module_id,
            "state":      self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error":      self.error,
            "version":    self.version,
            "schema":     self.schema,
        }
