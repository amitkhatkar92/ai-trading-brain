"""
test_knowledge_intelligence_m4.py
==================================
Comprehensive tests for C14 M4: Knowledge Intelligence Framework.

Test classes (33):
  1  TestConstants
  2  TestExceptions
  3  TestKnowledgeEntity
  4  TestKnowledgeRelationship
  5  TestKnowledgeGraph
  6  TestEmbeddingEngine
  7  TestVectorIndex
  8  TestVectorIndexEngine
  9  TestEntityResolutionEngine
  10 TestRelationshipEngine
  11 TestSemanticAnalysisEngine
  12 TestEmbeddingRegistry
  13 TestVectorStoreManager
  14 TestRetrievalEngine
  15 TestHybridSearchEngine
  16 TestRerankingEngine
  17 TestKnowledgeSimilarityEngine
  18 TestKnowledgeClusteringEngine
  19 TestKnowledgeReasoningEngine
  20 TestKnowledgeEnrichmentEngine
  21 TestKnowledgeMemoryEngine
  22 TestKnowledgeRecommendationEngine
  23 TestKnowledgeIntelligenceValidator
  24 TestKnowledgeIntelligenceStatistics
  25 TestKnowledgeIntelligenceHistory
  26 TestIntelligenceEvents
  27 TestKnowledgeIntelligenceFactory
  28 TestEngineLifecycle
  29 TestEngineProcess
  30 TestEngineRetrieval
  31 TestEngineIntrospection
  32 TestConcurrency
  33 TestRegression
"""
import dataclasses
import threading
import uuid
from typing import Any, Dict, List

import pytest

from iios.knowledge.intelligence.constants import (
    ClusteringAlgorithm,
    EntityType,
    IntelligenceEngineState,
    IntelligenceEventType,
    IntelligenceValidationCode,
    IntelligenceWorkflowType,
    RelationshipType,
    RetrievalMode,
    SimilarityMetric,
)
from iios.knowledge.intelligence.embedding_engine import (
    EmbeddingEngine,
    EmbeddingVector,
    _stub_embed,
)
from iios.knowledge.intelligence.embedding_registry import EmbeddingRegistry
from iios.knowledge.intelligence.entity_resolution_engine import EntityResolutionEngine
from iios.knowledge.intelligence.exceptions import (
    EmbeddingError,
    EnrichmentError,
    EntityResolutionError,
    IntelligenceCapacityError,
    IntelligenceNotRunningError,
    IntelligenceValidationError,
    KnowledgeGraphError,
    KnowledgeIntelligenceError,
    RetrievalError,
    VectorIndexError,
)
from iios.knowledge.intelligence.hybrid_search_engine import HybridSearchEngine
from iios.knowledge.intelligence.knowledge_clustering_engine import (
    KnowledgeClusteringEngine,
)
from iios.knowledge.intelligence.knowledge_enrichment_engine import (
    KnowledgeEnrichmentEngine,
)
from iios.knowledge.intelligence.knowledge_graph_builder import KnowledgeGraphBuilder
from iios.knowledge.intelligence.knowledge_graph_engine import (
    KnowledgeEntity,
    KnowledgeGraph,
    KnowledgeRelationship,
)
from iios.knowledge.intelligence.knowledge_graph_registry import (
    KnowledgeGraphRegistry,
)
from iios.knowledge.intelligence.knowledge_intelligence_context import (
    KnowledgeIntelligenceContext,
)
from iios.knowledge.intelligence.knowledge_intelligence_engine import (
    KnowledgeIntelligenceEngine,
)
from iios.knowledge.intelligence.knowledge_intelligence_events import (
    IntelligenceEvent,
    IntelligenceEventBus,
)
from iios.knowledge.intelligence.knowledge_intelligence_factory import (
    KnowledgeIntelligenceFactory,
)
from iios.knowledge.intelligence.knowledge_intelligence_history import (
    KnowledgeIntelligenceHistory,
)
from iios.knowledge.intelligence.knowledge_intelligence_manager import (
    KnowledgeIntelligenceManager,
)
from iios.knowledge.intelligence.knowledge_intelligence_registry import (
    KnowledgeIntelligenceRegistry,
)
from iios.knowledge.intelligence.knowledge_intelligence_request import (
    KnowledgeIntelligenceRequest,
)
from iios.knowledge.intelligence.knowledge_intelligence_response import (
    EnterpriseMemorySummary,
    KnowledgeIntelligenceReport,
    KnowledgeIntelligenceResponse,
    KnowledgeReasoningContext,
    KnowledgeRecommendationItem,
    KnowledgeRecommendationReport,
    KnowledgeRetrievalItem,
    KnowledgeRetrievalResult,
    KnowledgeSimilarityReport,
)
from iios.knowledge.intelligence.knowledge_intelligence_statistics import (
    KnowledgeIntelligenceStatistics,
)
from iios.knowledge.intelligence.knowledge_intelligence_validator import (
    IntelligenceValidationReport,
    KnowledgeIntelligenceValidator,
    ValidationResult,
)
from iios.knowledge.intelligence.knowledge_memory_engine import KnowledgeMemoryEngine
from iios.knowledge.intelligence.knowledge_reasoning_engine import (
    KnowledgeReasoningEngine,
)
from iios.knowledge.intelligence.knowledge_recommendation_engine import (
    KnowledgeRecommendationEngine,
)
from iios.knowledge.intelligence.knowledge_similarity_engine import (
    KnowledgeSimilarityEngine,
)
from iios.knowledge.intelligence.relationship_engine import RelationshipEngine
from iios.knowledge.intelligence.reranking_engine import RerankingEngine
from iios.knowledge.intelligence.retrieval_engine import RetrievalEngine
from iios.knowledge.intelligence.semantic_analysis_engine import SemanticAnalysisEngine
from iios.knowledge.intelligence.vector_index_engine import (
    VectorIndex,
    VectorIndexEngine,
    VectorSearchResult,
)
from iios.knowledge.intelligence.vector_store_manager import VectorStoreManager


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════

def _artifact(name: str = "test", **kwargs) -> Dict[str, Any]:
    """Build a minimal artifact dict."""
    base = {"artifact_id": f"art-{uuid.uuid4().hex[:8]}", "name": name}
    base.update(kwargs)
    return base


def _make_engine() -> KnowledgeIntelligenceEngine:
    return KnowledgeIntelligenceEngine.create_default()


def _started_engine() -> KnowledgeIntelligenceEngine:
    eng = _make_engine()
    eng.start()
    return eng


