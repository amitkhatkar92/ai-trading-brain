"""
knowledge_path.py -- iios.ai.memory_knowledge.graph
====================================================
:class:`KnowledgePath` — an immutable sequence of nodes and relationships
representing a traversal result through the knowledge graph.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Tuple

from .knowledge_node         import KnowledgeNode
from .knowledge_relationship import KnowledgeRelationship


@dataclass(frozen=True)
class KnowledgePath:
    """Immutable traversal path through a knowledge graph."""
    path_id:       str
    nodes:         Tuple[KnowledgeNode, ...]
    relationships: Tuple[KnowledgeRelationship, ...]

    @classmethod
    def create(
        cls,
        nodes:         Tuple[KnowledgeNode, ...],
        relationships: Tuple[KnowledgeRelationship, ...],
    ) -> "KnowledgePath":
        return cls(
            path_id       = str(uuid.uuid4()),
            nodes         = nodes,
            relationships = relationships,
        )

    @property
    def length(self) -> int:
        """Number of edges in the path."""
        return len(self.relationships)

    @property
    def start_node(self) -> KnowledgeNode:
        return self.nodes[0]

    @property
    def end_node(self) -> KnowledgeNode:
        return self.nodes[-1]
