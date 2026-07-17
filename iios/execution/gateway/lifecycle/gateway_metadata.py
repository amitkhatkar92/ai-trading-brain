"""iios/execution/gateway/lifecycle/gateway_metadata.py
==================================================
GatewayMetadata — mutable key-value annotation store attached to
an execution gateway request.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GatewayMetadata:
    """
    Mutable metadata bag attached to a gateway request.

    Used for tagging, routing attribution, priority, and source annotation.
    Thread safety is the caller's responsibility (GatewayRequest holds a lock).
    """

    tags:      Dict[str, str] = field(default_factory=dict)
    notes:     str            = ""
    source:    str            = ""
    priority:  int            = 0
    actor:     str            = ""
    version:   int            = 1
    created_at: float         = field(default_factory=time.time)
    updated_at: float         = field(default_factory=time.time)

    # ── Tag helpers ───────────────────────────────────────────────────────────

    def set_tag(self, key: str, value: str) -> None:
        """Set or overwrite a tag."""
        self.tags[key]   = value
        self.updated_at  = time.time()
        self.version    += 1

    def remove_tag(self, key: str) -> None:
        """Remove a tag; no-op if the key does not exist."""
        if key in self.tags:
            del self.tags[key]
            self.updated_at  = time.time()
            self.version    += 1

    def get_tag(self, key: str, default: str = "") -> str:
        return self.tags.get(key, default)

    def has_tag(self, key: str) -> bool:
        return key in self.tags

    # ── Notes helper ──────────────────────────────────────────────────────────

    def set_notes(self, notes: str) -> None:
        self.notes      = notes
        self.updated_at = time.time()
        self.version   += 1

    def set_priority(self, priority: int) -> None:
        """Set the request dispatch priority (higher is more urgent)."""
        self.priority   = priority
        self.updated_at = time.time()
        self.version   += 1

    def set_source(self, source: str) -> None:
        """Record the originating component or actor."""
        self.source     = source
        self.updated_at = time.time()
        self.version   += 1

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tags":       dict(self.tags),
            "notes":      self.notes,
            "source":     self.source,
            "priority":   self.priority,
            "actor":      self.actor,
            "version":    self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GatewayMetadata":
        obj = cls(
            tags=dict(data.get("tags", {})),
            notes=data.get("notes", ""),
            source=data.get("source", ""),
            priority=data.get("priority", 0),
            actor=data.get("actor", ""),
            version=data.get("version", 1),
        )
        obj.created_at = data.get("created_at", obj.created_at)
        obj.updated_at = data.get("updated_at", obj.updated_at)
        return obj
