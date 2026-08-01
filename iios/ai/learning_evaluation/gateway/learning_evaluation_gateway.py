"""
learning_evaluation_gateway.py -- iios.ai.learning_evaluation.gateway
=======================================================================
:class:`LearningEvaluationGateway` — single public entry point for the A7
Learning & Evaluation Platform.

Inherits :class:`AILifecycleAwareMixin` (A1) and uses ``_on_start`` /
``_on_stop`` hooks to wire and tear-down the DI container.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from ..benchmark.benchmark_suite                    import BenchmarkSuite
from ..container.learning_evaluation_container      import LearningEvaluationContainer
from ..core.benchmark_metadata                      import BenchmarkMetadata
from ..core.benchmark_result                        import BenchmarkResult
from ..core.evaluation_metadata                     import EvaluationMetadata, EvaluationStatus
from ..core.evaluation_request                      import EvaluationRequest
from ..core.evaluation_result                       import EvaluationOutcome, EvaluationResult
from ..core.feedback_record                         import FeedbackRecord, FeedbackSentiment, FeedbackType
from ..core.improvement_recommendation              import ImprovementRecommendation
from ..core.learning_record                         import LearningCategory, LearningRecord
from ..core.quality_score                           import QualityScore
from ..events.learning_evaluation_events            import (
    BenchmarkCompletedEvent,
    BenchmarkStartedEvent,
    EvaluationResultAddedEvent,
    EvaluationSessionCompletedEvent,
    EvaluationSessionCreatedEvent,
    FeedbackReceivedEvent,
    LearningRecordedEvent,
    QualityAssessedEvent,
)
from ..evaluation.evaluation_session                import EvaluationSession
from ..exceptions.learning_evaluation_exceptions    import (
    AIEvaluationSessionNotFoundError,
)
from ..lifecycle                                    import AILifecycleAwareMixin
from ..quality.validation_report                    import ValidationReport
from ..snapshot.learning_evaluation_snapshot        import (
    EvaluationSessionSnapshot,
    LearningEvaluationFrameworkSnapshot,
)

SYSTEM_ID = "iios:ai:learning_evaluation:gateway"
VERSION   = "1.0.0"


class LearningEvaluationGateway(AILifecycleAwareMixin):
    """
    Single public entry point for the A7 Learning & Evaluation Platform.

    Usage::

        gateway = LearningEvaluationGateway()
        gateway.start()

        session = gateway.create_session(metadata)
        result  = gateway.evaluate(session.session_id, request, evaluator_fn)

        gateway.stop()
    """

    SYSTEM_ID  : str = SYSTEM_ID
    VERSION    : str = VERSION
    MODULE_ID  : str = "A7"
    MODULE_NAME: str = "Learning & Evaluation"
    API_VERSION: str = "v1"
    DESCRIPTION: str = "Model evaluation, quality benchmarking and adaptive learning"
    STATUS     : str = "stable"

    def __init__(self) -> None:
        super().__init__()
        self._container: Optional[LearningEvaluationContainer] = None

    # ── lifecycle hooks ───────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._container = LearningEvaluationContainer()

    def _on_stop(self) -> None:
        self._container = None

    # ── internal helpers ──────────────────────────────────────────────────────

    @property
    def _c(self) -> LearningEvaluationContainer:
        if self._container is None:
            from ..exceptions.learning_evaluation_exceptions import AILearningEvaluationException
            raise AILearningEvaluationException(
                "[AI-1200] Gateway is not running — call start() first"
            )
        return self._container

    # ── evaluation ────────────────────────────────────────────────────────────

    def create_session(self, metadata: EvaluationMetadata) -> EvaluationSession:
        """Create and register a new evaluation session."""
        session = self._c.evaluation_manager.create_session(metadata)
        self._c.event_bus.publish(
            EvaluationSessionCreatedEvent.create(SYSTEM_ID, metadata.session_id)
        )
        return session

    def evaluate(
        self,
        session_id:    str,
        request:       EvaluationRequest,
        evaluator_fn:  Callable[[EvaluationRequest], EvaluationResult],
    ) -> EvaluationResult:
        """
        Execute ``evaluator_fn`` within the evaluation session.

        The session is automatically started on first call and the result is
        stored.  Call ``complete_session`` when all results have been submitted.
        """
        session = self._c.evaluation_manager.get_session(session_id)
        if session.status == EvaluationStatus.CREATED:
            session.start()

        result = evaluator_fn(request)
        session.add_result(result)
        self._c.event_bus.publish(
            EvaluationResultAddedEvent.create(SYSTEM_ID, session_id, result.result_id, result.is_success())
        )
        return result

    def complete_session(self, session_id: str) -> None:
        """Mark a session as completed and emit a completion event."""
        session = self._c.evaluation_manager.get_session(session_id)
        session.complete()
        self._c.event_bus.publish(
            EvaluationSessionCompletedEvent.create(
                SYSTEM_ID, session_id, session.result_count, session.pass_rate()
            )
        )

    def get_session(self, session_id: str) -> EvaluationSession:
        return self._c.evaluation_manager.get_session(session_id)

    def list_sessions(self, status: Optional[EvaluationStatus] = None) -> list:
        return self._c.evaluation_manager.list_sessions(status)

    # ── benchmarking ──────────────────────────────────────────────────────────

    def register_suite(self, suite: BenchmarkSuite) -> None:
        self._c.benchmark_manager.register_suite(suite)

    def benchmark(
        self,
        suite_id:       str,
        evaluator_fn:   Callable,
        pass_threshold: float = 0.6,
    ) -> BenchmarkResult:
        """Run a registered benchmark suite and store the result."""
        suite = self._c.benchmark_manager.get_suite(suite_id)
        self._c.event_bus.publish(
            BenchmarkStartedEvent.create(SYSTEM_ID, suite.suite_id)
        )
        result = suite.run(evaluator_fn, pass_threshold=pass_threshold)
        self._c.benchmark_manager.store_result(result)
        self._c.event_bus.publish(
            BenchmarkCompletedEvent.create(
                SYSTEM_ID, result.benchmark_id, result.weighted_score, result.is_success()
            )
        )
        return result

    def list_benchmarks(self) -> List[BenchmarkSuite]:
        return self._c.benchmark_manager.list_suites()

    # ── learning ──────────────────────────────────────────────────────────────

    def record_learning(
        self,
        source_id:   str,
        category:    LearningCategory,
        observation: Any,
        signal:      float          = 0.0,
        session_id:  Optional[str]  = None,
        **metadata:  Any,
    ) -> LearningRecord:
        record = self._c.learning_manager.record_learning(
            source_id, category, observation, signal, session_id, **metadata
        )
        self._c.event_bus.publish(
            LearningRecordedEvent.create(SYSTEM_ID, record.record_id, record.category.value)
        )
        return record

    def submit_feedback(
        self,
        target_id:     str,
        submitted_by:  str,
        feedback_type: FeedbackType,
        content:       Any,
        sentiment:     FeedbackSentiment = FeedbackSentiment.NEUTRAL,
        rating:        Optional[float]   = None,
        **metadata:    Any,
    ) -> FeedbackRecord:
        record = self._c.learning_manager.submit_feedback(
            target_id, submitted_by, feedback_type, content, sentiment, rating, **metadata
        )
        self._c.event_bus.publish(
            FeedbackReceivedEvent.create(
                SYSTEM_ID, record.feedback_id, record.target_id, record.sentiment.value
            )
        )
        return record

    def generate_report(self, source_id: str) -> List[ImprovementRecommendation]:
        return self._c.learning_manager.generate_recommendations(source_id)

    # ── quality ───────────────────────────────────────────────────────────────

    def assess_quality(
        self,
        target_id:  str,
        session_id: str,
        content:    Any,
    ) -> Tuple[QualityScore, ValidationReport]:
        quality_score, validation_report = self._c.quality_manager.assess(
            target_id, session_id, content
        )
        self._c.event_bus.publish(
            QualityAssessedEvent.create(
                SYSTEM_ID, target_id, quality_score.grade.value, quality_score.aggregate
            )
        )
        return quality_score, validation_report

    # ── introspection ─────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        return {
            "is_running":       self.is_ai_running,
            "active_sessions":  self._c.evaluation_manager.active_count() if self._container else 0,
            "total_sessions":   self._c.evaluation_manager.total_count() if self._container else 0,
            "total_benchmarks": self._c.benchmark_manager.total_results() if self._container else 0,
            "total_feedback":   self._c.learning_manager.feedback_collector.total_count() if self._container else 0,
            "total_learning":   self._c.learning_manager.learning_history.total_count() if self._container else 0,
            "system_id":        SYSTEM_ID,
            "version":          VERSION,
        }

    def status(self) -> Dict[str, Any]:
        return self.health()

    def snapshot(self) -> LearningEvaluationFrameworkSnapshot:
        c = self._c
        sessions = c.evaluation_manager.list_sessions()
        session_snaps = tuple(
            EvaluationSessionSnapshot.capture(
                s.session_id, s.status.value, s.result_count, s.pass_rate()
            )
            for s in sessions
        )
        return LearningEvaluationFrameworkSnapshot.build(
            is_running        = self.is_ai_running,
            active_sessions   = c.evaluation_manager.active_count(),
            total_sessions    = c.evaluation_manager.total_count(),
            total_benchmarks  = c.benchmark_manager.total_results(),
            total_feedback    = c.learning_manager.feedback_collector.total_count(),
            total_learning    = c.learning_manager.learning_history.total_count(),
            session_snapshots = session_snaps,
        )
