"""core/backtest_metadata.py — Metadata attached to every backtest entity."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BacktestMetadata:
    owner:      str             = ""
    source:     str             = ""
    version:    str             = "1.0.0"
    notes:      str             = ""
    labels:     dict[str, str]  = field(default_factory=dict)
    tags:       list[str]       = field(default_factory=list)
    created_at: float           = field(default_factory=time.time)
    updated_at: float           = field(default_factory=time.time)
    extra:      dict[str, Any]  = field(default_factory=dict)

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def touch(self) -> None:
        self.updated_at = time.time()

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)
        self.touch()

    def remove_tag(self, tag: str) -> None:
        self.tags = [t for t in self.tags if t != tag]
        self.touch()

    def set_label(self, key: str, value: str) -> None:
        self.labels[key] = value
        self.touch()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner":      self.owner,
            "source":     self.source,
            "version":    self.version,
            "notes":      self.notes,
            "labels":     dict(self.labels),
            "tags":       list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "extra":      dict(self.extra),
        }
