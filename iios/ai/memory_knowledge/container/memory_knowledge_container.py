"""
memory_knowledge_container.py -- iios.ai.memory_knowledge.container
====================================================================
:class:`MemoryKnowledgeContainer` — DI composition root for A4.

Wires every A4 component into a coherent unit; ``build()`` is idempotent.
"""
from __future__ import annotations

from typing import Optional

from ..events.event_bus              import MemoryEventBus
from ..graph.knowledge_graph         import KnowledgeGraph
from ..knowledge.knowledge_manager   import KnowledgeManager
from ..memory.memory_manager         import MemoryManager
from ..memory.memory_store           import InMemoryStore, MemoryStore
from ..policy.policies               import (
    ExpirationPolicy,
    NoExpirationPolicy,
    NeverExpireRetentionPolicy,
    PermissivePrivacyPolicy,
    PrivacyPolicy,
    RetentionPolicy,
    RetrievalPolicy,
    RankingPolicy,
    DefaultRankingPolicy,
    UnrestrictedRetrievalPolicy,
)
from ..retrieval.ranking_strategy    import KeywordRankingStrategy, RankingStrategy
from ..retrieval.retrieval_engine    import RetrievalEngine


class MemoryKnowledgeContainer:
    """
    DI composition root for the A4 Memory & Knowledge Platform.

    Usage::

        container = MemoryKnowledgeContainer()
        container.build()
        container.memory_manager.store(...)
    """

    def __init__(
        self,
        memory_store:      Optional[MemoryStore]      = None,
        ranking_strategy:  Optional[RankingStrategy]  = None,
        retention_policy:  Optional[RetentionPolicy]  = None,
        retrieval_policy:  Optional[RetrievalPolicy]  = None,
        ranking_policy:    Optional[RankingPolicy]    = None,
        privacy_policy:    Optional[PrivacyPolicy]    = None,
        expiration_policy: Optional[ExpirationPolicy] = None,
    ) -> None:
        self._memory_store_arg      = memory_store
        self._ranking_strategy_arg  = ranking_strategy
        self._retention_policy_arg  = retention_policy
        self._retrieval_policy_arg  = retrieval_policy
        self._ranking_policy_arg    = ranking_policy
        self._privacy_policy_arg    = privacy_policy
        self._expiration_policy_arg = expiration_policy

        self._built: bool = False

        # Components (set by build())
        self._event_bus:          Optional[MemoryEventBus]    = None
        self._memory_store:       Optional[MemoryStore]       = None
        self._memory_manager:     Optional[MemoryManager]     = None
        self._knowledge_manager:  Optional[KnowledgeManager]  = None
        self._knowledge_graph:    Optional[KnowledgeGraph]    = None
        self._retrieval_engine:   Optional[RetrievalEngine]   = None
        self._retention_policy:   Optional[RetentionPolicy]   = None
        self._retrieval_policy:   Optional[RetrievalPolicy]   = None
        self._ranking_policy:     Optional[RankingPolicy]     = None
        self._privacy_policy:     Optional[PrivacyPolicy]     = None
        self._expiration_policy:  Optional[ExpirationPolicy]  = None

    def build(self) -> None:
        """Wire all components.  Safe to call multiple times."""
        if self._built:
            return

        self._event_bus         = MemoryEventBus()
        self._memory_store      = self._memory_store_arg or InMemoryStore()
        self._memory_manager    = MemoryManager(self._memory_store, self._event_bus)
        self._knowledge_manager = KnowledgeManager(self._event_bus)
        self._knowledge_graph   = KnowledgeGraph(self._event_bus)

        ranking_strategy = self._ranking_strategy_arg or KeywordRankingStrategy()
        self._retrieval_engine  = RetrievalEngine(
            memory_manager    = self._memory_manager,
            knowledge_manager = self._knowledge_manager,
            strategy          = ranking_strategy,
            event_bus         = self._event_bus,
        )

        self._retention_policy  = self._retention_policy_arg  or NeverExpireRetentionPolicy()
        self._retrieval_policy  = self._retrieval_policy_arg  or UnrestrictedRetrievalPolicy()
        self._ranking_policy    = self._ranking_policy_arg    or DefaultRankingPolicy()
        self._privacy_policy    = self._privacy_policy_arg    or PermissivePrivacyPolicy()
        self._expiration_policy = self._expiration_policy_arg or NoExpirationPolicy()

        self._built = True

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def event_bus(self) -> MemoryEventBus:
        self._require_built()
        return self._event_bus  # type: ignore[return-value]

    @property
    def memory_manager(self) -> MemoryManager:
        self._require_built()
        return self._memory_manager  # type: ignore[return-value]

    @property
    def knowledge_manager(self) -> KnowledgeManager:
        self._require_built()
        return self._knowledge_manager  # type: ignore[return-value]

    @property
    def knowledge_graph(self) -> KnowledgeGraph:
        self._require_built()
        return self._knowledge_graph  # type: ignore[return-value]

    @property
    def retrieval_engine(self) -> RetrievalEngine:
        self._require_built()
        return self._retrieval_engine  # type: ignore[return-value]

    @property
    def retention_policy(self) -> RetentionPolicy:
        self._require_built()
        return self._retention_policy  # type: ignore[return-value]

    @property
    def retrieval_policy(self) -> RetrievalPolicy:
        self._require_built()
        return self._retrieval_policy  # type: ignore[return-value]

    @property
    def ranking_policy(self) -> RankingPolicy:
        self._require_built()
        return self._ranking_policy  # type: ignore[return-value]

    @property
    def privacy_policy(self) -> PrivacyPolicy:
        self._require_built()
        return self._privacy_policy  # type: ignore[return-value]

    @property
    def expiration_policy(self) -> ExpirationPolicy:
        self._require_built()
        return self._expiration_policy  # type: ignore[return-value]

    def _require_built(self) -> None:
        if not self._built:
            raise RuntimeError("MemoryKnowledgeContainer.build() has not been called")
