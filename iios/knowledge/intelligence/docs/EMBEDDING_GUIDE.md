# Embedding Guide

## Overview

The Embedding Engine converts knowledge artifact text into fixed-dimension float vectors.

## Stub Mode (Default)

No external ML library required. Uses SHA-256 hash to produce deterministic, L2-normalised vectors.

```python
from iios.knowledge.intelligence import EmbeddingEngine

engine = EmbeddingEngine(dimension=128)    # default
emb    = engine.generate("art-001", "NIFTY buy signal at 20000")
print(f"Dimension: {emb.dimension}")       # 128
print(f"Model: {emb.model_name}")          # "stub"
print(f"Vector[0]: {emb.vector[0]:.4f}")  # deterministic
```

## Injecting a Real Provider

Implement the `EmbeddingProvider` Protocol:

```python
from iios.knowledge.intelligence import EmbeddingProvider, EmbeddingEngine

class OpenAIEmbeddingProvider:
    def embed(self, text: str) -> list[float]:
        # call OpenAI embeddings API
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    @property
    def dimension(self) -> int:
        return 1536

    @property
    def model_name(self) -> str:
        return "text-embedding-3-small"

engine = EmbeddingEngine()
engine.set_provider(OpenAIEmbeddingProvider())   # or via factory
```

## Batch Generation

```python
embeddings = engine.generate_batch(
    artifact_ids = ["a1", "a2", "a3"],
    texts        = ["text one", "text two", "text three"],
)
```

## EmbeddingRegistry

```python
from iios.knowledge.intelligence import EmbeddingRegistry

registry = EmbeddingRegistry(max_embeddings=100_000)
registry.store(emb)
stored = registry.get("a1")
ids    = registry.all_artifact_ids()
```
