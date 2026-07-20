"""
tests/unit/execution/analytics/snapshot/test_execution_analytics_snapshot.py
=============================================================================
Comprehensive unit tests for the Execution Analytics Snapshot package
(C8 M5).

Covers:
  - Snapshot builder (M1/M2/M3/M4 sources, validation, rejection)
  - Validation (all 10 checks)
  - Store (CRUD, all 9 query types)
  - Cache (put/get/TTL/eviction)
  - History (per-dimension retrieval, versioning)
  - Registry (register/get/duplicate rejection)
  - Statistics (all 7 counters)
  - Events (all 6 types)
  - Serialization (to_dict / to_json / roundtrip)
  - Bundle (creation, filter, iteration)
  - Concurrency (thread safety)
  - Regression (all snapshot fields present and typed)

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any, Dict, List

import pytest

from iios.execution.analytics.snapshot import (
    AnalyticsHealth,
    AnalyticsMetadata,
    AnalyticsMode,
    AnalyticsScope,
    AnalyticsSnapshotBuilder,
    AnalyticsSnapshotBundle,
    AnalyticsSnapshotCache,
    AnalyticsSnapshotEvent,
    AnalyticsSnapshotFactory,
    AnalyticsSnapshotHistory,
    AnalyticsSnapshotRegistry,
    AnalyticsSnapshotStatistics,
    AnalyticsSnapshotStore,
    AnalyticsSnapshotValidator,
    AnalyticsStatus,
    AuditMetadata,
    BenchmarkSummary,
    ConfidenceSummary,
    ExecutionAnalyticsSnapshot,
    HistoricalSummary,
    PerformanceKPIs,
    PerformanceScorecard,
    PerformanceSummary,
    PredictionSummary,
    SnapshotAnalyticsStatistics,
    SnapshotCapacityForecast,
    SnapshotEventType,
    SnapshotForecastSummary,
    SnapshotLifecycleState,
    SnapshotRiskForecast,
    SnapshotValidationResult,
    TrendSummary,
    health_from_score,
    make_snapshot_archived_event,
    make_snapshot_bundle,
    make_snapshot_cached_event,
    make_snapshot_created_event,
    make_snapshot_published_event,
    make_snapshot_retrieved_event,
    make_snapshot_validated_event,
    SnapshotBuildError,
    SnapshotDuplicateError,
    SnapshotEngineNotRunningError,
    SnapshotNotFoundError,
    SnapshotValidationError,
    SNAPSHOT_FRAMEWORK_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_snapshot(
    snapshot_id:          str                   = "",
    analytics_session_id: str                   = "ses-test",
    execution_session_id: str                   = "exec-test",
    lifecycle_state:      SnapshotLifecycleState = SnapshotLifecycleState.READY,
    analytics_status:     AnalyticsStatus       = AnalyticsStatus.COMPLETED,
    analytics_health:     AnalyticsHealth       = AnalyticsHealth.HEALTHY,
    op_health:            float                 = 0.9,
    **kwargs: Any,
) -> ExecutionAnalyticsSnapshot:
    return ExecutionAnalyticsSnapshot(
        snapshot_id           = snapshot_id or str(uuid.uuid4()),
        snapshot_version      = SNAPSHOT_SCHEMA_VERSION,
        analytics_session_id  = analytics_session_id,
        execution_session_id  = execution_session_id,
        workflow_id           = kwargs.get("workflow_id", "wf-1"),
        portfolio_id          = kwargs.get("portfolio_id", "port-1"),
        strategy_id           = kwargs.get("strategy_id", "strat-1"),
        analytics_scope       = kwargs.get("analytics_scope", AnalyticsScope.EXECUTION),
        analytics_mode        = kwargs.get("analytics_mode", AnalyticsMode.ON_DEMAND),
        lifecycle_state       = lifecycle_state,
        analytics_status      = analytics_status,
        analytics_health      = analytics_health,
        performance_summary   = kwargs.get("performance_summary"),
        performance_kpis      = kwargs.get("performance_kpis"),
        performance_scorecard = kwargs.get("performance_scorecard"),
        trend_summary         = kwargs.get("trend_summary"),
        benchmark_summary     = kwargs.get("benchmark_summary"),
        historical_summary    = kwargs.get("historical_summary"),
        prediction_summary    = kwargs.get("prediction_summary"),
        forecast_summary      = kwargs.get("forecast_summary"),
        confidence_summary    = kwargs.get("confidence_summary"),
        operational_health_score = op_health,
        capacity_forecast     = kwargs.get("capacity_forecast"),
        risk_forecast         = kwargs.get("risk_forecast"),
        analytics_statistics  = kwargs.get("analytics_statistics"),
        analytics_metadata    = kwargs.get("analytics_metadata"),
        audit_metadata        = kwargs.get("audit_metadata"),
        framework_version     = SNAPSHOT_FRAMEWORK_VERSION,
        timestamp             = kwargs.get("timestamp", time.time()),
    )


def _make_rich_snapshot(**kwargs) -> ExecutionAnalyticsSnapshot:
    return _make_snapshot(
        performance_summary   = PerformanceSummary(success_rate=0.95, win_rate=0.6, fill_rate=0.99),
        performance_kpis      = PerformanceKPIs(execution_success_rate=0.95, fill_rate=0.99),
        performance_scorecard = PerformanceScorecard(overall_score=0.85, grade="B"),
        trend_summary         = TrendSummary(dominant_trend="improving", trend_count=5, improving_count=4),
        benchmark_summary     = BenchmarkSummary(overall_score=0.80, benchmark_count=3),
        historical_summary    = HistoricalSummary(data_points=100),
        prediction_summary    = PredictionSummary(total_predictions=11, avg_confidence=0.75),
        forecast_summary      = SnapshotForecastSummary(total_forecasts=11, avg_confidence=0.75),
        confidence_summary    = ConfidenceSummary(overall_confidence=0.80),
        capacity_forecast     = SnapshotCapacityForecast(forecasted_utilization=0.55, bottleneck_risk=0.10),
        risk_forecast         = SnapshotRiskForecast(risk_level="minimal", risk_score=0.05),
        analytics_statistics  = SnapshotAnalyticsStatistics(total_cycles=100, successful_cycles=95),
        analytics_metadata    = AnalyticsMetadata(source_version="1.0.0"),
        audit_metadata        = AuditMetadata(created_by="test"),
        **kwargs,
    )


# ── Class 1: ExecutionAnalyticsSnapshot — structure ──────────────────────────

class TestSnapshotStructure:
    def test_creates_successfully(self):
        snap = _make_snapshot()
        assert isinstance(snap, ExecutionAnalyticsSnapshot)

    def test_is_frozen(self):
        snap = _make_snapshot()
        with pytest.raises((TypeError, AttributeError)):
            snap.snapshot_id = "bad"  # type: ignore

    def test_all_required_fields_present(self):
        snap = _make_snapshot()
        assert snap.snapshot_id
        assert snap.snapshot_version
        assert snap.analytics_session_id
        assert snap.execution_session_id
        assert snap.framework_version == SNAPSHOT_FRAMEWORK_VERSION
        assert snap.timestamp > 0.0

    def test_is_valid_ready(self):
        snap = _make_snapshot(lifecycle_state=SnapshotLifecycleState.READY)
        assert snap.is_valid

    def test_is_valid_published(self):
        snap = _make_snapshot(lifecycle_state=SnapshotLifecycleState.PUBLISHED)
        assert snap.is_valid
        assert snap.is_published

    def test_invalid_state_not_valid(self):
        snap = _make_snapshot(lifecycle_state=SnapshotLifecycleState.INVALID)
        assert not snap.is_valid

    def test_has_performance_false_by_default(self):
        snap = _make_snapshot()
        assert not snap.has_performance

    def test_has_performance_true(self):
        snap = _make_rich_snapshot()
        assert snap.has_performance

    def test_has_predictions_false_by_default(self):
        snap = _make_snapshot()
        assert not snap.has_predictions

    def test_has_predictions_true(self):
        snap = _make_rich_snapshot()
        assert snap.has_predictions

    def test_has_risk_false_by_default(self):
        snap = _make_snapshot()
        assert not snap.has_risk

    def test_has_risk_true(self):
        snap = _make_rich_snapshot()
        assert snap.has_risk


# ── Class 2: ExecutionAnalyticsSnapshot — serialisation ──────────────────────

class TestSnapshotSerialisation:
    def test_to_dict_returns_dict(self):
        snap = _make_rich_snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_has_all_top_level_keys(self):
        snap = _make_rich_snapshot()
        d = snap.to_dict()
        for key in [
            "snapshot_id", "snapshot_version", "analytics_session_id",
            "execution_session_id", "workflow_id", "portfolio_id", "strategy_id",
            "analytics_scope", "analytics_mode", "lifecycle_state",
            "analytics_status", "analytics_health", "operational_health_score",
            "framework_version", "timestamp",
        ]:
            assert key in d, f"Missing key: {key}"

    def test_to_json_valid_json(self):
        snap = _make_rich_snapshot()
        j = snap.to_json()
        parsed = json.loads(j)
        assert parsed["snapshot_id"] == snap.snapshot_id

    def test_to_dict_performance_summary(self):
        snap = _make_rich_snapshot()
        d = snap.to_dict()
        ps = d["performance_summary"]
        assert isinstance(ps, dict)
        assert "success_rate" in ps

    def test_to_dict_risk_forecast(self):
        snap = _make_rich_snapshot()
        d = snap.to_dict()
        rf = d["risk_forecast"]
        assert isinstance(rf, dict)
        assert "risk_score" in rf

    def test_to_dict_none_optional(self):
        snap = _make_snapshot()
        d = snap.to_dict()
        assert d["performance_summary"] is None
        assert d["prediction_summary"] is None
        assert d["risk_forecast"] is None

    def test_roundtrip_snapshot_id(self):
        snap = _make_rich_snapshot()
        d = snap.to_dict()
        assert d["snapshot_id"] == snap.snapshot_id


# ── Class 3: Validation ───────────────────────────────────────────────────────

class TestValidation:
    def _validator(self):
        return AnalyticsSnapshotValidator()

    def test_valid_snapshot_passes(self):
        snap = _make_rich_snapshot()
        result = self._validator().validate(snap)
        assert result.is_valid

    def test_blank_snapshot_id_fails(self):
        snap = _make_snapshot(snapshot_id=" ")
        result = self._validator().validate(snap)
        assert not result.is_valid
        assert any("snapshot_id" in e for e in result.errors)

    def test_invalid_lifecycle_state_fails(self):
        snap = _make_snapshot(lifecycle_state=SnapshotLifecycleState.BUILDING)
        result = self._validator().validate(snap)
        assert not result.is_valid

    def test_out_of_range_success_rate_fails(self):
        snap = _make_snapshot(
            performance_summary=PerformanceSummary(success_rate=1.5, win_rate=0.5, fill_rate=0.9)
        )
        result = self._validator().validate(snap)
        assert not result.is_valid
        assert any("success_rate" in e for e in result.errors)

    def test_out_of_range_confidence_fails(self):
        snap = _make_snapshot(
            prediction_summary=PredictionSummary(avg_confidence=1.2)
        )
        result = self._validator().validate(snap)
        assert not result.is_valid

    def test_invalid_trend_name_fails(self):
        snap = _make_snapshot(
            trend_summary=TrendSummary(dominant_trend="", trend_count=5)
        )
        result = self._validator().validate(snap)
        assert not result.is_valid

    def test_out_of_range_benchmark_fails(self):
        snap = _make_snapshot(
            benchmark_summary=BenchmarkSummary(overall_score=1.5)
        )
        result = self._validator().validate(snap)
        assert not result.is_valid

    def test_out_of_range_risk_score_fails(self):
        snap = _make_snapshot(
            risk_forecast=SnapshotRiskForecast(risk_score=1.5, confidence=0.5)
        )
        result = self._validator().validate(snap)
        assert not result.is_valid

    def test_out_of_range_op_health_fails(self):
        snap = _make_snapshot(op_health=1.5)
        result = self._validator().validate(snap)
        assert not result.is_valid

    def test_validate_and_raise(self):
        snap = _make_snapshot(snapshot_id=" ")
        with pytest.raises(SnapshotValidationError) as exc_info:
            self._validator().validate_and_raise(snap)
        assert len(exc_info.value.errors) > 0

    def test_wrong_framework_version_fails(self):
        snap = ExecutionAnalyticsSnapshot(
            snapshot_id           = str(uuid.uuid4()),
            snapshot_version      = SNAPSHOT_SCHEMA_VERSION,
            analytics_session_id  = "s1",
            execution_session_id  = "e1",
            workflow_id           = "",
            portfolio_id          = "",
            strategy_id           = "",
            analytics_scope       = AnalyticsScope.EXECUTION,
            analytics_mode        = AnalyticsMode.ON_DEMAND,
            lifecycle_state       = SnapshotLifecycleState.READY,
            analytics_status      = AnalyticsStatus.COMPLETED,
            analytics_health      = AnalyticsHealth.HEALTHY,
            performance_summary   = None,
            performance_kpis      = None,
            performance_scorecard = None,
            trend_summary         = None,
            benchmark_summary     = None,
            historical_summary    = None,
            prediction_summary    = None,
            forecast_summary      = None,
            confidence_summary    = None,
            operational_health_score = 0.9,
            capacity_forecast     = None,
            risk_forecast         = None,
            analytics_statistics  = None,
            analytics_metadata    = None,
            audit_metadata        = None,
            framework_version     = "0.0.1",  # wrong
        )
        result = self._validator().validate(snap)
        assert not result.is_valid

    def test_validate_build_inputs_ok(self):
        v = self._validator()
        r = v.validate_build_inputs(
            analytics_session_id="s1", execution_session_id="e1"
        )
        assert r.is_valid

    def test_validate_build_inputs_missing_session(self):
        v = self._validator()
        r = v.validate_build_inputs(
            analytics_session_id="", execution_session_id="e1"
        )
        assert not r.is_valid


# ── Class 4: Builder ──────────────────────────────────────────────────────────

class TestBuilder:
    @pytest.fixture(autouse=True)
    def builder(self):
        b = AnalyticsSnapshotBuilder()
        b.start()
        yield b
        b.stop()

    def test_build_minimal(self, builder):
        snap = builder.build(
            analytics_session_id="s1",
            execution_session_id="e1",
        )
        assert isinstance(snap, ExecutionAnalyticsSnapshot)
        assert snap.analytics_session_id == "s1"
        assert snap.execution_session_id == "e1"

    def test_build_requires_session_id(self, builder):
        with pytest.raises(SnapshotBuildError):
            builder.build(execution_session_id="e1")

    def test_build_requires_execution_session_id(self, builder):
        with pytest.raises(SnapshotBuildError):
            builder.build(analytics_session_id="s1")

    def test_build_with_explicit_snapshot_id(self, builder):
        sid = "snap-explicit-1"
        snap = builder.build(
            analytics_session_id="s1",
            execution_session_id="e1",
            snapshot_id=sid,
        )
        assert snap.snapshot_id == sid

    def test_build_lifecycle_state_ready(self, builder):
        snap = builder.build(
            analytics_session_id="s1",
            execution_session_id="e1",
        )
        assert snap.lifecycle_state == SnapshotLifecycleState.READY

    def test_build_framework_version(self, builder):
        snap = builder.build(
            analytics_session_id="s1",
            execution_session_id="e1",
        )
        assert snap.framework_version == SNAPSHOT_FRAMEWORK_VERSION

    def test_build_before_start_raises(self):
        b = AnalyticsSnapshotBuilder()
        with pytest.raises(SnapshotEngineNotRunningError):
            b.build(analytics_session_id="s1", execution_session_id="e1")

    def test_build_with_scope_and_mode(self, builder):
        snap = builder.build(
            analytics_session_id="s1",
            execution_session_id="e1",
            analytics_scope=AnalyticsScope.PORTFOLIO,
            analytics_mode=AnalyticsMode.BATCH,
        )
        assert snap.analytics_scope == AnalyticsScope.PORTFOLIO
        assert snap.analytics_mode == AnalyticsMode.BATCH


# ── Class 5: Factory ──────────────────────────────────────────────────────────

class TestFactory:
    @pytest.fixture(autouse=True)
    def factory(self):
        f = AnalyticsSnapshotFactory()
        f.start()
        yield f
        f.stop()

    def test_create_minimal(self, factory):
        snap = factory.create_minimal(
            analytics_session_id="s1",
            execution_session_id="e1",
        )
        assert isinstance(snap, ExecutionAnalyticsSnapshot)

    def test_create_validates(self, factory):
        snap = factory.create(
            analytics_session_id="s2",
            execution_session_id="e2",
            validate=True,
        )
        assert isinstance(snap, ExecutionAnalyticsSnapshot)

    def test_factory_statistics_incremented(self, factory):
        factory.create_minimal(analytics_session_id="s3", execution_session_id="e3")
        assert factory.statistics.validation_success >= 1

    def test_factory_before_start_raises(self):
        f = AnalyticsSnapshotFactory()
        with pytest.raises(SnapshotEngineNotRunningError):
            f.create_minimal(analytics_session_id="s1", execution_session_id="e1")

    def test_builder_property(self, factory):
        assert isinstance(factory.builder, AnalyticsSnapshotBuilder)

    def test_create_with_m3(self, factory):
        """Build snapshot using a real M3 PerformanceAnalyticsEngine report."""
        from iios.execution.analytics.performance import PerformanceAnalyticsEngine
        pae = PerformanceAnalyticsEngine()
        pae.start()
        pr = pae.process("ses-test-m3")
        snap = factory.create(
            analytics_session_id="ses-test-m3",
            execution_session_id="exec-test-m3",
            performance_report=pr,
        )
        assert snap.has_performance
        assert snap.performance_scorecard is not None
        pae.stop()

    def test_create_with_m4(self, factory):
        """Build snapshot using a real M4 PredictiveIntelligenceEngine report."""
        from iios.execution.analytics.predictive import (
            ForecastHorizon,
            PredictionDomain,
            PredictiveIntelligenceEngine,
        )
        pie = PredictiveIntelligenceEngine()
        pie.start()
        pred = pie.submit(PredictionDomain.EXECUTION_PERFORMANCE, ForecastHorizon.NEXT_HOUR)
        snap = factory.create(
            analytics_session_id="ses-test-m4",
            execution_session_id="exec-test-m4",
            prediction_report=pred,
        )
        assert snap.has_predictions
        assert snap.prediction_summary.total_predictions == 11
        pie.stop()

    def test_create_with_m3_and_m4(self, factory):
        """Build snapshot from both M3 and M4."""
        from iios.execution.analytics.performance import PerformanceAnalyticsEngine
        from iios.execution.analytics.predictive import (
            ForecastHorizon,
            PredictionDomain,
            PredictiveIntelligenceEngine,
        )
        pae = PerformanceAnalyticsEngine(); pae.start()
        pie = PredictiveIntelligenceEngine(); pie.start()
        pr   = pae.process("ses-both")
        pred = pie.submit(PredictionDomain.EXECUTION_PERFORMANCE)
        snap = factory.create(
            analytics_session_id="ses-both",
            execution_session_id="exec-both",
            performance_report=pr,
            prediction_report=pred,
        )
        assert snap.has_performance
        assert snap.has_predictions
        assert snap.forecast_summary is not None
        pae.stop(); pie.stop()


# ── Class 6: Store ────────────────────────────────────────────────────────────

class TestStore:
    @pytest.fixture(autouse=True)
    def store(self):
        s = AnalyticsSnapshotStore()
        s.start()
        yield s
        s.stop()

    def test_save_and_get(self, store):
        snap = _make_snapshot()
        store.save(snap)
        retrieved = store.get_by_id(snap.snapshot_id)
        assert retrieved.snapshot_id == snap.snapshot_id

    def test_get_not_found_raises(self, store):
        with pytest.raises(SnapshotNotFoundError):
            store.get_by_id("nonexistent-id")

    def test_count_increments(self, store):
        for _ in range(3):
            store.save(_make_snapshot())
        assert store.count >= 3

    def test_publish_changes_lifecycle_state(self, store):
        snap = _make_snapshot()
        store.save(snap)
        published = store.publish(snap.snapshot_id)
        assert published.lifecycle_state == SnapshotLifecycleState.PUBLISHED

    def test_archive_changes_lifecycle_state(self, store):
        snap = _make_snapshot()
        store.save(snap)
        store.archive(snap.snapshot_id, reason="test")
        archived = store.get_by_id(snap.snapshot_id)
        assert archived.lifecycle_state == SnapshotLifecycleState.ARCHIVED

    # Query: by analytics session
    def test_query_by_analytics_session(self, store):
        sid = "ses-q1"
        for _ in range(3):
            store.save(_make_snapshot(analytics_session_id=sid))
        results = store.get_by_analytics_session(sid)
        assert len(results) >= 3

    # Query: by execution session
    def test_query_by_execution_session(self, store):
        eid = "exec-q1"
        for _ in range(2):
            store.save(_make_snapshot(execution_session_id=eid))
        results = store.get_by_execution_session(eid)
        assert len(results) >= 2

    # Query: by workflow
    def test_query_by_workflow(self, store):
        wid = "wf-q1"
        for _ in range(2):
            store.save(_make_snapshot(workflow_id=wid))
        results = store.get_by_workflow(wid)
        assert len(results) >= 2

    # Query: by portfolio
    def test_query_by_portfolio(self, store):
        pid = "port-q1"
        for _ in range(2):
            store.save(_make_snapshot(portfolio_id=pid))
        results = store.get_by_portfolio(pid)
        assert len(results) >= 2

    # Query: by strategy
    def test_query_by_strategy(self, store):
        stid = "strat-q1"
        for _ in range(2):
            store.save(_make_snapshot(strategy_id=stid))
        results = store.get_by_strategy(stid)
        assert len(results) >= 2

    # Query: by status
    def test_query_by_status(self, store):
        store.save(_make_snapshot(analytics_status=AnalyticsStatus.ACTIVE))
        store.save(_make_snapshot(analytics_status=AnalyticsStatus.COMPLETED))
        active = store.get_by_status(AnalyticsStatus.ACTIVE)
        assert any(s.analytics_status == AnalyticsStatus.ACTIVE for s in active)

    # Query: by health score
    def test_query_by_health(self, store):
        store.save(_make_snapshot(op_health=0.95))
        store.save(_make_snapshot(op_health=0.20))
        results = store.get_by_health(min_score=0.90)
        assert all(s.operational_health_score >= 0.90 for s in results)

    # Query: by timestamp range
    def test_query_by_timestamp_range(self, store):
        now = time.time()
        store.save(_make_snapshot(timestamp=now))
        results = store.get_by_timestamp_range(now - 1.0, now + 1.0)
        assert len(results) >= 1

    # Query: latest
    def test_query_latest(self, store):
        snap1 = _make_snapshot(timestamp=time.time() - 100)
        snap2 = _make_snapshot(timestamp=time.time())
        store.save(snap1)
        store.save(snap2)
        latest = store.get_latest()
        assert latest is not None

    # Query: historical versions
    def test_historical_versions(self, store):
        sid = "ses-hv"
        snaps = [_make_snapshot(analytics_session_id=sid) for _ in range(4)]
        for s in snaps:
            store.save(s)
        versions = store.historical_versions(sid)
        assert len(versions) >= 4

    def test_get_latest_for_session(self, store):
        sid = "ses-latest"
        for _ in range(3):
            store.save(_make_snapshot(analytics_session_id=sid))
        latest = store.get_latest_for_session(sid)
        assert latest is not None
        assert latest.analytics_session_id == sid

    def test_statistics_counts(self, store):
        store.save(_make_snapshot())
        assert store.statistics.snapshots_created >= 1


# ── Class 7: Cache ────────────────────────────────────────────────────────────

class TestCache:
    @pytest.fixture(autouse=True)
    def cache(self):
        c = AnalyticsSnapshotCache(max_size=5, ttl_seconds=3600.0)
        c.start()
        yield c
        c.stop()

    def test_put_and_get(self, cache):
        snap = _make_snapshot()
        cache.put(snap)
        result = cache.get(snap.snapshot_id)
        assert result is not None
        assert result.snapshot_id == snap.snapshot_id

    def test_miss_returns_none(self, cache):
        assert cache.get("nonexistent") is None

    def test_size_increments(self, cache):
        for _ in range(3):
            cache.put(_make_snapshot())
        assert cache.size == 3

    def test_eviction_at_max_size(self, cache):
        snaps = [_make_snapshot() for _ in range(6)]
        for s in snaps:
            cache.put(s)
        assert cache.size <= 5

    def test_hit_count_increments(self, cache):
        snap = _make_snapshot()
        cache.put(snap)
        cache.get(snap.snapshot_id)
        cache.get(snap.snapshot_id)
        assert cache.hit_count >= 2

    def test_miss_count_increments(self, cache):
        cache.get("miss-1")
        cache.get("miss-2")
        assert cache.miss_count >= 2

    def test_evict_removes_entry(self, cache):
        snap = _make_snapshot()
        cache.put(snap)
        cache.evict(snap.snapshot_id)
        assert cache.get(snap.snapshot_id) is None

    def test_clear_empties_cache(self, cache):
        for _ in range(3):
            cache.put(_make_snapshot())
        cache.clear()
        assert cache.size == 0

    def test_ttl_expiry(self):
        # Very short TTL
        c = AnalyticsSnapshotCache(max_size=10, ttl_seconds=0.01)
        c.start()
        snap = _make_snapshot()
        c.put(snap)
        time.sleep(0.05)
        result = c.get(snap.snapshot_id)
        assert result is None
        c.stop()


# ── Class 8: History ──────────────────────────────────────────────────────────

class TestHistory:
    def test_add_and_recent(self):
        h = AnalyticsSnapshotHistory()
        for _ in range(5):
            h.add(_make_snapshot())
        assert h.total_count == 5
        recent = h.recent(3)
        assert len(recent) == 3

    def test_by_session(self):
        h = AnalyticsSnapshotHistory()
        for _ in range(4):
            h.add(_make_snapshot(analytics_session_id="ses-h1"))
        h.add(_make_snapshot(analytics_session_id="ses-h2"))
        assert len(h.by_session("ses-h1")) == 4
        assert len(h.by_session("ses-h2")) == 1

    def test_by_portfolio(self):
        h = AnalyticsSnapshotHistory()
        for _ in range(3):
            h.add(_make_snapshot(portfolio_id="port-h1"))
        assert len(h.by_portfolio("port-h1")) == 3

    def test_by_strategy(self):
        h = AnalyticsSnapshotHistory()
        for _ in range(2):
            h.add(_make_snapshot(strategy_id="strat-h1"))
        assert len(h.by_strategy("strat-h1")) == 2

    def test_by_workflow(self):
        h = AnalyticsSnapshotHistory()
        for _ in range(3):
            h.add(_make_snapshot(workflow_id="wf-h1"))
        assert len(h.by_workflow("wf-h1")) == 3

    def test_latest_for_session(self):
        h = AnalyticsSnapshotHistory()
        for i in range(5):
            h.add(_make_snapshot(analytics_session_id="ses-latest"))
        latest = h.latest_for_session("ses-latest")
        assert latest is not None

    def test_clear(self):
        h = AnalyticsSnapshotHistory()
        for _ in range(5):
            h.add(_make_snapshot())
        h.clear()
        assert h.total_count == 0

    def test_session_count(self):
        h = AnalyticsSnapshotHistory()
        h.add(_make_snapshot(analytics_session_id="s1"))
        h.add(_make_snapshot(analytics_session_id="s2"))
        assert h.session_count == 2


# ── Class 9: Registry ─────────────────────────────────────────────────────────

class TestRegistry:
    @pytest.fixture(autouse=True)
    def registry(self):
        r = AnalyticsSnapshotRegistry()
        r.start()
        yield r
        r.stop()

    def test_register_and_get(self, registry):
        snap = _make_snapshot()
        registry.register(snap)
        result = registry.get(snap.snapshot_id)
        assert result.snapshot_id == snap.snapshot_id

    def test_get_not_found_raises(self, registry):
        with pytest.raises(SnapshotNotFoundError):
            registry.get("nonexistent")

    def test_duplicate_registration_raises(self, registry):
        snap = _make_snapshot()
        registry.register(snap)
        with pytest.raises(SnapshotDuplicateError):
            registry.register(snap)

    def test_contains(self, registry):
        snap = _make_snapshot()
        registry.register(snap)
        assert registry.contains(snap.snapshot_id)
        assert not registry.contains("other-id")

    def test_remove(self, registry):
        snap = _make_snapshot()
        registry.register(snap)
        registry.remove(snap.snapshot_id)
        assert not registry.contains(snap.snapshot_id)

    def test_count(self, registry):
        for _ in range(3):
            registry.register(_make_snapshot())
        assert registry.count == 3

    def test_list_all(self, registry):
        snaps = [_make_snapshot() for _ in range(4)]
        for s in snaps:
            registry.register(s)
        all_snaps = registry.list_all()
        assert len(all_snaps) == 4

    def test_registry_before_start_raises(self):
        r = AnalyticsSnapshotRegistry()
        with pytest.raises(SnapshotEngineNotRunningError):
            r.register(_make_snapshot())


# ── Class 10: Statistics ──────────────────────────────────────────────────────

class TestStatistics:
    def test_record_created(self):
        s = AnalyticsSnapshotStatistics()
        s.record_created(build_time_ms=10.0)
        assert s.snapshots_created == 1
        assert s.avg_build_time_ms == 10.0

    def test_record_published(self):
        s = AnalyticsSnapshotStatistics()
        s.record_published()
        assert s.snapshots_published == 1

    def test_record_archived(self):
        s = AnalyticsSnapshotStatistics()
        s.record_archived()
        assert s.snapshots_archived == 1

    def test_record_validation_success(self):
        s = AnalyticsSnapshotStatistics()
        s.record_validation_success()
        assert s.validation_success == 1
        assert s.validation_success_rate == 1.0

    def test_record_validation_failure(self):
        s = AnalyticsSnapshotStatistics()
        s.record_validation_failure()
        assert s.validation_failure == 1
        assert s.validation_success_rate == 0.0

    def test_mixed_validation_rate(self):
        s = AnalyticsSnapshotStatistics()
        s.record_validation_success()
        s.record_validation_success()
        s.record_validation_failure()
        assert abs(s.validation_success_rate - 2/3) < 0.01

    def test_record_size(self):
        s = AnalyticsSnapshotStatistics()
        s.record_size(1000)
        s.record_size(2000)
        assert s.avg_snapshot_size == 1500.0

    def test_snapshot_dict(self):
        s = AnalyticsSnapshotStatistics()
        s.record_created(5.0)
        d = s.snapshot()
        assert "snapshots_created" in d
        assert "avg_build_time_ms" in d
        assert "validation_success_rate" in d

    def test_reset(self):
        s = AnalyticsSnapshotStatistics()
        s.record_created()
        s.reset()
        assert s.snapshots_created == 0


# ── Class 11: Events ──────────────────────────────────────────────────────────

class TestEvents:
    def test_created_event(self):
        ev = make_snapshot_created_event("snap-1", "ses-1")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_CREATED
        assert ev.snapshot_id == "snap-1"

    def test_validated_event(self):
        ev = make_snapshot_validated_event("snap-2")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_VALIDATED

    def test_published_event(self):
        ev = make_snapshot_published_event("snap-3")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_PUBLISHED

    def test_archived_event(self):
        ev = make_snapshot_archived_event("snap-4", reason="expired")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_ARCHIVED
        assert ev.payload["reason"] == "expired"

    def test_retrieved_event(self):
        ev = make_snapshot_retrieved_event("snap-5")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_RETRIEVED

    def test_cached_event(self):
        ev = make_snapshot_cached_event("snap-6")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_CACHED

    def test_event_to_dict(self):
        ev = make_snapshot_created_event("snap-7", "ses-7")
        d = ev.to_dict()
        assert d["event_type"] == SnapshotEventType.SNAPSHOT_CREATED.value
        assert "occurred_at" in d

    def test_event_is_frozen(self):
        ev = make_snapshot_created_event("snap-8", "ses-8")
        with pytest.raises((TypeError, AttributeError)):
            ev.snapshot_id = "bad"  # type: ignore

    def test_event_has_unique_ids(self):
        ev1 = make_snapshot_created_event("snap-x", "ses-x")
        ev2 = make_snapshot_created_event("snap-x", "ses-x")
        assert ev1.event_id != ev2.event_id


# ── Class 12: Bundle ──────────────────────────────────────────────────────────

class TestBundle:
    def test_create_bundle(self):
        snaps = [_make_snapshot() for _ in range(5)]
        bundle = make_snapshot_bundle(snaps, label="test-bundle")
        assert bundle.count == 5
        assert bundle.label == "test-bundle"

    def test_bundle_is_frozen(self):
        bundle = make_snapshot_bundle([_make_snapshot()])
        with pytest.raises((TypeError, AttributeError)):
            bundle.label = "bad"  # type: ignore

    def test_bundle_avg_health(self):
        snaps = [
            _make_snapshot(op_health=0.8),
            _make_snapshot(op_health=0.6),
        ]
        bundle = make_snapshot_bundle(snaps)
        assert abs(bundle.avg_operational_health - 0.7) < 0.01

    def test_bundle_published_count(self):
        pub  = _make_snapshot(lifecycle_state=SnapshotLifecycleState.PUBLISHED)
        ready = _make_snapshot(lifecycle_state=SnapshotLifecycleState.READY)
        bundle = make_snapshot_bundle([pub, ready])
        assert bundle.published_count == 1

    def test_bundle_filter_by_status(self):
        active    = _make_snapshot(analytics_status=AnalyticsStatus.ACTIVE)
        completed = _make_snapshot(analytics_status=AnalyticsStatus.COMPLETED)
        bundle = make_snapshot_bundle([active, completed])
        filtered = bundle.filter_by_status(AnalyticsStatus.ACTIVE)
        assert filtered.count == 1

    def test_bundle_filter_by_health(self):
        healthy  = _make_snapshot(analytics_health=AnalyticsHealth.HEALTHY)
        degraded = _make_snapshot(analytics_health=AnalyticsHealth.DEGRADED)
        bundle   = make_snapshot_bundle([healthy, degraded])
        filtered = bundle.filter_by_health(AnalyticsHealth.HEALTHY)
        assert filtered.count == 1

    def test_bundle_get_by_id(self):
        snap = _make_snapshot()
        bundle = make_snapshot_bundle([snap])
        result = bundle.get(snap.snapshot_id)
        assert result is not None
        assert result.snapshot_id == snap.snapshot_id

    def test_bundle_iteration(self):
        snaps = [_make_snapshot() for _ in range(4)]
        bundle = make_snapshot_bundle(snaps)
        count = sum(1 for _ in bundle)
        assert count == 4

    def test_bundle_to_dict(self):
        bundle = make_snapshot_bundle([_make_snapshot()], label="test")
        d = bundle.to_dict()
        assert "bundle_id" in d
        assert "count" in d
        assert "snapshots" in d

    def test_bundle_to_json(self):
        bundle = make_snapshot_bundle([_make_snapshot()])
        j = bundle.to_json()
        parsed = json.loads(j)
        assert "bundle_id" in parsed

    def test_empty_bundle(self):
        bundle = make_snapshot_bundle([])
        assert bundle.is_empty
        assert bundle.count == 0


# ── Class 13: Concurrency ─────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_store_writes(self):
        store = AnalyticsSnapshotStore()
        store.start()
        errors = []

        def worker():
            try:
                snap = _make_snapshot()
                store.save(snap)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0
        assert store.count == 20
        store.stop()

    def test_concurrent_cache_access(self):
        cache = AnalyticsSnapshotCache()
        cache.start()
        snap = _make_snapshot()
        cache.put(snap)
        errors = []

        def reader():
            try:
                result = cache.get(snap.snapshot_id)
                assert result is not None
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0
        cache.stop()

    def test_concurrent_factory_create(self):
        factory = AnalyticsSnapshotFactory()
        factory.start()
        results = []
        errors  = []

        def worker(i):
            try:
                snap = factory.create_minimal(
                    analytics_session_id=f"s-{i}",
                    execution_session_id=f"e-{i}",
                )
                results.append(snap)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert len(errors) == 0
        assert len(results) == 10
        factory.stop()


# ── Class 14: Regression ──────────────────────────────────────────────────────

class TestRegression:
    def test_all_snapshot_fields_in_to_dict(self):
        snap = _make_rich_snapshot()
        d = snap.to_dict()
        expected_keys = [
            "snapshot_id", "snapshot_version", "analytics_session_id",
            "execution_session_id", "workflow_id", "portfolio_id", "strategy_id",
            "analytics_scope", "analytics_mode", "lifecycle_state",
            "analytics_status", "analytics_health",
            "performance_summary", "performance_kpis", "performance_scorecard",
            "trend_summary", "benchmark_summary", "historical_summary",
            "prediction_summary", "forecast_summary", "confidence_summary",
            "operational_health_score",
            "capacity_forecast", "risk_forecast",
            "analytics_statistics", "analytics_metadata", "audit_metadata",
            "framework_version", "timestamp",
        ]
        for key in expected_keys:
            assert key in d, f"Missing field in to_dict: {key}"

    def test_health_from_score_all_levels(self):
        assert health_from_score(0.95) == AnalyticsHealth.HEALTHY
        assert health_from_score(0.65) == AnalyticsHealth.DEGRADED
        assert health_from_score(0.30) == AnalyticsHealth.CRITICAL
        assert health_from_score(0.05) == AnalyticsHealth.CRITICAL

    def test_snapshot_ids_are_unique(self):
        snaps = [_make_snapshot() for _ in range(100)]
        ids = {s.snapshot_id for s in snaps}
        assert len(ids) == 100

    def test_snapshot_timestamp_positive(self):
        snap = _make_snapshot()
        assert snap.timestamp > 0.0

    def test_performance_summary_fields_in_range(self):
        snap = _make_rich_snapshot()
        ps = snap.performance_summary
        assert 0.0 <= ps.success_rate <= 1.0
        assert 0.0 <= ps.win_rate <= 1.0
        assert 0.0 <= ps.fill_rate <= 1.0

    def test_risk_forecast_fields_in_range(self):
        snap = _make_rich_snapshot()
        rf = snap.risk_forecast
        assert 0.0 <= rf.risk_score <= 1.0
        assert 0.0 <= rf.confidence <= 1.0

    def test_capacity_forecast_fields_in_range(self):
        snap = _make_rich_snapshot()
        cf = snap.capacity_forecast
        assert 0.0 <= cf.forecasted_utilization <= 1.0
        assert 0.0 <= cf.bottleneck_risk <= 1.0

    def test_confidence_summary_fields_in_range(self):
        snap = _make_rich_snapshot()
        cs = snap.confidence_summary
        for field in [cs.overall_confidence, cs.performance_confidence,
                      cs.prediction_confidence, cs.risk_confidence]:
            assert 0.0 <= field <= 1.0
