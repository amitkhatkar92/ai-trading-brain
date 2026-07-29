"""
embedding_service.py -- iios.ai.memory_knowledge.vector
========================================================
:class:`EmbeddingService` — provider-independent ABC for text-to-vector
conversion.  Concrete implementations wrap OpenAI, HuggingFace, Cohere etc.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

Vector = List[float]


class EmbeddingService(ABC):
    """Abstract text embedding provider."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensionality."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the underlying model identifier."""

    @abstractmethod
    def embed(self, text: str) -> Vector:
        """Convert a single text to a dense vector."""

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[Vector]:
        """Convert a list of texts to dense vectors (batched for efficiency)."""
