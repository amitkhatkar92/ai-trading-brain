"""
knowledge_relationship.py -- iios.ai.memory_knowledge.graph
============================================================
:class:`KnowledgeRelationship` — immutable directed edge in a knowledge graph.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class KnowledgeRelationship:
    """Immutable directed edge: source_node --[relation_type]--> target_node."""
    rel_id:        str
    source_id:     str
    target_id:     str
    relation_type: str
    properties:    Dict[str, Any]
    weight:        float       # optional semantic weight [0.0, 1.0]
    created_at:    float

    @classmethod
    def create(
        cls,
        source_id:     str,
        target_id:     str,
        relation_type: str,
        properties:    Optional[Dict[str, Any]] = None,
        weight:        float                    = 1.0,
        *,
        rel_id:        Optional[str]            = None,
    ) -> "KnowledgeRelationship":
        return cls(
            rel_id        = rel_id or str(uuid.uuid4()),
            source_id     = source_id,
            target_id     = target_id,
            relation_type = relation_type,
            properties    = dict(properties or {}),
            weight        = max(0.0, min(1.0, weight)),
            created_at    = time.time(),
        )
