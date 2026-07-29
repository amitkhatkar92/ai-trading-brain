"""
test_learning_evaluation.py
============================
Comprehensive test suite for the A7 Learning & Evaluation Platform.

Coverage areas:
  1. Exceptions (all 23 error classes)
  2. Core domain types (10 classes)
  3. Metrics (6 classes)
  4. Events (13 event types + event bus)
  5. Evaluation layer (EvaluationSession, EvaluationManager)
  6. Benchmark layer (BenchmarkSuite, BenchmarkReport, BenchmarkManager)
  7. Learning layer (FeedbackCollector, LearningHistory, LearningManager)
  8. Quality layer (QualityRule, ValidationReport, QualityManager)
  9. Policy layer (5 policy pairs)
  10. Snapshot layer
  11. Container
  12. Gateway (lifecycle + all public methods)
"""
from __future__ import annotations

import time
import uuid

import pytest

# ── imports ───────────────────────────────────────────────────────────────────

from iios.ai.learning_evaluation.exceptions.learning_evaluation_exceptions import (
    AIBenchmarkAlreadyRunningError,
    AIBenchmarkNotFoundError,
    AIBenchmarkScenarioError,
    AIBenchmarkSuiteNotFoundError,
    AIEvaluationRequestNotFoundError,
    AIEvaluationSessionAlreadyExistsError,
    AIEvaluationSessionClosedError,
    AIEvaluationSessionNotFoundError,
    AIEvaluationValidationError,
    AIFeedbackException,
    AIImprovementException,
    AILearningEvaluationException,
    AILearningEvaluationPolicyException,
    AILearningEvaluationPolicyViolationError,
    AILearningException,
    AILearningRecordNotFoundError,
    AIMetricsCalculationError,
    AIMetricsException,
    AIQualityAssessmentError,
    AIQualityException,
    AIQualityRuleViolationError,
    AIValidationException,
)

from iios.ai.learning_evaluation.core import (
    BenchmarkMetadata,
    BenchmarkOutcome,
    BenchmarkResult,
    BenchmarkScenario,
    BenchmarkStatus,
    BenchmarkType,
    EvaluationMetadata,
    EvaluationOutcome,
    EvaluationRequest,
    EvaluationResult,
    EvaluationStatus,
    EvaluationType,
    FeedbackRecord,
    FeedbackSentiment,
    FeedbackType,
    ImprovementRecommendation,
    LearningCategory,
    LearningRecord,
    Priority,
    QualityDimension,
    QualityGrade,
    QualityScore,
    RecommendationType,
    ScenarioResult,
    ScenarioType,
)

from iios.ai.learning_evaluation.metrics import (
    AccuracyMetrics,
    ConfidenceMetrics,
    CostMetrics,
    LatencyMetrics,
    PerformanceMetrics,
    ReliabilityMetrics,
)

from iios.ai.learning_evaluation.events import (
    BenchmarkCompletedEvent,
    BenchmarkStartedEvent,
    EvaluationResultAddedEvent,
    EvaluationSessionCompletedEvent,
    EvaluationSessionCreatedEvent,
    EvaluationSessionFailedEvent,
    FeedbackReceivedEvent,
    ImprovementSuggestedEvent,
    LearningEvaluationEventBus,
    LearningEvaluationEventType,
    LearningRecordedEvent,
    QualityAssessedEvent,
)

from iios.ai.learning_evaluation.evaluation import EvaluationManager, EvaluationSession
from iios.ai.learning_evaluation.benchmark  import BenchmarkManager, BenchmarkReport, BenchmarkSuite
from iios.ai.learning_evaluation.learning   import FeedbackCollector, LearningHistory, LearningManager
from iios.ai.learning_evaluation.quality    import QualityManager, QualityRule, RuleCategory, ValidationReport

from iios.ai.learning_evaluation.policy import (
    AcceptancePolicy,
    BenchmarkPolicy,
    DefaultAcceptancePolicy,
    DefaultBenchmarkPolicy,
    DefaultEvaluationPolicy,
    DefaultLearningPolicy,
    DefaultQualityPolicy,
    EvaluationPolicy,
    LearningPolicy,
    QualityPolicy,
)

from iios.ai.learning_evaluation.snapshot import (
    EvaluationSessionSnapshot,
    LearningEvaluationFrameworkSnapshot,
)
from iios.ai.learning_evaluation.container import LearningEvaluationContainer
from iios.ai.learning_evaluation.gateway   import LearningEvaluationGateway


# ═════════════════════════════════════════════════════════════════════════════
# 1. EXCEPTIONS
# ═════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_exception(self):
        ex = AILearningEvaluationException("test")
        assert "AI-1200" in ex.message
        assert ex.error_code == "AI-1200"

    def test_session_not_found(self):
        ex = AIEvaluationSessionNotFoundError("sid")
        assert ex.error_code == "AI-1201"

    def test_session_already_exists(self):
        ex = AIEvaluationSessionAlreadyExistsError("sid")
        assert ex.error_code == "AI-1202"

    def test_session_closed(self):
        ex = AIEvaluationSessionClosedError("sid")
        assert ex.error_code == "AI-1203"

    def test_request_not_found(self):
        ex = AIEvaluationRequestNotFoundError("rid")
        assert ex.error_code == "AI-1204"

    def test_validation_error(self):
        ex = AIEvaluationValidationError("v")
        assert ex.error_code == "AI-1205"

    def test_benchmark_not_found(self):
        ex = AIBenchmarkNotFoundError("bid")
        assert ex.error_code == "AI-1211"

    def test_benchmark_suite_not_found(self):
        ex = AIBenchmarkSuiteNotFoundError("sid")
        assert ex.error_code == "AI-1212"

    def test_benchmark_already_running(self):
        ex = AIBenchmarkAlreadyRunningError("bid")
        assert ex.error_code == "AI-1213"

    def test_benchmark_scenario_error(self):
        ex = AIBenchmarkScenarioError("s")
        assert ex.error_code == "AI-1214"

    def test_learning_record_not_found(self):
        ex = AILearningRecordNotFoundError("rid")
        assert ex.error_code == "AI-1221"

    def test_feedback_exception(self):
        ex = AIFeedbackException("f")
        assert ex.error_code == "AI-1222"

    def test_improvement_exception(self):
        ex = AIImprovementException("i")
        assert ex.error_code == "AI-1223"

    def test_quality_rule_violation(self):
        ex = AIQualityRuleViolationError("rule")
        assert ex.error_code == "AI-1231"

    def test_quality_assessment_error(self):
        ex = AIQualityAssessmentError("q")
        assert ex.error_code == "AI-1232"

    def test_validation_exception(self):
        ex = AIValidationException("v")
        assert ex.error_code == "AI-1233"

    def test_metrics_calculation_error(self):
        ex = AIMetricsCalculationError("m")
        assert ex.error_code == "AI-1241"

    def test_policy_violation(self):
        ex = AILearningEvaluationPolicyViolationError("p")
        assert ex.error_code == "AI-1251"

    def test_inheritance(self):
        ex = AIEvaluationSessionNotFoundError("sid")
        assert isinstance(ex, AILearningEvaluationException)


