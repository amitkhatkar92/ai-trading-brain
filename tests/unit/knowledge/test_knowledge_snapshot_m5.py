"""
test_knowledge_snapshot_m5.py
------------------------------
Comprehensive test suite for C14 M5 — Knowledge Snapshot.

Coverage targets ≥ 95% of iios/knowledge/snapshot/*.

Run:
    .venv/Scripts/python.exe -m pytest tests/unit/knowledge/test_knowledge_snapshot_m5.py -x --tb=short -q
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List

import pytest

# ════════════════════════════════════════════════════════════════════════
# Imports under test
# ════════════════════════════════════════════════════════════════════════
from iios.knowledge.snapshot import (
    # Enums & constants
    SNAPSHOT_SYSTEM_ID, VERSION, SCHEMA_VERSION, FRAMEWORK_VERSION,
    BUILD_VERSION, ACTOR_SNAPSHOT, ACTOR_BUILDER, ACTOR_SYSTEM,
    DEFAULT_MAX_SNAPSHOTS, DEFAULT_CACHE_SIZE, DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_BUNDLES,
    KnowledgeScope, KnowledgeType,
    SnapshotState, SnapshotVersionTag,
    SnapshotEventType, SnapshotValidationCode,
    # Exceptions
    KnowledgeSnapshotError, SnapshotBuildError, SnapshotValidationError,
    SnapshotNotFoundError, SnapshotVersionError, SnapshotSerializationError,
    SnapshotStoreError, SnapshotCapacityError, SnapshotIntegrityError,
    # Core data objects
    KnowledgeSummary, GraphSummary, EmbeddingSummary,
    VectorIndexSummary, RetrievalSummary, RecommendationSummary,
    SnapshotMemorySummary, SnapshotAudit, SnapshotStatistics,
    SnapshotMetadata, KnowledgeSnapshot,
    # Metadata builder
    SnapshotMetadataBuilder,
    # Builder & Factory
    KnowledgeSnapshotBuilder, KnowledgeSnapshotFactory,
    # Validation
    KnowledgeSnapshotValidation, SnapshotValidationReport, SnapshotValidationResult,
    # Storage
    KnowledgeSnapshotRegistry, KnowledgeSnapshotStore,
    KnowledgeSnapshotCache, KnowledgeSnapshotHistory,
    # Statistics
    KnowledgeSnapshotStatistics, SnapshotStatisticsReport,
    # Events
    SnapshotEvent, SnapshotEventBus,
    # Bundle
    KnowledgeSnapshotBundle, KnowledgeSnapshotBundleRegistry,
)


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════

def _make_snapshot(
    session_id: str = "sess-test",
    workflow_id: str = "wf-test",
    enterprise_id: str = "ent-test",
) -> KnowledgeSnapshot:
    return KnowledgeSnapshotFactory().create_default(
        knowledge_session_id  = session_id,
        knowledge_workflow_id = workflow_id,
        enterprise_session_id = enterprise_id,
    )


# ════════════════════════════════════════════════════════════════════════
# 1. Constants
# ════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_snapshot_system_id(self):
        assert SNAPSHOT_SYSTEM_ID == "iios:knowledge:snapshot"

    def test_version_strings(self):
        assert VERSION
        assert SCHEMA_VERSION
        assert FRAMEWORK_VERSION
        assert BUILD_VERSION

    def test_actors(self):
        assert ACTOR_SNAPSHOT
        assert ACTOR_BUILDER
        assert ACTOR_SYSTEM

    def test_snapshot_state_members(self):
        assert len(SnapshotState) == 6
        assert SnapshotState.BUILT in SnapshotState
        assert SnapshotState.PUBLISHED in SnapshotState

    def test_version_tag_members(self):
        assert len(SnapshotVersionTag) == 4

    def test_knowledge_scope_members(self):
        assert len(KnowledgeScope) == 4
        assert KnowledgeScope.ENTERPRISE in KnowledgeScope

    def test_knowledge_type_members(self):
        assert len(KnowledgeType) == 4

    def test_event_type_members(self):
        assert len(SnapshotEventType) == 10

    def test_validation_code_members(self):
        assert len(SnapshotValidationCode) == 8

    def test_defaults(self):
        assert DEFAULT_MAX_SNAPSHOTS == 10_000
        assert DEFAULT_CACHE_SIZE == 100
        assert DEFAULT_MAX_HISTORY == 1_000
        assert DEFAULT_MAX_BUNDLES == 500


# ════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_hierarchy(self):
        for exc_cls in [
            SnapshotBuildError, SnapshotValidationError, SnapshotNotFoundError,
            SnapshotVersionError, SnapshotSerializationError, SnapshotStoreError,
            SnapshotCapacityError, SnapshotIntegrityError,
        ]:
            assert issubclass(exc_cls, KnowledgeSnapshotError)
            assert issubclass(exc_cls, Exception)

    def test_error_codes(self):
        assert KnowledgeSnapshotError.error_code == "KSN-000"
        assert SnapshotBuildError.error_code == "KSN-001"
        assert SnapshotValidationError.error_code == "KSN-002"
        assert SnapshotNotFoundError.error_code == "KSN-003"
        assert SnapshotVersionError.error_code == "KSN-004"
        assert SnapshotSerializationError.error_code == "KSN-005"
        assert SnapshotStoreError.error_code == "KSN-006"
        assert SnapshotCapacityError.error_code == "KSN-007"
        assert SnapshotIntegrityError.error_code == "KSN-008"

    def test_snapshot_not_found_has_id(self):
        exc = SnapshotNotFoundError("snap-xyz")
        assert exc.snapshot_id == "snap-xyz"

    def test_capacity_error_has_limit(self):
        exc = SnapshotCapacityError(limit=100)
        assert exc.limit == 100

    def test_validation_error_has_failed_checks(self):
        exc = SnapshotValidationError("fail", failed_checks=["A", "B"])
        assert exc.failed_checks == ["A", "B"]


# ════════════════════════════════════════════════════════════════════════
# 3. Sub-dataclasses
# ════════════════════════════════════════════════════════════════════════

class TestKnowledgeSummary:
    def _make(self) -> KnowledgeSummary:
        return KnowledgeSummary(
            artifacts=10, sources=("s1",), domains=("d1",),
            categories=("c1",), quality_score=0.9, coverage_score=0.8,
            freshness_score=0.7, confidence_score=0.85, completeness_score=0.75,
        )

    def test_frozen(self):
        ks = self._make()
        with pytest.raises((AttributeError, TypeError)):
            ks.artifacts = 99   # type: ignore[misc]

    def test_empty(self):
        ks = KnowledgeSummary.empty()
        assert ks.artifacts == 0
        assert ks.quality_score == 0.0

    def test_to_dict_from_dict_roundtrip(self):
        ks = self._make()
        assert KnowledgeSummary.from_dict(ks.to_dict()) == ks


class TestGraphSummary:
    def _make(self) -> GraphSummary:
        return GraphSummary(
            graph_version="1.0", total_nodes=50, total_edges=120,
            entity_types=("e1", "e2"), relationship_types=("r1",),
            connected_components=3, graph_health="healthy",
        )

    def test_frozen(self):
        gs = self._make()
        with pytest.raises((AttributeError, TypeError)):
            gs.total_nodes = 99   # type: ignore[misc]

    def test_roundtrip(self):
        gs = self._make()
        assert GraphSummary.from_dict(gs.to_dict()) == gs


class TestEmbeddingSummary:
    def test_roundtrip(self):
        es = EmbeddingSummary(
            provider="hash", model="stub", model_version="1.0",
            vector_dimensions=128, embedding_count=500, embedding_health="ok",
        )
        assert EmbeddingSummary.from_dict(es.to_dict()) == es


class TestVectorIndexSummary:
    def test_roundtrip(self):
        vi = VectorIndexSummary(
            vector_store="in-memory", index_version="1.0",
            index_size=500, indexed_artifacts=500, index_health="ok",
        )
        assert VectorIndexSummary.from_dict(vi.to_dict()) == vi


class TestRetrievalSummary:
    def test_roundtrip(self):
        rs = RetrievalSummary(
            strategy="hybrid", hybrid_search_enabled=True,
            average_retrieval_ms=12.5, quality_score=0.88,
        )
        assert RetrievalSummary.from_dict(rs.to_dict()) == rs


class TestRecommendationSummary:
    def test_roundtrip(self):
        rec = RecommendationSummary(
            recommendations_generated=5,
            categories=("trading",),
            confidence_score=0.77,
        )
        assert RecommendationSummary.from_dict(rec.to_dict()) == rec


class TestSnapshotMemorySummary:
    def test_roundtrip(self):
        sm = SnapshotMemorySummary(
            memory_objects=10, memory_domains=("m1",),
            cross_subsystem_links=3, historical_references=7,
        )
        assert SnapshotMemorySummary.from_dict(sm.to_dict()) == sm


class TestSnapshotAudit:
    def test_roundtrip(self):
        sa = SnapshotAudit(
            governance_version="1.0", graph_version="1.0",
            embedding_version="1.0",
            validation_summary={"check": "passed"},
            audit_trail=({"event": "built"},),
        )
        assert SnapshotAudit.from_dict(sa.to_dict()) == sa


class TestSnapshotStatisticsObject:
    def test_roundtrip(self):
        ss = SnapshotStatistics(
            processing_duration_ms=42.0, snapshot_size_bytes=4096,
            artifact_count=10, entity_count=50, relationship_count=30,
            embedding_count=10, vector_count=10,
        )
        assert SnapshotStatistics.from_dict(ss.to_dict()) == ss


class TestSnapshotMetadataObject:
    def test_roundtrip(self):
        sm = SnapshotMetadata(
            environment="test", framework_version="1.0.0",
            build_version="1.0.0-stable",
            source_components=("iios.knowledge.engine",),
            correlation_ids=("cid-1",), trace_ids=("tid-1",),
        )
        assert SnapshotMetadata.from_dict(sm.to_dict()) == sm


# ════════════════════════════════════════════════════════════════════════
# 4. KnowledgeSnapshot (core)
# ════════════════════════════════════════════════════════════════════════

class TestKnowledgeSnapshot:
    def test_create_and_frozen(self):
        snap = _make_snapshot()
        assert snap.snapshot_id.startswith("snap-")
        with pytest.raises((AttributeError, TypeError)):
            snap.snapshot_id = "x"   # type: ignore[misc]

    def test_to_dict_from_dict_roundtrip(self):
        snap = _make_snapshot()
        d    = snap.to_dict()
        snap2 = KnowledgeSnapshot.from_dict(d)
        assert snap2.snapshot_id == snap.snapshot_id
        assert snap2.content_hash == snap.content_hash

    def test_to_json_from_json_roundtrip(self):
        snap = _make_snapshot()
        j    = snap.to_json()
        snap2 = KnowledgeSnapshot.from_json(j)
        assert snap2.content_hash == snap.content_hash

    def test_verify_integrity(self):
        snap = _make_snapshot()
        assert snap.verify_integrity() is True

    def test_content_hash_is_set(self):
        snap = _make_snapshot()
        assert len(snap.content_hash) == 64   # SHA-256 hex = 64 chars

    def test_schema_version(self):
        snap = _make_snapshot()
        assert snap.schema_version == SCHEMA_VERSION

    def test_state_default(self):
        snap = _make_snapshot()
        assert snap.state == SnapshotState.BUILT


# ════════════════════════════════════════════════════════════════════════
# 5. SnapshotMetadataBuilder
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotMetadataBuilder:
    def test_fluent_api(self):
        meta = (
            SnapshotMetadataBuilder()
            .with_environment("production")
            .with_framework_version("2.0.0")
            .with_build_version("2.0.0-rc1")
            .with_source_components(["iios.knowledge.engine"])
            .with_correlation_id("cid-abc")
            .with_trace_id("tid-xyz")
            .build()
        )
        assert meta.environment == "production"
        assert "cid-abc" in meta.correlation_ids
        assert "tid-xyz" in meta.trace_ids

    def test_default(self):
        meta = SnapshotMetadataBuilder.default()
        assert meta.framework_version
        assert len(meta.source_components) >= 4

    def test_auto_trace(self):
        meta = SnapshotMetadataBuilder().auto_trace().build()
        assert len(meta.trace_ids) >= 1


# ════════════════════════════════════════════════════════════════════════
# 6. KnowledgeSnapshotBuilder
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotBuilder:
    def test_minimal_build(self):
        snap = (
            KnowledgeSnapshotBuilder()
            .set_knowledge_session("s1")
            .set_knowledge_workflow("w1")
            .set_enterprise_session("e1")
            .set_metadata(SnapshotMetadataBuilder.default())
            .build()
        )
        assert snap.knowledge_session_id == "s1"
        assert snap.verify_integrity()

    def test_missing_required_raises(self):
        with pytest.raises(SnapshotBuildError):
            KnowledgeSnapshotBuilder().build()

    def test_missing_session_raises(self):
        with pytest.raises(SnapshotBuildError):
            (
                KnowledgeSnapshotBuilder()
                .set_knowledge_workflow("w1")
                .set_enterprise_session("e1")
                .build()
            )

    def test_content_hash_changes_with_different_data(self):
        snap1 = _make_snapshot("sess-1")
        snap2 = _make_snapshot("sess-2")
        assert snap1.content_hash != snap2.content_hash

    def test_from_intelligence_response(self):
        response: Dict[str, Any] = {
            "knowledge_id": "kid-abc",
            "knowledge_version": "2.0.0",
            "lifecycle_state": "active",
            "governance_state": "compliant",
            "knowledge_state": "ready",
        }
        snap = (
            KnowledgeSnapshotBuilder()
            .set_knowledge_session("kid-abc")
            .set_knowledge_workflow("kid-abc")
            .set_enterprise_session("ent-1")
            .from_intelligence_response(response)
            .set_metadata(SnapshotMetadataBuilder.default())
            .build()
        )
        assert snap.knowledge_session_id == "kid-abc"


# ════════════════════════════════════════════════════════════════════════
# 7. KnowledgeSnapshotValidation
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotValidation:
    def test_valid_snapshot_passes(self):
        snap   = _make_snapshot()
        report = KnowledgeSnapshotValidation().validate(snap)
        assert isinstance(report, SnapshotValidationReport)
        assert report.passed

    def test_all_8_checks_present(self):
        snap   = _make_snapshot()
        report = KnowledgeSnapshotValidation().validate(snap)
        codes  = {r.code for r in report.results}
        assert len(codes) == 8

    def test_report_snapshot_id(self):
        snap   = _make_snapshot()
        report = KnowledgeSnapshotValidation().validate(snap)
        assert report.snapshot_id == snap.snapshot_id


# ════════════════════════════════════════════════════════════════════════
# 8. KnowledgeSnapshotFactory
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotFactory:
    def test_create_default(self):
        snap = KnowledgeSnapshotFactory().create_default()
        assert snap.snapshot_id
        assert snap.verify_integrity()

    def test_create_with_summaries(self):
        ks = KnowledgeSummary(
            artifacts=5, sources=("r",), domains=("d",), categories=("c",),
            quality_score=0.9, coverage_score=0.9, freshness_score=0.9,
            confidence_score=0.9, completeness_score=0.9,
        )
        snap = KnowledgeSnapshotFactory().create(
            knowledge_session_id  = "s",
            knowledge_workflow_id = "w",
            enterprise_session_id = "e",
            knowledge_summary     = ks,
        )
        assert snap.knowledge_summary.artifacts == 5

    def test_from_intelligence_response(self):
        resp = {"knowledge_id": "ki-1", "knowledge_version": "1.0"}
        snap = KnowledgeSnapshotFactory().from_intelligence_response(resp, "ent-1")
        assert snap.enterprise_session_id == "ent-1"


# ════════════════════════════════════════════════════════════════════════
# 9. KnowledgeSnapshotRegistry
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotRegistry:
    def test_register_and_get(self):
        reg  = KnowledgeSnapshotRegistry()
        snap = _make_snapshot()
        reg.register(snap)
        assert reg.get(snap.snapshot_id) is snap

    def test_remove(self):
        reg  = KnowledgeSnapshotRegistry()
        snap = _make_snapshot()
        reg.register(snap)
        assert reg.remove(snap.snapshot_id) is True
        assert reg.get(snap.snapshot_id) is None

    def test_remove_missing_returns_false(self):
        reg = KnowledgeSnapshotRegistry()
        assert reg.remove("nonexistent") is False

    def test_by_session(self):
        reg  = KnowledgeSnapshotRegistry()
        s1   = _make_snapshot("sess-A")
        s2   = _make_snapshot("sess-A")
        s3   = _make_snapshot("sess-B")
        for s in (s1, s2, s3):
            reg.register(s)
        result = reg.by_session("sess-A")
        assert len(result) == 2

    def test_capacity_error(self):
        reg = KnowledgeSnapshotRegistry(max_snapshots=1)
        reg.register(_make_snapshot())
        with pytest.raises(SnapshotCapacityError):
            reg.register(_make_snapshot())

    def test_count_and_clear(self):
        reg = KnowledgeSnapshotRegistry()
        reg.register(_make_snapshot())
        assert reg.count() == 1
        reg.clear()
        assert reg.count() == 0


# ════════════════════════════════════════════════════════════════════════
# 10. KnowledgeSnapshotStore
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotStore:
    def test_put_and_get(self):
        store = KnowledgeSnapshotStore()
        snap  = _make_snapshot()
        store.put(snap)
        assert store.get(snap.snapshot_id) is snap

    def test_get_or_raise_not_found(self):
        store = KnowledgeSnapshotStore()
        with pytest.raises(SnapshotNotFoundError):
            store.get_or_raise("missing")

    def test_delete(self):
        store = KnowledgeSnapshotStore()
        snap  = _make_snapshot()
        store.put(snap)
        assert store.delete(snap.snapshot_id) is True
        assert store.get(snap.snapshot_id) is None

    def test_delete_missing_returns_false(self):
        store = KnowledgeSnapshotStore()
        assert store.delete("nope") is False

    def test_list_snapshots(self):
        store = KnowledgeSnapshotStore()
        s1, s2 = _make_snapshot(), _make_snapshot()
        store.put(s1)
        store.put(s2)
        assert len(store.list_snapshots()) == 2

    def test_by_session(self):
        store = KnowledgeSnapshotStore()
        s1 = _make_snapshot("sess-X")
        s2 = _make_snapshot("sess-X")
        s3 = _make_snapshot("sess-Y")
        for s in (s1, s2, s3):
            store.put(s)
        assert len(store.by_session("sess-X")) == 2

    def test_capacity_error(self):
        store = KnowledgeSnapshotStore(max_snapshots=1)
        store.put(_make_snapshot())
        with pytest.raises(SnapshotCapacityError):
            store.put(_make_snapshot())

    def test_export_import(self):
        store = KnowledgeSnapshotStore()
        snap  = _make_snapshot()
        store.put(snap)
        records = store.export_all()
        assert len(records) == 1

        store2 = KnowledgeSnapshotStore()
        count  = store2.import_all(records)
        assert count == 1
        assert store2.get(snap.snapshot_id) is not None


# ════════════════════════════════════════════════════════════════════════
# 11. KnowledgeSnapshotCache (LRU)
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotCache:
    def test_put_and_get(self):
        cache = KnowledgeSnapshotCache(max_size=5)
        snap  = _make_snapshot()
        cache.put(snap)
        assert cache.get(snap.snapshot_id) is snap

    def test_miss_returns_none(self):
        cache = KnowledgeSnapshotCache()
        assert cache.get("missing") is None

    def test_hit_miss_counts(self):
        cache = KnowledgeSnapshotCache()
        snap  = _make_snapshot()
        cache.put(snap)
        cache.get(snap.snapshot_id)   # hit
        cache.get("missing")          # miss
        assert cache.hits() == 1
        assert cache.misses() == 1

    def test_lru_eviction(self):
        cache = KnowledgeSnapshotCache(max_size=2)
        s1, s2, s3 = _make_snapshot(), _make_snapshot(), _make_snapshot()
        cache.put(s1)
        cache.put(s2)
        cache.put(s3)   # should evict s1 (LRU)
        assert cache.get(s1.snapshot_id) is None
        assert cache.get(s2.snapshot_id) is s2

    def test_invalidate(self):
        cache = KnowledgeSnapshotCache()
        snap  = _make_snapshot()
        cache.put(snap)
        assert cache.invalidate(snap.snapshot_id) is True
        assert cache.get(snap.snapshot_id) is None

    def test_clear_resets_stats(self):
        cache = KnowledgeSnapshotCache()
        snap  = _make_snapshot()
        cache.put(snap)
        cache.get(snap.snapshot_id)
        cache.clear()
        assert cache.size() == 0
        assert cache.hits() == 0

    def test_hit_rate(self):
        cache = KnowledgeSnapshotCache()
        snap  = _make_snapshot()
        cache.put(snap)
        cache.get(snap.snapshot_id)
        cache.get("miss")
        rate = cache.hit_rate()
        assert abs(rate - 0.5) < 1e-9


# ════════════════════════════════════════════════════════════════════════
# 12. KnowledgeSnapshotHistory
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotHistory:
    def test_record_and_recent(self):
        hist = KnowledgeSnapshotHistory()
        snap = _make_snapshot()
        hist.record(snap)
        assert snap in hist.recent()

    def test_by_session(self):
        hist = KnowledgeSnapshotHistory()
        s1   = _make_snapshot("sess-H")
        s2   = _make_snapshot("sess-H")
        s3   = _make_snapshot("sess-I")
        for s in (s1, s2, s3):
            hist.record(s)
        assert len(hist.by_session("sess-H")) == 2

    def test_bounded_history(self):
        hist = KnowledgeSnapshotHistory(max_history=3)
        for _ in range(5):
            hist.record(_make_snapshot())
        assert hist.count() == 3

    def test_latest_for_session(self):
        hist = KnowledgeSnapshotHistory()
        s1   = _make_snapshot("sess-J")
        s2   = _make_snapshot("sess-J")
        hist.record(s1)
        hist.record(s2)
        assert hist.latest_for_session("sess-J") is s2

    def test_clear(self):
        hist = KnowledgeSnapshotHistory()
        hist.record(_make_snapshot())
        hist.clear()
        assert hist.count() == 0


# ════════════════════════════════════════════════════════════════════════
# 13. KnowledgeSnapshotStatistics
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotStatisticsEngine:
    def _make_stats(self) -> KnowledgeSnapshotStatistics:
        return KnowledgeSnapshotStatistics()

    def test_all_10_counters(self):
        stats = self._make_stats()
        stats.record_built()
        stats.record_validated()
        stats.record_stored()
        stats.record_retrieved()
        stats.record_cached()
        stats.record_cache_hit()
        stats.record_cache_miss()
        stats.record_validation_failure()
        stats.record_expired()
        stats.record_bundled()
        r = stats.report()
        assert r.snapshots_built      == 1
        assert r.snapshots_validated  == 1
        assert r.snapshots_stored     == 1
        assert r.snapshots_retrieved  == 1
        assert r.snapshots_cached     == 1
        assert r.cache_hits           == 1
        assert r.cache_misses         == 1
        assert r.validation_failures  == 1
        assert r.snapshots_expired    == 1
        assert r.snapshots_bundled    == 1

    def test_reset(self):
        stats = self._make_stats()
        stats.record_built(5)
        stats.reset()
        r = stats.report()
        assert r.snapshots_built == 0

    def test_report_frozen(self):
        r = self._make_stats().report()
        with pytest.raises((AttributeError, TypeError)):
            r.snapshots_built = 99   # type: ignore[misc]

    def test_report_to_dict(self):
        r = self._make_stats().report()
        d = r.to_dict()
        assert "snapshots_built" in d
        assert "captured_at" in d


# ════════════════════════════════════════════════════════════════════════
# 14. Events
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotEvents:
    def test_event_create(self):
        evt = SnapshotEvent.create(
            SnapshotEventType.SNAPSHOT_BUILT,
            {"snapshot_id": "snap-1"},
        )
        assert evt.event_type == SnapshotEventType.SNAPSHOT_BUILT
        assert evt.event_id.startswith("sevt-")
        assert evt.emitted_at

    def test_event_to_dict(self):
        evt = SnapshotEvent.create(SnapshotEventType.SNAPSHOT_STORED, {})
        d   = evt.to_dict()
        assert d["event_type"] == SnapshotEventType.SNAPSHOT_STORED.value

    def test_event_frozen(self):
        evt = SnapshotEvent.create(SnapshotEventType.SNAPSHOT_CACHED, {})
        with pytest.raises((AttributeError, TypeError)):
            evt.event_id = "x"   # type: ignore[misc]

    def test_bus_emit_and_listener(self):
        bus     = SnapshotEventBus()
        received: List[SnapshotEvent] = []
        bus.add_listener(received.append)
        bus.emit(SnapshotEventType.SNAPSHOT_BUILT, {"k": "v"})
        assert len(received) == 1
        assert received[0].event_type == SnapshotEventType.SNAPSHOT_BUILT

    def test_bus_remove_listener(self):
        bus = SnapshotEventBus()
        fn  = lambda e: None
        bus.add_listener(fn)
        bus.remove_listener(fn)
        assert bus.listener_count() == 0

    def test_bus_suppresses_listener_exceptions(self):
        bus = SnapshotEventBus()
        bus.add_listener(lambda e: 1 / 0)   # will raise ZeroDivisionError
        # Should not raise
        bus.emit(SnapshotEventType.SNAPSHOT_BUILT, {})

    def test_bus_isolation(self):
        bus1 = SnapshotEventBus()
        bus2 = SnapshotEventBus()
        received1: List[SnapshotEvent] = []
        bus1.add_listener(received1.append)
        bus2.emit(SnapshotEventType.SNAPSHOT_STORED, {})
        assert len(received1) == 0

    def test_bus_clear(self):
        bus = SnapshotEventBus()
        bus.add_listener(lambda e: None)
        bus.clear()
        assert bus.listener_count() == 0


# ════════════════════════════════════════════════════════════════════════
# 15. Bundle
# ════════════════════════════════════════════════════════════════════════

class TestSnapshotBundle:
    def _make_bundle(self, n: int = 3) -> KnowledgeSnapshotBundle:
        snaps = [_make_snapshot() for _ in range(n)]
        return KnowledgeSnapshotBundle.create("Test Bundle", snaps)

    def test_create(self):
        b = self._make_bundle()
        assert b.name == "Test Bundle"
        assert b.snapshot_count == 3
        assert b.bundle_id.startswith("bundle-")

    def test_get_snapshot(self):
        snaps = [_make_snapshot()]
        b     = KnowledgeSnapshotBundle.create("b", snaps)
        found = b.get(snaps[0].snapshot_id)
        assert found is snaps[0]

    def test_get_missing_returns_none(self):
        b = self._make_bundle()
        assert b.get("nonexistent") is None

    def test_frozen(self):
        b = self._make_bundle()
        with pytest.raises((AttributeError, TypeError)):
            b.name = "x"   # type: ignore[misc]

    def test_to_dict(self):
        b = self._make_bundle()
        d = b.to_dict()
        assert d["snapshot_count"] == 3
        assert "snapshot_ids" in d

    def test_to_full_dict(self):
        b = self._make_bundle(2)
        d = b.to_full_dict()
        assert len(d["snapshots"]) == 2

    def test_bundle_registry(self):
        reg = KnowledgeSnapshotBundleRegistry()
        b   = self._make_bundle()
        reg.register(b)
        assert reg.get(b.bundle_id) is b
        assert reg.count() == 1

    def test_bundle_registry_remove(self):
        reg = KnowledgeSnapshotBundleRegistry()
        b   = self._make_bundle()
        reg.register(b)
        assert reg.remove(b.bundle_id) is True
        assert reg.get(b.bundle_id) is None

    def test_bundle_registry_capacity(self):
        reg = KnowledgeSnapshotBundleRegistry(max_bundles=1)
        reg.register(self._make_bundle())
        with pytest.raises(SnapshotCapacityError):
            reg.register(self._make_bundle())


# ════════════════════════════════════════════════════════════════════════
# 16. Serialization round-trip
# ════════════════════════════════════════════════════════════════════════

class TestSerializationRoundTrip:
    def test_to_dict_from_dict(self):
        snap  = _make_snapshot()
        snap2 = KnowledgeSnapshot.from_dict(snap.to_dict())
        assert snap2 == snap

    def test_to_json_from_json(self):
        snap  = _make_snapshot()
        snap2 = KnowledgeSnapshot.from_json(snap.to_json())
        assert snap2.content_hash == snap.content_hash

    def test_integrity_after_roundtrip(self):
        snap  = _make_snapshot()
        snap2 = KnowledgeSnapshot.from_dict(snap.to_dict())
        assert snap2.verify_integrity()


# ════════════════════════════════════════════════════════════════════════
# 17. Versioning
# ════════════════════════════════════════════════════════════════════════

class TestVersioning:
    def test_content_hash_stable(self):
        snap = _make_snapshot("stable-sess")
        d    = snap.to_dict()
        snap2 = KnowledgeSnapshot.from_dict(d)
        assert snap2.content_hash == snap.content_hash

    def test_different_sessions_different_hash(self):
        s1 = _make_snapshot("sess-1")
        s2 = _make_snapshot("sess-2")
        assert s1.content_hash != s2.content_hash

    def test_version_tag_default(self):
        snap = _make_snapshot()
        assert snap.version_tag == SnapshotVersionTag.STABLE

    def test_schema_version_constant(self):
        snap = _make_snapshot()
        assert snap.schema_version == SCHEMA_VERSION


# ════════════════════════════════════════════════════════════════════════
# 18. Concurrency
# ════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_store(self):
        store = KnowledgeSnapshotStore(max_snapshots=1_000)
        errors: List[Exception] = []
        snaps  = [_make_snapshot() for _ in range(50)]

        def worker(s: KnowledgeSnapshot) -> None:
            try:
                store.put(s)
                _ = store.get(s.snapshot_id)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(s,)) for s in snaps]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert store.count() == 50

    def test_concurrent_cache(self):
        cache  = KnowledgeSnapshotCache(max_size=100)
        errors: List[Exception] = []
        snaps  = [_make_snapshot() for _ in range(50)]

        def worker(s: KnowledgeSnapshot) -> None:
            try:
                cache.put(s)
                cache.get(s.snapshot_id)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(s,)) for s in snaps]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_concurrent_statistics(self):
        stats  = KnowledgeSnapshotStatistics()
        errors: List[Exception] = []

        def worker() -> None:
            try:
                for _ in range(20):
                    stats.record_built()
                    stats.record_stored()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        r = stats.report()
        assert r.snapshots_built == 200
        assert r.snapshots_stored == 200


# ════════════════════════════════════════════════════════════════════════
# 19. Regression — M1–M4 imports unaffected, M5 importable
# ════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_m5_package_importable(self):
        import iios.knowledge.snapshot as m5
        assert hasattr(m5, "KnowledgeSnapshot")

    def test_m4_package_importable(self):
        import iios.knowledge.intelligence as m4
        assert hasattr(m4, "KnowledgeIntelligenceEngine")

    def test_m2_package_importable(self):
        import iios.knowledge.governance as m2
        assert hasattr(m2, "CertificationManager")

    def test_m1_package_importable(self):
        import iios.knowledge.engine as m1
        assert hasattr(m1, "KnowledgeEngine")

    def test_all_exports_present(self):
        import iios.knowledge.snapshot as m5
        for name in m5.__all__:
            assert hasattr(m5, name), f"Missing export: {name!r}"
