"""
knowledge_node.py -- iios.ai.memory_knowledge.graph
====================================================
:class:`KnowledgeNode` — immutable node in a knowledge graph.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Optional


@dataclass(frozen=True)
class KnowledgeNode:
    """Immutable vertex in a knowledge graph."""
    node_id:    str
    label:      str                 # human-readable label (e.g. entity type)
    properties: Dict[str, Any]      # arbitrary key-value pairs
    tags:       FrozenSet[str]
    created_at: float

    @classmethod
    def create(
        cls,
        label:      str,
        properties: Optional[Dict[str, Any]] = None,
        tags:       FrozenSet[str]            = frozenset(),
        *,
        node_id:    Optional[str]             = None,
    ) -> "KnowledgeNode":
        return cls(
            node_id    = node_id or str(uuid.uuid4()),
            label      = label,
            properties = dict(properties or {}),
            tags       = tags,
            created_at = time.time(),
        )
