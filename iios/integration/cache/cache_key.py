"""iios/integration/cache/cache_key.py"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CacheKey:
    """Immutable, hashable cache key."""

    provider_id: str
    category:    str
    frequency:   str
    symbol:      str | None
    extra:       str = ""        # JSON string of extra params

    @classmethod
    def build(
        cls,
        provider_id: str,
        category:    str,
        frequency:   str,
        symbol:      str | None = None,
        **params: Any,
    ) -> "CacheKey":
        extra = json.dumps(params, sort_keys=True, default=str) if params else ""
        return cls(
            provider_id=provider_id,
            category=category,
            frequency=frequency,
            symbol=symbol,
            extra=extra,
        )

    def to_string(self) -> str:
        parts = [self.provider_id, self.category, self.frequency]
        if self.symbol:
            parts.append(self.symbol)
        if self.extra:
            parts.append(self.extra)
        return ":".join(parts)

    def to_hash(self) -> str:
        return hashlib.sha256(self.to_string().encode()).hexdigest()[:16]
