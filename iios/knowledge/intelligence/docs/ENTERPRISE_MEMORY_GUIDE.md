# Enterprise Memory Guide

## Overview

Enterprise Memory tracks the cumulative state of the intelligence framework across all processing cycles.

## EnterpriseMemorySummary

```python
from iios.knowledge.intelligence import EnterpriseMemorySummary

summary = engine.memory_summary()

print(f"Total artifacts:     {summary.total_artifacts}")
print(f"Total entities:      {summary.total_entities}")
print(f"Total relationships: {summary.total_relationships}")
print(f"Total embeddings:    {summary.total_embeddings}")
print(f"Total vectors:       {summary.total_vectors}")
print(f"Graph density:       {summary.graph_density:.4f}")
print(f"Generated:           {summary.generated_at}")
```

## KnowledgeMemoryEngine

```python
from iios.knowledge.intelligence import (
    KnowledgeGraph, EmbeddingRegistry, VectorStoreManager, KnowledgeMemoryEngine
)

memory = KnowledgeMemoryEngine(
    graph              = graph,
    embedding_registry = embedding_registry,
    vector_store       = vector_store,
)

memory.record_artifacts(5)   # track processed artifacts
summary = memory.summary()   # EnterpriseMemorySummary
```

## Statistics Counters (10)

| Counter                   | Tracked via                         |
|---------------------------|-------------------------------------|
| artifacts_processed       | `record_artifacts(n)`               |
| entities_extracted        | `record_entities(n)`                |
| relationships_discovered  | `record_relationships(n)`           |
| graph_nodes               | `record_graph_state(nodes, edges)`  |
| graph_edges               | `record_graph_state(nodes, edges)`  |
| embeddings_generated      | `record_embeddings(n)`              |
| vectors_indexed           | `record_vectors(n)`                 |
| retrieval_requests        | `record_retrieval()`                |
| recommendations_generated | `record_recommendations(n)`         |
| enrichment_operations     | `record_enrichment(n)`              |

## Processing History

```python
# Last 20 responses
history = engine.history(20)
for resp in history:
    print(f"{resp.responded_at}  succeeded={resp.succeeded}")
```
