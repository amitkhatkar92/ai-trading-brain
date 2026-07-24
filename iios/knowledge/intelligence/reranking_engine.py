"""
reranking_engine.py — iios.knowledge.intelligence
--------------------------------------------------
Reranks a list of KnowledgeRetrievalItem objects by a secondary score.

Stub strategy: linear combination of original score with a length-based
freshness heuristic derived from metadata.

A RerankingAdapter Protocol allows injection of a cross-encoder or
learned reranking model.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from iios.common.logging.logging_manager import get_logger

from .knowledge_intelligence_response import KnowledgeRetrievalItem

_log = get_logger(__name__)


@runtime_checkable
class RerankingAdapter(Protocol):
    """Protocol for learnable reranking backends (cross-encoder, etc.)."""
    def rerank(
        self,
        query: str,
        items: List[KnowledgeRetrievalItem],
    ) -> List[KnowledgeRetrievalItem]: ...


def _freshness_bonus(metadata: Dict[str, Any]) -> float:
    """Small bonus for artifacts that carry a 'created_at' timestamp field."""
    if "created_at" in metadata or "timestamp" in metadata:
        return 0.02
    return 0.0


class RerankingEngine:
    """
    Reranks retrieval results by a secondary scoring pass.

    Stub mode: penalises lower original ranks, adds a freshness bonus.
    Adapter mode: delegates to an injected RerankingAdapter.
    """

    def __init__(
        self,
        adapter:        Optional[RerankingAdapter] = None,
        decay_per_rank: float                      = 0.005,
    ) -> None:
        self._adapter       = adapter
        self._decay_per_rank = decay_per_rank

    def rerank(
        self,
        query: str,
        items: List[KnowledgeRetrievalItem],
    ) -> List[KnowledgeRetrievalItem]:
        """Return reranked list. Never raises."""
        if not items:
            return []
        try:
            if self._adapter:
                return self._adapter.rerank(query, items)
            return self._stub_rerank(items)
        except Exception as exc:
            _log.warning(f"Reranking failed: {exc!r}")
            return items

    def _stub_rerank(
        self,
        items: List[KnowledgeRetrievalItem],
    ) -> List[KnowledgeRetrievalItem]:
        scored = []
        for item in items:
            new_score = (
                item.score
                - self._decay_per_rank * (item.rank - 1)
                + _freshness_bonus(item.metadata)
            )
            scored.append((max(0.0, new_score), item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            KnowledgeRetrievalItem(
                item_id     = item.item_id,
                artifact_id = item.artifact_id,
                score       = round(score, 6),
                metadata    = item.metadata,
                rank        = rank + 1,
            )
            for rank, (score, item) in enumerate(scored)
        ]

    def set_adapter(self, adapter: RerankingAdapter) -> None:
        self._adapter = adapter
        _log.info("RerankingAdapter registered")
