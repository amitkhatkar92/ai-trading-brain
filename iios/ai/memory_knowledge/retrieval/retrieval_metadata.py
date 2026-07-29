"""
retrieval_metadata.py -- iios.ai.memory_knowledge.retrieval
=============================================================
:class:`RetrievalMetadata` — diagnostic stats attached to a retrieval run.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalMetadata:
    """Immutable diagnostics for a retrieval call."""
    request_id:       str
    strategy_used:    str
    candidates_seen:  int
    results_returned: int
    duration_ms:      float
    from_cache:       bool

    @classmethod
    def create(
        cls,
        request_id:       str,
        strategy_used:    str,
        candidates_seen:  int,
        results_returned: int,
        duration_ms:      float,
        from_cache:       bool = False,
    ) -> "RetrievalMetadata":
        return cls(
            request_id       = request_id,
            strategy_used    = strategy_used,
            candidates_seen  = candidates_seen,
            results_returned = results_returned,
            duration_ms      = duration_ms,
            from_cache       = from_cache,
        )
