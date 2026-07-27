"""
session_metadata.py -- iios.ai.foundation.session
==================================================
Immutable metadata attached to every AI session at creation time.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class SessionMetadata:
    """
    Immutable descriptor attached to an :class:`AISession` at creation.

    Fields
    ------
    session_id :    Unique session identifier (UUID4).
    module_id :     Originating AI module (e.g. ``"iios:ai:a3:context"``).
    trace_id :      Distributed trace identifier (links to caller's span).
    user_id :       Optional caller / strategy identifier.
    priority :      Request priority string (``"critical"`` | ``"high"`` | ``"normal"`` | ``"low"``).
    ttl_s :         Session time-to-live in seconds (0 = no expiry).
    created_at :    Wall-clock creation time.
    capability :    Required AI capability string.
    tags :          Caller-supplied string key-value tags.
    """
    session_id: str
    module_id:  str
    trace_id:   str
    created_at: float
    priority:   str              = "normal"
    user_id:    str              = ""
    ttl_s:      float            = 300.0
    capability: str              = "completion"
    tags:       Dict[str, str]   = field(default_factory=dict)
    schema:     str              = SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        module_id:  str,
        *,
        priority:   str            = "normal",
        user_id:    str            = "",
        ttl_s:      float          = 300.0,
        capability: str            = "completion",
        trace_id:   str            = "",
        **tags: str,
    ) -> "SessionMetadata":
        """Convenience factory -- auto-generates session_id and trace_id."""
        return cls(
            session_id = str(uuid.uuid4()),
            module_id  = module_id,
            trace_id   = trace_id or str(uuid.uuid4()),
            created_at = time.time(),
            priority   = priority,
            user_id    = user_id,
            ttl_s      = ttl_s,
            capability = capability,
            tags       = dict(tags),
        )

    @property
    def expires_at(self) -> Optional[float]:
        """Expiry wall-clock time, or ``None`` if ``ttl_s == 0``."""
        if self.ttl_s <= 0:
            return None
        return self.created_at + self.ttl_s

    def is_expired(self) -> bool:
        """Return ``True`` iff the session has exceeded its TTL."""
        exp = self.expires_at
        return exp is not None and time.time() > exp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "module_id":  self.module_id,
            "trace_id":   self.trace_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "priority":   self.priority,
            "user_id":    self.user_id,
            "ttl_s":      self.ttl_s,
            "capability": self.capability,
            "tags":       self.tags,
        }
