# Knowledge Graph Guide

## Overview

The Knowledge Graph stores extracted entities and their relationships.

## Domain Objects

### KnowledgeEntity (frozen dataclass)

```python
from iios.knowledge.intelligence import KnowledgeEntity, EntityType

entity = KnowledgeEntity.create(
    name               = "price:20000",
    entity_type        = EntityType.METRIC,
    source_artifact_id = "art-001",
    confidence         = 0.9,
    attributes         = {"raw_value": "20000"},
)
```

**EntityType enum (12 types):** CONCEPT, METRIC, EVENT, SIGNAL, ASSET, POSITION, RISK, DECISION, INSIGHT, PATTERN, ANOMALY, SYSTEM

### KnowledgeRelationship (frozen dataclass)

```python
from iios.knowledge.intelligence import KnowledgeRelationship, RelationshipType

rel = KnowledgeRelationship.create(
    source_entity_id  = entity1.entity_id,
    target_entity_id  = entity2.entity_id,
    relationship_type = RelationshipType.CAUSES,
    weight            = 0.8,
    confidence        = 0.9,
)
```

**RelationshipType enum (12 types):** CAUSES, CORRELATES_WITH, PRECEDES, FOLLOWS, CONTAINS, BELONGS_TO, REFERENCES, IMPACTS, SIMILAR_TO, OPPOSES, INFLUENCES, TRIGGERS

### KnowledgeGraph (mutable)

```python
from iios.knowledge.intelligence import KnowledgeGraph

graph = KnowledgeGraph(max_entities=100_000, max_relations=500_000)
graph.add_entity(entity)
graph.add_relationship(rel)
neighbors = graph.get_neighbors(entity.entity_id)
rels      = graph.get_entity_relationships(entity.entity_id)
```

## Pluggable Graph Backend

Inject a `KnowledgeGraphAdapter` for Neo4j, TigerGraph, etc.:

```python
class Neo4jAdapter:
    def add_entity(self, entity): ...
    def add_relationship(self, rel): ...
    def get_entity(self, entity_id): ...
    def get_neighbors(self, entity_id): ...
    def entity_count(self): ...
    def relationship_count(self): ...

graph = KnowledgeGraph(adapter=Neo4jAdapter())
```

## Entity Resolution

```python
from iios.knowledge.intelligence import EntityResolutionEngine

resolver  = EntityResolutionEngine()
artifacts = [{"artifact_id": "a1", "price": 100, "signal": "buy"}]
entities  = resolver.extract_batch(artifacts)
```

## Relationship Discovery

```python
from iios.knowledge.intelligence import RelationshipEngine

engine        = RelationshipEngine()
relationships = engine.discover(entities)
```
