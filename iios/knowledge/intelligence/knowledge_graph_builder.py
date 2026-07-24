"""
knowledge_graph_builder.py — iios.knowledge.intelligence
---------------------------------------------------------
Constructs and updates KnowledgeGraph instances from extracted entities
and relationships.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List

from iios.common.logging.logging_manager import get_logger

from .knowledge_graph_engine import (
    KnowledgeEntity,
    KnowledgeGraph,
    KnowledgeRelationship,
)

_log = get_logger(__name__)


class KnowledgeGraphBuilder:
    """
    Populates a KnowledgeGraph from entity and relationship lists.

    Used by the intelligence manager in the BUILDING phase.
    """

    def build(
        self,
        graph:         KnowledgeGraph,
        entities:      List[KnowledgeEntity],
        relationships: List[KnowledgeRelationship],
    ) -> int:
        """
        Add entities and relationships to *graph*.

        Returns the number of new nodes + edges added.
        """
        added = 0
        for entity in entities:
            try:
                graph.add_entity(entity)
                added += 1
            except Exception as exc:
                _log.debug(f"Skipped entity {entity.entity_id!r}: {exc!r}")

        for rel in relationships:
            try:
                graph.add_relationship(rel)
                added += 1
            except Exception as exc:
                _log.debug(f"Skipped relationship {rel.relationship_id!r}: {exc!r}")

        _log.debug(
            f"Graph build: {added} elements added "
            f"(nodes={graph.node_count}, edges={graph.edge_count})"
        )
        return added
