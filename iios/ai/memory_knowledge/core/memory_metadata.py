"""
memory_metadata.py -- iios.ai.memory_knowledge.core
=====================================================
:class:`MemoryMetadata` — immutable metadata attached to every
:class:`MemoryEntry`.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import FrozenSet, Optional

from .memory_scope import MemoryScope


@dataclass(frozen=True)
class MemoryMetadata:
    """Immutable metadata for a memory entry."""
    entry_id:    str
    scope:       MemoryScope
    owner_id:    str                  # agent, session, or component ID
    tags:        FrozenSet[str]
    created_at:  float
    updated_at:  float
    expires_at:  Optional[float]      # None = no expiry
    source:      str                  # free-text provenance label
    version:     int                  # incremented on each update

    @classmethod
    def create(
        cls,
        scope:       MemoryScope,
        owner_id:    str              = "system",
        tags:        FrozenSet[str]   = frozenset(),
        expires_at:  Optional[float]  = None,
        source:      str              = "",
        *,
        entry_id:    Optional[str]    = None,
    ) -> "MemoryMetadata":
        now = time.time()
        return cls(
            entry_id   = entry_id or str(uuid.uuid4()),
            scope      = scope,
            owner_id   = owner_id,
            tags       = tags,
            created_at = now,
            updated_at = now,
            expires_at = expires_at,
            source     = source,
            version    = 1,
        )

    def is_expired(self, at: Optional[float] = None) -> bool:
        """Return True if ``expires_at`` is set and in the past."""
        if self.expires_at is None:
            return False
        return (at or time.time()) >= self.expires_at

    def with_update(self) -> "MemoryMetadata":
        """Return a copy with ``updated_at`` = now and ``version`` incremented."""
        return MemoryMetadata(
            entry_id   = self.entry_id,
            scope      = self.scope,
            owner_id   = self.owner_id,
            tags       = self.tags,
            created_at = self.created_at,
            updated_at = time.time(),
            expires_at = self.expires_at,
            source     = self.source,
            version    = self.version + 1,
        )
