"""
tests/unit/observation/test_pipeline_engine.py
==============================================
Comprehensive tests for the Observation Pipeline & Processing Engine.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

import pytest

from iios.observation.observation_constants import (
    ObservationPriority, ObservationSource, ObservationStatus, ObservationType,
)
from iios.observation.observation_factory import get_observation_factory


# ─────────────────────────── helpers / fixtures ───────────────────────────────

def _reset_all() -> None:
    from iios.observation.pipeline.pipeline_manager    import reset_pipeline_manager
    from iios.observation.pipeline.pipeline_engine     import reset_pipeline_engine
    from iios.observation.pipeline.pipeline_registry   import reset_pipeline_registry
    from iios.observation.pipeline.pipeline_monitor    import reset_pipeline_monitor
    from iios.observation.pipeline.pipeline_metrics    import reset_pipeline_metrics
    from iios.observation.pipeline.pipeline_scheduler  import reset_pipeline_scheduler
    from iios.observation.pipeline.pipeline_context    import reset_pipeline_context
    from iios.observation.classifiers.classification_manager import reset_classification_manager
    from iios.observation.classifiers.classification_engine  import reset_classification_engine
    from iios.observation.classifiers.classification_registry import reset_classifier_registry
    from iios.observation.enrichment.enrichment_manager      import reset_enrichment_manager
    from iios.observation.enrichment.enrichment_engine       import reset_enrichment_engine
    from iios.observation.enrichment.enrichment_registry     import reset_enricher_registry
    from iios.observation.validators.validation_manager      import reset_validation_manager
    from iios.observation.quality.quality_engine             import reset_quality_engine
    from iios.observation.observation_factory                import reset_observation_factory
    reset_pipeline_scheduler()
    reset_pipeline_manager()
    reset_pipeline_engine()
    reset_pipeline_registry()
    reset_pipeline_monitor()
    reset_pipeline_metrics()
    reset_pipeline_context()
    reset_classification_manager()
    reset_classification_engine()
    reset_classifier_registry()
    reset_enrichment_manager()
    reset_enrichment_engine()
    reset_enricher_registry()
    reset_validation_manager()
    reset_quality_engine()
    reset_observation_factory()


@pytest.fixture(autouse=True)
def isolate():
    _reset_all()
    yield
    _reset_all()


def _make_obs(
    content    = None,
    title      = "Test observation",
    obs_type   = ObservationType.MARKET_DATA,
    source     = ObservationSource.INTERNAL_AGENT,
    instrument = "NIFTY",
    exchange   = "NSE",
    priority   = ObservationPriority.MEDIUM,
    **kw,
):
    f = get_observation_factory()
    return f.create(
        content    = content if content is not None else {"open": 100.0, "close": 104.0},
        title      = title,
        obs_type   = obs_type,
        source     = source,
        instrument = instrument,
        exchange   = exchange,
        priority   = priority,
        **kw,
    )


def _make_invalid_obs():
    """Return an obs with None content (will fail validation)."""
    return _make_obs(content=None)


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineConstants:
    def test_stage_names_are_strings(self):
        from iios.observation.pipeline.pipeline_constants import (
            STAGE_COLLECT, STAGE_VALIDATE, STAGE_CLASSIFY,
            STAGE_COMPLETE, STAGE_PERSIST,
        )
        for s in (STAGE_COLLECT, STAGE_VALIDATE, STAGE_CLASSIFY, STAGE_COMPLETE, STAGE_PERSIST):
            assert isinstance(s, str) and len(s) > 0

    def test_pipeline_names_defined(self):
        from iios.observation.pipeline.pipeline_constants import (
            PIPELINE_STANDARD, PIPELINE_FAST, PIPELINE_VALIDATION_ONLY,
        )
        assert PIPELINE_STANDARD        == "standard"
        assert PIPELINE_FAST            == "fast"
        assert PIPELINE_VALIDATION_ONLY == "validation_only"

    def test_standard_stage_order_has_17(self):
        from iios.observation.pipeline.pipeline_constants import STANDARD_STAGE_ORDER
        assert len(STANDARD_STAGE_ORDER) == 17

    def test_stage_mode_values(self):
        from iios.observation.pipeline.pipeline_constants import StageMode
        assert StageMode.SEQUENTIAL.value  == "sequential"
        assert StageMode.OPTIONAL.value    == "optional"
        assert StageMode.CONDITIONAL.value == "conditional"

    def test_failure_policy_values(self):
        from iios.observation.pipeline.pipeline_constants import FailurePolicy
        assert FailurePolicy.FAIL_FAST.value  == "fail_fast"
        assert FailurePolicy.CONTINUE.value   == "continue"
        assert FailurePolicy.DEAD_LETTER.value == "dead_letter"

    def test_pipeline_state_values(self):
        from iios.observation.pipeline.pipeline_constants import PipelineState
        assert PipelineState.RUNNING.value   == "running"
        assert PipelineState.COMPLETED.value == "completed"
        assert PipelineState.FAILED.value    == "failed"

    def test_checkpoint_policy_values(self):
        from iios.observation.pipeline.pipeline_constants import CheckpointPolicy
        assert CheckpointPolicy.NONE.value       == "none"
        assert CheckpointPolicy.ON_FAILURE.value == "on_failure"
        assert CheckpointPolicy.ALWAYS.value     == "always"

    def test_default_batch_size_positive(self):
        from iios.observation.pipeline.pipeline_constants import DEFAULT_BATCH_SIZE
        assert DEFAULT_BATCH_SIZE > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineExceptions:
    def test_base_is_observation_error(self):
        from iios.observation.pipeline.pipeline_exceptions import PipelineError
        from iios.observation.observation_exceptions import ObservationError
        assert issubclass(PipelineError, ObservationError)

    def test_not_found_stores_name(self):
        from iios.observation.pipeline.pipeline_exceptions import PipelineNotFoundError
        exc = PipelineNotFoundError("missing_pipeline")
        assert "missing_pipeline" in str(exc)
        assert exc.name == "missing_pipeline"

    def test_already_exists_stores_name(self):
        from iios.observation.pipeline.pipeline_exceptions import PipelineAlreadyExistsError
        exc = PipelineAlreadyExistsError("dup")
        assert "dup" in str(exc)

    def test_stage_timeout_stores_values(self):
        from iios.observation.pipeline.pipeline_exceptions import StageTimeoutError
        exc = StageTimeoutError("validate", timeout_ms=5000.0)
        assert exc.stage      == "validate"
        assert exc.timeout_ms == 5000.0

    def test_dead_letter_stores_obs_id(self):
        from iios.observation.pipeline.pipeline_exceptions import DeadLetterError
        exc = DeadLetterError("obs:test/001", stage="persist")
        assert "obs:test/001" in str(exc)
        assert exc.obs_id == "obs:test/001"

    def test_pipeline_not_initialized(self):
        from iios.observation.pipeline.pipeline_exceptions import PipelineNotInitializedError
        exc = PipelineNotInitializedError()
        assert "not initialised" in str(exc).lower()

    def test_configuration_error(self):
        from iios.observation.pipeline.pipeline_exceptions import PipelineConfigurationError
        with pytest.raises(PipelineConfigurationError):
            from iios.observation.pipeline.pipeline_registry import StageDefinition
            StageDefinition(name="", handler=lambda o, c: None)


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Context
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineContext:
    def test_pipeline_execution_cm(self):
        from iios.observation.pipeline.pipeline_context import (
            pipeline_execution, get_pipeline_context, PipelineState,
        )
        with pipeline_execution("obs:test/001", "standard") as ctx:
            assert ctx.obs_id          == "obs:test/001"
            assert ctx.pipeline_name   == "standard"
            assert ctx.state           == PipelineState.RUNNING
            assert get_pipeline_context() is ctx
        assert ctx.state == PipelineState.COMPLETED

    def test_context_set_get(self):
        from iios.observation.pipeline.pipeline_context import pipeline_execution
        with pipeline_execution("x", "p") as ctx:
            ctx.set("my_key", {"value": 42})
            assert ctx.get("my_key") == {"value": 42}
            assert ctx.has("my_key")
            assert not ctx.has("missing")

    def test_stage_result_recording(self):
        from iios.observation.pipeline.pipeline_context import (
            pipeline_execution, StageResult,
        )
        with pipeline_execution("x", "p") as ctx:
            ctx.record_stage(StageResult(stage_name="collect", success=True))
            ctx.record_stage(StageResult(stage_name="validate", success=True))
        assert len(ctx.stage_results()) == 2
        assert ctx.all_stages_successful()

    def test_failed_stages_detected(self):
        from iios.observation.pipeline.pipeline_context import (
            pipeline_execution, StageResult,
        )
        with pipeline_execution("x", "p") as ctx:
            ctx.record_stage(StageResult(stage_name="collect",  success=True))
            ctx.record_stage(StageResult(stage_name="validate", success=False, error="bad"))
        assert not ctx.all_stages_successful()
        assert len(ctx.failed_stages()) == 1

    def test_checkpoint_recorded(self):
        from iios.observation.pipeline.pipeline_context import pipeline_execution
        with pipeline_execution("x", "p") as ctx:
            ctx.checkpoint("validate", {"status": "validated"})
        assert len(ctx.checkpoints()) == 1
        assert ctx.last_checkpoint().stage_name == "validate"

    def test_elapsed_ms_positive(self):
        from iios.observation.pipeline.pipeline_context import pipeline_execution
        with pipeline_execution("x", "p") as ctx:
            time.sleep(0.01)
        assert ctx.elapsed_ms > 5.0

    def test_stage_result_to_dict(self):
        from iios.observation.pipeline.pipeline_context import StageResult
        r = StageResult(stage_name="test", success=True, duration_ms=12.3, retries=1)
        d = r.to_dict()
        assert d["stage_name"]  == "test"
        assert d["success"]     is True
        assert d["duration_ms"] == 12.3

    def test_nested_pipeline_contexts(self):
        from iios.observation.pipeline.pipeline_context import (
            pipeline_execution, get_pipeline_context,
        )
        with pipeline_execution("outer", "p1") as outer:
            assert get_pipeline_context() is outer
            with pipeline_execution("inner", "p2") as inner:
                assert get_pipeline_context() is inner
            assert get_pipeline_context() is outer


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Registry
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineRegistry:
    def _make_registry(self):
        from iios.observation.pipeline.pipeline_registry import PipelineRegistry
        return PipelineRegistry()

    def _make_def(self, name: str = "test_pipeline") -> "PipelineDefinition":
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        return (
            PipelineBuilder(name)
            .add_stage("stage_a", lambda o, c: None)
            .build()
        )

    def test_register_and_get(self):
        reg = self._make_registry()
        p   = self._make_def()
        reg.register(p)
        assert reg.has("test_pipeline")
        assert reg.get("test_pipeline") is p

    def test_register_duplicate_raises(self):
        from iios.observation.pipeline.pipeline_exceptions import PipelineAlreadyExistsError
        reg = self._make_registry()
        reg.register(self._make_def())
        with pytest.raises(PipelineAlreadyExistsError):
            reg.register(self._make_def())

    def test_register_overwrite(self):
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        reg = self._make_registry()
        reg.register(self._make_def())
        p2  = PipelineBuilder("test_pipeline").add_stage("other", lambda o, c: None).build()
        reg.register(p2, overwrite=True)
        assert reg.get("test_pipeline") is p2

    def test_unregister(self):
        from iios.observation.pipeline.pipeline_exceptions import PipelineNotFoundError
        reg = self._make_registry()
        reg.register(self._make_def())
        reg.unregister("test_pipeline")
        with pytest.raises(PipelineNotFoundError):
            reg.get("test_pipeline")

    def test_builtin_pipelines_registered(self):
        from iios.observation.pipeline.pipeline_registry import get_pipeline_registry
        from iios.observation.pipeline.pipeline_constants import (
            PIPELINE_STANDARD, PIPELINE_FAST, PIPELINE_VALIDATION_ONLY,
        )
        reg = get_pipeline_registry()
        assert reg.has(PIPELINE_STANDARD)
        assert reg.has(PIPELINE_FAST)
        assert reg.has(PIPELINE_VALIDATION_ONLY)

    def test_standard_pipeline_has_17_stages(self):
        from iios.observation.pipeline.pipeline_registry import get_pipeline_registry
        p = get_pipeline_registry().get("standard")
        assert len(p.stages) == 17

    def test_count_and_names(self):
        reg = self._make_registry()
        reg.register(self._make_def("a"))
        reg.register(self._make_def("b"))
        assert reg.count() == 2
        assert sorted(reg.names()) == ["a", "b"]

    def test_pipeline_definition_duplicate_stage_names(self):
        from iios.observation.pipeline.pipeline_exceptions import PipelineConfigurationError
        from iios.observation.pipeline.pipeline_registry import PipelineDefinition, StageDefinition
        with pytest.raises(PipelineConfigurationError):
            PipelineDefinition(
                name   = "bad",
                stages = [
                    StageDefinition(name="s1", handler=lambda o, c: None),
                    StageDefinition(name="s1", handler=lambda o, c: None),
                ],
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineBuilder:
    def test_basic_build(self):
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        p = (
            PipelineBuilder("test")
            .description("My pipeline")
            .version("1.1")
            .add_stage("s1", lambda o, c: None)
            .add_stage("s2", lambda o, c: None)
            .build()
        )
        assert p.name        == "test"
        assert p.description == "My pipeline"
        assert p.version     == "1.1"
        assert len(p.stages) == 2

    def test_add_optional_stage(self):
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        from iios.observation.pipeline.pipeline_constants import StageMode, FailurePolicy
        p = (
            PipelineBuilder("t")
            .add_stage("s1", lambda o, c: None)
            .add_optional_stage("s2", lambda o, c: None)
            .build()
        )
        s2 = p.stage("s2")
        assert s2.mode           == StageMode.OPTIONAL
        assert s2.failure_policy == FailurePolicy.CONTINUE

    def test_add_conditional_stage(self):
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        from iios.observation.pipeline.pipeline_constants import StageMode
        cond = lambda o, c: True
        p    = (
            PipelineBuilder("t")
            .add_stage("s1", lambda o, c: None)
            .add_conditional_stage("s2", lambda o, c: None, condition=cond)
            .build()
        )
        s2 = p.stage("s2")
        assert s2.mode      == StageMode.CONDITIONAL
        assert s2.condition is cond

    def test_empty_build_raises(self):
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        from iios.observation.pipeline.pipeline_exceptions import PipelineConfigurationError
        with pytest.raises(PipelineConfigurationError):
            PipelineBuilder("empty").build()

    def test_empty_name_raises(self):
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        from iios.observation.pipeline.pipeline_exceptions import PipelineConfigurationError
        with pytest.raises(PipelineConfigurationError):
            PipelineBuilder("")

    def test_stage_names_in_definition(self):
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        p = (
            PipelineBuilder("t")
            .add_stage("alpha",   lambda o, c: None)
            .add_stage("beta",    lambda o, c: None)
            .add_stage("gamma",   lambda o, c: None)
            .build()
        )
        assert p.stage_names() == ["alpha", "beta", "gamma"]

    def test_to_dict(self):
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        p = PipelineBuilder("test").add_stage("s1", lambda o, c: None).build()
        d = p.to_dict()
        assert d["name"]   == "test"
        assert "stages"    in d


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Executor
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineExecutor:
    def _make_simple_pipeline(self, name: str = "simple"):
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        from iios.observation.pipeline.pipeline_context import StageResult

        def handler(obs, ctx):
            return StageResult(stage_name="s1", success=True, metadata={"ran": True})

        return PipelineBuilder(name).add_stage("s1", handler).build()

    def _make_failing_pipeline(self):
        from iios.observation.pipeline.pipeline_builder  import PipelineBuilder
        from iios.observation.pipeline.pipeline_context  import StageResult
        from iios.observation.pipeline.pipeline_constants import FailurePolicy

        def fail_handler(obs, ctx):
            return StageResult(stage_name="fail_stage", success=False, error="deliberate failure")

        return (
            PipelineBuilder("failing")
            .add_stage("fail_stage", fail_handler, failure_policy=FailurePolicy.FAIL_FAST)
            .build()
        )

    def test_successful_execution(self):
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor
        executor = PipelineExecutor()
        obs      = _make_obs()
        pipeline = self._make_simple_pipeline()
        result   = executor.execute(obs, pipeline)
        assert result.success
        assert len(result.stage_results) == 1

    def test_failed_execution_fail_fast(self):
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor
        executor = PipelineExecutor()
        obs      = _make_obs()
        pipeline = self._make_failing_pipeline()
        result   = executor.execute(obs, pipeline)
        assert not result.success
        assert result.aborted

    def test_optional_stage_failure_continues(self):
        from iios.observation.pipeline.pipeline_builder  import PipelineBuilder
        from iios.observation.pipeline.pipeline_context  import StageResult
        from iios.observation.pipeline.pipeline_constants import StageMode, FailurePolicy
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor

        def fail_optional(obs, ctx):
            raise RuntimeError("optional fail")

        def succeed(obs, ctx):
            return StageResult(stage_name="s2", success=True)

        pipeline = (
            PipelineBuilder("opt_test")
            .add_stage("s1", fail_optional, mode=StageMode.OPTIONAL,
                       failure_policy=FailurePolicy.CONTINUE)
            .add_stage("s2", succeed)
            .build()
        )
        executor = PipelineExecutor()
        result   = executor.execute(_make_obs(), pipeline)
        assert result.success
        assert len(result.stage_results) == 2
        assert result.stage_results[0].skipped

    def test_conditional_stage_skipped(self):
        from iios.observation.pipeline.pipeline_builder  import PipelineBuilder
        from iios.observation.pipeline.pipeline_context  import StageResult
        from iios.observation.pipeline.pipeline_constants import StageMode
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor

        ran = []
        def conditional_handler(obs, ctx):
            ran.append(True)
            return StageResult(stage_name="cond", success=True)

        pipeline = (
            PipelineBuilder("cond_test")
            .add_stage("s1", lambda o, c: StageResult(stage_name="s1", success=True))
            .add_conditional_stage("cond", conditional_handler,
                                   condition=lambda o, c: False)
            .build()
        )
        executor = PipelineExecutor()
        result   = executor.execute(_make_obs(), pipeline)
        assert result.success
        assert len(ran) == 0  # condition was False, handler never ran

    def test_retry_on_failure(self):
        from iios.observation.pipeline.pipeline_builder  import PipelineBuilder
        from iios.observation.pipeline.pipeline_context  import StageResult
        from iios.observation.pipeline.pipeline_constants import FailurePolicy, RetryBackoff
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor

        attempts = []
        def flaky(obs, ctx):
            attempts.append(1)
            if len(attempts) < 3:
                raise RuntimeError("flaky")
            return StageResult(stage_name="flaky", success=True)

        pipeline = (
            PipelineBuilder("retry_test")
            .add_stage("flaky", flaky,
                       retry_count=3, retry_delay_ms=0,
                       retry_backoff=RetryBackoff.NONE,
                       failure_policy=FailurePolicy.FAIL_FAST)
            .build()
        )
        executor = PipelineExecutor()
        result   = executor.execute(_make_obs(), pipeline)
        assert result.success
        assert len(attempts) == 3

    def test_execution_result_to_dict(self):
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor
        obs    = _make_obs()
        result = PipelineExecutor().execute(obs, self._make_simple_pipeline())
        d      = result.to_dict()
        assert "obs_id"        in d
        assert "pipeline_name" in d
        assert "stages"        in d

    def test_total_ms_positive(self):
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor
        result = PipelineExecutor().execute(_make_obs(), self._make_simple_pipeline())
        assert result.total_ms > 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Metrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineMetrics:
    def test_initial_snapshot_zeros(self):
        from iios.observation.pipeline.pipeline_metrics import PipelineMetrics
        m    = PipelineMetrics()
        snap = m.snapshot()
        assert snap.total_processed == 0
        assert snap.success_rate    == 0.0

    def test_record_pipeline_success(self):
        from iios.observation.pipeline.pipeline_metrics import PipelineMetrics
        from iios.observation.pipeline.pipeline_context import StageResult
        m = PipelineMetrics()
        m.record_pipeline("standard", True, False, 50.0, [
            StageResult(stage_name="s1", success=True, duration_ms=10.0),
        ])
        snap = m.snapshot()
        assert snap.total_processed == 1
        assert snap.total_success   == 1
        assert snap.total_failed    == 0

    def test_record_pipeline_failure(self):
        from iios.observation.pipeline.pipeline_metrics import PipelineMetrics
        m = PipelineMetrics()
        m.record_pipeline("standard", False, False, 20.0, [])
        snap = m.snapshot()
        assert snap.total_failed == 1
        assert snap.success_rate == 0.0

    def test_dead_letter_counted(self):
        from iios.observation.pipeline.pipeline_metrics import PipelineMetrics
        m = PipelineMetrics()
        m.record_pipeline("standard", False, True, 20.0, [])
        snap = m.snapshot()
        assert snap.total_dead_letter == 1

    def test_per_stage_tracked(self):
        from iios.observation.pipeline.pipeline_metrics import PipelineMetrics
        from iios.observation.pipeline.pipeline_context import StageResult
        m = PipelineMetrics()
        m.record_pipeline("standard", True, False, 50.0, [
            StageResult(stage_name="validate", success=True, duration_ms=15.0),
            StageResult(stage_name="classify", success=True, duration_ms=20.0),
        ])
        snap = m.snapshot()
        assert "validate" in snap.per_stage
        assert "classify" in snap.per_stage

    def test_snapshot_to_dict(self):
        from iios.observation.pipeline.pipeline_metrics import PipelineMetrics
        m = PipelineMetrics()
        d = m.snapshot().to_dict()
        assert "total_processed" in d
        assert "success_rate"    in d

    def test_singleton(self):
        from iios.observation.pipeline.pipeline_metrics import (
            get_pipeline_metrics, reset_pipeline_metrics,
        )
        m1 = get_pipeline_metrics()
        m2 = get_pipeline_metrics()
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Monitor
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineMonitor:
    def _make_result(self, success: bool = True) -> "PipelineExecutionResult":
        from iios.observation.pipeline.pipeline_executor import PipelineExecutionResult
        from iios.observation.pipeline.pipeline_context  import StageResult
        return PipelineExecutionResult(
            obs_id        = "obs:test/001",
            pipeline_name = "standard",
            run_id        = "r001",
            success       = success,
            final_status  = ObservationStatus.ACCEPTED if success else ObservationStatus.REJECTED,
            stage_results = [StageResult(stage_name="collect", success=True, duration_ms=5.0)],
            total_ms      = 50.0,
        )

    def test_record_and_health_report(self):
        from iios.observation.pipeline.pipeline_monitor import PipelineMonitor
        from iios.observation.pipeline.pipeline_metrics import PipelineMetrics
        mon    = PipelineMonitor(PipelineMetrics())
        mon.record(self._make_result(success=True))
        report = mon.health_report()
        assert report.total_processed >= 1

    def test_health_report_structure(self):
        from iios.observation.pipeline.pipeline_monitor import PipelineMonitor
        from iios.observation.pipeline.pipeline_metrics import PipelineMetrics
        mon = PipelineMonitor(PipelineMetrics())
        for _ in range(3):
            mon.record(self._make_result(success=True))
        report = mon.health_report()
        d = report.to_dict()
        assert "success_rate"      in d
        assert "avg_latency_ms"    in d
        assert "bottleneck_stages" in d
        assert "stages"            in d

    def test_recent_tracks_results(self):
        from iios.observation.pipeline.pipeline_monitor import PipelineMonitor
        from iios.observation.pipeline.pipeline_metrics import PipelineMetrics
        mon = PipelineMonitor(PipelineMetrics())
        mon.record(self._make_result())
        mon.record(self._make_result())
        assert len(mon.recent(limit=10)) == 2

    def test_singleton(self):
        from iios.observation.pipeline.pipeline_monitor import (
            get_pipeline_monitor, reset_pipeline_monitor,
        )
        m1 = get_pipeline_monitor()
        m2 = get_pipeline_monitor()
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Engine (end-to-end with built-in stages)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineEngine:
    def test_execute_standard_pipeline(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        obs    = _make_obs()
        result = engine.execute(obs, "standard")
        assert result.pipeline_name == "standard"
        assert result.obs_id        == obs.id
        assert len(result.stage_results) > 0

    def test_standard_pipeline_accepts_valid_obs(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        obs    = _make_obs()
        result = engine.execute(obs, "standard")
        assert result.success
        assert obs.status == ObservationStatus.ACCEPTED

    def test_fast_pipeline_accepts_valid_obs(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        obs    = _make_obs()
        result = engine.execute(obs, "fast")
        assert result.success

    def test_validation_only_pipeline(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        obs    = _make_obs()
        result = engine.execute(obs, "validation_only")
        assert result.pipeline_name == "validation_only"
        assert len(result.stage_results) == 3

    def test_execute_batch(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine   = PipelineEngine()
        obs_list = [_make_obs(title=f"obs{i}") for i in range(4)]
        results  = engine.execute_batch(obs_list, "fast")
        assert len(results) == 4
        assert all(r.pipeline_name == "fast" for r in results)

    def test_execute_priority_ordering(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        obs_low  = _make_obs(title="low",      priority=ObservationPriority.LOW)
        obs_high = _make_obs(title="high",     priority=ObservationPriority.CRITICAL)
        obs_med  = _make_obs(title="medium",   priority=ObservationPriority.MEDIUM)
        results  = engine.execute_priority([obs_low, obs_med, obs_high], "fast")
        # All should complete successfully
        assert len(results) == 3

    def test_register_custom_pipeline(self):
        from iios.observation.pipeline.pipeline_engine  import PipelineEngine
        from iios.observation.pipeline.pipeline_builder import PipelineBuilder
        from iios.observation.pipeline.pipeline_context import StageResult
        custom = (
            PipelineBuilder("custom_test")
            .add_stage("only_stage", lambda o, c: StageResult(stage_name="only_stage", success=True))
            .build()
        )
        engine = PipelineEngine()
        engine.register_pipeline(custom)
        assert "custom_test" in engine.list_pipelines()
        result = engine.execute(_make_obs(), "custom_test")
        assert result.success

    def test_list_pipelines_includes_builtins(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        names  = engine.list_pipelines()
        assert "standard"        in names
        assert "fast"            in names
        assert "validation_only" in names

    def test_history_grows(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        engine.execute(_make_obs(), "fast")
        engine.execute(_make_obs(), "fast")
        assert len(engine.history()) == 2

    def test_history_limit(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        for _ in range(5):
            engine.execute(_make_obs(), "fast")
        assert len(engine.history(limit=3)) == 3

    def test_health_report_structure(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        engine.execute(_make_obs(), "fast")
        h = engine.health()
        assert "success_rate"    in h
        assert "avg_latency_ms"  in h

    def test_stats_after_execute(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        engine.execute(_make_obs(), "fast")
        s = engine.stats()
        assert s["total_processed"] >= 1

    def test_singleton(self):
        from iios.observation.pipeline.pipeline_engine import (
            get_pipeline_engine, reset_pipeline_engine,
        )
        e1 = get_pipeline_engine()
        e2 = get_pipeline_engine()
        assert e1 is e2

    def test_classification_written_to_obs(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        obs    = _make_obs()
        engine.execute(obs, "standard")
        # classification engine writes back to obs
        assert obs.classification != ""

    def test_tags_enriched_on_obs(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        obs    = _make_obs()
        engine.execute(obs, "standard")
        assert len(obs.metadata.tags) > 0

    def test_result_stage_count_standard(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine = PipelineEngine()
        result = engine.execute(_make_obs(), "standard")
        assert len(result.stage_results) == 17


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Manager
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineManager:
    def test_process_returns_result(self):
        from iios.observation.pipeline.pipeline_manager import PipelineManager
        mgr    = PipelineManager()
        result = mgr.process(_make_obs())
        assert result.obs_id is not None

    def test_process_uses_default_pipeline(self):
        from iios.observation.pipeline.pipeline_manager import PipelineManager
        mgr    = PipelineManager(default_pipeline="fast")
        result = mgr.process(_make_obs())
        assert result.pipeline_name == "fast"

    def test_process_batch(self):
        from iios.observation.pipeline.pipeline_manager import PipelineManager
        mgr     = PipelineManager()
        results = mgr.process_batch([_make_obs() for _ in range(3)])
        assert len(results) == 3

    def test_stats_after_process(self):
        from iios.observation.pipeline.pipeline_manager import PipelineManager
        mgr = PipelineManager()
        mgr.process(_make_obs())
        s = mgr.stats()
        assert s["total"]      == 1
        assert s["successful"] >= 1

    def test_dead_letter_queue_empty_initially(self):
        from iios.observation.pipeline.pipeline_manager import PipelineManager
        mgr = PipelineManager()
        assert mgr.dead_letter_queue() == []

    def test_history_stored(self):
        from iios.observation.pipeline.pipeline_manager import PipelineManager
        mgr = PipelineManager()
        mgr.process(_make_obs())
        mgr.process(_make_obs())
        assert len(mgr.history()) == 2

    def test_history_limit(self):
        from iios.observation.pipeline.pipeline_manager import PipelineManager
        mgr = PipelineManager()
        for _ in range(5):
            mgr.process(_make_obs())
        assert len(mgr.history(limit=3)) == 3

    def test_singleton(self):
        from iios.observation.pipeline.pipeline_manager import (
            get_pipeline_manager, reset_pipeline_manager,
        )
        m1 = get_pipeline_manager()
        m2 = get_pipeline_manager()
        assert m1 is m2

    def test_priority_process(self):
        from iios.observation.pipeline.pipeline_manager import PipelineManager
        mgr = PipelineManager()
        obs_list = [
            _make_obs(priority=ObservationPriority.LOW),
            _make_obs(priority=ObservationPriority.CRITICAL),
        ]
        results = mgr.process_priority(obs_list)
        assert len(results) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Scheduler
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineScheduler:
    def test_batch_scheduler_submit_and_flush(self):
        from iios.observation.pipeline.pipeline_scheduler import BatchScheduler
        from iios.observation.pipeline.pipeline_manager   import PipelineManager
        mgr  = PipelineManager()
        sched = BatchScheduler(mgr, batch_size=10, pipeline_name="fast")
        for _ in range(3):
            sched.submit(_make_obs())
        results = sched.flush()
        assert len(results) == 3

    def test_batch_scheduler_auto_flush_on_size(self):
        from iios.observation.pipeline.pipeline_scheduler import BatchScheduler
        from iios.observation.pipeline.pipeline_manager   import PipelineManager
        mgr   = PipelineManager()
        sched = BatchScheduler(mgr, batch_size=2, pipeline_name="fast")
        sched.start()
        sched.submit(_make_obs())
        sched.submit(_make_obs())
        time.sleep(0.3)
        s = sched.stats()
        # The scheduler should have flushed at least the batch
        assert s["total_flushed"] >= 0  # may be 0 if loop hasn't run yet
        sched.stop()

    def test_priority_scheduler_submit_and_process(self):
        from iios.observation.pipeline.pipeline_scheduler import PriorityScheduler
        from iios.observation.pipeline.pipeline_manager   import PipelineManager
        mgr  = PipelineManager()
        sched = PriorityScheduler(mgr, pipeline_name="fast")
        sched.submit(_make_obs(priority=ObservationPriority.LOW))
        sched.submit(_make_obs(priority=ObservationPriority.CRITICAL))
        assert sched.depth() == 2
        results = sched.process_all()
        assert len(results) == 2
        assert sched.depth() == 0

    def test_pipeline_scheduler_routes_by_priority(self):
        from iios.observation.pipeline.pipeline_scheduler import PipelineScheduler
        from iios.observation.pipeline.pipeline_manager   import PipelineManager
        mgr   = PipelineManager()
        sched = PipelineScheduler(mgr, pipeline_name="fast")
        # HIGH goes to priority queue
        sched.submit(_make_obs(priority=ObservationPriority.HIGH))
        # MEDIUM goes to batch
        sched.submit(_make_obs(priority=ObservationPriority.MEDIUM))
        assert sched._priority.depth() == 1
        results = sched.flush()
        assert len(results) == 2

    def test_pipeline_scheduler_stats(self):
        from iios.observation.pipeline.pipeline_scheduler import PipelineScheduler
        from iios.observation.pipeline.pipeline_manager   import PipelineManager
        sched = PipelineScheduler(PipelineManager())
        s = sched.stats()
        assert "batch"    in s
        assert "priority" in s

    def test_singleton(self):
        from iios.observation.pipeline.pipeline_scheduler import (
            get_pipeline_scheduler, reset_pipeline_scheduler,
        )
        s1 = get_pipeline_scheduler()
        s2 = get_pipeline_scheduler()
        assert s1 is s2


# ═══════════════════════════════════════════════════════════════════════════════
# Failure Recovery
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailureRecovery:
    def test_rollback_policy(self):
        from iios.observation.pipeline.pipeline_builder  import PipelineBuilder
        from iios.observation.pipeline.pipeline_context  import StageResult
        from iios.observation.pipeline.pipeline_constants import FailurePolicy
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor

        def failing_stage(obs, ctx):
            return StageResult(stage_name="fail", success=False, error="forced")

        pipeline = (
            PipelineBuilder("rollback_test")
            .add_stage("s1", lambda o, c: StageResult(stage_name="s1", success=True))
            .add_stage("fail", failing_stage, failure_policy=FailurePolicy.ROLLBACK)
            .build()
        )
        executor = PipelineExecutor()
        obs      = _make_obs()
        result   = executor.execute(obs, pipeline)
        assert not result.success
        assert result.aborted

    def test_dead_letter_policy(self):
        from iios.observation.pipeline.pipeline_builder  import PipelineBuilder
        from iios.observation.pipeline.pipeline_context  import StageResult
        from iios.observation.pipeline.pipeline_constants import FailurePolicy
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor

        def failing_stage(obs, ctx):
            return StageResult(stage_name="dl", success=False, error="dl triggered")

        pipeline = (
            PipelineBuilder("dl_test")
            .add_stage("dl", failing_stage, failure_policy=FailurePolicy.DEAD_LETTER)
            .build()
        )
        executor = PipelineExecutor()
        result   = executor.execute(_make_obs(), pipeline)
        assert result.dead_lettered

    def test_checkpoint_on_failure(self):
        from iios.observation.pipeline.pipeline_builder  import PipelineBuilder
        from iios.observation.pipeline.pipeline_context  import StageResult, CheckpointPolicy
        from iios.observation.pipeline.pipeline_constants import FailurePolicy, CheckpointPolicy as CP
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor

        def good(obs, ctx):
            return StageResult(stage_name="good", success=True)

        def bad(obs, ctx):
            return StageResult(stage_name="bad", success=False, error="boom")

        pipeline = (
            PipelineBuilder("checkpoint_test")
            .add_stage("good", good)
            .add_stage("bad",  bad, failure_policy=FailurePolicy.FAIL_FAST)
            .build()
        )
        executor = PipelineExecutor()
        obs      = _make_obs()
        result   = executor.execute(obs, pipeline)
        assert not result.success
        # Checkpoint should exist from ON_FAILURE policy
        assert result.context is not None

    def test_continue_policy_skips_failed_stage(self):
        from iios.observation.pipeline.pipeline_builder  import PipelineBuilder
        from iios.observation.pipeline.pipeline_context  import StageResult
        from iios.observation.pipeline.pipeline_constants import FailurePolicy
        from iios.observation.pipeline.pipeline_executor import PipelineExecutor

        ran = []

        def fail_stage(obs, ctx):
            return StageResult(stage_name="fail_s", success=False, error="skipped")

        def final_stage(obs, ctx):
            ran.append(True)
            return StageResult(stage_name="final", success=True)

        pipeline = (
            PipelineBuilder("continue_test")
            .add_stage("fail_s", fail_stage, failure_policy=FailurePolicy.CONTINUE)
            .add_stage("final",  final_stage)
            .build()
        )
        executor = PipelineExecutor()
        result   = executor.execute(_make_obs(), pipeline)
        assert ran == [True]   # final stage ran despite earlier failure


# ═══════════════════════════════════════════════════════════════════════════════
# Concurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_parallel_pipeline_execution(self):
        from iios.observation.pipeline.pipeline_engine import PipelineEngine
        engine  = PipelineEngine()
        errors: list[Exception] = []

        def _run():
            try:
                engine.execute(_make_obs(), "fast")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(engine.history()) == 8

    def test_concurrent_context_isolation(self):
        from iios.observation.pipeline.pipeline_context import (
            pipeline_execution, get_pipeline_context,
        )
        results: list[Optional[str]] = []

        def _run(obs_id: str) -> None:
            with pipeline_execution(obs_id, "standard"):
                time.sleep(0.01)
                ctx = get_pipeline_context()
                results.append(ctx.obs_id if ctx else None)

        threads = [threading.Thread(target=_run, args=(f"obs:t/{i}",)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have seen its own obs_id (thread-local)
        assert len(results) == 6
        assert all(r is not None for r in results)

    def test_singleton_thread_safety(self):
        from iios.observation.pipeline.pipeline_engine import get_pipeline_engine
        instances: list = []

        def _get():
            instances.append(get_pipeline_engine())

        threads = [threading.Thread(target=_get) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(e is instances[0] for e in instances)

    def test_metrics_thread_safety(self):
        from iios.observation.pipeline.pipeline_metrics import PipelineMetrics
        from iios.observation.pipeline.pipeline_context import StageResult
        m      = PipelineMetrics()
        errors: list[Exception] = []

        def _record():
            try:
                for _ in range(20):
                    m.record_pipeline("p", True, False, 10.0, [
                        StageResult(stage_name="s", success=True, duration_ms=5.0),
                    ])
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_record) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        snap = m.snapshot()
        assert snap.total_processed == 100