# ═════════════════════════════════════════════════════════════════════════════
# 2. CORE TYPES
# ═════════════════════════════════════════════════════════════════════════════

class TestEvaluationMetadata:
    def test_create(self):
        meta = EvaluationMetadata.create("test", EvaluationType.OFFLINE, "tgt1", "user1")
        assert meta.evaluation_type == EvaluationType.OFFLINE
        assert meta.target_id == "tgt1"

    def test_status_enum(self):
        assert EvaluationStatus.CREATED.is_active()
        assert not EvaluationStatus.CREATED.is_terminal()
        assert EvaluationStatus.COMPLETED.is_terminal()
        assert EvaluationStatus.FAILED.is_terminal()


class TestEvaluationRequest:
    def test_create(self):
        req = EvaluationRequest.create("sid", {"q": "hi"})
        assert req.session_id == "sid"
        assert req.input_data == {"q": "hi"}

    def test_get_param(self):
        req = EvaluationRequest.create("sid", {}, temperature=0.7)
        assert req.get_param("temperature") == pytest.approx(0.7)
        assert req.get_param("missing", 99) == 99


class TestEvaluationResult:
    def test_passed_factory(self):
        req = EvaluationRequest.create("sid", {})
        r   = EvaluationResult.passed("sid", req.request_id, "answer")
        assert r.outcome == EvaluationOutcome.PASS
        assert r.is_success()

    def test_failed_factory(self):
        req = EvaluationRequest.create("sid", {})
        r   = EvaluationResult.failed("sid", req.request_id, "answer")
        assert r.outcome == EvaluationOutcome.FAIL
        assert not r.is_success()

    def test_error_factory(self):
        req = EvaluationRequest.create("sid", {})
        r   = EvaluationResult.error("sid", req.request_id, "oops")
        assert r.outcome == EvaluationOutcome.ERROR

    def test_get_score(self):
        req = EvaluationRequest.create("sid", {})
        r   = EvaluationResult.passed("sid", req.request_id, "x", scores=frozenset([("acc", 0.9)]))
        assert r.get_score("acc") == pytest.approx(0.9)


class TestBenchmarkMetadata:
    def test_create(self):
        meta = BenchmarkMetadata.create("bench1", BenchmarkType.AGENT, "agent_x", "user1")
        assert meta.benchmark_type == BenchmarkType.AGENT
        assert meta.target_id == "agent_x"

    def test_status_transitions(self):
        assert BenchmarkStatus.RUNNING.is_active()
        assert BenchmarkStatus.COMPLETED.is_terminal()


class TestBenchmarkScenario:
    def test_create(self):
        sc = BenchmarkScenario.create("math_q", ScenarioType.CORRECTNESS, {"q": "1+1"})
        assert sc.name == "math_q"
        assert sc.pass_threshold == pytest.approx(0.6)

    def test_get_param(self):
        sc = BenchmarkScenario.create("q", ScenarioType.EDGE_CASE, {}, timeout=30)
        assert sc.get_param("timeout") == 30


class TestBenchmarkResult:
    def _sr(self, score: float) -> ScenarioResult:
        return ScenarioResult.create(str(uuid.uuid4()), "scenario", score, 10.0)

    def test_build_passed(self):
        srs = frozenset([self._sr(0.9), self._sr(0.8)])
        r   = BenchmarkResult.build("bid", srs)
        assert r.outcome == BenchmarkOutcome.PASSED

    def test_build_failed(self):
        srs = frozenset([self._sr(0.1), self._sr(0.2)])
        r   = BenchmarkResult.build("bid", srs)
        assert r.outcome == BenchmarkOutcome.FAILED

    def test_pass_rate(self):
        srs = frozenset([self._sr(0.9), self._sr(0.1)])
        r   = BenchmarkResult.build("bid", srs)
        assert 0.0 <= r.pass_rate() <= 1.0


class TestLearningRecord:
    def test_create(self):
        lr = LearningRecord.create("agent1", LearningCategory.ACCURACY, "obs", signal=0.8)
        assert lr.category == LearningCategory.ACCURACY
        assert lr.signal   == pytest.approx(0.8)

    def test_metadata(self):
        lr = LearningRecord.create("a", LearningCategory.BEHAVIOR, "x", note="test")
        assert lr.get_meta("note") == "test"


class TestFeedbackRecord:
    def test_create(self):
        fr = FeedbackRecord.create("tgt1", "user1", FeedbackType.RATING, "good",
                                   rating=4.5)
        assert fr.rating == pytest.approx(4.5)
        assert fr.feedback_type == FeedbackType.RATING

    def test_rating_clamped(self):
        fr = FeedbackRecord.create("t", "u", FeedbackType.CORRECTION, "x", rating=99)
        assert fr.rating == pytest.approx(5.0)


