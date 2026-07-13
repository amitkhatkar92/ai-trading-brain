"""iios/investment/strategy/core/strategy_metadata.py
Mutable business and operational metadata for a strategy.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategyMetadata:
    """Mutable operational metadata — updated throughout a strategy's life."""

    strategy_id:        str            = ""
    display_name:       str            = ""
    description:        str            = ""
    long_description:   str            = ""
    author:             str            = ""
    team:               str            = ""
    contact:            str            = ""
    tags:               list[str]      = field(default_factory=list)
    labels:             dict[str, str] = field(default_factory=dict)
    notes:              list[str]      = field(default_factory=list)
    external_refs:      list[str]      = field(default_factory=list)
    attributes:         dict[str, Any] = field(default_factory=dict)
    updated_at:         float          = field(default_factory=time.time)

    def add_note(self, note: str) -> None:
        self.notes.append(note)
        self.updated_at = time.time()

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = time.time()

    def get(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.attributes[key] = value
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id":      self.strategy_id,
            "display_name":     self.display_name,
            "description":      self.description,
            "author":           self.author,
            "team":             self.team,
            "tags":             self.tags,
            "labels":           self.labels,
            "notes":            self.notes,
            "external_refs":    self.external_refs,
            "attributes":       self.attributes,
            "updated_at":       self.updated_at,
        }
