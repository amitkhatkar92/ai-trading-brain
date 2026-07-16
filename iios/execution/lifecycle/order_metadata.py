"""iios/execution/lifecycle/order_metadata.py
==================================================
OrderMetadata — mutable extended attributes for an Order.

Metadata does not participate in the state machine.
It carries informational context (source system, tags,
free-text notes, custom key-value pairs) and a monotonic
version counter that increments on every change.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, FrozenSet


@dataclass
class OrderMetadata:
    """
    Mutable informational metadata attached to every Order.

    Parameters
    ----------
    source : str
        System or component that created the order
        (e.g. "order_factory", "strategy_engine").
    tags : frozenset[str]
        Immutable label set (replaced, never mutated in-place).
    notes : str
        Free-form human-readable annotation.
    version : int
        Monotonically increasing edit counter, starting at 1.
    created_at : float
        Unix timestamp of initial creation.
    updated_at : float
        Unix timestamp of most recent change.
    custom : dict[str, Any]
        Arbitrary key-value extension.
    """
    source:     str
    tags:       FrozenSet[str] = field(default_factory=frozenset)
    notes:      str            = ""
    version:    int            = 1
    created_at: float          = field(default_factory=time.time)
    updated_at: float          = field(default_factory=time.time)
    custom:     dict[str, Any] = field(default_factory=dict)

    def bump_version(self, now: float | None = None) -> None:
        """Increment version and update updated_at.  Called by the Order."""
        self.version   += 1
        self.updated_at = now if now is not None else time.time()

    def add_tag(self, tag: str) -> None:
        self.tags = frozenset(self.tags | {tag})
        self.bump_version()

    def remove_tag(self, tag: str) -> None:
        self.tags = frozenset(self.tags - {tag})
        self.bump_version()

    def set_note(self, note: str) -> None:
        self.notes = note
        self.bump_version()

    def set_custom(self, key: str, value: Any) -> None:
        self.custom[key] = value
        self.bump_version()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source":     self.source,
            "tags":       sorted(self.tags),
            "notes":      self.notes,
            "version":    self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "custom":     dict(self.custom),
        }
