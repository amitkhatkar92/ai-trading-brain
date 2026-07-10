"""iios/integration/cache/cache_entry.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """One cached item with TTL and hit tracking."""

    key:       str
    value:     Any
    ttl_sec:   float              = 300.0
    created_at: float             = field(default_factory=time.time)
    hits:      int                = 0
    metadata:  dict[str, Any]     = field(default_factory=dict)

    def is_expired(self, now: float | None = None) -> bool:
        if now is None:
            now = time.time()
        return (now - self.created_at) > self.ttl_sec

    def age_sec(self, now: float | None = None) -> float:
        if now is None:
            now = time.time()
        return now - self.created_at

    def touch(self) -> None:
        self.hits += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "key":        self.key,
            "ttl_sec":    self.ttl_sec,
            "created_at": self.created_at,
            "hits":       self.hits,
            "expired":    self.is_expired(),
        }