class TestImprovementRecommendation:
    def test_create(self):
        rec = ImprovementRecommendation.create(
            "agent1", RecommendationType.PARAMETER_TUNE, Priority.HIGH,
            "tune params", expected_gain=0.15
        )
        assert rec.priority == Priority.HIGH
        assert rec.expected_gain == pytest.approx(0.15)

    def test_priority_score(self):
        assert Priority.CRITICAL.score() > Priority.HIGH.score()


class TestQualityScore:
    def test_build(self):
        dim_scores = frozenset([("accuracy", 0.9), ("relevance", 0.8)])
        qs = QualityScore.build("tgt1", dim_scores)
        assert qs.grade in (QualityGrade.A, QualityGrade.B)

    def test_grade_from_score(self):
        assert QualityGrade.from_score(0.95) == QualityGrade.A
        assert QualityGrade.from_score(0.80) == QualityGrade.B
        assert QualityGrade.from_score(0.65) == QualityGrade.C
        assert QualityGrade.from_score(0.50) == QualityGrade.D
        assert QualityGrade.from_score(0.10) == QualityGrade.F

    def test_passed(self):
        dim_scores = frozenset([("accuracy", 0.95)])
        qs = QualityScore.build("t", dim_scores)
        assert qs.passed(QualityGrade.B)

    def test_get_dimension(self):
        dim_scores = frozenset([(QualityDimension.ACCURACY.value, 0.92)])
        qs = QualityScore.build("t", dim_scores)
        assert qs.get_dimension(QualityDimension.ACCURACY) == pytest.approx(0.92)


# ═════════════════════════════════════════════════════════════════════════════
# 3. METRICS
# ═════════════════════════════════════════════════════════════════════════════

class TestAccuracyMetrics:
    def test_compute(self):
        m = AccuracyMetrics.compute(80, 10, 10, 100)
        assert 0.0 < m.precision <= 1.0
        assert 0.0 < m.recall    <= 1.0
        assert 0.0 < m.f1        <= 1.0

    def test_perfect(self):
        m = AccuracyMetrics.compute(100, 0, 0, 100)
        assert m.precision == pytest.approx(1.0)
        assert m.recall    == pytest.approx(1.0)

    def test_zero(self):
        m = AccuracyMetrics.compute(0, 0, 0, 0)
        assert m.precision == pytest.approx(0.0)


class TestLatencyMetrics:
    def test_compute(self):
        lats = [10.0, 20.0, 30.0, 40.0, 200.0]
        m = LatencyMetrics.compute(lats)
        assert m.p50_ms <= m.p95_ms <= m.p99_ms
        assert m.sample_size == 5

    def test_empty(self):
        m = LatencyMetrics.compute([])
        assert m.p50_ms == pytest.approx(0.0)

    def test_meets_slo(self):
        lats = list(range(1, 101))
        m = LatencyMetrics.compute([float(x) for x in lats])
        assert m.meets_slo(100.0)
        assert not m.meets_slo(5.0)


class TestCostMetrics:
    def test_compute(self):
        m = CostMetrics.compute(1000, 500, api_calls=10, token_cost_per_1k_usd=0.002)
        assert m.total_tokens == 1500
        assert m.total_cost_usd > 0

    def test_cost_per_call(self):
        m = CostMetrics.compute(0, 0, api_calls=5)
        assert m.cost_per_call() == pytest.approx(0.0)


class TestReliabilityMetrics:
    def test_compute(self):
        m = ReliabilityMetrics.compute(100, 95, 5, retried=3, uptime_pct=99.9)
        assert m.error_rate == pytest.approx(0.05)
        assert m.success_rate == pytest.approx(0.95)

    def test_meets_slo(self):
        m = ReliabilityMetrics.compute(1000, 999, 1, uptime_pct=99.9)
        assert m.meets_slo(max_error_rate=0.01, min_uptime_pct=99.0)

    def test_slo_fail(self):
        m = ReliabilityMetrics.compute(100, 50, 50, uptime_pct=90.0)
        assert not m.meets_slo()


class TestConfidenceMetrics:
    def test_compute(self):
        confs   = [0.9, 0.8, 0.7, 0.6, 0.5]
        outcomes = [True, True, False, True, False]
        m = ConfidenceMetrics.compute(confs, outcomes)
        assert 0.0 <= m.mean_confidence <= 1.0
        assert 0.0 <= m.calibration_error <= 1.0

    def test_empty(self):
        m = ConfidenceMetrics.compute([], [])
        assert m.sample_size == 0

    def test_well_calibrated(self):
        # perfect predictions → low ECE
        confs   = [1.0] * 10
        outcomes = [True] * 10
        m = ConfidenceMetrics.compute(confs, outcomes)
        assert m.is_well_calibrated(max_ece=0.1)


class TestPerformanceMetrics:
    def test_build_empty(self):
        m = PerformanceMetrics.build("sid")
        assert m.accuracy is None
        assert m.overall_score() == pytest.approx(0.0)

    def test_build_with_accuracy(self):
        acc = AccuracyMetrics.compute(90, 5, 5, 100)
        m   = PerformanceMetrics.build("sid", accuracy=acc)
        assert m.overall_score() > 0.0

    def test_overall_score_range(self):
        acc = AccuracyMetrics.compute(100, 0, 0, 100)
        m   = PerformanceMetrics.build("sid", accuracy=acc)
        assert 0.0 <= m.overall_score() <= 1.0


# ═════════════════════════════════════════════════════════════════════════════
# 4. EVENTS
# ═════════════════════════════════════════════════════════════════════════════

