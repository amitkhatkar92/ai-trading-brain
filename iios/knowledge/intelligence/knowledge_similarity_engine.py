"""
knowledge_similarity_engine.py — iios.knowledge.intelligence
------------------------------------------------------------
Pairwise cosine similarity over embedding vectors.

Returns KnowledgeSimilarityReport for an anchor artifact.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_TOP_K, SimilarityMetric
from .embedding_registry import EmbeddingRegistry
from .knowledge_intelligence_response import KnowledgeSimilarityReport

_log = get_logger(__name__)


def _cosine(a: tuple, b: tuple) -> float:
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


class KnowledgeSimilarityEngine:
    """
    Computes pairwise cosine similarity using the embedding registry.

    No external ML dependency; all arithmetic done in pure Python.
    """

    def __init__(
        self,
        registry: EmbeddingRegistry,
        metric:   SimilarityMetric = SimilarityMetric.COSINE,
        top_k:    int              = DEFAULT_TOP_K,
    ) -> None:
        self._registry = registry
        self._metric   = metric
        self._top_k    = top_k

    def similarity_report(
        self,
        anchor_artifact_id: str,
        top_k:              int = 0,
    ) -> Optional[KnowledgeSimilarityReport]:
        """Find artifacts most similar to the anchor. Returns None on failure."""
        k = top_k or self._top_k
        anchor = self._registry.get(anchor_artifact_id)
        if anchor is None:
            _log.debug(f"Anchor not found: {anchor_artifact_id!r}")
            return None

        all_ids = self._registry.all_artifact_ids()
        scored: List[Dict[str, Any]] = []
        for aid in all_ids:
            if aid == anchor_artifact_id:
                continue
            emb = self._registry.get(aid)
            if emb is None:
                continue
            score = _cosine(anchor.vector, emb.vector)
            scored.append({"artifact_id": aid, "score": round(score, 6)})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return KnowledgeSimilarityReport.create(
            anchor_artifact_id = anchor_artifact_id,
            similar_artifacts  = scored[:k],
            metric             = self._metric,
        )
