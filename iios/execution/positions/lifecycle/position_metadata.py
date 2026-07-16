"""iios/execution/positions/lifecycle/position_metadata.py
==================================================
PositionMetadata — mutable key-value annotation store attached to
a trading position.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PositionMetadata:
    """
    Mutable metadata bag attached to a trading position.

    Used for tagging, notes, and source attribution.
    Thread safety is the caller's responsibility (Position holds a lock).
    """

    tags:       Dict[str, str] = field(default_factory=dict)
    notes:      str            = ""
    source:     str            = ""
    version:    int            = 1
    created_at: float          = field(default_factory=time.time)
    updated_at: float          = field(default_factory=time.time)

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

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tags":       dict(self.tags),
            "notes":      self.notes,
            "source":     self.source,
            "version":    self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PositionMetadata":
        m            = cls()
        m.tags       = dict(data.get("tags", {}))
        m.notes      = data.get("notes", "")
        m.source     = data.get("source", "")
        m.version    = int(data.get("version", 1))
        m.created_at = float(data.get("created_at", time.time()))
        m.updated_at = float(data.get("updated_at", time.time()))
        return m
