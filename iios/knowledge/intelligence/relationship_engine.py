"""
relationship_engine.py — iios.knowledge.intelligence
-----------------------------------------------------
Discovers relationships between extracted knowledge entities.

Stub strategy: entities extracted from the same artifact receive a
REFERENCES relationship. Weight is based on shared source artifact.

A RelationshipDiscoveryAdapter Protocol allows ML/rule-based injection.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import itertools
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from iios.common.logging.logging_manager import get_logger

from .constants import RelationshipType
from .knowledge_graph_engine import KnowledgeEntity, KnowledgeRelationship

_log = get_logger(__name__)


@runtime_checkable
class RelationshipDiscoveryAdapter(Protocol):
    """Protocol for ML-based relationship discovery backends."""
    def discover(
        self,
        entities: List[KnowledgeEntity],
    ) -> List[KnowledgeRelationship]: ...


class RelationshipEngine:
    """
    Discovers relationships between knowledge entities.

    Stub mode: co-occurrence within the same artifact → REFERENCES.
    Adapter mode: delegates to a RelationshipDiscoveryAdapter.
    """

    def __init__(
        self,
        adapter: Optional[RelationshipDiscoveryAdapter] = None,
    ) -> None:
        self._adapter = adapter

    def discover(
        self,
        entities: List[KnowledgeEntity],
    ) -> List[KnowledgeRelationship]:
        """Return discovered relationships. Never raises."""
        try:
            if self._adapter:
                return self._adapter.discover(entities)
            return self._stub_discover(entities)
        except Exception as exc:
            _log.warning(f"Relationship discovery failed: {exc!r}")
            return []

    def _stub_discover(
        self,
        entities: List[KnowledgeEntity],
    ) -> List[KnowledgeRelationship]:
        """Co-occurrence: entities from the same artifact → REFERENCES."""
        # Group by source artifact
        by_artifact: Dict[str, List[KnowledgeEntity]] = {}
        for entity in entities:
            by_artifact.setdefault(entity.source_artifact_id, []).append(entity)

        relationships: List[KnowledgeRelationship] = []
        for _aid, group in by_artifact.items():
            for src, tgt in itertools.combinations(group, 2):
                rel = KnowledgeRelationship.create(
                    source_entity_id  = src.entity_id,
                    target_entity_id  = tgt.entity_id,
                    relationship_type = RelationshipType.REFERENCES,
                    weight            = 0.7,
                    confidence        = 0.75,
                    metadata          = {"source": "co_occurrence"},
                )
                relationships.append(rel)
        return relationships

    def set_adapter(self, adapter: RelationshipDiscoveryAdapter) -> None:
        self._adapter = adapter
        _log.info("RelationshipDiscoveryAdapter registered")
