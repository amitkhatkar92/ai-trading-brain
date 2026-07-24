# Knowledge Intelligence Framework

## C14 M4 — Institutional Knowledge Intelligence

**Package:** `iios.knowledge.intelligence`
**Version:** 1.0.0

---

## What It Does

The Knowledge Intelligence Framework transforms governed knowledge artifacts into structured intelligence through an 11-phase pipeline:

1. Validate artifacts
2. Extract entities (type-classified from artifact fields)
3. Resolve entity identities (deduplication)
4. Discover relationships (co-occurrence → REFERENCES)
5. Build knowledge graph (in-memory adjacency)
6. Generate embeddings (deterministic stub or pluggable provider)
7. Update vector index (in-memory linear cosine or pluggable adapter)
8. Enrich knowledge (metadata augmentation)
9. Build reasoning context (graph + semantic features)
10. Generate recommendations (cosine similarity top-K)
11. Return `KnowledgeIntelligenceResponse`

---

## Quick Start

```python
from iios.knowledge.intelligence import (
    KnowledgeIntelligenceEngine,
    KnowledgeIntelligenceRequest,
)

# Create and start engine (stub mode — no external services needed)
engine = KnowledgeIntelligenceEngine.create_default()
engine.start()

# Process knowledge artifacts
request = KnowledgeIntelligenceRequest.create(
    knowledge_id = "system:market-intelligence",
    subsystem_id = "market-intelligence",
    artifacts    = [
        {
            "artifact_id": "art-001",
            "signal":      "buy",
            "asset":       "NIFTY",
            "price":       20000.0,
        }
    ],
)

response = engine.process(request)
print(f"Succeeded: {response.succeeded}")
print(f"Entities extracted: {response.report.entities_extracted}")
print(f"Embeddings: {response.report.embeddings_generated}")
```

---

## Error Codes (KIF prefix)

| Code    | Exception                    | Meaning                        |
|---------|------------------------------|--------------------------------|
| KIF-000 | KnowledgeIntelligenceError   | Base error                     |
| KIF-001 | IntelligenceNotRunningError  | Engine not started             |
| KIF-002 | IntelligenceValidationError  | Request validation failed      |
| KIF-003 | KnowledgeGraphError          | Graph operation failure        |
| KIF-004 | EntityResolutionError        | Entity extraction failure      |
| KIF-005 | EmbeddingError               | Embedding generation failure   |
| KIF-006 | VectorIndexError             | Vector index failure           |
| KIF-007 | RetrievalError               | Retrieval operation failure    |
| KIF-008 | EnrichmentError              | Enrichment failure             |
| KIF-009 | IntelligenceCapacityError    | Capacity limit exceeded        |

---

## Pluggable Adapters

All external service dependencies are behind Protocol interfaces:

| Protocol               | Default (stub)            | Injected via                     |
|------------------------|---------------------------|----------------------------------|
| `EmbeddingProvider`    | Hash-based deterministic  | `engine.set_embedding_provider()`|
| `VectorStoreAdapter`   | In-memory linear search   | `engine.set_vector_adapter()`    |
| `KnowledgeGraphAdapter`| In-memory adjacency dict  | Constructor injection            |
| `EntityExtractionAdapter`| Keyword classification  | `entity_resolver.set_adapter()`  |
| `RelationshipDiscoveryAdapter`| Co-occurrence      | `relationship_engine.set_adapter()`|
| `ClusteringAdapter`    | Hash bucketing            | `clustering_engine.set_adapter()`|
| `RerankingAdapter`     | Decay + freshness bonus   | `reranker.set_adapter()`         |
| `EnrichmentAdapter`    | Field metadata injection  | `enrichment_engine.set_adapter()`|
