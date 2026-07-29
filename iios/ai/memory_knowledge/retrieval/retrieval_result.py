"""
retrieval_result.py -- iios.ai.memory_knowledge.retrieval
==========================================================
:class:`RetrievalResult` — immutable result set from a retrieval request.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


@dataclass(frozen=True)
class RetrievalHit:
    """A single ranked result item."""
    hit_id:    str           # entry_id or item_id of the source
    source:    str           # "memory" or "knowledge"
    content:   Any
    score:     float         # relevance score [0.0, 1.0]
    title:     str
    tags:      frozenset


@dataclass(frozen=True)
class RetrievalResult:
    """Immutable container of ranked retrieval hits."""
    result_id:   str
    request_id:  str
    hits:        Tuple[RetrievalHit, ...]
    strategy:    str
    total_found: int
    retrieved_at: float

    @classmethod
    def create(
        cls,
        request_id:  str,
        hits:        List[RetrievalHit],
        strategy:    str,
        total_found: Optional[int] = None,
    ) -> "RetrievalResult":
        return cls(
            result_id    = str(uuid.uuid4()),
            request_id   = request_id,
            hits         = tuple(hits),
            strategy     = strategy,
            total_found  = total_found if total_found is not None else len(hits),
            retrieved_at = time.time(),
        )

    @property
    def count(self) -> int:
        return len(self.hits)

    def top(self, n: int = 1) -> Tuple[RetrievalHit, ...]:
        return self.hits[:n]