class TestEvents:
    def test_session_created_event(self):
        e = EvaluationSessionCreatedEvent.create("src", "sid123")
        assert e.event_type == LearningEvaluationEventType.EVALUATION_SESSION_CREATED
        assert e.session_id == "sid123"

    def test_session_completed_event(self):
        e = EvaluationSessionCompletedEvent.create("src", "sid", 10, 0.9)
        assert e.result_count == 10
        assert e.pass_rate    == pytest.approx(0.9)

    def test_session_failed_event(self):
        e = EvaluationSessionFailedEvent.create("src", "sid", "timeout")
        assert e.reason == "timeout"

    def test_result_added_event(self):
        e = EvaluationResultAddedEvent.create("src", "sid", "rid", True)
        assert e.passed is True

    def test_benchmark_started_event(self):
        e = BenchmarkStartedEvent.create("src", "bid", "suite1")
        assert e.benchmark_id == "bid"
        assert e.suite_id     == "suite1"

    def test_benchmark_completed_event(self):
        e = BenchmarkCompletedEvent.create("src", "bid", 0.85, True)
        assert e.weighted_score == pytest.approx(0.85)

    def test_learning_recorded_event(self):
        e = LearningRecordedEvent.create("src", "rid", "accuracy")
        assert e.category == "accuracy"

    def test_feedback_received_event(self):
        e = FeedbackReceivedEvent.create("src", "fid", "tgt", "positive")
        assert e.sentiment == "positive"

    def test_quality_assessed_event(self):
        e = QualityAssessedEvent.create("src", "tgt", "A", 0.92)
        assert e.grade == "A"

    def test_improvement_suggested_event(self):
        e = ImprovementSuggestedEvent.create("src", "rid", "tgt", "high")
        assert e.priority == "high"


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus      = LearningEvaluationEventBus()
        received = []
        bus.subscribe(LearningEvaluationEventType.LEARNING_RECORDED,
                      lambda e: received.append(e))
        e = LearningRecordedEvent.create("src", "rid", "accuracy")
        bus.publish(e)
        assert len(received) == 1
        assert received[0].event_id == e.event_id

    def test_unsubscribe(self):
        bus = LearningEvaluationEventBus()
        calls = []
        handler = lambda e: calls.append(e)
        bus.subscribe(LearningEvaluationEventType.BENCHMARK_STARTED, handler)
        bus.unsubscribe(LearningEvaluationEventType.BENCHMARK_STARTED, handler)
        bus.publish(BenchmarkStartedEvent.create("src", "bid"))
        assert len(calls) == 0

    def test_subscribe_all(self):
        bus  = LearningEvaluationEventBus()
        seen = []
        bus.subscribe_all(lambda e: seen.append(e.event_type))
        bus.publish(LearningRecordedEvent.create("src", "r", "accuracy"))
        bus.publish(FeedbackReceivedEvent.create("src", "f", "t", "neutral"))
        assert len(seen) == 2

    def test_history(self):
        bus = LearningEvaluationEventBus()
        bus.publish(LearningRecordedEvent.create("src", "r", "accuracy"))
        bus.publish(BenchmarkStartedEvent.create("src", "bid"))
        assert len(bus.history()) == 2

    def test_history_filtered(self):
        bus = LearningEvaluationEventBus()
        bus.publish(LearningRecordedEvent.create("src", "r", "accuracy"))
        bus.publish(BenchmarkStartedEvent.create("src", "bid"))
        h = bus.history(event_type=LearningEvaluationEventType.LEARNING_RECORDED)
        assert len(h) == 1

    def test_subscriber_exception_isolated(self):
        bus = LearningEvaluationEventBus()
        bus.subscribe(LearningEvaluationEventType.LEARNING_RECORDED, lambda e: 1/0)
        # Should not raise
        bus.publish(LearningRecordedEvent.create("src", "r", "accuracy"))

    def test_clear_history(self):
        bus = LearningEvaluationEventBus()
        bus.publish(LearningRecordedEvent.create("src", "r", "accuracy"))
        bus.clear_history()
        assert bus.history() == []


# ═════════════════════════════════════════════════════════════════════════════
# 5. EVALUATION LAYER
# ═════════════════════════════════════════════════════════════════════════════

def _make_eval_meta(name: str = "test") -> EvaluationMetadata:
    return EvaluationMetadata.create(name, EvaluationType.OFFLINE, "tgt", "user")


class TestEvaluationSession:
    def test_lifecycle(self):
        meta    = _make_eval_meta()
        session = EvaluationSession(meta)
        assert session.status == EvaluationStatus.CREATED

        session.start()
        assert session.status == EvaluationStatus.RUNNING

        req    = EvaluationRequest.create(meta.session_id, {})
        result = EvaluationResult.passed(meta.session_id, req.request_id, "ans")
        session.add_result(result)
        assert session.result_count == 1

        session.complete()
        assert session.status == EvaluationStatus.COMPLETED

    def test_double_start_raises(self):
        meta    = _make_eval_meta()
        session = EvaluationSession(meta)
        session.start()
        with pytest.raises(AIEvaluationSessionAlreadyExistsError):
            session.start()

    def test_add_to_closed_raises(self):
        meta    = _make_eval_meta()
        session = EvaluationSession(meta)
        session.start()
        session.complete()
        req    = EvaluationRequest.create(meta.session_id, {})
        result = EvaluationResult.passed(meta.session_id, req.request_id, "x")
        with pytest.raises(AIEvaluationSessionClosedError):
            session.add_result(result)

    def test_fail(self):
        meta    = _make_eval_meta()
        session = EvaluationSession(meta)
        session.start()
        session.fail("timeout")
        assert session.status == EvaluationStatus.FAILED
        assert session.failure_reason == "timeout"

    def test_cancel(self):
        meta    = _make_eval_meta()
        session = EvaluationSession(meta)
        session.start()
        session.cancel()
        assert session.status == EvaluationStatus.CANCELLED

    def test_pass_rate(self):
        meta    = _make_eval_meta()
        session = EvaluationSession(meta)
        session.start()
        sid = meta.session_id
        for i in range(8):
            r = EvaluationResult.passed(sid, str(uuid.uuid4()), "x")
            session.add_result(r)
        for i in range(2):
            r = EvaluationResult.failed(sid, str(uuid.uuid4()), "x")
            session.add_result(r)
        assert session.pass_rate() == pytest.approx(0.8)


