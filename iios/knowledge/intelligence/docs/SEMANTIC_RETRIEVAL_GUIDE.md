# Semantic Retrieval Guide

## Overview

The retrieval subsystem provides three retrieval modes:

| Mode         | Description                                      |
|--------------|--------------------------------------------------|
| SEMANTIC     | Embedding vector similarity (cosine)             |
| HYBRID       | α·semantic + (1-α)·keyword (Jaccard token overlap)|
| KEYWORD      | Token overlap only                               |
| GRAPH        | Traversal-based (graph neighbor expansion)       |
| RECOMMENDATION | Similarity-ranked suggestions                 |

## Basic Retrieval

```python
from iios.knowledge.intelligence import RetrievalMode

# Semantic
result = engine.retrieve("NIFTY buy signal", top_k=10)

# Hybrid
result = engine.retrieve("NIFTY risk exposure", mode=RetrievalMode.HYBRID)
```

## KnowledgeRetrievalResult

```python
result = engine.retrieve("signal")
print(f"Mode: {result.mode.value}")
print(f"Items found: {result.total_results}")
print(f"Time: {result.retrieval_ms:.1f}ms")

for item in result.items:
    print(f"  [{item.rank}] {item.artifact_id}  score={item.score:.4f}")
```

## RetrievalEngine (direct use)

```python
from iios.knowledge.intelligence import (
    EmbeddingEngine, VectorStoreManager, RetrievalEngine
)

emb_eng     = EmbeddingEngine()
vector_store = VectorStoreManager()
retrieval    = RetrievalEngine(emb_eng, vector_store, top_k=10)

result = retrieval.retrieve("market trend signal")
```

## HybridSearchEngine

```python
from iios.knowledge.intelligence import HybridSearchEngine

hybrid = HybridSearchEngine(
    embedding_engine = emb_eng,
    vector_store     = vector_store,
    alpha            = 0.7,    # 70% semantic, 30% keyword
    top_k            = 10,
)
result = hybrid.search("NIFTY buy")
```

## Reranking

```python
from iios.knowledge.intelligence import RerankingEngine

reranker = RerankingEngine(decay_per_rank=0.005)
reranked = reranker.rerank("query text", result.items)
```
