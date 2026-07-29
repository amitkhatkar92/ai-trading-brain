"""
retrieval_engine.py -- iios.ai.memory_knowledge.retrieval
==========================================================
:class:`RetrievalEngine` — M2 engine orchestrating keyword, semantic,
and hybrid retrieval across memory and knowledge stores.
"""
from __future__ import annotations

import time
from typing import Any, List, Optional, Tuple

from ..core.knowledge_category import KnowledgeCategory
from ..events.event_bus        import MemoryEventBus
from ..events.memory_events    import RankingCompletedEvent, RetrievalCompletedEvent
from ..exceptions              import AIRetrievalFailedError
from ..knowledge.knowledge_manager import KnowledgeManager
from ..memory.memory_manager        import MemoryManager
from .ranking_strategy              import KeywordRankingStrategy, RankingStrategy
from .retrieval_metadata            import RetrievalMetadata
from .retrieval_request             import RetrievalRequest
from .retrieval_result              import RetrievalHit, RetrievalResult

SYSTEM_ID = "iios:ai:memory_knowledge:retrieval_engine"


class RetrievalEngine:
    """
    Orchestrates retrieval across memory and knowledge stores.

    Usage::

        engine = RetrievalEngine(memory_manager, knowledge_manager)
        request = RetrievalRequest.create("market regime analysis", top_k=5)
        result  = engine.retrieve(request)
    """

    def __init__(
        self,
        memory_manager:    Optional[MemoryManager]    = None,
        knowledge_manager: Optional[KnowledgeManager] = None,
        strategy:          Optional[RankingStrategy]  = None,
        event_bus:         Optional[MemoryEventBus]   = None,
    ) -> None:
        self._memory    = memory_manager    or MemoryManager()
        self._knowledge = knowledge_manager or KnowledgeManager()
        self._strategy  = strategy          or KeywordRankingStrategy()
        self._event_bus = event_bus         or MemoryEventBus()

    # ── Primary API ───────────────────────────────────────────────────────────

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Execute the retrieval request; return ranked results."""
        t0 = time.time()
        try:
            candidates = self._collect_candidates(request)
            ranked     = self._strategy.rank(
                query      = request.query,
                candidates = candidates,
                min_score  = request.min_score,
                top_k      = request.top_k,
            )
        except Exception as exc:
            raise AIRetrievalFailedError(str(exc)) from exc

        hits = [
            RetrievalHit(
                hit_id  = row[0],
                source  = row[1],
                content = row[2],
                score   = row[5],
                title   = row[3],
                tags    = row[4],
            )
            for row in ranked
        ]
        result = RetrievalResult.create(
            request_id  = request.request_id,
            hits        = hits,
            strategy    = self._strategy.STRATEGY_NAME,
            total_found = len(candidates),
        )
        duration_ms = (time.time() - t0) * 1000.0

        self._event_bus.publish(
            RetrievalCompletedEvent.create(
                request.request_id,
                len(hits),
                self._strategy.STRATEGY_NAME,
            )
        )
        self._event_bus.publish(
            RankingCompletedEvent.create(
                request.request_id,
                len(hits),
                self._strategy.STRATEGY_NAME,
            )
        )
        return result

    def with_strategy(self, strategy: RankingStrategy) -> "RetrievalEngine":
        """Return a new RetrievalEngine using the given ranking strategy."""
        return RetrievalEngine(
            memory_manager    = self._memory,
            knowledge_manager = self._knowledge,
            strategy          = strategy,
            event_bus         = self._event_bus,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _collect_candidates(
        self, request: RetrievalRequest
    ) -> List[Tuple[str, str, Any, str, Any]]:
        """Collect (id, source, content, title, tags) tuples."""
        candidates: List[Tuple[str, str, Any, str, Any]] = []

        if request.include_memory:
            for entry in self._memory.list_all():
                if request.tags and not request.tags.issubset(entry.tags):
                    continue
                candidates.append(
                    (entry.entry_id, "memory", entry.content, "", entry.tags)
                )

        if request.include_knowledge:
            items = self._knowledge.search(
                category=request.category,
                tags    =request.tags if request.tags else None,
                keyword =None,
            )
            for item in items:
                candidates.append(
                    (item.item_id, "knowledge", item.content, item.title, item.tags)
                )

        return candidates