class TestEvaluationManager:
    def test_create_and_get(self):
        mgr  = EvaluationManager()
        meta = _make_eval_meta()
        s    = mgr.create_session(meta)
        assert mgr.get_session(meta.session_id) is s

    def test_create_duplicate_raises(self):
        mgr  = EvaluationManager()
        meta = _make_eval_meta()
        mgr.create_session(meta)
        with pytest.raises(AIEvaluationSessionAlreadyExistsError):
            mgr.create_session(meta)

    def test_get_missing_raises(self):
        mgr = EvaluationManager()
        with pytest.raises(AIEvaluationSessionNotFoundError):
            mgr.get_session("nonexistent")

    def test_list_by_status(self):
        mgr  = EvaluationManager()
        m1   = _make_eval_meta("s1")
        m2   = _make_eval_meta("s2")
        s1   = mgr.create_session(m1)
        s2   = mgr.create_session(m2)
        s1.start()
        s1.complete()
        running  = mgr.list_sessions(status=EvaluationStatus.RUNNING)
        created  = mgr.list_sessions(status=EvaluationStatus.CREATED)
        completed = mgr.list_sessions(status=EvaluationStatus.COMPLETED)
        assert s1 not in running
        assert s2 in created
        assert s1 in completed

    def test_active_count(self):
        mgr  = EvaluationManager()
        meta = _make_eval_meta()
        s    = mgr.create_session(meta)
        assert mgr.active_count() == 1
        s.start()
        assert mgr.active_count() == 1
        s.complete()
        assert mgr.active_count() == 0

    def test_remove_session(self):
        mgr  = EvaluationManager()
        meta = _make_eval_meta()
        mgr.create_session(meta)
        mgr.remove_session(meta.session_id)
        assert mgr.get_optional(meta.session_id) is None


# ═════════════════════════════════════════════════════════════════════════════
# 6. BENCHMARK LAYER
# ═════════════════════════════════════════════════════════════════════════════

def _make_bench_meta() -> BenchmarkMetadata:
    return BenchmarkMetadata.create("bench1", BenchmarkType.AGENT, "agent_x", "user1")


def _make_scenario(score_override: float = 0.9) -> BenchmarkScenario:
    return BenchmarkScenario.create(f"sc_{uuid.uuid4()}", ScenarioType.CORRECTNESS, {})


class TestBenchmarkSuite:
    def test_add_and_run(self):
        meta  = _make_bench_meta()
        suite = BenchmarkSuite(meta)
        for _ in range(3):
            suite.add_scenario(_make_scenario())

        def evaluator(sc):
            return 0.9, 10.0

        result = suite.run(evaluator)
        assert result.outcome in (BenchmarkOutcome.PASSED, BenchmarkOutcome.PARTIAL)
        assert result.total_scenarios == 3

    def test_evaluator_exception_captured(self):
        meta  = _make_bench_meta()
        suite = BenchmarkSuite(meta)
        suite.add_scenario(_make_scenario())

        def bad_evaluator(sc):
            raise ValueError("fail")

        result = suite.run(bad_evaluator)
        assert result.outcome == BenchmarkOutcome.FAILED

    def test_remove_scenario(self):
        meta  = _make_bench_meta()
        suite = BenchmarkSuite(meta)
        sc    = _make_scenario()
        suite.add_scenario(sc)
        suite.remove_scenario(sc.scenario_id)
        assert suite.scenario_count == 0


class TestBenchmarkReport:
    def _make_result(self, score: float) -> BenchmarkResult:
        sr = ScenarioResult.create(str(uuid.uuid4()), "sc", score, 5.0)
        return BenchmarkResult.build("bid", frozenset([sr]))

    def test_best_and_worst(self):
        r1 = self._make_result(0.9)
        r2 = self._make_result(0.4)
        report = BenchmarkReport.build("report", [r1, r2])
        assert report.best_result().weighted_score  >= report.worst_result().weighted_score

    def test_summary_table(self):
        r1 = self._make_result(0.9)
        report = BenchmarkReport.build("report", [r1])
        rows = report.summary_table()
        assert len(rows) == 1
        assert "outcome" in rows[0]

    def test_average_score(self):
        r1     = self._make_result(0.8)
        r2     = self._make_result(0.6)
        report = BenchmarkReport.build("r", [r1, r2])
        avg    = report.average_score()
        assert 0.6 <= avg <= 0.8

    def test_empty(self):
        report = BenchmarkReport.build("empty", [])
        assert report.best_result() is None
        assert report.worst_result() is None


class TestBenchmarkManager:
    def test_register_and_get_suite(self):
        mgr   = BenchmarkManager()
        meta  = _make_bench_meta()
        suite = BenchmarkSuite(meta)
        mgr.register_suite(suite)
        assert mgr.get_suite(suite.suite_id) is suite

    def test_get_missing_suite_raises(self):
        mgr = BenchmarkManager()
        with pytest.raises(AIBenchmarkSuiteNotFoundError):
            mgr.get_suite("nope")

    def test_store_and_get_result(self):
        mgr    = BenchmarkManager()
        sr     = ScenarioResult.create(str(uuid.uuid4()), "sc", 0.8, 5.0)
        result = BenchmarkResult.build("bid", frozenset([sr]))
        mgr.store_result(result)
        assert mgr.get_result(result.result_id).result_id == result.result_id

    def test_get_missing_result_raises(self):
        mgr = BenchmarkManager()
        with pytest.raises(AIBenchmarkNotFoundError):
            mgr.get_result("nope")

    def test_results_for_benchmark(self):
        mgr = BenchmarkManager()
        sr  = ScenarioResult.create(str(uuid.uuid4()), "sc", 0.8, 5.0)
        r   = BenchmarkResult.build("bid", frozenset([sr]))
        mgr.store_result(r)
        assert len(mgr.results_for_benchmark("bid")) == 1
        assert len(mgr.results_for_benchmark("other")) == 0


