"""
knowledge_graph_engine.py — iios.knowledge.intelligence
---------------------------------------------------------
Core knowledge graph domain objects.

Defines:
    KnowledgeEntity        — an extracted knowledge entity (frozen)
    KnowledgeRelationship  — a directed relationship between entities (frozen)
    KnowledgeGraph         — mutable in-memory graph

The graph is backed by an in-memory adjacency store.
A pluggable KnowledgeGraphAdapter Protocol allows future external graph
databases (Neo4j, TigerGraph, etc.) to be injected.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from iios.common.logging.logging_manager import get_logger

from .constants import EntityType, RelationshipType

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain value objects (frozen)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeEntity:
    """An extracted and resolved knowledge entity."""
    entity_id:          str
    name:               str
    entity_type:        EntityType
    source_artifact_id: str
    attributes:         Dict[str, Any]
    aliases:            tuple             # Tuple[str]
    confidence:         float             # [0.0 – 1.0]
    created_at:         str               # ISO-8601

    @classmethod
    def create(
        cls,
        name:               str,
        entity_type:        EntityType,
        source_artifact_id: str,
        *,
        entity_id:   str              = "",
        attributes:  Dict[str, Any]   = None,
        aliases:     List[str]        = None,
        confidence:  float            = 1.0,
    ) -> "KnowledgeEntity":
        return cls(
            entity_id          = entity_id or f"ent-{uuid.uuid4().hex[:12]}",
            name               = name,
            entity_type        = entity_type,
            source_artifact_id = source_artifact_id,
            attributes         = dict(attributes or {}),
            aliases            = tuple(aliases or []),
            confidence         = confidence,
            created_at         = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id":          self.entity_id,
            "name":               self.name,
            "entity_type":        self.entity_type.value,
            "source_artifact_id": self.source_artifact_id,
            "attributes":         self.attributes,
            "aliases":            list(self.aliases),
            "confidence":         self.confidence,
            "created_at":         self.created_at,
        }


@dataclass(frozen=True)
class KnowledgeRelationship:
    """A directed relationship between two knowledge entities."""
    relationship_id:  str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    weight:           float            # [0.0 – 1.0]
    confidence:       float            # [0.0 – 1.0]
    metadata:         Dict[str, Any]
    created_at:       str              # ISO-8601

    @classmethod
    def create(
        cls,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: RelationshipType,
        *,
        relationship_id: str            = "",
        weight:          float          = 1.0,
        confidence:      float          = 1.0,
        metadata:        Dict[str, Any] = None,
    ) -> "KnowledgeRelationship":
        return cls(
            relationship_id   = relationship_id or f"rel-{uuid.uuid4().hex[:12]}",
            source_entity_id  = source_entity_id,
            target_entity_id  = target_entity_id,
            relationship_type = relationship_type,
            weight            = weight,
            confidence        = confidence,
            metadata          = dict(metadata or {}),
            created_at        = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id":   self.relationship_id,
            "source_entity_id":  self.source_entity_id,
            "target_entity_id":  self.target_entity_id,
            "relationship_type": self.relationship_type.value,
            "weight":            self.weight,
            "confidence":        self.confidence,
            "metadata":          self.metadata,
            "created_at":        self.created_at,
        }


# ---------------------------------------------------------------------------
# Pluggable adapter Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class KnowledgeGraphAdapter(Protocol):
    """
    Protocol for external knowledge graph backends (Neo4j, TigerGraph, etc.).

    If no adapter is injected, KnowledgeGraph uses its in-memory store.
    """
    def add_entity(self, entity: KnowledgeEntity) -> None: ...
    def add_relationship(self, rel: KnowledgeRelationship) -> None: ...
    def get_entity(self, entity_id: str) -> Optional[KnowledgeEntity]: ...
    def get_neighbors(self, entity_id: str) -> List[KnowledgeEntity]: ...
    def entity_count(self) -> int: ...
    def relationship_count(self) -> int: ...


# ---------------------------------------------------------------------------
# In-memory knowledge graph
# ---------------------------------------------------------------------------


class KnowledgeGraph:
    """
    Thread-safe in-memory knowledge graph.

    Stores entities and directed relationships.  An optional
    KnowledgeGraphAdapter can delegate operations to an external
    graph database.

    node_count : number of unique entities
    edge_count : number of directed relationships
    """

    def __init__(
        self,
        *,
        graph_id:      str                            = "",
        adapter:       Optional[KnowledgeGraphAdapter] = None,
        max_entities:  int                            = 100_000,
        max_relations: int                            = 500_000,
    ) -> None:
        self._graph_id       = graph_id or f"graph-{uuid.uuid4().hex[:10]}"
        self._adapter        = adapter
        self._max_entities   = max_entities
        self._max_relations  = max_relations
        self._entities:      Dict[str, KnowledgeEntity]       = {}
        self._relationships: Dict[str, KnowledgeRelationship] = {}
        self._adj:           Dict[str, List[str]]             = {}  # entity_id → [rel_ids]
        self._lock           = threading.Lock()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def graph_id(self) -> str:
        return self._graph_id

    @property
    def node_count(self) -> int:
        with self._lock:
            return (
                self._adapter.entity_count() if self._adapter
                else len(self._entities)
            )

    @property
    def edge_count(self) -> int:
        with self._lock:
            return (
                self._adapter.relationship_count() if self._adapter
                else len(self._relationships)
            )

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_entity(self, entity: KnowledgeEntity) -> None:
        with self._lock:
            if entity.entity_id in self._entities:
                return   # idempotent
            if len(self._entities) >= self._max_entities:
                from .exceptions import IntelligenceCapacityError
                raise IntelligenceCapacityError(limit=self._max_entities)
            self._entities[entity.entity_id] = entity
            self._adj.setdefault(entity.entity_id, [])
            if self._adapter:
                self._adapter.add_entity(entity)

    def add_relationship(self, rel: KnowledgeRelationship) -> None:
        with self._lock:
            if rel.relationship_id in self._relationships:
                return   # idempotent
            if len(self._relationships) >= self._max_relations:
                from .exceptions import IntelligenceCapacityError
                raise IntelligenceCapacityError(limit=self._max_relations)
            self._relationships[rel.relationship_id] = rel
            self._adj.setdefault(rel.source_entity_id, []).append(rel.relationship_id)
            if self._adapter:
                self._adapter.add_relationship(rel)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_entity(self, entity_id: str) -> Optional[KnowledgeEntity]:
        with self._lock:
            if self._adapter:
                return self._adapter.get_entity(entity_id)
            return self._entities.get(entity_id)

    def get_neighbors(self, entity_id: str) -> List[KnowledgeEntity]:
        with self._lock:
            if self._adapter:
                return self._adapter.get_neighbors(entity_id)
            rel_ids = self._adj.get(entity_id, [])
            result = []
            for rid in rel_ids:
                rel = self._relationships.get(rid)
                if rel:
                    nbr = self._entities.get(rel.target_entity_id)
                    if nbr:
                        result.append(nbr)
            return result

    def get_entity_relationships(
        self, entity_id: str,
    ) -> List[KnowledgeRelationship]:
        with self._lock:
            rel_ids = self._adj.get(entity_id, [])
            return [
                self._relationships[rid]
                for rid in rel_ids
                if rid in self._relationships
            ]

    def all_entities(self) -> List[KnowledgeEntity]:
        with self._lock:
            return list(self._entities.values())

    def all_relationships(self) -> List[KnowledgeRelationship]:
        with self._lock:
            return list(self._relationships.values())

    def entities_by_type(self, entity_type: EntityType) -> List[KnowledgeEntity]:
        with self._lock:
            return [e for e in self._entities.values() if e.entity_type == entity_type]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id":   self._graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
        }
