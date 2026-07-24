"""
knowledge_recommendation_engine.py — iios.knowledge.intelligence
-----------------------------------------------------------------
Generates knowledge recommendations based on similarity and retrieval.

Stub strategy: uses the similarity engine to find top-K similar artifacts
and packages them as a KnowledgeRecommendationReport.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_RECOMMENDATIONS
from .embedding_engine import EmbeddingEngine
from .embedding_registry import EmbeddingRegistry
from .knowledge_intelligence_response import (
    KnowledgeRecommendationItem,
    KnowledgeRecommendationReport,
)
from .knowledge_similarity_engine import KnowledgeSimilarityEngine

_log = get_logger(__name__)


class KnowledgeRecommendationEngine:
    """
    Generates knowledge recommendations for a given artifact.

    Uses the similarity engine to rank related artifacts by cosine proximity.
    """

    def __init__(
        self,
        similarity_engine: KnowledgeSimilarityEngine,
        max_recommendations: int = DEFAULT_MAX_RECOMMENDATIONS,
    ) -> None:
        self._similarity_engine   = similarity_engine
        self._max_recommendations = max_recommendations

    def recommend(
        self,
        knowledge_id: str,
        anchor_artifact_id: str,
        top_k: int = 0,
    ) -> KnowledgeRecommendationReport:
        """Generate recommendations; returns an empty report on failure."""
        k = min(top_k or self._max_recommendations, self._max_recommendations)
        items: List[KnowledgeRecommendationItem] = []
        try:
            report = self._similarity_engine.similarity_report(
                anchor_artifact_id, top_k=k
            )
            if report:
                for entry in report.similar_artifacts:
                    item = KnowledgeRecommendationItem(
                        item_id         = f"rec-{uuid.uuid4().hex[:8]}",
                        artifact_id     = entry["artifact_id"],
                        relevance_score = entry["score"],
                        reason          = "cosine_similarity",
                    )
                    items.append(item)
        except Exception as exc:
            _log.warning(f"Recommendation failed: {exc!r}")

        return KnowledgeRecommendationReport.create(
            knowledge_id = knowledge_id,
            items        = items,
        )