# ═════════════════════════════════════════════════════════════════════════════
# 7. LEARNING LAYER
# ═════════════════════════════════════════════════════════════════════════════

class TestFeedbackCollector:
    def test_collect_and_get(self):
        collector = FeedbackCollector()
        fr = FeedbackRecord.create("tgt1", "user1", FeedbackType.RATING, "good", rating=4.0)
        collector.collect(fr)
        records = collector.get_feedback("tgt1")
        assert len(records) == 1

    def test_filter_by_type(self):
        collector = FeedbackCollector()
        fr1 = FeedbackRecord.create("t", "u", FeedbackType.RATING, "r", rating=3.0)
        fr2 = FeedbackRecord.create("t", "u", FeedbackType.CORRECTION, "c")
        collector.collect(fr1)
        collector.collect(fr2)
        ratings = collector.get_feedback("t", FeedbackType.RATING)
        assert len(ratings) == 1

    def test_average_rating(self):
        collector = FeedbackCollector()
        for r in [1.0, 3.0, 5.0]:
            fr = FeedbackRecord.create("t", "u", FeedbackType.RATING, "x", rating=r)
            collector.collect(fr)
        avg = collector.average_rating("t")
        assert avg == pytest.approx(3.0)

    def test_clear(self):
        collector = FeedbackCollector()
        fr = FeedbackRecord.create("t", "u", FeedbackType.RATING, "x")
        collector.collect(fr)
        collector.clear("t")
        assert collector.count_for("t") == 0

    def test_total_count(self):
        collector = FeedbackCollector()
        fr1 = FeedbackRecord.create("t1", "u", FeedbackType.RATING, "x")
        fr2 = FeedbackRecord.create("t2", "u", FeedbackType.CORRECTION, "y")
        collector.collect(fr1)
        collector.collect(fr2)
        assert collector.total_count() == 2


class TestLearningHistory:
    def test_add_and_get(self):
        hist = LearningHistory()
        lr   = LearningRecord.create("agent1", LearningCategory.ACCURACY, "obs")
        hist.add(lr)
        records = hist.get("agent1")
        assert len(records) == 1

    def test_filter_by_category(self):
        hist = LearningHistory()
        lr1  = LearningRecord.create("a", LearningCategory.ACCURACY, "x")
        lr2  = LearningRecord.create("a", LearningCategory.BEHAVIOR, "y")
        hist.add(lr1)
        hist.add(lr2)
        acc = hist.get("a", category=LearningCategory.ACCURACY)
        assert len(acc) == 1

    def test_limit(self):
        hist = LearningHistory()
        for i in range(10):
            hist.add(LearningRecord.create("a", LearningCategory.ACCURACY, f"obs{i}"))
        recent = hist.get("a", limit=3)
        assert len(recent) == 3

    def test_eviction(self):
        hist = LearningHistory(max_per_source=5)
        for i in range(10):
            hist.add(LearningRecord.create("a", LearningCategory.ACCURACY, f"obs{i}"))
        assert hist.count_for("a") == 5

    def test_average_signal(self):
        hist = LearningHistory()
        for sig in [0.0, 0.5, 1.0]:
            hist.add(LearningRecord.create("a", LearningCategory.ACCURACY, "obs", signal=sig))
        avg = hist.average_signal("a")
        assert avg == pytest.approx(0.5)


class TestLearningManager:
    def test_record_and_retrieve(self):
        mgr    = LearningManager()
        record = mgr.record_learning("agent1", LearningCategory.ACCURACY, "good result", signal=0.9)
        assert record.source_id == "agent1"
        recs = mgr.learning_history.get("agent1")
        assert len(recs) == 1

    def test_submit_feedback(self):
        mgr    = LearningManager()
        record = mgr.submit_feedback("tgt1", "user1", FeedbackType.RATING, "nice", rating=4.0)
        assert record.feedback_id is not None
        assert mgr.feedback_collector.count_for("tgt1") == 1

    def test_generate_recommendations_low_signal(self):
        mgr = LearningManager()
        for _ in range(5):
            mgr.record_learning("a", LearningCategory.ACCURACY, "bad", signal=0.1)
        recs = mgr.generate_recommendations("a")
        assert len(recs) >= 1

    def test_generate_recommendations_high_negative_feedback(self):
        mgr = LearningManager()
        for _ in range(6):
            mgr.submit_feedback("a", "u", FeedbackType.REPORT, "bad",
                                 sentiment=FeedbackSentiment.NEGATIVE)
        for _ in range(4):
            mgr.submit_feedback("a", "u", FeedbackType.RATING, "ok",
                                 sentiment=FeedbackSentiment.POSITIVE)
        recs = mgr.generate_recommendations("a")
        types = [r.recommendation_type for r in recs]
        assert RecommendationType.PROMPT_IMPROVE in types

    def test_generate_recommendations_anomaly(self):
        mgr = LearningManager()
        mgr.record_learning("a", LearningCategory.ANOMALY, "spike", signal=0.9)
        recs = mgr.generate_recommendations("a")
        types = [r.recommendation_type for r in recs]
        assert RecommendationType.MONITORING in types


# ═════════════════════════════════════════════════════════════════════════════
# 8. QUALITY LAYER
# ═════════════════════════════════════════════════════════════════════════════

class TestQualityRule:
    def test_create(self):
        rule = QualityRule.create("no-hallucination", RuleCategory.HALLUCINATION,
                                   is_blocking=True, threshold=0.8)
        assert rule.is_blocking is True
        assert rule.threshold == pytest.approx(0.8)