# ════════════════════════════════════════════════════════════════════════
# 1. TestConstants
# ════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_engine_states_count(self):
        assert len(IntelligenceEngineState) == 12

    def test_workflow_types_count(self):
        assert len(IntelligenceWorkflowType) == 8

    def test_entity_types_count(self):
        assert len(EntityType) == 12

    def test_relationship_types_count(self):
        assert len(RelationshipType) == 12

    def test_retrieval_modes_count(self):
        assert len(RetrievalMode) == 5

    def test_similarity_metrics_count(self):
        assert len(SimilarityMetric) == 5

    def test_clustering_algorithms_count(self):
        assert len(ClusteringAlgorithm) == 4

    def test_intelligence_event_types_count(self):
        assert len(IntelligenceEventType) == 10

    def test_validation_codes_count(self):
        assert len(IntelligenceValidationCode) == 8


# ════════════════════════════════════════════════════════════════════════
# 2. TestExceptions
# ════════════════════════════════════════════════════════════════════════


class TestExceptions:
    def test_base_error_code(self):
        e = KnowledgeIntelligenceError("msg")
        assert "KIF-000" in str(e.args) or e.error_code == "KIF-000"

    def test_not_running_error(self):
        e = IntelligenceNotRunningError()
        assert e.error_code == "KIF-001"

    def test_validation_error(self):
        e = IntelligenceValidationError("bad")
        assert e.error_code == "KIF-002"

    def test_graph_error_has_graph_id(self):
        e = KnowledgeGraphError("bad graph", graph_id="g-123")
        assert e.graph_id == "g-123"
        assert e.error_code == "KIF-003"

    def test_entity_resolution_error(self):
        e = EntityResolutionError("fail", entity_id="e-1")
        assert e.entity_id == "e-1"
        assert e.error_code == "KIF-004"

    def test_embedding_error(self):
        e = EmbeddingError("fail", artifact_id="a-1")
        assert e.artifact_id == "a-1"
        assert e.error_code == "KIF-005"

    def test_vector_index_error(self):
        e = VectorIndexError("fail", index_id="i-1")
        assert e.index_id == "i-1"
        assert e.error_code == "KIF-006"

    def test_retrieval_error(self):
        e = RetrievalError("fail")
        assert e.error_code == "KIF-007"

    def test_enrichment_error(self):
        e = EnrichmentError("fail")
        assert e.error_code == "KIF-008"

    def test_capacity_error_has_limit(self):
        e = IntelligenceCapacityError(limit=1000)
        assert e.limit == 1000
        assert e.error_code == "KIF-009"

    def test_hierarchy(self):
        assert issubclass(IntelligenceNotRunningError, KnowledgeIntelligenceError)
        assert issubclass(KnowledgeGraphError, KnowledgeIntelligenceError)
        assert issubclass(EmbeddingError, KnowledgeIntelligenceError)


# ════════════════════════════════════════════════════════════════════════
# 3. TestKnowledgeEntity
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeEntity:
    def test_create(self):
        e = KnowledgeEntity.create("price:100", EntityType.METRIC, "art-1")
        assert e.entity_id.startswith("ent-")
        assert e.entity_type == EntityType.METRIC
        assert e.confidence == 1.0

    def test_frozen(self):
        e = KnowledgeEntity.create("x", EntityType.CONCEPT, "a")
        with pytest.raises((AttributeError, TypeError)):
            e.name = "y"  # type: ignore

    def test_to_dict(self):
        e = KnowledgeEntity.create("x", EntityType.ASSET, "a")
        d = e.to_dict()
        assert d["entity_type"] == "asset"
        assert "entity_id" in d

    def test_aliases_stored_as_tuple(self):
        e = KnowledgeEntity.create(
            "x", EntityType.RISK, "a", aliases=["alias1", "alias2"]
        )
        assert isinstance(e.aliases, tuple)
        assert len(e.aliases) == 2

    def test_attributes_stored(self):
        e = KnowledgeEntity.create(
            "x", EntityType.SIGNAL, "a", attributes={"key": "val"}
        )
        assert e.attributes["key"] == "val"


# ════════════════════════════════════════════════════════════════════════
# 4. TestKnowledgeRelationship
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeRelationship:
    def test_create(self):
        r = KnowledgeRelationship.create("e1", "e2", RelationshipType.CAUSES)
        assert r.relationship_id.startswith("rel-")
        assert r.relationship_type == RelationshipType.CAUSES

    def test_frozen(self):
        r = KnowledgeRelationship.create("e1", "e2", RelationshipType.FOLLOWS)
        with pytest.raises((AttributeError, TypeError)):
            r.weight = 0.5  # type: ignore

    def test_to_dict(self):
        r = KnowledgeRelationship.create("e1", "e2", RelationshipType.REFERENCES)
        d = r.to_dict()
        assert d["relationship_type"] == "references"
        assert d["source_entity_id"] == "e1"


# ════════════════════════════════════════════════════════════════════════
# 5. TestKnowledgeGraph
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeGraph:
    def _entity(self) -> KnowledgeEntity:
        return KnowledgeEntity.create("x", EntityType.CONCEPT, "art-1")

    def test_add_entity_increments_count(self):
        g = KnowledgeGraph()
        assert g.node_count == 0
        g.add_entity(self._entity())
        assert g.node_count == 1

    def test_add_idempotent(self):
        g = KnowledgeGraph()
        e = self._entity()
        g.add_entity(e)
        g.add_entity(e)   # second add must not increment
        assert g.node_count == 1

    def test_add_relationship(self):
        g  = KnowledgeGraph()
        e1 = self._entity()
        e2 = self._entity()
        g.add_entity(e1)
        g.add_entity(e2)
        rel = KnowledgeRelationship.create(
            e1.entity_id, e2.entity_id, RelationshipType.CAUSES
        )
        g.add_relationship(rel)
        assert g.edge_count == 1

    def test_get_entity(self):
        g = KnowledgeGraph()
        e = self._entity()
        g.add_entity(e)
        assert g.get_entity(e.entity_id) is e

    def test_get_neighbors(self):
        g  = KnowledgeGraph()
        e1 = self._entity()
        e2 = self._entity()
        g.add_entity(e1)
        g.add_entity(e2)
        rel = KnowledgeRelationship.create(
            e1.entity_id, e2.entity_id, RelationshipType.CONTAINS
        )
        g.add_relationship(rel)
        neighbors = g.get_neighbors(e1.entity_id)
        assert e2 in neighbors

    def test_capacity_error(self):
        g = KnowledgeGraph(max_entities=1)
        g.add_entity(self._entity())
        with pytest.raises(IntelligenceCapacityError):
            g.add_entity(self._entity())

    def test_to_dict(self):
        g = KnowledgeGraph(graph_id="g-test")
        d = g.to_dict()
        assert d["graph_id"] == "g-test"


