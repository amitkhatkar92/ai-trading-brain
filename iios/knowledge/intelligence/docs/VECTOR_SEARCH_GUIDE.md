# Vector Search Guide

## Overview

The vector index stores embedding vectors and provides similarity search.

## In-Memory Linear Search (Default)

```python
from iios.knowledge.intelligence import VectorIndex, VectorIndexEngine

# Direct VectorIndex usage
idx = VectorIndex(max_vectors=100_000)
idx.upsert("art-001", [0.5, 0.3, -0.2, ...], metadata={"source": "market"})
idx.upsert("art-002", [0.1, 0.8, -0.1, ...], metadata={"source": "signal"})

results = idx.search(query_vector=[0.5, 0.3, -0.2, ...], top_k=5)
for r in results:
    print(f"Rank {r.rank}: {r.artifact_id}  score={r.score:.4f}")
```

## VectorIndexEngine (Orchestrator)

```python
from iios.knowledge.intelligence import VectorIndexEngine

engine = VectorIndexEngine()                          # stub mode
engine.upsert("art-001", vector=[...], metadata={})
results = engine.search(query_vector=[...], top_k=10)
```

## Injecting a Real Vector Store

Implement the `VectorStoreAdapter` Protocol:

```python
from iios.knowledge.intelligence import VectorStoreAdapter, VectorSearchResult

class PineconeAdapter:
    def upsert(self, artifact_id, vector, metadata): ...
    def search(self, query_vector, top_k) -> list[VectorSearchResult]: ...
    def delete(self, artifact_id) -> bool: ...
    def count(self) -> int: ...

engine.set_adapter(PineconeAdapter())
```

Supported via `engine.set_vector_adapter()` on `KnowledgeIntelligenceEngine`.

## VectorStoreManager

```python
from iios.knowledge.intelligence import VectorStoreManager, EmbeddingEngine

emb_engine = EmbeddingEngine()
emb        = emb_engine.generate("art-001", "NIFTY signal")

vs = VectorStoreManager()
vs.index_embedding(emb, metadata={"subsystem": "market"})

query_emb = emb_engine.generate("query", "buy signal")
results   = vs.search(query_emb, top_k=5)
```

## Similarity Metrics

| Metric      | Formula                         |
|-------------|----------------------------------|
| COSINE      | dot(a,b) / (|a| · |b|)          |
| DOT_PRODUCT | dot(a,b)                         |
| EUCLIDEAN   | √Σ(aᵢ-bᵢ)²                      |
| MANHATTAN   | Σ|aᵢ-bᵢ|                         |
| JACCARD     | |A∩B|/|A∪B| (set-based)          |

Default stub uses COSINE similarity.