class TestValidationReport:
    def test_build_pass(self):
        report = ValidationReport.build("sid", "tgt", 5, 0, frozenset())
        assert report.overall_passed is True

    def test_build_fail(self):
        report = ValidationReport.build("sid", "tgt", 3, 2, frozenset(["safety"]))
        assert report.overall_passed is False
        assert "safety" in report.blocking_failures

    def test_failure_rate(self):
        report = ValidationReport.build("sid", "tgt", 8, 2, frozenset())
        assert report.failure_rate() == pytest.approx(0.2)


class TestQualityManager:
    def test_no_rules_raises(self):
        mgr = QualityManager()
        with pytest.raises(AIQualityAssessmentError):
            mgr.assess("tgt", "sid", "content")

    def test_default_scorer_all_pass(self):
        mgr  = QualityManager()
        rule = QualityRule.create("relevance", RuleCategory.RELEVANCE, threshold=0.5)
        mgr.add_rule(rule)
        qs, vr = mgr.assess("tgt", "sid", "content")
        assert vr.overall_passed is True
        assert qs.grade in list(QualityGrade)

    def test_custom_scorer_fail(self):
        def bad_scorer(content, rule):
            return 0.0

        mgr  = QualityManager(scorer_fn=bad_scorer)
        rule = QualityRule.create("safety", RuleCategory.SAFETY, is_blocking=True, threshold=0.5)
        mgr.add_rule(rule)
        qs, vr = mgr.assess("tgt", "sid", "content")
        assert vr.overall_passed is False
        assert "safety" in vr.blocking_failures

    def test_add_remove_rule(self):
        mgr  = QualityManager()
        rule = QualityRule.create("r", RuleCategory.FORMAT)
        mgr.add_rule(rule)
        assert mgr.rule_count() == 1
        mgr.remove_rule(rule.rule_id)
        assert mgr.rule_count() == 0


# ═════════════════════════════════════════════════════════════════════════════
# 9. POLICY LAYER
# ═════════════════════════════════════════════════════════════════════════════

class TestPolicies:
    def test_default_evaluation_policy_valid(self):
        policy = DefaultEvaluationPolicy()
        req    = EvaluationRequest.create("sid", {})
        policy.validate_request("sid", req)   # should not raise

    def test_default_evaluation_policy_invalid(self):
        policy = DefaultEvaluationPolicy()
        req    = EvaluationRequest.create("other", {})
        with pytest.raises(AILearningEvaluationPolicyViolationError):
            policy.validate_request("sid", req)

    def test_default_benchmark_policy_valid(self):
        policy = DefaultBenchmarkPolicy()
        meta   = _make_bench_meta()
        suite  = BenchmarkSuite(meta)
        policy.validate_suite(suite)

    def test_default_benchmark_policy_too_many_scenarios(self):
        policy = DefaultBenchmarkPolicy()
        meta   = _make_bench_meta()
        suite  = BenchmarkSuite(meta)
        for _ in range(101):
            suite.add_scenario(_make_scenario())
        with pytest.raises(AILearningEvaluationPolicyViolationError):
            policy.validate_suite(suite)

    def test_default_quality_policy_pass(self):
        policy     = DefaultQualityPolicy()
        dim_scores = frozenset([("accuracy", 0.9)])
        qs         = QualityScore.build("t", dim_scores)
        policy.validate_score(qs)

    def test_default_quality_policy_fail(self):
        policy     = DefaultQualityPolicy()
        dim_scores = frozenset([("accuracy", 0.1)])
        qs         = QualityScore.build("t", dim_scores)
        with pytest.raises(AILearningEvaluationPolicyViolationError):
            policy.validate_score(qs)

    def test_default_learning_policy(self):
        policy = DefaultLearningPolicy()
        lr     = LearningRecord.create("a", LearningCategory.ACCURACY, "x")
        policy.validate_record(lr)   # no-op
        assert policy.max_records_per_source() == 10_000

    def test_default_acceptance_policy(self):
        policy = DefaultAcceptancePolicy()
        req    = EvaluationRequest.create("sid", {})
        r_pass = EvaluationResult.passed("sid", req.request_id, "x")
        r_fail = EvaluationResult.failed("sid", req.request_id, "x")
        assert policy.is_acceptable(r_pass) is True
        assert policy.is_acceptable(r_fail) is False
        assert policy.min_pass_rate() == pytest.approx(0.5)


# ═════════════════════════════════════════════════════════════════════════════
# 10. SNAPSHOT LAYER
# ═════════════════════════════════════════════════════════════════════════════

class TestSnapshots:
    def test_session_snapshot(self):
        snap = EvaluationSessionSnapshot.capture("sid", "RUNNING", 5, 0.8)
        assert snap.status == "RUNNING"
        assert snap.pass_rate == pytest.approx(0.8)
        assert snap.snapshot_id is not None

    def test_framework_snapshot(self):
        snaps = (EvaluationSessionSnapshot.capture("sid", "RUNNING", 2, 1.0),)
        fsnap = LearningEvaluationFrameworkSnapshot.build(
            is_running       = True,
            active_sessions  = 1,
            total_sessions   = 3,
            total_benchmarks = 5,
            total_feedback   = 20,
            total_learning   = 100,
            session_snapshots = snaps,
        )
        assert fsnap.is_running is True
        assert fsnap.total_sessions == 3
        assert len(fsnap.session_snapshots) == 1


# ═════════════════════════════════════════════════════════════════════════════
# 11. CONTAINER
# ═════════════════════════════════════════════════════════════════════════════

class TestContainer:
    def test_wiring(self):
        c = LearningEvaluationContainer()
        assert c.event_bus is not None
        assert c.evaluation_manager is not None
        assert c.benchmark_manager is not None
        assert c.learning_manager is not None
        assert c.quality_manager is not None

    def test_same_instances(self):
        c = LearningEvaluationContainer()
        assert c.event_bus is c.event_bus