# ════════════════════════════════════════════════════════════════════════
# 6. TestEmbeddingEngine
# ════════════════════════════════════════════════════════════════════════


class TestEmbeddingEngine:
    def test_stub_mode_returns_vector(self):
        eng = EmbeddingEngine(dimension=64)
        ev  = eng.generate("art-1", "hello world")
        assert isinstance(ev, EmbeddingVector)
        assert ev.dimension == 64
        assert len(ev.vector) == 64

    def test_deterministic_stub(self):
        eng  = EmbeddingEngine(dimension=32)
        ev1  = eng.generate("a", "same text")
        ev2  = eng.generate("b", "same text")
        assert ev1.vector == ev2.vector

    def test_different_texts_different_vectors(self):
        eng = EmbeddingEngine(dimension=32)
        ev1 = eng.generate("a", "text one")
        ev2 = eng.generate("b", "text two")
        assert ev1.vector != ev2.vector

    def test_model_name_stub(self):
        eng = EmbeddingEngine()
        assert eng.model_name == "stub"

    def test_batch_generation(self):
        eng  = EmbeddingEngine(dimension=16)
        evs  = eng.generate_batch(["a1", "a2"], ["text one", "text two"])
        assert len(evs) == 2
        assert all(isinstance(e, EmbeddingVector) for e in evs)

    def test_provider_injection(self):
        class FakeProvider:
            def embed(self, text):
                return [0.1] * 8
            def embed_batch(self, texts):
                return [[0.1] * 8 for _ in texts]
            @property
            def dimension(self):
                return 8
            @property
            def model_name(self):
                return "fake"

        eng = EmbeddingEngine()
        eng.set_provider(FakeProvider())
        ev = eng.generate("art-x", "anything")
        assert ev.model_name == "fake"
        assert ev.dimension == 8

    def test_stub_vector_normalised(self):
        import math
        v   = _stub_embed("hello", 32)
        mag = math.sqrt(sum(x**2 for x in v))
        assert abs(mag - 1.0) < 1e-6


# ════════════════════════════════════════════════════════════════════════
# 7. TestVectorIndex
# ════════════════════════════════════════════════════════════════════════


