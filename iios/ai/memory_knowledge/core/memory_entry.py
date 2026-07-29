"""
memory_entry.py -- iios.ai.memory_knowledge.core
=================================================
:class:`MemoryEntry` — the fundamental unit of memory in A4.

Each entry holds arbitrary ``content`` (any serialisable value) together
with immutable :class:`MemoryMetadata`.  Entries are immutable by design;
"updating" an entry yields a new entry with incremented version.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, FrozenSet, Optional

from .memory_metadata import MemoryMetadata
from .memory_scope    import MemoryScope


@dataclass(frozen=True)
class MemoryEntry:
    """Immutable unit of stored memory."""
    metadata: MemoryMetadata
    content:  Any            # Any JSON-serialisable payload

    # ── Convenience aliases ───────────────────────────────────────────────────

    @property
    def entry_id(self) -> str:
        return self.metadata.entry_id

    @property
    def scope(self) -> MemoryScope:
        return self.metadata.scope

    @property
    def owner_id(self) -> str:
        return self.metadata.owner_id

    @property
    def tags(self) -> FrozenSet[str]:
        return self.metadata.tags

    @property
    def created_at(self) -> float:
        return self.metadata.created_at

    @property
    def expires_at(self) -> Optional[float]:
        return self.metadata.expires_at

    def is_expired(self) -> bool:
        return self.metadata.is_expired()

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        content:     Any,
        scope:       MemoryScope        = MemoryScope.SESSION,
        owner_id:    str                = "system",
        tags:        FrozenSet[str]     = frozenset(),
        expires_at:  Optional[float]    = None,
        source:      str                = "",
        *,
        entry_id:    Optional[str]      = None,
    ) -> "MemoryEntry":
        meta = MemoryMetadata.create(
            scope      = scope,
            owner_id   = owner_id,
            tags       = tags,
            expires_at = expires_at,
            source     = source,
            entry_id   = entry_id,
        )
        return cls(metadata=meta, content=content)

    def with_content(self, new_content: Any) -> "MemoryEntry":
        """Return a new entry with updated content and incremented version."""
        return MemoryEntry(
            metadata = self.metadata.with_update(),
            content  = new_content,
        )