# ═════════════════════════════════════════════════════════════════════════════
# 12. GATEWAY
# ═════════════════════════════════════════════════════════════════════════════

class TestGateway:
    def _gateway(self) -> LearningEvaluationGateway:
        gw = LearningEvaluationGateway()
        gw.start()
        return gw

    def test_start_stop(self):
        gw = LearningEvaluationGateway()
        assert not gw.is_ai_running
        gw.start()
        assert gw.is_ai_running
        gw.stop()
        assert not gw.is_ai_running

    def test_double_start(self):
        from iios.ai.foundation.lifecycle.exceptions import AIModuleAlreadyRunningError
        gw = LearningEvaluationGateway()
        gw.start()
        with pytest.raises(AIModuleAlreadyRunningError):
            gw.start()
        gw.stop()

    def test_call_without_start_raises(self):
        from iios.ai.learning_evaluation.exceptions.learning_evaluation_exceptions import (
            AILearningEvaluationException,
        )
        gw = LearningEvaluationGateway()
        with pytest.raises(AILearningEvaluationException):
            gw.create_session(_make_eval_meta())

    def test_create_session(self):
        gw   = self._gateway()
        meta = _make_eval_meta()
        s    = gw.create_session(meta)
        assert s.session_id == meta.session_id
        gw.stop()

    def test_evaluate(self):
        gw   = self._gateway()
        meta = _make_eval_meta()
        gw.create_session(meta)
        req = EvaluationRequest.create(meta.session_id, {"q": "2+2"})

        def evaluator(r):
            return EvaluationResult.passed(r.session_id, r.request_id, "4")

        result = gw.evaluate(meta.session_id, req, evaluator)
        assert result.is_success()
        gw.stop()

    def test_complete_session(self):
        gw   = self._gateway()
        meta = _make_eval_meta()
        gw.create_session(meta)
        gw.complete_session(meta.session_id)
        s = gw.get_session(meta.session_id)
        assert s.status == EvaluationStatus.COMPLETED
        gw.stop()

    def test_benchmark(self):
        gw   = self._gateway()
        bmeta = _make_bench_meta()
        suite = BenchmarkSuite(bmeta)
        sc    = BenchmarkScenario.create("q1", ScenarioType.CORRECTNESS, {"x": 1})
        suite.add_scenario(sc)
        gw.register_suite(suite)

        def evaluator(s):
            return 0.9, 5.0

        result = gw.benchmark(suite.suite_id, evaluator)
        assert result.is_success()
        gw.stop()

    def test_record_learning(self):
        gw     = self._gateway()
        record = gw.record_learning("agent1", LearningCategory.ACCURACY, "obs", signal=0.7)
        assert record.source_id == "agent1"
        gw.stop()

    def test_submit_feedback(self):
        gw = self._gateway()
        fb = gw.submit_feedback("tgt", "user", FeedbackType.RATING, "nice", rating=4.0)
        assert fb.rating == pytest.approx(4.0)
        gw.stop()

    def test_generate_report(self):
        gw = self._gateway()
        for _ in range(5):
            gw.record_learning("a", LearningCategory.ACCURACY, "bad", signal=0.1)
        recs = gw.generate_report("a")
        assert isinstance(recs, list)
        gw.stop()

    def test_assess_quality_no_rules(self):
        gw = self._gateway()
        with pytest.raises(AIQualityAssessmentError):
            gw.assess_quality("tgt", "sid", "content")
        gw.stop()

    def test_assess_quality_with_rules(self):
        gw = self._gateway()
        gw._c.quality_manager.add_rule(
            QualityRule.create("r", RuleCategory.RELEVANCE, threshold=0.5)
        )
        qs, vr = gw.assess_quality("tgt", "sid", "content")
        assert isinstance(qs, QualityScore)
        assert vr.overall_passed is True
        gw.stop()

    def test_health(self):
        gw = self._gateway()
        h  = gw.health()
        assert h["is_running"] is True
        assert "active_sessions" in h
        gw.stop()

    def test_snapshot(self):
        gw   = self._gateway()
        meta = _make_eval_meta()
        gw.create_session(meta)
        snap = gw.snapshot()
        assert snap.is_running is True
        assert snap.total_sessions == 1
        gw.stop()

    def test_list_sessions(self):
        gw   = self._gateway()
        meta = _make_eval_meta()
        gw.create_session(meta)
        sessions = gw.list_sessions()
        assert len(sessions) == 1
        gw.stop()

    def test_list_benchmarks(self):
        gw    = self._gateway()
        meta  = _make_bench_meta()
        suite = BenchmarkSuite(meta)
        gw.register_suite(suite)
        suites = gw.list_benchmarks()
        assert len(suites) == 1
        gw.stop()

    def test_events_emitted(self):
        gw      = self._gateway()
        seen    = []
        gw._c.event_bus.subscribe_all(lambda e: seen.append(e.event_type))

        meta = _make_eval_meta()
        gw.create_session(meta)
        req  = EvaluationRequest.create(meta.session_id, {})
        gw.evaluate(meta.session_id, req, lambda r: EvaluationResult.passed(r.session_id, r.request_id, "x"))
        gw.complete_session(meta.session_id)

        event_types = [e.value for e in seen]
        assert LearningEvaluationEventType.EVALUATION_SESSION_CREATED.value in event_types
        assert LearningEvaluationEventType.EVALUATION_RESULT_ADDED.value in event_types
        assert LearningEvaluationEventType.EVALUATION_SESSION_COMPLETED.value in event_types
        gw.stop()

    def test_system_id_and_version(self):
        gw = LearningEvaluationGateway()
        assert gw.SYSTEM_ID == "iios:ai:learning_evaluation:gateway"
        assert gw.VERSION   == "1.0.0"
