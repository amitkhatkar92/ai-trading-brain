"""
ai_context.py -- iios.ai.foundation.context
============================================
:class:`AIContext` -- mutable context object assembled before an AI call.

A context holds an ordered list of messages (system prompt, retrieved
documents, conversation history, user query) and tracks estimated token
usage.  The context is passed as a parameter -- no module pulls context
by reaching into another module.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .context_metadata import ContextMetadata
from ..exceptions       import AIContextTooLargeError


@dataclass
class ContextEntry:
    """A single message entry in an AIContext."""
    role:             str          # "system" | "user" | "assistant" | "tool"
    content:          str
    label:            str          = ""      # source label (e.g. "system_prompt")
    estimated_tokens: int          = 0
    metadata:         Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role":             self.role,
            "content":          self.content,
            "label":            self.label,
            "estimated_tokens": self.estimated_tokens,
        }


class AIContext:
    """
    Mutable AI operation context -- a sequence of :class:`ContextEntry` objects.

    Built by :class:`ContextBuilder`; validated by :class:`ContextValidator`.

    Thread-safe: multiple pipeline stages may read concurrently.

    Parameters
    ----------
    metadata : Immutable context descriptor (created by :class:`ContextBuilder`).
    """

    def __init__(self, metadata: ContextMetadata) -> None:
        self._metadata: ContextMetadata    = metadata
        self._entries:  List[ContextEntry] = []
        self._lock:     threading.RLock    = threading.RLock()
        self._total_estimated_tokens: int  = 0
        self._extra:    Dict[str, Any]     = {}   # arbitrary attached data

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def context_id(self) -> str:
        return self._metadata.context_id

    @property
    def session_id(self) -> str:
        return self._metadata.session_id

    @property
    def metadata(self) -> ContextMetadata:
        return self._metadata

    @property
    def max_tokens(self) -> int:
        return self._metadata.max_tokens

    @property
    def estimated_tokens(self) -> int:
        with self._lock:
            return self._total_estimated_tokens

    @property
    def is_within_budget(self) -> bool:
        return self.estimated_tokens <= self.max_tokens

    # ── Entry management ──────────────────────────────────────────────────────

    def add_entry(
        self,
        role:             str,
        content:          str,
        *,
        label:            str  = "",
        estimated_tokens: int  = 0,
        **metadata: Any,
    ) -> None:
        """Append a message entry to this context."""
        entry = ContextEntry(
            role             = role,
            content          = content,
            label            = label,
            estimated_tokens = estimated_tokens,
            metadata         = dict(metadata),
        )
        with self._lock:
            self._entries.append(entry)
            self._total_estimated_tokens += estimated_tokens

    def add_system(self, content: str, *, estimated_tokens: int = 0) -> None:
        self.add_entry("system", content, label="system_prompt", estimated_tokens=estimated_tokens)

    def add_user(self, content: str, *, label: str = "user_query", estimated_tokens: int = 0) -> None:
        self.add_entry("user", content, label=label, estimated_tokens=estimated_tokens)

    def add_assistant(self, content: str, *, label: str = "assistant", estimated_tokens: int = 0) -> None:
        self.add_entry("assistant", content, label=label, estimated_tokens=estimated_tokens)

    def add_retrieved(self, content: str, *, label: str = "retrieved", estimated_tokens: int = 0) -> None:
        self.add_entry("user", content, label=label, estimated_tokens=estimated_tokens)

    def remove_last(self) -> Optional[ContextEntry]:
        """Remove and return the last entry (used by compressor)."""
        with self._lock:
            if not self._entries:
                return None
            entry = self._entries.pop()
            self._total_estimated_tokens -= entry.estimated_tokens
            return entry

    # ── Merge ─────────────────────────────────────────────────────────────────

    def merge(self, other: "AIContext") -> None:
        """Append all entries from ``other`` into this context."""
        with other._lock:
            entries = list(other._entries)
        for e in entries:
            self.add_entry(
                e.role,
                e.content,
                label            = e.label,
                estimated_tokens = e.estimated_tokens,
                **e.metadata,
            )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_messages(self) -> List[Dict[str, str]]:
        """Return entries as a list of {role, content} dicts (provider format)."""
        with self._lock:
            return [{"role": e.role, "content": e.content} for e in self._entries]

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "context_id":       self._metadata.context_id,
                "session_id":       self._metadata.session_id,
                "entry_count":      len(self._entries),
                "estimated_tokens": self._total_estimated_tokens,
                "max_tokens":       self._metadata.max_tokens,
                "within_budget":    self.is_within_budget,
                "metadata":         self._metadata.to_dict(),
            }

    def entries(self) -> List[ContextEntry]:
        """Return a snapshot copy of all entries."""
        with self._lock:
            return list(self._entries)

    # ── Extra data ────────────────────────────────────────────────────────────

    def set_extra(self, key: str, value: Any) -> None:
        with self._lock:
            self._extra[key] = value

    def get_extra(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._extra.get(key, default)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def __repr__(self) -> str:
        return (
            f"<AIContext id={self.context_id!r} "
            f"entries={len(self._entries)} "
            f"tokens={self._total_estimated_tokens}/{self.max_tokens}>"
        )
