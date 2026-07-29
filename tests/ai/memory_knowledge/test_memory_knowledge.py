"""
test_memory_knowledge.py -- tests.ai.memory_knowledge
======================================================
Comprehensive unit tests for A4 – Memory & Knowledge Platform.

Coverage
--------
* Memory lifecycle (store, retrieve, update, delete, expiry, scopes)
* Knowledge lifecycle (add, remove, update, search, collections)
* Retrieval framework (keyword, hybrid, recency, filtering)
* Ranking strategies (scoring, ranking, edge cases)
* Policy evaluation (retention, retrieval, privacy, expiration, ranking)
* Event generation (all 10 event types, pub/sub, counts)
* Knowledge graph (nodes, relationships, traversal, shortest path)
* Vector abstractions (ABCs are not concrete — tested via interface contracts)
* Snapshot (capture, immutability, counts)
* Container (DI wiring, idempotent build)
* Gateway API completeness (all public methods callable)
* Exception hierarchy (error codes, inheritance)
* Thread safety (concurrent memory writes)
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, FrozenSet, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def gateway():
    from iios.ai.memory_knowledge.gateway import MemoryKnowledgeGateway
    gw = MemoryKnowledgeGateway()
    gw.initialize()
    gw.start()
    return gw


@pytest.fixture
def memory_manager():
    from iios.ai.memory_knowledge.memory import MemoryManager
    return MemoryManager()


@pytest.fixture
def knowledge_manager():
    from iios.ai.memory_knowledge.knowledge import KnowledgeManager
    return KnowledgeManager()


@pytest.fixture
def retrieval_engine(memory_manager, knowledge_manager):
    from iios.ai.memory_knowledge.retrieval import RetrievalEngine
    return RetrievalEngine(
        memory_manager    = memory_manager,
        knowledge_manager = knowledge_manager,
    )


@pytest.fixture
def event_bus():
    from iios.ai.memory_knowledge.events import MemoryEventBus
    return MemoryEventBus()


@pytest.fixture
def knowledge_graph(event_bus):
    from iios.ai.memory_knowledge.graph import KnowledgeGraph
    return KnowledgeGraph(event_bus)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Memory Lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestMemoryLifecycle:
    """Memory store, retrieve, update, delete, and scope behaviour."""

    def test_store_returns_entry_with_id(self, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        entry = memory_manager.store("hello", scope=MemoryScope.SESSION)
        assert entry.entry_id
        assert entry.content == "hello"
        assert entry.scope == MemoryScope.SESSION

    def test_retrieve_existing_entry(self, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        entry = memory_manager.store("data", scope=MemoryScope.WORKING)
        found = memory_manager.retrieve(entry.entry_id)
        assert found.content == "data"

    def test_retrieve_missing_raises(self, memory_manager):
        from iios.ai.memory_knowledge.exceptions import AIMemoryNotFoundError
        with pytest.raises(AIMemoryNotFoundError):
            memory_manager.retrieve("nonexistent-id")

    def test_update_content(self, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        entry   = memory_manager.store("v1", scope=MemoryScope.SESSION)
        updated = memory_manager.update(entry.entry_id, "v2")
        assert updated.content == "v2"
        assert updated.metadata.version == 2

    def test_update_missing_raises(self, memory_manager):
        from iios.ai.memory_knowledge.exceptions import AIMemoryNotFoundError
        with pytest.raises(AIMemoryNotFoundError):
            memory_manager.update("bad-id", "x")

    def test_delete_entry(self, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        from iios.ai.memory_knowledge.exceptions import AIMemoryNotFoundError
        entry = memory_manager.store("bye", scope=MemoryScope.SESSION)
        memory_manager.delete(entry.entry_id)
        with pytest.raises(AIMemoryNotFoundError):
            memory_manager.retrieve(entry.entry_id)

    def test_delete_missing_raises(self, memory_manager):
        from iios.ai.memory_knowledge.exceptions import AIMemoryNotFoundError
        with pytest.raises(AIMemoryNotFoundError):
            memory_manager.delete("missing-id")

    def test_retrieve_by_scope(self, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        memory_manager.store("s1", scope=MemoryScope.SESSION)
        memory_manager.store("s2", scope=MemoryScope.SESSION)
        memory_manager.store("l1", scope=MemoryScope.LONG_TERM)
        session_entries = memory_manager.retrieve_by_scope(MemoryScope.SESSION)
        assert len(session_entries) == 2
        assert all(e.scope == MemoryScope.SESSION for e in session_entries)

    def test_retrieve_by_owner(self, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        memory_manager.store("a", scope=MemoryScope.SESSION, owner_id="alice")
        memory_manager.store("b", scope=MemoryScope.SESSION, owner_id="alice")
        memory_manager.store("c", scope=MemoryScope.SESSION, owner_id="bob")
        alice_entries = memory_manager.retrieve_by_owner("alice")
        assert len(alice_entries) == 2

    def test_retrieve_by_tags(self, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        memory_manager.store("t1", scope=MemoryScope.SESSION, tags=frozenset({"nifty", "market"}))
        memory_manager.store("t2", scope=MemoryScope.SESSION, tags=frozenset({"nifty"}))
        memory_manager.store("t3", scope=MemoryScope.SESSION, tags=frozenset({"forex"}))
        results = memory_manager.retrieve_by_tags(frozenset({"nifty"}))
        assert len(results) == 2

    def test_expiry_raises_on_retrieve(self, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        from iios.ai.memory_knowledge.exceptions import AIMemoryExpiredError
        past = time.time() - 1
        entry = memory_manager.store("old", scope=MemoryScope.WORKING, expires_at=past)
        with pytest.raises(AIMemoryExpiredError):
            memory_manager.retrieve(entry.entry_id)

    def test_evict_expired_returns_count(self, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        past = time.time() - 1
        memory_manager.store("x", scope=MemoryScope.SESSION, expires_at=past)
        memory_manager.store("y", scope=MemoryScope.SESSION, expires_at=past)
        memory_manager.store("z", scope=MemoryScope.SESSION)
        count = memory_manager.evict_expired()
        assert count == 2

    def test_all_memory_scopes_supported(self, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        for scope in MemoryScope:
            e = memory_manager.store(f"test_{scope.value}", scope=scope)
            assert e.scope == scope


# ─────────────────────────────────────────────────────────────────────────────
# 2. Knowledge Lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestKnowledgeLifecycle:
    """Knowledge add, remove, update, search, and collections."""

    def test_add_returns_item_with_id(self, knowledge_manager):
        item = knowledge_manager.add("NIFTY analysis", "content here")
        assert item.item_id
        assert item.title == "NIFTY analysis"

    def test_add_duplicate_id_raises(self, knowledge_manager):
        from iios.ai.memory_knowledge.exceptions import AIKnowledgeAlreadyExistsError
        kid = str(uuid.uuid4())
        knowledge_manager.add("T1", "c1", item_id=kid)
        with pytest.raises(AIKnowledgeAlreadyExistsError):
            knowledge_manager.add("T2", "c2", item_id=kid)

    def test_blank_title_raises(self, knowledge_manager):
        from iios.ai.memory_knowledge.exceptions import AIKnowledgeValidationError
        with pytest.raises(AIKnowledgeValidationError):
            knowledge_manager.add("   ", "content")

    def test_remove_item(self, knowledge_manager):
        from iios.ai.memory_knowledge.exceptions import AIKnowledgeNotFoundError
        item = knowledge_manager.add("To Remove", "data")
        knowledge_manager.remove(item.item_id)
        with pytest.raises(AIKnowledgeNotFoundError):
            knowledge_manager.get(item.item_id)

    def test_remove_missing_raises(self, knowledge_manager):
        from iios.ai.memory_knowledge.exceptions import AIKnowledgeNotFoundError
        with pytest.raises(AIKnowledgeNotFoundError):
            knowledge_manager.remove("missing")

    def test_update_knowledge(self, knowledge_manager):
        item    = knowledge_manager.add("Update Test", "v1")
        updated = knowledge_manager.update(item.item_id, "v2")
        assert updated.content == "v2"
        assert updated.metadata.version == 2

    def test_get_existing(self, knowledge_manager):
        item  = knowledge_manager.add("Get Test", "some fact")
        found = knowledge_manager.get(item.item_id)
        assert found.title == "Get Test"

    def test_get_missing_raises(self, knowledge_manager):
        from iios.ai.memory_knowledge.exceptions import AIKnowledgeNotFoundError
        with pytest.raises(AIKnowledgeNotFoundError):
            knowledge_manager.get("nonexistent")

    def test_search_by_keyword(self, knowledge_manager):
        knowledge_manager.add("NIFTY 50 analysis", "bull run")
        knowledge_manager.add("BANKNIFTY forecast", "neutral")
        knowledge_manager.add("Crude oil report", "bearish")
        results = knowledge_manager.search(keyword="NIFTY")
        assert len(results) == 2

    def test_search_by_category(self, knowledge_manager):
        from iios.ai.memory_knowledge.core import KnowledgeCategory
        knowledge_manager.add("Fact 1", "f", category=KnowledgeCategory.FACT)
        knowledge_manager.add("Doc 1",  "d", category=KnowledgeCategory.DOCUMENT)
        knowledge_manager.add("Fact 2", "f2", category=KnowledgeCategory.FACT)
        results = knowledge_manager.search(category=KnowledgeCategory.FACT)
        assert len(results) == 2

    def test_search_by_tags(self, knowledge_manager):
        knowledge_manager.add("T1", "c1", tags=frozenset({"alpha", "beta"}))
        knowledge_manager.add("T2", "c2", tags=frozenset({"alpha"}))
        knowledge_manager.add("T3", "c3", tags=frozenset({"gamma"}))
        results = knowledge_manager.search(tags=frozenset({"alpha"}))
        assert len(results) == 2

    def test_create_and_list_collections(self, knowledge_manager):
        from iios.ai.memory_knowledge.core import KnowledgeCategory
        col = knowledge_manager.create_collection("Research", KnowledgeCategory.RESEARCH)
        assert col.name == "Research"
        cols = knowledge_manager.list_collections()
        assert len(cols) == 1

    def test_all_knowledge_categories_supported(self, knowledge_manager):
        from iios.ai.memory_knowledge.core import KnowledgeCategory
        for cat in KnowledgeCategory:
            item = knowledge_manager.add(f"Item {cat.value}", "data", category=cat)
            assert item.category == cat


# ─────────────────────────────────────────────────────────────────────────────
# 3. Retrieval Framework
# ─────────────────────────────────────────────────────────────────────────────

class TestRetrievalFramework:
    """RetrievalEngine, RetrievalRequest, RetrievalResult."""

    def test_retrieve_from_knowledge(self, retrieval_engine, knowledge_manager):
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest
        knowledge_manager.add("NIFTY market analysis", "bull regime")
        request = RetrievalRequest.create("NIFTY", top_k=5)
        result  = retrieval_engine.retrieve(request)
        assert result.count >= 1
        assert result.hits[0].source == "knowledge"

    def test_retrieve_from_memory(self, retrieval_engine, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest
        memory_manager.store("session context data", scope=MemoryScope.SESSION)
        request = RetrievalRequest.create("session", top_k=5)
        result  = retrieval_engine.retrieve(request)
        assert result.count >= 1

    def test_retrieval_respects_top_k(self, retrieval_engine, knowledge_manager):
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest
        for i in range(10):
            knowledge_manager.add(f"Item {i}", f"content {i}")
        request = RetrievalRequest.create("item", top_k=3)
        result  = retrieval_engine.retrieve(request)
        assert result.count <= 3

    def test_retrieval_result_has_request_id(self, retrieval_engine):
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest
        request = RetrievalRequest.create("anything")
        result  = retrieval_engine.retrieve(request)
        assert result.request_id == request.request_id

    def test_retrieval_with_min_score_filters(self, retrieval_engine, knowledge_manager):
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest
        knowledge_manager.add("NIFTY analysis deep dive", "content")
        request = RetrievalRequest.create("NIFTY", min_score=0.99)
        result  = retrieval_engine.retrieve(request)
        assert all(h.score >= 0.99 for h in result.hits)

    def test_retrieval_strategy_name_recorded(self, retrieval_engine):
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest
        request = RetrievalRequest.create("test")
        result  = retrieval_engine.retrieve(request)
        assert result.strategy == "keyword"

    def test_retrieval_with_strategy_swap(self, retrieval_engine, knowledge_manager):
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest, HybridRankingStrategy
        knowledge_manager.add("hybrid test item", "hybrid content")
        engine2 = retrieval_engine.with_strategy(HybridRankingStrategy())
        request = RetrievalRequest.create("hybrid", top_k=5)
        result  = engine2.retrieve(request)
        assert result.strategy == "hybrid"

    def test_retrieval_empty_store_returns_zero(self, retrieval_engine):
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest
        request = RetrievalRequest.create("no match here xyz")
        result  = retrieval_engine.retrieve(request)
        assert result.count == 0

    def test_retrieval_include_memory_flag(self, retrieval_engine, knowledge_manager, memory_manager):
        from iios.ai.memory_knowledge.core import MemoryScope
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest
        knowledge_manager.add("shared knowledge item", "data")
        memory_manager.store("shared memory item", scope=MemoryScope.SHARED)
        # only knowledge
        req_k = RetrievalRequest.create("shared", include_memory=False)
        res_k = retrieval_engine.retrieve(req_k)
        assert all(h.source == "knowledge" for h in res_k.hits)

    def test_retrieval_request_top_k_minimum_one(self):
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest
        req = RetrievalRequest.create("q", top_k=0)
        assert req.top_k == 1


# ─────────────────────────────────────────────────────────────────────────────
# 4. Ranking Strategies
# ─────────────────────────────────────────────────────────────────────────────

class TestRankingStrategies:
    """Score correctness and ranking order for all strategies."""

    def test_keyword_exact_match_score_one(self):
        from iios.ai.memory_knowledge.retrieval import KeywordRankingStrategy
        s = KeywordRankingStrategy()
        assert s.score("nifty", None, "nifty") == pytest.approx(1.0)

    def test_keyword_no_match_score_zero(self):
        from iios.ai.memory_knowledge.retrieval import KeywordRankingStrategy
        s = KeywordRankingStrategy()
        assert s.score("xyz", None, "abc def") == pytest.approx(0.0)

    def test_keyword_partial_match(self):
        from iios.ai.memory_knowledge.retrieval import KeywordRankingStrategy
        s = KeywordRankingStrategy()
        score = s.score("nifty banknifty", None, "nifty analysis")
        assert 0.0 < score < 1.0

    def test_keyword_empty_query_score_zero(self):
        from iios.ai.memory_knowledge.retrieval import KeywordRankingStrategy
        s = KeywordRankingStrategy()
        assert s.score("", None, "something") == pytest.approx(0.0)

    def test_semantic_stub_returns_half(self):
        from iios.ai.memory_knowledge.retrieval import SemanticRankingStrategy
        s = SemanticRankingStrategy()
        assert s.score("any query", "any content") == pytest.approx(0.5)

    def test_hybrid_weights_sum_to_one_required(self):
        from iios.ai.memory_knowledge.retrieval import HybridRankingStrategy
        with pytest.raises(ValueError):
            HybridRankingStrategy(keyword_weight=0.3, semantic_weight=0.3)

    def test_hybrid_score_is_weighted_average(self):
        from iios.ai.memory_knowledge.retrieval import HybridRankingStrategy
        h = HybridRankingStrategy(keyword_weight=1.0, semantic_weight=0.0)
        # with 100% keyword weight, result equals keyword score
        assert h.score("nifty", None, "nifty") == pytest.approx(1.0)

    def test_recency_recent_item_scores_near_one(self):
        from iios.ai.memory_knowledge.retrieval import RecencyRankingStrategy
        s = RecencyRankingStrategy()
        content = {"created_at": time.time() - 60}  # 1 minute ago
        score = s.score("q", content)
        assert score > 0.99

    def test_recency_old_item_scores_low(self):
        from iios.ai.memory_knowledge.retrieval import RecencyRankingStrategy
        s = RecencyRankingStrategy()
        content = {"created_at": time.time() - 365 * 86400}  # 1 year ago
        score = s.score("q", content)
        assert score < 0.01

    def test_rank_returns_sorted_by_score_descending(self):
        from iios.ai.memory_knowledge.retrieval import KeywordRankingStrategy
        s = KeywordRankingStrategy()
        candidates = [
            ("id1", "knowledge", "one word", "alpha beta gamma", frozenset()),
            ("id2", "knowledge", "alpha",    "alpha",            frozenset()),
            ("id3", "knowledge", "unrelated","totally unrelated", frozenset()),
        ]
        ranked = s.rank("alpha beta gamma", candidates, min_score=0.0, top_k=10)
        scores = [r[5] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_top_k_respected(self):
        from iios.ai.memory_knowledge.retrieval import KeywordRankingStrategy
        s = KeywordRankingStrategy()
        candidates = [
            (f"id{i}", "k", f"item {i}", f"item {i}", frozenset())
            for i in range(20)
        ]
        ranked = s.rank("item", candidates, top_k=5)
        assert len(ranked) <= 5


# ─────────────────────────────────────────────────────────────────────────────
# 5. Policy Evaluation
# ─────────────────────────────────────────────────────────────────────────────

class TestPolicyEvaluation:
    """Retention, retrieval, privacy, expiration, and ranking policies."""

    def _make_entry(self, scope, owner="system", expires_at=None):
        from iios.ai.memory_knowledge.core import MemoryScope
        from iios.ai.memory_knowledge.memory import MemoryManager
        mm = MemoryManager()
        return mm.store("test", scope=scope, owner_id=owner, expires_at=expires_at)

    def test_never_expire_retains_all(self):
        from iios.ai.memory_knowledge.policy import NeverExpireRetentionPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = NeverExpireRetentionPolicy()
        entry  = self._make_entry(MemoryScope.SESSION)
        assert policy.should_retain(entry) is True

    def test_ttl_retention_retains_live(self):
        from iios.ai.memory_knowledge.policy import TTLRetentionPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = TTLRetentionPolicy()
        entry  = self._make_entry(MemoryScope.SESSION)
        assert policy.should_retain(entry) is True

    def test_ttl_retention_rejects_expired(self):
        from iios.ai.memory_knowledge.policy import TTLRetentionPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = TTLRetentionPolicy()
        entry  = self._make_entry(MemoryScope.SESSION, expires_at=time.time() - 1)
        assert policy.should_retain(entry) is False

    def test_scope_retention_correct_scope(self):
        from iios.ai.memory_knowledge.policy import ScopeRetentionPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = ScopeRetentionPolicy(MemoryScope.SESSION)
        entry  = self._make_entry(MemoryScope.SESSION)
        assert policy.should_retain(entry) is True

    def test_scope_retention_wrong_scope(self):
        from iios.ai.memory_knowledge.policy import ScopeRetentionPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = ScopeRetentionPolicy(MemoryScope.WORKING)
        entry  = self._make_entry(MemoryScope.SESSION)
        assert policy.should_retain(entry) is False

    def test_unrestricted_retrieval_allows_all(self):
        from iios.ai.memory_knowledge.policy import UnrestrictedRetrievalPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = UnrestrictedRetrievalPolicy()
        entry  = self._make_entry(MemoryScope.SESSION)
        assert policy.is_retrievable(entry, "anyone") is True

    def test_owner_only_retrieval_matches(self):
        from iios.ai.memory_knowledge.policy import OwnerOnlyRetrievalPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = OwnerOnlyRetrievalPolicy()
        entry  = self._make_entry(MemoryScope.SESSION, owner="alice")
        assert policy.is_retrievable(entry, "alice") is True
        assert policy.is_retrievable(entry, "bob")   is False

    def test_permissive_privacy_allows_all(self):
        from iios.ai.memory_knowledge.policy import PermissivePrivacyPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = PermissivePrivacyPolicy()
        entry  = self._make_entry(MemoryScope.WORKING, owner="agent-1")
        assert policy.is_accessible(entry, "other-agent") is True

    def test_scope_restricted_privacy_working(self):
        from iios.ai.memory_knowledge.policy import ScopeRestrictedPrivacyPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = ScopeRestrictedPrivacyPolicy()
        entry  = self._make_entry(MemoryScope.WORKING, owner="alice")
        assert policy.is_accessible(entry, "alice") is True
        assert policy.is_accessible(entry, "bob")   is False

    def test_scope_restricted_privacy_shared(self):
        from iios.ai.memory_knowledge.policy import ScopeRestrictedPrivacyPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = ScopeRestrictedPrivacyPolicy()
        entry  = self._make_entry(MemoryScope.SHARED, owner="system")
        assert policy.is_accessible(entry, "anyone") is True

    def test_no_expiration_returns_none(self):
        from iios.ai.memory_knowledge.policy import NoExpirationPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = NoExpirationPolicy()
        assert policy.expires_at(MemoryScope.SESSION) is None

    def test_ttl_expiration_working_scope(self):
        from iios.ai.memory_knowledge.policy import TTLExpirationPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = TTLExpirationPolicy()
        exp = policy.expires_at(MemoryScope.WORKING)
        assert exp is not None
        assert exp > time.time()

    def test_ttl_expiration_long_term_is_none(self):
        from iios.ai.memory_knowledge.policy import TTLExpirationPolicy
        from iios.ai.memory_knowledge.core import MemoryScope
        policy = TTLExpirationPolicy()
        assert policy.expires_at(MemoryScope.LONG_TERM) is None

    def test_default_ranking_policy_returns_keyword(self):
        from iios.ai.memory_knowledge.policy import DefaultRankingPolicy
        policy = DefaultRankingPolicy()
        assert policy.preferred_strategy() == "keyword"

    def test_semantic_ranking_policy(self):
        from iios.ai.memory_knowledge.policy import SemanticRankingPolicy
        assert SemanticRankingPolicy().preferred_strategy() == "semantic"

    def test_hybrid_ranking_policy(self):
        from iios.ai.memory_knowledge.policy import HybridRankingPolicy
        assert HybridRankingPolicy().preferred_strategy() == "hybrid"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Event Generation
# ─────────────────────────────────────────────────────────────────────────────

class TestEventGeneration:
    """All 10 event types, pub/sub, and published_count."""

    def test_memory_created_event_published(self, event_bus):
        from iios.ai.memory_knowledge.events import MemoryEventType
        from iios.ai.memory_knowledge.memory import MemoryManager
        from iios.ai.memory_knowledge.core   import MemoryScope
        received = []
        event_bus.subscribe(MemoryEventType.MEMORY_CREATED, received.append)
        mm = MemoryManager(event_bus=event_bus)
        mm.store("hello", scope=MemoryScope.SESSION)
        assert len(received) == 1

    def test_memory_updated_event_published(self, event_bus):
        from iios.ai.memory_knowledge.events import MemoryEventType
        from iios.ai.memory_knowledge.memory import MemoryManager
        from iios.ai.memory_knowledge.core   import MemoryScope
        received = []
        event_bus.subscribe(MemoryEventType.MEMORY_UPDATED, received.append)
        mm    = MemoryManager(event_bus=event_bus)
        entry = mm.store("v1", scope=MemoryScope.SESSION)
        mm.update(entry.entry_id, "v2")
        assert len(received) == 1

    def test_memory_deleted_event_published(self, event_bus):
        from iios.ai.memory_knowledge.events import MemoryEventType
        from iios.ai.memory_knowledge.memory import MemoryManager
        from iios.ai.memory_knowledge.core   import MemoryScope
        received = []
        event_bus.subscribe(MemoryEventType.MEMORY_DELETED, received.append)
        mm    = MemoryManager(event_bus=event_bus)
        entry = mm.store("data", scope=MemoryScope.SESSION)
        mm.delete(entry.entry_id)
        assert len(received) == 1

    def test_memory_expired_event_published(self, event_bus):
        from iios.ai.memory_knowledge.events import MemoryEventType
        from iios.ai.memory_knowledge.memory import MemoryManager
        from iios.ai.memory_knowledge.core   import MemoryScope
        from iios.ai.memory_knowledge.exceptions import AIMemoryExpiredError
        received = []
        event_bus.subscribe(MemoryEventType.MEMORY_EXPIRED, received.append)
        mm    = MemoryManager(event_bus=event_bus)
        entry = mm.store("old", scope=MemoryScope.SESSION, expires_at=time.time() - 1)
        with pytest.raises(AIMemoryExpiredError):
            mm.retrieve(entry.entry_id)
        assert len(received) == 1

    def test_knowledge_added_event_published(self, event_bus):
        from iios.ai.memory_knowledge.events     import MemoryEventType
        from iios.ai.memory_knowledge.knowledge  import KnowledgeManager
        received = []
        event_bus.subscribe(MemoryEventType.KNOWLEDGE_ADDED, received.append)
        km = KnowledgeManager(event_bus=event_bus)
        km.add("New fact", "some data")
        assert len(received) == 1

    def test_knowledge_removed_event_published(self, event_bus):
        from iios.ai.memory_knowledge.events     import MemoryEventType
        from iios.ai.memory_knowledge.knowledge  import KnowledgeManager
        received = []
        event_bus.subscribe(MemoryEventType.KNOWLEDGE_REMOVED, received.append)
        km   = KnowledgeManager(event_bus=event_bus)
        item = km.add("Temp item", "data")
        km.remove(item.item_id)
        assert len(received) == 1

    def test_knowledge_updated_event_published(self, event_bus):
        from iios.ai.memory_knowledge.events     import MemoryEventType
        from iios.ai.memory_knowledge.knowledge  import KnowledgeManager
        received = []
        event_bus.subscribe(MemoryEventType.KNOWLEDGE_UPDATED, received.append)
        km   = KnowledgeManager(event_bus=event_bus)
        item = km.add("Update me", "v1")
        km.update(item.item_id, "v2")
        assert len(received) == 1

    def test_retrieval_completed_event_published(self, event_bus):
        from iios.ai.memory_knowledge.events     import MemoryEventType
        from iios.ai.memory_knowledge.retrieval  import RetrievalEngine, RetrievalRequest
        received = []
        event_bus.subscribe(MemoryEventType.RETRIEVAL_COMPLETED, received.append)
        engine  = RetrievalEngine(event_bus=event_bus)
        engine.retrieve(RetrievalRequest.create("test"))
        assert len(received) == 1

    def test_graph_traversed_event_published(self, event_bus):
        from iios.ai.memory_knowledge.events import MemoryEventType
        from iios.ai.memory_knowledge.graph  import KnowledgeGraph, KnowledgeNode
        received = []
        event_bus.subscribe(MemoryEventType.GRAPH_TRAVERSED, received.append)
        g    = KnowledgeGraph(event_bus)
        node = KnowledgeNode.create("TestNode")
        g.add_node(node)
        g.traverse_bfs(node.node_id, max_depth=2)
        assert len(received) == 1

    def test_event_bus_published_count_increments(self, event_bus):
        from iios.ai.memory_knowledge.events.memory_events import MemoryCreatedEvent
        initial = event_bus.published_count
        event_bus.publish(MemoryCreatedEvent.create("eid", "session", "owner"))
        assert event_bus.published_count == initial + 1

    def test_event_bus_unsubscribe(self, event_bus):
        from iios.ai.memory_knowledge.events import MemoryEventType
        received = []
        handler = received.append
        event_bus.subscribe(MemoryEventType.MEMORY_CREATED, handler)
        event_bus.unsubscribe(MemoryEventType.MEMORY_CREATED, handler)
        event_bus.publish(
            __import__(
                "iios.ai.memory_knowledge.events.memory_events",
                fromlist=["MemoryCreatedEvent"]
            ).MemoryCreatedEvent.create("x", "session", "sys")
        )
        assert len(received) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 7. Knowledge Graph
# ─────────────────────────────────────────────────────────────────────────────

class TestKnowledgeGraph:
    """Nodes, relationships, BFS traversal, shortest path."""

    def test_add_and_get_node(self, knowledge_graph):
        from iios.ai.memory_knowledge.graph import KnowledgeNode
        node = KnowledgeNode.create("Entity A")
        knowledge_graph.add_node(node)
        found = knowledge_graph.get_node(node.node_id)
        assert found.label == "Entity A"

    def test_get_missing_node_returns_none(self, knowledge_graph):
        assert knowledge_graph.get_node("nonexistent") is None

    def test_add_relationship(self, knowledge_graph):
        from iios.ai.memory_knowledge.graph import KnowledgeNode, KnowledgeRelationship
        a = KnowledgeNode.create("A")
        b = KnowledgeNode.create("B")
        knowledge_graph.add_node(a)
        knowledge_graph.add_node(b)
        rel = KnowledgeRelationship.create(a.node_id, b.node_id, "RELATED_TO")
        knowledge_graph.add_relationship(rel)
        assert knowledge_graph.relationship_count() == 1

    def test_neighbours_out(self, knowledge_graph):
        from iios.ai.memory_knowledge.graph import KnowledgeNode, KnowledgeRelationship
        a = KnowledgeNode.create("A")
        b = KnowledgeNode.create("B")
        c = KnowledgeNode.create("C")
        for n in (a, b, c):
            knowledge_graph.add_node(n)
        knowledge_graph.add_relationship(
            KnowledgeRelationship.create(a.node_id, b.node_id, "R1")
        )
        knowledge_graph.add_relationship(
            KnowledgeRelationship.create(a.node_id, c.node_id, "R2")
        )
        neighbours = knowledge_graph.neighbours_out(a.node_id)
        neighbour_ids = {n.node_id for n in neighbours}
        assert neighbour_ids == {b.node_id, c.node_id}

    def test_neighbours_in(self, knowledge_graph):
        from iios.ai.memory_knowledge.graph import KnowledgeNode, KnowledgeRelationship
        a = KnowledgeNode.create("A")
        b = KnowledgeNode.create("B")
        knowledge_graph.add_node(a)
        knowledge_graph.add_node(b)
        knowledge_graph.add_relationship(
            KnowledgeRelationship.create(a.node_id, b.node_id, "POINTS_TO")
        )
        ins = knowledge_graph.neighbours_in(b.node_id)
        assert ins[0].node_id == a.node_id

    def test_bfs_traversal_respects_max_depth(self, knowledge_graph):
        from iios.ai.memory_knowledge.graph import KnowledgeNode, KnowledgeRelationship
        nodes = [KnowledgeNode.create(f"N{i}") for i in range(5)]
        for n in nodes:
            knowledge_graph.add_node(n)
        # chain: 0->1->2->3->4
        for i in range(4):
            knowledge_graph.add_relationship(
                KnowledgeRelationship.create(nodes[i].node_id, nodes[i+1].node_id, "NEXT")
            )
        result = knowledge_graph.traverse_bfs(nodes[0].node_id, max_depth=2)
        assert len(result) == 3  # start + 2 hops

    def test_shortest_path_direct(self, knowledge_graph):
        from iios.ai.memory_knowledge.graph import KnowledgeNode, KnowledgeRelationship
        a = KnowledgeNode.create("A")
        b = KnowledgeNode.create("B")
        knowledge_graph.add_node(a)
        knowledge_graph.add_node(b)
        knowledge_graph.add_relationship(
            KnowledgeRelationship.create(a.node_id, b.node_id, "DIRECT")
        )
        path = knowledge_graph.shortest_path(a.node_id, b.node_id)
        assert path is not None
        assert path.length == 1

    def test_shortest_path_no_path_returns_none(self, knowledge_graph):
        from iios.ai.memory_knowledge.graph import KnowledgeNode
        a = KnowledgeNode.create("A")
        b = KnowledgeNode.create("B")
        knowledge_graph.add_node(a)
        knowledge_graph.add_node(b)
        assert knowledge_graph.shortest_path(a.node_id, b.node_id) is None

    def test_shortest_path_same_node(self, knowledge_graph):
        from iios.ai.memory_knowledge.graph import KnowledgeNode
        a = KnowledgeNode.create("A")
        knowledge_graph.add_node(a)
        path = knowledge_graph.shortest_path(a.node_id, a.node_id)
        assert path is not None
        assert path.length == 0

    def test_remove_node_cascades_relationships(self, knowledge_graph):
        from iios.ai.memory_knowledge.graph import KnowledgeNode, KnowledgeRelationship
        a = KnowledgeNode.create("A")
        b = KnowledgeNode.create("B")
        knowledge_graph.add_node(a)
        knowledge_graph.add_node(b)
        knowledge_graph.add_relationship(
            KnowledgeRelationship.create(a.node_id, b.node_id, "LINK")
        )
        knowledge_graph.remove_node(a.node_id)
        assert knowledge_graph.node_count() == 1
        assert knowledge_graph.relationship_count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# 8. Vector Abstractions
# ─────────────────────────────────────────────────────────────────────────────

class TestVectorAbstractions:
    """ABCs are abstract; verify they cannot be instantiated directly."""

    def test_vector_store_is_abstract(self):
        from iios.ai.memory_knowledge.vector import VectorStore
        with pytest.raises(TypeError):
            VectorStore()  # type: ignore

    def test_embedding_service_is_abstract(self):
        from iios.ai.memory_knowledge.vector import EmbeddingService
        with pytest.raises(TypeError):
            EmbeddingService()  # type: ignore

    def test_similarity_search_is_abstract(self):
        from iios.ai.memory_knowledge.vector import SimilaritySearch
        with pytest.raises(TypeError):
            SimilaritySearch()  # type: ignore

    def test_vector_index_is_abstract(self):
        from iios.ai.memory_knowledge.vector import VectorIndex
        with pytest.raises(TypeError):
            VectorIndex()  # type: ignore

    def test_concrete_store_implements_all_methods(self):
        """InMemoryStore satisfies the full MemoryStore ABC."""
        from iios.ai.memory_knowledge.memory import InMemoryStore
        from iios.ai.memory_knowledge.core   import MemoryScope, MemoryEntry
        store = InMemoryStore()
        entry = MemoryEntry.create("content", scope=MemoryScope.SESSION)
        store.put(entry)
        assert store.get(entry.entry_id) is not None
        assert store.count() == 1
        store.delete(entry.entry_id)
        assert store.count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# 9. Snapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshot:
    def test_snapshot_captures_counts(self, gateway):
        from iios.ai.memory_knowledge.core import MemoryScope, KnowledgeCategory
        gateway.store_memory("mem1", scope=MemoryScope.SESSION)
        gateway.add_knowledge("Know 1", "content", category=KnowledgeCategory.FACT)
        snap = gateway.snapshot()
        assert snap.memory_count    >= 1
        assert snap.knowledge_count >= 1

    def test_snapshot_is_immutable(self, gateway):
        snap = gateway.snapshot()
        with pytest.raises((AttributeError, TypeError, Exception)):
            snap.memory_count = 999  # type: ignore

    def test_snapshot_has_unique_id(self, gateway):
        s1 = gateway.snapshot()
        s2 = gateway.snapshot()
        assert s1.snapshot_id != s2.snapshot_id

    def test_snapshot_graph_counts(self, gateway):
        from iios.ai.memory_knowledge.graph import KnowledgeNode, KnowledgeRelationship
        a = KnowledgeNode.create("A")
        b = KnowledgeNode.create("B")
        gateway.add_graph_node(a)
        gateway.add_graph_node(b)
        gateway.add_graph_relationship(
            KnowledgeRelationship.create(a.node_id, b.node_id, "LINKED")
        )
        snap = gateway.snapshot()
        assert snap.graph_node_count    >= 2
        assert snap.graph_rel_count     >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 10. Container DI Wiring
# ─────────────────────────────────────────────────────────────────────────────

class TestContainerDIWiring:
    def test_build_is_idempotent(self):
        from iios.ai.memory_knowledge.container import MemoryKnowledgeContainer
        c = MemoryKnowledgeContainer()
        c.build()
        c.build()  # second call should not raise
        assert c.memory_manager is not None

    def test_all_components_available_after_build(self):
        from iios.ai.memory_knowledge.container import MemoryKnowledgeContainer
        c = MemoryKnowledgeContainer()
        c.build()
        assert c.event_bus         is not None
        assert c.memory_manager    is not None
        assert c.knowledge_manager is not None
        assert c.knowledge_graph   is not None
        assert c.retrieval_engine  is not None
        assert c.retention_policy  is not None
        assert c.retrieval_policy  is not None
        assert c.ranking_policy    is not None
        assert c.privacy_policy    is not None
        assert c.expiration_policy is not None

    def test_access_before_build_raises(self):
        from iios.ai.memory_knowledge.container import MemoryKnowledgeContainer
        c = MemoryKnowledgeContainer()
        with pytest.raises(RuntimeError):
            _ = c.memory_manager

    def test_custom_store_injected(self):
        from iios.ai.memory_knowledge.container import MemoryKnowledgeContainer
        from iios.ai.memory_knowledge.memory    import InMemoryStore
        store = InMemoryStore()
        c = MemoryKnowledgeContainer(memory_store=store)
        c.build()
        assert c.memory_manager is not None


# ─────────────────────────────────────────────────────────────────────────────
# 11. Gateway API Completeness
# ─────────────────────────────────────────────────────────────────────────────

class TestGatewayAPICompleteness:
    """Verify all public methods are callable end-to-end via the gateway."""

    def test_store_and_retrieve_memory(self, gateway):
        from iios.ai.memory_knowledge.core import MemoryScope
        e = gateway.store_memory("payload", scope=MemoryScope.SESSION)
        r = gateway.retrieve_memory(e.entry_id)
        assert r.content == "payload"

    def test_update_memory(self, gateway):
        from iios.ai.memory_knowledge.core import MemoryScope
        e = gateway.store_memory("old", scope=MemoryScope.SESSION)
        u = gateway.update_memory(e.entry_id, "new")
        assert u.content == "new"

    def test_delete_memory(self, gateway):
        from iios.ai.memory_knowledge.core import MemoryScope
        from iios.ai.memory_knowledge.exceptions import AIMemoryNotFoundError
        e = gateway.store_memory("del", scope=MemoryScope.SESSION)
        gateway.delete_memory(e.entry_id)
        with pytest.raises(AIMemoryNotFoundError):
            gateway.retrieve_memory(e.entry_id)

    def test_list_memory_by_scope(self, gateway):
        from iios.ai.memory_knowledge.core import MemoryScope
        gateway.store_memory("x", scope=MemoryScope.WORKING)
        entries = gateway.list_memory(scope=MemoryScope.WORKING)
        assert len(entries) >= 1

    def test_add_and_get_knowledge(self, gateway):
        item = gateway.add_knowledge("API test item", "content")
        got  = gateway.get_knowledge(item.item_id)
        assert got.title == "API test item"

    def test_remove_knowledge(self, gateway):
        from iios.ai.memory_knowledge.exceptions import AIKnowledgeNotFoundError
        item = gateway.add_knowledge("To be removed", "data")
        gateway.remove_knowledge(item.item_id)
        with pytest.raises(AIKnowledgeNotFoundError):
            gateway.get_knowledge(item.item_id)

    def test_search_knowledge(self, gateway):
        gateway.add_knowledge("NIFTY deep analysis", "bull")
        results = gateway.search_knowledge("NIFTY")
        assert len(results) >= 1

    def test_list_knowledge(self, gateway):
        from iios.ai.memory_knowledge.core import KnowledgeCategory
        gateway.add_knowledge("Listed item", "data", category=KnowledgeCategory.FACT)
        items = gateway.list_knowledge(category=KnowledgeCategory.FACT)
        assert len(items) >= 1

    def test_retrieve_via_request(self, gateway):
        from iios.ai.memory_knowledge.retrieval import RetrievalRequest
        gateway.add_knowledge("Retrieval target item", "data")
        req    = RetrievalRequest.create("retrieval target", top_k=5)
        result = gateway.retrieve(req)
        assert result.count >= 1

    def test_create_and_list_collections(self, gateway):
        from iios.ai.memory_knowledge.core import KnowledgeCategory
        gateway.create_collection("ML Papers", KnowledgeCategory.RESEARCH)
        cols = gateway.list_collections()
        assert any(c.name == "ML Papers" for c in cols)

    def test_graph_nodes_and_traversal(self, gateway):
        from iios.ai.memory_knowledge.graph import KnowledgeNode, KnowledgeRelationship
        a = KnowledgeNode.create("Alpha")
        b = KnowledgeNode.create("Beta")
        gateway.add_graph_node(a)
        gateway.add_graph_node(b)
        gateway.add_graph_relationship(
            KnowledgeRelationship.create(a.node_id, b.node_id, "IMPLIES")
        )
        result = gateway.traverse_graph(a.node_id, max_depth=2)
        assert len(result) == 2

    def test_health_returns_dict(self, gateway):
        h = gateway.health()
        assert "memory_entries" in h
        assert "knowledge_items" in h

    def test_status_returns_uptime(self, gateway):
        s = gateway.status()
        assert s["uptime_s"] is not None
        assert s["uptime_s"] >= 0

    def test_evict_expired_memory(self, gateway):
        from iios.ai.memory_knowledge.core import MemoryScope
        gateway.store_memory("old", scope=MemoryScope.SESSION, expires_at=time.time() - 1)
        count = gateway.evict_expired_memory()
        assert count >= 1

    def test_shortest_path_via_gateway(self, gateway):
        from iios.ai.memory_knowledge.graph import KnowledgeNode, KnowledgeRelationship
        a = KnowledgeNode.create("X")
        b = KnowledgeNode.create("Y")
        gateway.add_graph_node(a)
        gateway.add_graph_node(b)
        gateway.add_graph_relationship(
            KnowledgeRelationship.create(a.node_id, b.node_id, "LINKS")
        )
        path = gateway.shortest_path(a.node_id, b.node_id)
        assert path is not None and path.length == 1


# ─────────────────────────────────────────────────────────────────────────────
# 12. Exception Hierarchy
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptionHierarchy:
    @pytest.mark.parametrize("exc_cls,expected_code", [
        ("AIMemoryException",            "AI-900"),
        ("AIMemoryNotFoundError",        "AI-901"),
        ("AIMemoryAlreadyExistsError",   "AI-902"),
        ("AIMemoryExpiredError",         "AI-903"),
        ("AIMemoryStorageError",         "AI-904"),
        ("AIMemoryCapacityError",        "AI-905"),
        ("AIKnowledgeException",         "AI-910"),
        ("AIKnowledgeNotFoundError",     "AI-911"),
        ("AIKnowledgeAlreadyExistsError","AI-912"),
        ("AIKnowledgeValidationError",   "AI-913"),
        ("AIRetrievalException",         "AI-920"),
        ("AIRetrievalFailedError",       "AI-921"),
        ("AINoResultsError",             "AI-922"),
        ("AIVectorStoreException",       "AI-930"),
        ("AIVectorStoreNotReadyError",   "AI-931"),
        ("AIEmbeddingServiceException",  "AI-940"),
        ("AIMemoryPolicyViolationError", "AI-950"),
    ])
    def test_error_codes(self, exc_cls, expected_code):
        import iios.ai.memory_knowledge.exceptions as exc_mod
        cls = getattr(exc_mod, exc_cls)
        err = cls()
        assert hasattr(err, "error_code") and err.error_code == expected_code

    def test_all_memory_exceptions_extend_ai_exception(self):
        from iios.ai.foundation.exceptions import AIException
        import iios.ai.memory_knowledge.exceptions as exc_mod
        for name in exc_mod.__all__:
            cls = getattr(exc_mod, name)
            assert issubclass(cls, AIException), f"{name} must extend AIException"


# ─────────────────────────────────────────────────────────────────────────────
# 13. Thread Safety
# ─────────────────────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_memory_writes(self):
        from iios.ai.memory_knowledge.memory import MemoryManager
        from iios.ai.memory_knowledge.core   import MemoryScope
        mm      = MemoryManager()
        errors  = []
        entries = []

        def writer():
            try:
                e = mm.store(f"content-{threading.get_ident()}", scope=MemoryScope.SESSION)
                entries.append(e)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert mm.count() == 20

    def test_concurrent_knowledge_writes(self):
        from iios.ai.memory_knowledge.knowledge import KnowledgeManager
        km     = KnowledgeManager()
        errors = []

        def writer(idx):
            try:
                km.add(f"Item {idx} unique-{uuid.uuid4()}", f"content {idx}")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert km.count() == 20
