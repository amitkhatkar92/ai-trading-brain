"""
retrieval_request.py -- iios.ai.memory_knowledge.retrieval
===========================================================
:class:`RetrievalRequest` — immutable specification for a retrieval call.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import FrozenSet, Optional

from ..core.knowledge_category import KnowledgeCategory


@dataclass(frozen=True)
class RetrievalRequest:
    """Immutable specification of what to retrieve."""
    request_id:   str
    query:        str                          # free-text query
    top_k:        int                          # max results to return
    category:     Optional[KnowledgeCategory]  # optional category filter
    tags:         FrozenSet[str]               # required tags (all must match)
    min_score:    float                        # minimum relevance score [0, 1]
    include_memory:    bool                    # search memory entries
    include_knowledge: bool                    # search knowledge items
    session_id:   Optional[str]
    trace_id:     Optional[str]

    @classmethod
    def create(
        cls,
        query:             str,
        top_k:             int                      = 10,
        category:          Optional[KnowledgeCategory] = None,
        tags:              FrozenSet[str]            = frozenset(),
        min_score:         float                     = 0.0,
        include_memory:    bool                      = True,
        include_knowledge: bool                      = True,
        session_id:        Optional[str]             = None,
        trace_id:          Optional[str]             = None,
    ) -> "RetrievalRequest":
        return cls(
            request_id        = str(uuid.uuid4()),
            query             = query,
            top_k             = max(1, top_k),
            category          = category,
            tags              = tags,
            min_score         = max(0.0, min(1.0, min_score)),
            include_memory    = include_memory,
            include_knowledge = include_knowledge,
            session_id        = session_id,
            trace_id          = trace_id,
        )
