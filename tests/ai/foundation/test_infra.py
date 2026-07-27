"""Tests for configuration, health, exceptions, and container."""
from __future__ import annotations

import pytest

from iios.ai.foundation.config import (
    FeatureFlags,
    AIFrameworkConfiguration,
    RuntimeConfiguration,
    EnvironmentConfigurationLoader,
)
from iios.ai.foundation.health import (
    HealthLevel,
    HealthStatus,
    ReadinessStatus,
    LivenessStatus,
    HealthCheck,
    HealthReporter,
)
from iios.ai.foundation.exceptions import (
    AIException,
    AIConfigurationException,
    AIMissingConfigurationException,
    AIInvalidConfigurationException,
    AISessionException,
    AISessionNotFoundError,
    AIContextTooLargeError,
    AIRequestValidationError,
    AIProviderNotAvailableError,
    AIPipelineError,
    AIResponseValidationError,
    AIPolicyViolationError,
)
from iios.ai.foundation.container import AIContainer
from iios.ai.foundation.observability import (
    CorrelationContext,
    StructuredLogger,
    ExecutionTimer,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class TestFeatureFlags:
    def test_defaults_are_conservative(self):
        flags = FeatureFlags()
        assert not flags.enable_streaming
        assert not flags.enable_caching
        assert flags.enable_tracing
        assert flags.enable_retry

    def test_all_enabled(self):
        flags = FeatureFlags.all_enabled()
        assert flags.enable_streaming
        assert flags.enable_caching

    def test_to_dict(self):
        flags = FeatureFlags()
        d = flags.to_dict()
        assert isinstance(d["enable_streaming"], bool)


class TestAIFrameworkConfiguration:
    def test_defaults(self):
        cfg = AIFrameworkConfiguration()
        assert cfg.environment == "production"
        assert cfg.default_timeout_s == 30.0
        assert cfg.max_sessions == 500

    def test_to_dict(self):
        cfg = AIFrameworkConfiguration()
        d   = cfg.to_dict()
        assert "environment" in d
        assert "feature_flags" in d


class TestRuntimeConfiguration:
    def test_get_base_value(self):
        cfg     = AIFrameworkConfiguration(environment="staging")
        runtime = RuntimeConfiguration(cfg)
        assert runtime.get("environment") == "staging"

    def test_override(self):
        cfg     = AIFrameworkConfiguration()
        runtime = RuntimeConfiguration(cfg)
        runtime.override("environment", "test")
        assert runtime.get("environment") == "test"

    def test_clear_override(self):
        cfg     = AIFrameworkConfiguration()
        runtime = RuntimeConfiguration(cfg)
        runtime.override("environment", "test")
        runtime.clear_override("environment")
        assert runtime.get("environment") == "production"

    def test_reload(self):
        cfg1    = AIFrameworkConfiguration(environment="staging")
        cfg2    = AIFrameworkConfiguration(environment="production")
        runtime = RuntimeConfiguration(cfg1)
        runtime.reload(cfg2)
        assert runtime.get("environment") == "production"


class TestEnvironmentConfigurationLoader:
    def test_loads_defaults(self):
        loader = EnvironmentConfigurationLoader()
        cfg    = loader.load()
        assert isinstance(cfg, AIFrameworkConfiguration)
        assert cfg.environment in ("production", "staging", "test")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class AlwaysPassCheck(HealthCheck):
    @property
    def name(self) -> str:
        return "always_pass"
    def check(self) -> bool:
        return True


class AlwaysFailCheck(HealthCheck):
    @property
    def name(self) -> str:
        return "always_fail"
    def check(self) -> bool:
        return False


class TestHealthReporter:
    def test_all_pass_is_healthy(self):
        reporter = HealthReporter("test-component")
        reporter.add_check(AlwaysPassCheck())
        h = reporter.health()
        assert h.level == HealthLevel.HEALTHY
        assert h.is_healthy

    def test_all_fail_is_unhealthy(self):
        reporter = HealthReporter("test-component")
        reporter.add_check(AlwaysFailCheck())
        h = reporter.health()
        assert h.level == HealthLevel.UNHEALTHY

    def test_mixed_is_degraded(self):
        reporter = HealthReporter("test-component")
        reporter.add_check(AlwaysPassCheck())
        reporter.add_check(AlwaysFailCheck())
        h = reporter.health()
        assert h.level == HealthLevel.DEGRADED

    def test_readiness_healthy_is_ready(self):
        reporter = HealthReporter("test-component")
        reporter.add_check(AlwaysPassCheck())
        r = reporter.readiness()
        assert r.ready

    def test_readiness_unhealthy_is_not_ready(self):
        reporter = HealthReporter("test-component")
        reporter.add_check(AlwaysFailCheck())
        r = reporter.readiness()
        assert not r.ready

    def test_liveness(self):
        reporter = HealthReporter("test-component")
        reporter.add_check(AlwaysPassCheck())
        l = reporter.liveness()
        assert l.alive
        assert l.uptime_s >= 0

    def test_to_dict(self):
        reporter = HealthReporter("test-component")
        reporter.add_check(AlwaysPassCheck())
        d = reporter.health().to_dict()
        assert "level" in d
        assert "checks" in d


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    def test_all_are_subclass_of_ai_exception(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(AIException, IIOSError)
        assert issubclass(AIMissingConfigurationException, AIException)
        assert issubclass(AISessionNotFoundError, AIException)
        assert issubclass(AIContextTooLargeError, AIException)
        assert issubclass(AIRequestValidationError, AIException)
        assert issubclass(AIProviderNotAvailableError, AIException)
        assert issubclass(AIPipelineError, AIException)
        assert issubclass(AIPolicyViolationError, AIException)

    def test_session_not_found_stores_id(self):
        exc = AISessionNotFoundError("s-001")
        assert exc.session_id == "s-001"
        assert "s-001" in str(exc)

    def test_context_too_large_stores_counts(self):
        exc = AIContextTooLargeError(5_000, 4_096)
        assert exc.estimated_tokens == 5_000
        assert exc.budget == 4_096

    def test_missing_config_stores_key(self):
        exc = AIMissingConfigurationException("IIOS_AI_API_KEY")
        assert exc.key == "IIOS_AI_API_KEY"

    def test_policy_violation_stores_policy(self):
        exc = AIPolicyViolationError("cost_guard", "exceeds budget")
        assert exc.policy == "cost_guard"

    def test_error_codes_are_correct(self):
        assert AIException.CODE           == "AI-000"
        assert AIConfigurationException.CODE == "AI-100"
        assert AISessionException.CODE    == "AI-200"
        assert AIPipelineError.CODE       == "AI-601"


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------

class TestAIContainer:
    def test_requires_build_before_access(self):
        container = AIContainer()
        with pytest.raises(RuntimeError, match="build"):
            _ = container.session_manager

    def test_build_provides_components(self):
        container = AIContainer()
        container.build()
        assert container.session_manager is not None
        assert container.pipeline is not None
        assert container.health_reporter is not None
        assert container.configuration is not None

    def test_rebuild(self):
        container = AIContainer()
        container.build()
        mgr1 = container.session_manager
        container.rebuild()
        mgr2 = container.session_manager
        assert mgr1 is not mgr2  # new instance after rebuild

    def test_is_built_flag(self):
        container = AIContainer()
        assert not container.is_built()
        container.build()
        assert container.is_built()

    def test_pipeline_runs_through_container(self):
        container = AIContainer()
        container.build()
        from iios.ai.foundation.request import RequestMetadata, AIRequest, AIExecutionRequest
        meta     = RequestMetadata.create("s-001", "a3")
        req      = AIRequest.create(meta, [{"role": "user", "content": "Q"}], max_tokens=50)
        exec_req = AIExecutionRequest(request=req)
        result   = container.pipeline.run(exec_req)
        assert result.succeeded


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

class TestCorrelationContext:
    def test_create(self):
        ctx = CorrelationContext.create("a3", "s-001")
        assert ctx.module_id == "a3"
        assert ctx.session_id == "s-001"
        assert ctx.trace_id
        assert ctx.span_id

    def test_child_span_preserves_trace(self):
        ctx   = CorrelationContext.create("a3", "s-001")
        child = ctx.child_span()
        assert child.trace_id == ctx.trace_id
        assert child.span_id  != ctx.span_id

    def test_to_dict(self):
        ctx = CorrelationContext.create("a3", "s-001")
        d   = ctx.to_dict()
        assert "trace_id"   in d
        assert "session_id" in d


class TestExecutionTimer:
    def test_measures_elapsed(self):
        timer = ExecutionTimer("test_op")
        import time
        with timer.measure() as result:
            time.sleep(0.01)
        assert result.elapsed_ms >= 10.0
        assert result.succeeded

    def test_captures_exception(self):
        timer = ExecutionTimer("bad_op")
        with pytest.raises(ValueError):
            with timer.measure() as result:
                raise ValueError("oops")
        assert not result.succeeded
        assert "oops" in result.error
