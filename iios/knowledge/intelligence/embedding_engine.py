"""
embedding_engine.py — iios.knowledge.intelligence
---------------------------------------------------
EmbeddingVector and EmbeddingEngine.

The EmbeddingEngine is provider-agnostic:
  - In stub mode:  deterministic hash-based pseudo-embeddings (no ML)
  - With provider: delegates to an injected EmbeddingProvider adapter

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import hashlib
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_EMBEDDING_DIMENSION, EMBEDDING_SYSTEM_ID

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmbeddingVector:
    """An embedding vector for a single knowledge artifact."""
    embedding_id: str
    artifact_id:  str
    vector:       tuple        # Tuple[float, ...]
    dimension:    int
    model_name:   str          # "stub" in stub mode; provider name otherwise
    created_at:   str          # ISO-8601

    @property
    def as_list(self) -> List[float]:
        return list(self.vector)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "embedding_id": self.embedding_id,
            "artifact_id":  self.artifact_id,
            "dimension":    self.dimension,
            "model_name":   self.model_name,
            "created_at":   self.created_at,
        }


# ---------------------------------------------------------------------------
# Pluggable adapter Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class EmbeddingProvider(Protocol):
    """
    Protocol for pluggable embedding backends.

    Implementations can wrap OpenAI, Sentence-Transformers, Cohere, etc.
    """
    def embed(self, text: str) -> List[float]: ...
    def embed_batch(self, texts: List[str]) -> List[List[float]]: ...
    @property
    def dimension(self) -> int: ...
    @property
    def model_name(self) -> str: ...


# ---------------------------------------------------------------------------
# Stub embedding (deterministic, no ML)
# ---------------------------------------------------------------------------


def _stub_embed(text: str, dimension: int = DEFAULT_EMBEDDING_DIMENSION) -> List[float]:
    """
    Generate a deterministic pseudo-embedding from a text string.

    Uses SHA-256 to produce a reproducible fixed-dimension vector.
    The vector is L2-normalised.
    """
    raw = hashlib.sha256(text.encode("utf-8")).digest()
    floats: List[float] = []
    for i in range(dimension):
        byte_val = raw[i % len(raw)]
        floats.append((byte_val - 128.0) / 128.0)
    mag = math.sqrt(sum(f * f for f in floats)) or 1.0
    return [f / mag for f in floats]


# ---------------------------------------------------------------------------
# Embedding Engine
# ---------------------------------------------------------------------------


class EmbeddingEngine:
    """
    Generates embedding vectors for knowledge artifacts.

    In stub mode (no provider): deterministic hash-based vectors.
    With provider:              delegates to the injected EmbeddingProvider.
    """

    def __init__(
        self,
        provider:  Optional[EmbeddingProvider] = None,
        dimension: int                         = DEFAULT_EMBEDDING_DIMENSION,
    ) -> None:
        self._provider  = provider
        self._dimension = dimension if not provider else provider.dimension
        self._model     = provider.model_name if provider else "stub"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def has_provider(self) -> bool:
        return self._provider is not None

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, artifact_id: str, text: str) -> EmbeddingVector:
        """Generate a single embedding.  Never raises on stub mode."""
        try:
            if self._provider:
                vector = self._provider.embed(text)
            else:
                vector = _stub_embed(text, self._dimension)
        except Exception as exc:
            _log.warning(
                f"Embedding generation error: artifact_id={artifact_id!r} error={exc!r}"
            )
            vector = _stub_embed(text, self._dimension)

        return EmbeddingVector(
            embedding_id = f"emb-{uuid.uuid4().hex[:12]}",
            artifact_id  = artifact_id,
            vector       = tuple(vector),
            dimension    = len(vector),
            model_name   = self._model,
            created_at   = datetime.now(tz=timezone.utc).isoformat(),
        )

    def generate_batch(
        self,
        artifact_ids: List[str],
        texts:        List[str],
    ) -> List[EmbeddingVector]:
        """Generate embeddings for a batch. Falls back to individual generation."""
        if len(artifact_ids) != len(texts):
            raise ValueError("artifact_ids and texts must have the same length")
        try:
            if self._provider:
                vectors = self._provider.embed_batch(texts)
                return [
                    EmbeddingVector(
                        embedding_id = f"emb-{uuid.uuid4().hex[:12]}",
                        artifact_id  = aid,
                        vector       = tuple(v),
                        dimension    = len(v),
                        model_name   = self._model,
                        created_at   = datetime.now(tz=timezone.utc).isoformat(),
                    )
                    for aid, v in zip(artifact_ids, vectors)
                ]
        except Exception as exc:
            _log.warning(f"Batch embedding error: {exc!r}")

        return [self.generate(aid, text) for aid, text in zip(artifact_ids, texts)]

    def set_provider(self, provider: EmbeddingProvider) -> None:
        """Swap the embedding provider at runtime."""
        self._provider  = provider
        self._dimension = provider.dimension
        self._model     = provider.model_name
        _log.info(
            f"Embedding provider set: model={self._model!r} "
            f"dimension={self._dimension}"
        )