class TestVectorIndex:
    def test_upsert_and_count(self):
        idx = VectorIndex()
        idx.upsert("a1", [0.5, 0.5], {})
        assert idx.count() == 1

    def test_search_returns_results(self):
        idx = VectorIndex()
        idx.upsert("a1", [1.0, 0.0], {"name": "art1"})
        idx.upsert("a2", [0.0, 1.0], {"name": "art2"})
        results = idx.search([1.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0].artifact_id == "a1"

    def test_cosine_ranking(self):
        idx = VectorIndex()
        idx.upsert("best",  [1.0, 0.0],  {})
        idx.upsert("worst", [0.0, 1.0],  {})
        idx.upsert("mid",   [0.7, 0.7],  {})
        results = idx.search([1.0, 0.0], top_k=3)
        assert results[0].artifact_id == "best"
        assert results[0].rank == 1

    def test_delete(self):
        idx = VectorIndex()
        idx.upsert("a1", [1.0, 0.0], {})
        assert idx.delete("a1") is True
        assert idx.count() == 0

    def test_delete_nonexistent(self):
        idx = VectorIndex()
        assert idx.delete("missing") is False

    def test_capacity_error(self):
        idx = VectorIndex(max_vectors=1)
        idx.upsert("a1", [1.0], {})
        with pytest.raises(IntelligenceCapacityError):
            idx.upsert("a2", [0.5], {})


# ════════════════════════════════════════════════════════════════════════
# 8. TestVectorIndexEngine
# ════════════════════════════════════════════════════════════════════════


class TestVectorIndexEngine:
    def test_upsert_and_search(self):
        eng = VectorIndexEngine()
        eng.upsert("a1", [1.0, 0.0], {})
        results = eng.search([1.0, 0.0], top_k=1)
        assert results[0].artifact_id == "a1"

    def test_delete(self):
        eng = VectorIndexEngine()
        eng.upsert("a1", [1.0, 0.0], {})
        assert eng.delete("a1") is True
        assert eng.count() == 0

    def test_adapter_injection(self):
        results_store = []

        class FakeAdapter:
            def upsert(self, id, vector, meta):
                pass
            def search(self, q, k):
                return [VectorSearchResult("fa1", 0.9, {}, 1)]
            def delete(self, id):
                return True
            def count(self):
                return 99

        eng = VectorIndexEngine()
        eng.set_adapter(FakeAdapter())
        assert eng.has_adapter is True
        res = eng.search([0.0, 1.0], top_k=1)
        assert res[0].artifact_id == "fa1"
        assert eng.count() == 99


# ════════════════════════════════════════════════════════════════════════
# 9. TestEntityResolutionEngine
# ════════════════════════════════════════════════════════════════════════


class TestEntityResolutionEngine:
    def test_extracts_entities(self):
        eng      = EntityResolutionEngine()
        artifact = {"artifact_id": "a1", "price": 100.0, "symbol": "NIFTY"}
        entities = eng.extract("a1", artifact)
        assert len(entities) > 0

    def test_entity_has_source_id(self):
        eng      = EntityResolutionEngine()
        artifact = {"artifact_id": "a1", "signal": "buy"}
        entities = eng.extract("a1", artifact)
        for e in entities:
            assert e.source_artifact_id == "a1"

    def test_batch_deduplication(self):
        eng = EntityResolutionEngine()
        a1  = {"artifact_id": "a1", "price": 100}
        a2  = {"artifact_id": "a2", "price": 100}  # same price value
        entities = eng.extract_batch([a1, a2])
        # price:100 should appear only once
        names = [e.name for e in entities]
        assert names.count("price:100") == 1

    def test_never_raises_on_empty(self):
        eng      = EntityResolutionEngine()
        entities = eng.extract("a1", {})
        assert isinstance(entities, list)

    def test_keyword_classification(self):
        eng      = EntityResolutionEngine()
        artifact = {"artifact_id": "a1", "risk_value": 0.5}
        entities = eng.extract("a1", artifact)
        types    = {e.entity_type for e in entities}
        assert EntityType.RISK in types


# ════════════════════════════════════════════════════════════════════════
# 10. TestRelationshipEngine
# ════════════════════════════════════════════════════════════════════════


class TestRelationshipEngine:
    def test_discover_references_from_same_artifact(self):
        eng = RelationshipEngine()
        e1  = KnowledgeEntity.create("e1", EntityType.METRIC, "art-1")
        e2  = KnowledgeEntity.create("e2", EntityType.ASSET,  "art-1")
        e3  = KnowledgeEntity.create("e3", EntityType.RISK,   "art-1")
        rels = eng.discover([e1, e2, e3])
        # C(3,2) = 3 pairs
        assert len(rels) == 3
        for r in rels:
            assert r.relationship_type == RelationshipType.REFERENCES

    def test_no_cross_artifact_relationships_in_stub(self):
        eng = RelationshipEngine()
        e1  = KnowledgeEntity.create("e1", EntityType.METRIC, "art-1")
        e2  = KnowledgeEntity.create("e2", EntityType.ASSET,  "art-2")
        rels = eng.discover([e1, e2])
        # Different artifacts → no relationship in co-occurrence stub
        assert len(rels) == 0

    def test_never_raises_on_empty(self):
        eng  = RelationshipEngine()
        rels = eng.discover([])
        assert rels == []


# ════════════════════════════════════════════════════════════════════════
# 11. TestSemanticAnalysisEngine
# ════════════════════════════════════════════════════════════════════════


class TestSemanticAnalysisEngine:
    def test_returns_keywords(self):
        eng    = SemanticAnalysisEngine()
        result = eng.analyze("buy nifty signal trend")
        assert "keywords" in result
        assert len(result["keywords"]) > 0

    def test_char_count(self):
        eng    = SemanticAnalysisEngine()
        text   = "hello world"
        result = eng.analyze(text)
        assert result["char_count"] == len(text)

    def test_empty_text(self):
        eng    = SemanticAnalysisEngine()
        result = eng.analyze("")
        assert result["token_count"] == 0

    def test_artifact_text_extraction(self):
        eng   = SemanticAnalysisEngine()
        art   = {"name": "NIFTY", "price": 20000, "signal": "buy"}
        text  = eng.artifact_text(art)
        assert "NIFTY" in text


# ════════════════════════════════════════════════════════════════════════
# 12. TestEmbeddingRegistry
# ════════════════════════════════════════════════════════════════════════


class TestEmbeddingRegistry:
    def _make_emb(self, aid: str = "a1") -> EmbeddingVector:
        eng = EmbeddingEngine(dimension=16)
        return eng.generate(aid, "test text")

    def test_store_and_get(self):
        reg = EmbeddingRegistry()
        emb = self._make_emb("a1")
        reg.store(emb)
        assert reg.get("a1") is emb

    def test_has(self):
        reg = EmbeddingRegistry()
        emb = self._make_emb("a1")
        reg.store(emb)
        assert reg.has("a1") is True
        assert reg.has("missing") is False

    def test_count(self):
        reg = EmbeddingRegistry()
        reg.store(self._make_emb("a1"))
        reg.store(self._make_emb("a2"))
        assert reg.count() == 2

    def test_remove(self):
        reg = EmbeddingRegistry()
        reg.store(self._make_emb("a1"))
        assert reg.remove("a1") is True
        assert reg.has("a1") is False

    def test_capacity_error(self):
        reg = EmbeddingRegistry(max_embeddings=1)
        reg.store(self._make_emb("a1"))
        with pytest.raises(IntelligenceCapacityError):
            reg.store(self._make_emb("a2"))


# ════════════════════════════════════════════════════════════════════════
# 13. TestVectorStoreManager
# ════════════════════════════════════════════════════════════════════════


class TestVectorStoreManager:
    def test_index_and_count(self):
        mgr = VectorStoreManager()
        eng = EmbeddingEngine(dimension=16)
        emb = eng.generate("a1", "hello")
        mgr.index_embedding(emb)
        assert mgr.count() == 1

    def test_search(self):
        mgr = VectorStoreManager()
        eng = EmbeddingEngine(dimension=16)
        mgr.index_embedding(eng.generate("a1", "nifty signal"))
        query_emb = eng.generate("q", "nifty signal")
        results   = mgr.search(query_emb, top_k=1)
        assert len(results) == 1
        assert results[0].artifact_id == "a1"

    def test_delete(self):
        mgr = VectorStoreManager()
        eng = EmbeddingEngine(dimension=16)
        mgr.index_embedding(eng.generate("a1", "text"))
        assert mgr.delete("a1") is True
        assert mgr.count() == 0

    def test_batch_indexing(self):
        mgr  = VectorStoreManager()
        eng  = EmbeddingEngine(dimension=16)
        embs = [eng.generate(f"a{i}", f"text {i}") for i in range(5)]
        n    = mgr.index_batch(embs)
        assert n == 5
        assert mgr.count() == 5


# ════════════════════════════════════════════════════════════════════════
# 14. TestRetrievalEngine
# ════════════════════════════════════════════════════════════════════════


class TestRetrievalEngine:
    def _setup(self):
        emb_eng  = EmbeddingEngine(dimension=16)
        reg      = EmbeddingRegistry()
        vs       = VectorStoreManager()
        emb      = emb_eng.generate("a1", "nifty buy signal")
        vs.index_embedding(emb)
        retrieval = RetrievalEngine(emb_eng, vs, top_k=5)
        return retrieval

    def test_retrieve_returns_result(self):
        engine = self._setup()
        result = engine.retrieve("nifty signal")
        assert isinstance(result, KnowledgeRetrievalResult)

    def test_retrieve_has_items(self):
        engine = self._setup()
        result = engine.retrieve("nifty buy signal")
        assert result.total_results >= 1

    def test_retrieve_mode_is_semantic(self):
        engine = self._setup()
        result = engine.retrieve("anything")
        assert result.mode == RetrievalMode.SEMANTIC

    def test_retrieve_empty_store(self):
        emb_eng  = EmbeddingEngine(dimension=16)
        vs       = VectorStoreManager()
        engine   = RetrievalEngine(emb_eng, vs)
        result   = engine.retrieve("query")
        assert result.total_results == 0


# ════════════════════════════════════════════════════════════════════════
# 15. TestHybridSearchEngine
# ════════════════════════════════════════════════════════════════════════


class TestHybridSearchEngine:
    def _setup(self):
        emb_eng = EmbeddingEngine(dimension=16)
        vs      = VectorStoreManager()
        emb     = emb_eng.generate("a1", "nifty trend signal")
        vs.index_embedding(emb, metadata={"name": "nifty"})
        return HybridSearchEngine(emb_eng, vs, alpha=0.6, top_k=5), emb_eng, vs

    def test_search_returns_result(self):
        engine, *_ = self._setup()
        result = engine.search("nifty signal")
        assert isinstance(result, KnowledgeRetrievalResult)
        assert result.mode == RetrievalMode.HYBRID

    def test_hybrid_scores_bounded(self):
        engine, *_ = self._setup()
        result = engine.search("nifty trend")
        for item in result.items:
            assert 0.0 <= item.score <= 1.0


# ════════════════════════════════════════════════════════════════════════
# 16. TestRerankingEngine
# ════════════════════════════════════════════════════════════════════════


class TestRerankingEngine:
    def _items(self) -> List[KnowledgeRetrievalItem]:
        return [
            KnowledgeRetrievalItem(f"r{i}", f"a{i}", 1.0 - i * 0.1, {}, i + 1)
            for i in range(3)
        ]

    def test_rerank_returns_list(self):
        eng   = RerankingEngine()
        items = self._items()
        out   = eng.rerank("query", items)
        assert len(out) == 3

    def test_rerank_changes_scores(self):
        eng    = RerankingEngine(decay_per_rank=0.05)
        items  = self._items()
        out    = eng.rerank("query", items)
        # After decay rank-2 and rank-3 get smaller scores
        assert out[0].score >= out[1].score

    def test_empty_list_returns_empty(self):
        eng = RerankingEngine()
        assert eng.rerank("q", []) == []

    def test_ranks_rewritten(self):
        eng   = RerankingEngine()
        items = self._items()
        out   = eng.rerank("query", items)
        ranks = [i.rank for i in out]
        assert ranks == sorted(ranks)


# ════════════════════════════════════════════════════════════════════════
# 17. TestKnowledgeSimilarityEngine
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeSimilarityEngine:
    def _setup(self):
        emb_eng = EmbeddingEngine(dimension=16)
        reg     = EmbeddingRegistry()
        for aid in ["a1", "a2", "a3"]:
            reg.store(emb_eng.generate(aid, f"text for {aid}"))
        return KnowledgeSimilarityEngine(reg, top_k=2), reg

    def test_report_returned(self):
        eng, _ = self._setup()
        report = eng.similarity_report("a1")
        assert isinstance(report, KnowledgeSimilarityReport)

    def test_report_excludes_anchor(self):
        eng, _ = self._setup()
        report = eng.similarity_report("a1")
        ids = [s["artifact_id"] for s in report.similar_artifacts]
        assert "a1" not in ids

    def test_missing_anchor_returns_none(self):
        eng, _ = self._setup()
        result = eng.similarity_report("missing")
        assert result is None

    def test_scores_in_range(self):
        eng, _ = self._setup()
        report = eng.similarity_report("a1")
        for s in report.similar_artifacts:
            assert -1.0 <= s["score"] <= 1.0


# ════════════════════════════════════════════════════════════════════════
# 18. TestKnowledgeClusteringEngine
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeClusteringEngine:
    def test_cluster_returns_dict(self):
        emb_eng = EmbeddingEngine(dimension=8)
        reg     = EmbeddingRegistry()
        for i in range(5):
            reg.store(emb_eng.generate(f"a{i}", f"text {i}"))
        eng     = KnowledgeClusteringEngine(reg, n_clusters=3)
        result  = eng.cluster()
        assert isinstance(result, dict)
        assert len(result) == 3

    def test_all_artifacts_assigned(self):
        emb_eng = EmbeddingEngine(dimension=8)
        reg     = EmbeddingRegistry()
        ids     = [f"a{i}" for i in range(6)]
        for aid in ids:
            reg.store(emb_eng.generate(aid, f"text {aid}"))
        eng    = KnowledgeClusteringEngine(reg, n_clusters=2)
        result = eng.cluster()
        all_assigned = [aid for g in result.values() for aid in g]
        assert set(all_assigned) == set(ids)

    def test_empty_registry(self):
        reg    = EmbeddingRegistry()
        eng    = KnowledgeClusteringEngine(reg, n_clusters=3)
        result = eng.cluster()
        assert result == {}


# ════════════════════════════════════════════════════════════════════════
# 19. TestKnowledgeReasoningEngine
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeReasoningEngine:
    def test_context_returned(self):
        graph   = KnowledgeGraph()
        sem     = SemanticAnalysisEngine()
        eng     = KnowledgeReasoningEngine(graph, sem)
        ctx     = eng.build_context("knowledge-1")
        assert isinstance(ctx, KnowledgeReasoningContext)

    def test_context_has_graph_summary(self):
        graph   = KnowledgeGraph()
        sem     = SemanticAnalysisEngine()
        eng     = KnowledgeReasoningEngine(graph, sem)
        ctx     = eng.build_context("knowledge-1")
        assert "node_count" in ctx.graph_summary

    def test_context_has_knowledge_id(self):
        graph = KnowledgeGraph()
        sem   = SemanticAnalysisEngine()
        eng   = KnowledgeReasoningEngine(graph, sem)
        ctx   = eng.build_context("knowledge-abc")
        assert ctx.knowledge_id == "knowledge-abc"


# ════════════════════════════════════════════════════════════════════════
# 20. TestKnowledgeEnrichmentEngine
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeEnrichmentEngine:
    def test_enriched_dict_returned(self):
        graph   = KnowledgeGraph()
        sem     = SemanticAnalysisEngine()
        eng     = KnowledgeEnrichmentEngine(graph, sem)
        art     = {"artifact_id": "a1", "name": "NIFTY"}
        result  = eng.enrich(art)
        assert "_enriched" in result
        assert result["artifact_id"] == "a1"

    def test_original_not_mutated(self):
        graph   = KnowledgeGraph()
        sem     = SemanticAnalysisEngine()
        eng     = KnowledgeEnrichmentEngine(graph, sem)
        art     = {"artifact_id": "a1"}
        result  = eng.enrich(art)
        assert "_enriched" not in art

    def test_batch_enrichment(self):
        graph   = KnowledgeGraph()
        sem     = SemanticAnalysisEngine()
        eng     = KnowledgeEnrichmentEngine(graph, sem)
        arts    = [{"artifact_id": f"a{i}", "val": i} for i in range(3)]
        results = eng.enrich_batch(arts)
        assert len(results) == 3
        for r in results:
            assert "_enriched" in r


# ════════════════════════════════════════════════════════════════════════
# 21. TestKnowledgeMemoryEngine
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeMemoryEngine:
    def _make(self):
        graph   = KnowledgeGraph()
        reg     = EmbeddingRegistry()
        vs      = VectorStoreManager()
        return KnowledgeMemoryEngine(graph, reg, vs)

    def test_summary_returned(self):
        eng     = self._make()
        summary = eng.summary()
        assert isinstance(summary, EnterpriseMemorySummary)

    def test_record_artifacts(self):
        eng = self._make()
        eng.record_artifacts(5)
        summary = eng.summary()
        assert summary.total_artifacts == 5

    def test_to_dict(self):
        eng = self._make()
        d   = eng.to_dict()
        assert "total_artifacts" in d


# ════════════════════════════════════════════════════════════════════════
# 22. TestKnowledgeRecommendationEngine
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeRecommendationEngine:
    def test_recommend_returns_report(self):
        emb_eng = EmbeddingEngine(dimension=16)
        reg     = EmbeddingRegistry()
        for i in range(3):
            reg.store(emb_eng.generate(f"a{i}", f"text {i}"))
        sim_eng = KnowledgeSimilarityEngine(reg)
        rec_eng = KnowledgeRecommendationEngine(sim_eng)
        report  = rec_eng.recommend("knowledge-1", "a0")
        assert isinstance(report, KnowledgeRecommendationReport)

    def test_items_are_recommendations(self):
        emb_eng = EmbeddingEngine(dimension=16)
        reg     = EmbeddingRegistry()
        for i in range(3):
            reg.store(emb_eng.generate(f"a{i}", f"knowledge {i}"))
        sim_eng = KnowledgeSimilarityEngine(reg, top_k=2)
        rec_eng = KnowledgeRecommendationEngine(sim_eng, max_recommendations=2)
        report  = rec_eng.recommend("k1", "a0")
        for item in report.items:
            assert isinstance(item, KnowledgeRecommendationItem)
            assert item.relevance_score >= 0.0

    def test_empty_registry_returns_empty_report(self):
        reg     = EmbeddingRegistry()
        sim_eng = KnowledgeSimilarityEngine(reg)
        rec_eng = KnowledgeRecommendationEngine(sim_eng)
        report  = rec_eng.recommend("k1", "missing-anchor")
        assert isinstance(report, KnowledgeRecommendationReport)
        assert len(report.items) == 0


# ════════════════════════════════════════════════════════════════════════
# 23. TestKnowledgeIntelligenceValidator
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeIntelligenceValidator:
    def _make_validator(self):
        graph   = KnowledgeGraph()
        reg     = EmbeddingRegistry()
        vs      = VectorStoreManager()
        return KnowledgeIntelligenceValidator(graph, reg, vs)

    def test_valid_request_passes(self):
        v       = self._make_validator()
        request = KnowledgeIntelligenceRequest.create(
            knowledge_id = "k1",
            subsystem_id = "sub1",
            artifacts    = [{"artifact_id": "a1", "val": 1}],
        )
        report  = v.validate(request)
        assert isinstance(report, IntelligenceValidationReport)
        assert report.passed is True

    def test_missing_artifacts_fails(self):
        v       = self._make_validator()
        request = KnowledgeIntelligenceRequest.create(
            knowledge_id = "k1",
            subsystem_id = "sub1",
            artifacts    = [],
        )
        report = v.validate(request)
        assert report.passed is False

    def test_missing_artifact_id_fails(self):
        v       = self._make_validator()
        request = KnowledgeIntelligenceRequest.create(
            knowledge_id = "k1",
            subsystem_id = "sub1",
            artifacts    = [{"val": 1}],   # no artifact_id
        )
        report = v.validate(request)
        # ENTITY_INTEGRITY check fails
        integrity = [
            r for r in report.results
            if r.code == IntelligenceValidationCode.ENTITY_INTEGRITY
        ][0]
        assert integrity.passed is False

    def test_eight_checks_run(self):
        v       = self._make_validator()
        request = KnowledgeIntelligenceRequest.create(
            knowledge_id = "k1",
            subsystem_id = "sub1",
            artifacts    = [{"artifact_id": "a1"}],
        )
        report = v.validate(request)
        assert len(report.results) == 8


# ════════════════════════════════════════════════════════════════════════
# 24. TestKnowledgeIntelligenceStatistics
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeIntelligenceStatistics:
    def test_all_counters_start_at_zero(self):
        stats = KnowledgeIntelligenceStatistics()
        snap  = stats.snapshot()
        assert snap.artifacts_processed == 0
        assert snap.entities_extracted == 0
        assert snap.relationships_discovered == 0
        assert snap.graph_nodes == 0
        assert snap.graph_edges == 0
        assert snap.embeddings_generated == 0
        assert snap.vectors_indexed == 0
        assert snap.retrieval_requests == 0
        assert snap.recommendations_generated == 0
        assert snap.enrichment_operations == 0

    def test_increment_artifacts(self):
        stats = KnowledgeIntelligenceStatistics()
        stats.record_artifacts(3)
        assert stats.snapshot().artifacts_processed == 3

    def test_increment_all(self):
        stats = KnowledgeIntelligenceStatistics()
        stats.record_artifacts(1)
        stats.record_entities(2)
        stats.record_relationships(3)
        stats.record_graph_state(10, 20)
        stats.record_embeddings(5)
        stats.record_vectors(5)
        stats.record_retrieval()
        stats.record_recommendations(4)
        stats.record_enrichment(2)
        snap = stats.snapshot()
        assert snap.artifacts_processed == 1
        assert snap.entities_extracted == 2
        assert snap.graph_nodes == 10
        assert snap.retrieval_requests == 1

    def test_reset(self):
        stats = KnowledgeIntelligenceStatistics()
        stats.record_artifacts(99)
        stats.reset()
        assert stats.snapshot().artifacts_processed == 0

    def test_snapshot_to_dict_has_10_keys(self):
        stats = KnowledgeIntelligenceStatistics()
        d     = stats.snapshot().to_dict()
        # 10 counters + captured_at = 11 keys
        assert "artifacts_processed" in d
        assert len(d) >= 10


# ════════════════════════════════════════════════════════════════════════
# 25. TestKnowledgeIntelligenceHistory
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeIntelligenceHistory:
    def _dummy_response(self) -> KnowledgeIntelligenceResponse:
        return KnowledgeIntelligenceResponse.failure(
            request_id   = f"req-{uuid.uuid4().hex[:6]}",
            knowledge_id = "k1",
            errors       = ["test error"],
        )

    def test_record_and_count(self):
        h = KnowledgeIntelligenceHistory()
        h.record(self._dummy_response())
        assert h.count() == 1

    def test_bounded(self):
        h = KnowledgeIntelligenceHistory(max_history=3)
        for _ in range(5):
            h.record(self._dummy_response())
        assert h.count() == 3

    def test_recent(self):
        h = KnowledgeIntelligenceHistory()
        for _ in range(10):
            h.record(self._dummy_response())
        assert len(h.recent(5)) == 5

    def test_clear(self):
        h = KnowledgeIntelligenceHistory()
        h.record(self._dummy_response())
        h.clear()
        assert h.count() == 0

    def test_all_returns_list(self):
        h = KnowledgeIntelligenceHistory()
        h.record(self._dummy_response())
        assert isinstance(h.all(), list)


# ════════════════════════════════════════════════════════════════════════
# 26. TestIntelligenceEvents
# ════════════════════════════════════════════════════════════════════════


class TestIntelligenceEvents:
    def test_event_create(self):
        e = IntelligenceEvent.create(
            IntelligenceEventType.KNOWLEDGE_RECEIVED, {"k": "v"}
        )
        assert e.event_type == IntelligenceEventType.KNOWLEDGE_RECEIVED
        assert e.payload["k"] == "v"

    def test_event_to_dict(self):
        e = IntelligenceEvent.create(IntelligenceEventType.EMBEDDINGS_GENERATED)
        d = e.to_dict()
        assert "event_id" in d
        assert "emitted_at" in d

    def test_bus_listener_called(self):
        received = []
        bus = IntelligenceEventBus()
        bus.add_listener(lambda e: received.append(e.event_type))
        bus.emit(IntelligenceEventType.ENTITIES_EXTRACTED, {})
        assert IntelligenceEventType.ENTITIES_EXTRACTED in received

    def test_bus_listener_count(self):
        bus = IntelligenceEventBus()
        fn  = lambda e: None
        bus.add_listener(fn)
        assert bus.listener_count() == 1

    def test_bus_remove_listener(self):
        bus = IntelligenceEventBus()
        fn  = lambda e: None
        bus.add_listener(fn)
        bus.remove_listener(fn)
        assert bus.listener_count() == 0

    def test_bus_listener_exception_suppressed(self):
        bus = IntelligenceEventBus()
        bus.add_listener(lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        # Must not propagate
        bus.emit(IntelligenceEventType.KNOWLEDGE_INTELLIGENCE_COMPLETED, {})

    def test_ten_event_types(self):
        assert len(IntelligenceEventType) == 10

    def test_bus_isolation(self):
        bus1 = IntelligenceEventBus()
        bus2 = IntelligenceEventBus()
        received1, received2 = [], []
        bus1.add_listener(lambda e: received1.append(1))
        bus2.add_listener(lambda e: received2.append(2))
        bus1.emit(IntelligenceEventType.KNOWLEDGE_RECEIVED)
        assert received1 == [1]
        assert received2 == []


# ════════════════════════════════════════════════════════════════════════
# 27. TestKnowledgeIntelligenceFactory
# ════════════════════════════════════════════════════════════════════════


class TestKnowledgeIntelligenceFactory:
    def test_build_all_keys(self):
        factory = KnowledgeIntelligenceFactory()
        parts   = factory.build_all()
        assert "graph" in parts
        assert "embedding_engine" in parts
        assert "vector_store" in parts
        assert "validator" in parts
        assert "statistics" in parts
        assert "event_bus" in parts

    def test_build_graph(self):
        factory = KnowledgeIntelligenceFactory()
        g       = factory.build_graph()
        assert isinstance(g, KnowledgeGraph)

    def test_build_embedding_engine(self):
        factory = KnowledgeIntelligenceFactory(embedding_dimension=32)
        eng     = factory.build_embedding_engine()
        assert eng.dimension == 32

    def test_build_statistics(self):
        factory = KnowledgeIntelligenceFactory()
        stats   = factory.build_statistics()
        assert isinstance(stats, KnowledgeIntelligenceStatistics)

    def test_build_event_bus(self):
        factory = KnowledgeIntelligenceFactory()
        bus     = factory.build_event_bus()
        assert isinstance(bus, IntelligenceEventBus)


# ════════════════════════════════════════════════════════════════════════
# 28. TestEngineLifecycle
# ════════════════════════════════════════════════════════════════════════


class TestEngineLifecycle:
    def test_start_changes_state(self):
        eng = _make_engine()
        eng.start()
        assert eng.lifecycle_state().value == "running"
        eng.stop()

    def test_stop_changes_state(self):
        eng = _make_engine()
        eng.start()
        eng.stop()
        assert eng.lifecycle_state().value != "running"

    def test_double_start_raises(self):
        eng = _make_engine()
        eng.start()
        from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError
        with pytest.raises(EngineAlreadyRunningError):
            eng.start()
        eng.stop()

    def test_not_running_raises_on_process(self):
        eng     = _make_engine()
        request = KnowledgeIntelligenceRequest.create(
            "k1", "sub1", [{"artifact_id": "a1"}]
        )
        with pytest.raises(IntelligenceNotRunningError):
            eng.process(request)

    def test_health_returns_dict(self):
        eng = _started_engine()
        h   = eng.health()
        assert "status" in h
        assert h["status"] == "healthy"
        eng.stop()


# ════════════════════════════════════════════════════════════════════════
# 29. TestEngineProcess
# ════════════════════════════════════════════════════════════════════════


class TestEngineProcess:
    def test_full_pipeline_succeeds(self):
        eng     = _started_engine()
        request = KnowledgeIntelligenceRequest.create(
            knowledge_id = "k-test",
            subsystem_id = "sub-test",
            artifacts    = [
                {"artifact_id": "a1", "price": 100.0, "signal": "buy"},
                {"artifact_id": "a2", "risk": 0.3, "asset": "NIFTY"},
            ],
        )
        response = eng.process(request)
        assert isinstance(response, KnowledgeIntelligenceResponse)
        assert response.succeeded is True
        eng.stop()

    def test_report_has_entities(self):
        eng     = _started_engine()
        request = KnowledgeIntelligenceRequest.create(
            "k1", "sub1",
            [{"artifact_id": "a1", "price": 100, "signal": "buy"}],
        )
        response = eng.process(request)
        assert response.report.entities_extracted > 0
        eng.stop()

    def test_report_has_embeddings(self):
        eng     = _started_engine()
        request = KnowledgeIntelligenceRequest.create(
            "k1", "sub1",
            [{"artifact_id": "a1", "price": 100}],
        )
        response = eng.process(request)
        assert response.report.embeddings_generated >= 1
        eng.stop()

    def test_events_fired(self):
        eng     = _started_engine()
        fired   = []
        eng.add_listener(lambda e: fired.append(e.event_type))
        request = KnowledgeIntelligenceRequest.create(
            "k1", "sub1",
            [{"artifact_id": "a1", "val": 1}],
        )
        eng.process(request)
        assert IntelligenceEventType.KNOWLEDGE_RECEIVED in fired
        assert IntelligenceEventType.KNOWLEDGE_INTELLIGENCE_COMPLETED in fired
        eng.stop()

    def test_invalid_request_returns_failure(self):
        eng     = _started_engine()
        request = KnowledgeIntelligenceRequest.create(
            "k1", "sub1", []
        )
        response = eng.process(request)
        assert response.succeeded is False
        assert len(response.errors) > 0
        eng.stop()

    def test_response_has_knowledge_id(self):
        eng     = _started_engine()
        request = KnowledgeIntelligenceRequest.create(
            "unique-id", "sub1",
            [{"artifact_id": "a1"}],
        )
        response = eng.process(request)
        assert response.knowledge_id == "unique-id"
        eng.stop()


# ════════════════════════════════════════════════════════════════════════
# 30. TestEngineRetrieval
# ════════════════════════════════════════════════════════════════════════


class TestEngineRetrieval:
    def _engine_with_data(self) -> KnowledgeIntelligenceEngine:
        eng     = _started_engine()
        request = KnowledgeIntelligenceRequest.create(
            "k1", "sub1",
            [
                {"artifact_id": "a1", "signal": "buy", "price": 100},
                {"artifact_id": "a2", "signal": "sell", "risk": 0.5},
            ],
        )
        eng.process(request)
        return eng

    def test_semantic_retrieve(self):
        eng    = self._engine_with_data()
        result = eng.retrieve("buy signal")
        assert isinstance(result, KnowledgeRetrievalResult)
        eng.stop()

    def test_hybrid_retrieve(self):
        eng    = self._engine_with_data()
        result = eng.retrieve("buy signal", mode=RetrievalMode.HYBRID)
        assert result.mode == RetrievalMode.HYBRID
        eng.stop()

    def test_recommend(self):
        eng    = self._engine_with_data()
        report = eng.recommend("k1", anchor_artifact_id="a1")
        assert isinstance(report, KnowledgeRecommendationReport)
        eng.stop()

    def test_get_graph(self):
        eng   = self._engine_with_data()
        graph = eng.get_graph()
        assert isinstance(graph, KnowledgeGraph)
        eng.stop()

    def test_memory_summary(self):
        eng     = self._engine_with_data()
        summary = eng.memory_summary()
        assert isinstance(summary, EnterpriseMemorySummary)
        assert summary.total_artifacts >= 2
        eng.stop()


# ════════════════════════════════════════════════════════════════════════
# 31. TestEngineIntrospection
# ════════════════════════════════════════════════════════════════════════


class TestEngineIntrospection:
    def test_health(self):
        eng = _started_engine()
        h   = eng.health()
        assert h["status"] == "healthy"
        assert "version" in h
        eng.stop()

    def test_status(self):
        eng = _started_engine()
        s   = eng.status()
        assert "lifecycle_state" in s
        assert "statistics" in s
        eng.stop()

    def test_statistics(self):
        eng  = _started_engine()
        snap = eng.statistics()
        assert hasattr(snap, "artifacts_processed")
        eng.stop()

    def test_history(self):
        eng     = _started_engine()
        request = KnowledgeIntelligenceRequest.create(
            "k1", "sub1", [{"artifact_id": "a1", "val": 1}]
        )
        eng.process(request)
        hist = eng.history()
        assert len(hist) >= 1
        eng.stop()

    def test_engine_state(self):
        eng   = _started_engine()
        state = eng.engine_state()
        assert isinstance(state, IntelligenceEngineState)
        eng.stop()

    def test_intelligence_delegate(self):
        eng  = _started_engine()
        fn   = eng.intelligence_delegate
        result = fn("k-delegate", {"artifacts": [], "subsystem_id": "sub1"})
        assert isinstance(result, dict)
        eng.stop()


# ════════════════════════════════════════════════════════════════════════
# 32. TestConcurrency
# ════════════════════════════════════════════════════════════════════════


class TestConcurrency:
    def test_concurrent_process_calls(self):
        eng      = _started_engine()
        errors   = []
        results  = []

        def _run(idx: int):
            try:
                req = KnowledgeIntelligenceRequest.create(
                    f"k{idx}", f"sub{idx}",
                    [{"artifact_id": f"a{idx}", "val": idx}],
                )
                resp = eng.process(req)
                results.append(resp)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 8
        eng.stop()

    def test_concurrent_retrieve_calls(self):
        eng = _started_engine()
        req = KnowledgeIntelligenceRequest.create(
            "k1", "sub1",
            [{"artifact_id": "a1", "signal": "buy"}],
        )
        eng.process(req)

        results = []
        errors  = []

        def _retrieve():
            try:
                r = eng.retrieve("buy signal")
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_retrieve) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 6
        eng.stop()


# ════════════════════════════════════════════════════════════════════════
# 33. TestRegression  — M1/M2/M3 imports must be unaffected
# ════════════════════════════════════════════════════════════════════════


class TestRegression:
    def test_m1_lifecycle_importable(self):
        from iios.knowledge.lifecycle import KnowledgeLifecycle
        assert KnowledgeLifecycle is not None

    def test_m2_engine_importable(self):
        from iios.knowledge.engine import KnowledgeEngine
        assert KnowledgeEngine is not None

    def test_m3_policy_importable(self):
        from iios.knowledge.policies import KnowledgeGovernancePolicyEngine
        assert KnowledgeGovernancePolicyEngine is not None

    def test_m4_package_importable(self):
        from iios.knowledge.intelligence import KnowledgeIntelligenceEngine
        assert KnowledgeIntelligenceEngine is not None

    def test_no_cross_contamination(self):
        from iios.knowledge.intelligence import INTELLIGENCE_SYSTEM_ID
        assert "intelligence" in INTELLIGENCE_SYSTEM_ID
