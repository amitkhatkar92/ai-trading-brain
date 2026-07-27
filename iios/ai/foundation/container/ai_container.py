"""
ai_container.py -- iios.ai.foundation.container
================================================
:class:`AIContainer` -- lightweight dependency injection container.

Wires all A1 AI Foundation infrastructure components together using
constructor injection.  No global singletons.

Usage::

    from iios.ai.foundation.container import AIContainer

    container = AIContainer()
    container.build()

    # Legacy 6-stage pipeline (A1 M3)
    pipeline        = container.pipeline

    # Modern 8-stage runtime (A1 Provider Runtime)
    exec_runtime    = container.execution_runtime
    exec_runtime.initialize()
    exec_runtime.start()
    response, ctx   = exec_runtime.execute(exec_request)

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from typing import Optional, Any

from ..config.config_models     import (
    AIFrameworkConfiguration,
    ConfigurationLoader,
    RuntimeConfiguration,
    EnvironmentConfigurationLoader,
)
from ..session.session_factory  import SessionFactory
from ..session.session_manager  import AISessionManager
from ..context.context_validator import ContextValidator
from ..context.context_compressor import TruncationContextCompressor
from ..pipeline.execution_pipeline import ExecutionPipeline as _LegacyPipeline
from ..health.health_models     import HealthReporter
from ..observability.observability import StructuredLogger

# Provider Runtime (Phase 3)
from ..events.event_bus          import AIEventBus
from ..metrics.metrics_models    import RuntimeMetrics
from ..cost.cost_tracker         import CostTracker
from ..retry.retry_models        import RetryPolicy
from ..timeout.timeout_models    import TimeoutPolicy
from ..provider.provider_manager import AIProviderRuntime
from ..runtime.execution_runtime import ExecutionRuntime


class AIContainer:
    """
    Lightweight DI container for the AI Foundation infrastructure.

    All components are created lazily on first access and cached.
    Components are re-created when :meth:`rebuild` is called.

    The container avoids global state -- each instance is fully
    independent.  The typical pattern is one container per process.
    """

    def __init__(
        self,
        loader:         Optional[ConfigurationLoader] = None,
        config:         Optional[AIFrameworkConfiguration] = None,
        provider_registry: Optional[Any] = None,
        retry_policy:   Optional[RetryPolicy]   = None,
        timeout_policy: Optional[TimeoutPolicy] = None,
    ) -> None:
        self._loader:           ConfigurationLoader      = loader or EnvironmentConfigurationLoader()
        self._config:           Optional[AIFrameworkConfiguration] = config
        self._provider_registry: Optional[Any]           = provider_registry
        self._runtime_config:   Optional[RuntimeConfiguration] = None
        self._retry_policy      = retry_policy
        self._timeout_policy    = timeout_policy

        # Lazily built components — legacy
        self._session_factory:  Optional[SessionFactory]     = None
        self._session_manager:  Optional[AISessionManager]   = None
        self._context_validator: Optional[ContextValidator]  = None
        self._context_compressor: Optional[TruncationContextCompressor] = None
        self._pipeline:         Optional[_LegacyPipeline]    = None
        self._health_reporter:  Optional[HealthReporter]     = None
        self._logger:           Optional[StructuredLogger]   = None

        # Lazily built components — Provider Runtime
        self._event_bus:        Optional[AIEventBus]         = None
        self._runtime_metrics:  Optional[RuntimeMetrics]     = None
        self._cost_tracker:     Optional[CostTracker]        = None
        self._provider_runtime: Optional[AIProviderRuntime]  = None
        self._execution_runtime: Optional[ExecutionRuntime]  = None

        self._built:            bool                         = False

    # ── Construction ──────────────────────────────────────────────────────────

    def build(self) -> "AIContainer":
        """
        Load configuration and construct all components.

        Must be called before accessing any component property.
        Returns ``self`` for chaining.

        Constructs two execution paths:
        * **Legacy 6-stage pipeline** (``container.pipeline``) — backward-compat.
        * **Provider Runtime 8-stage** (``container.execution_runtime``) — recommended.
        """
        if self._config is None:
            self._config = self._loader.load()

        self._runtime_config   = RuntimeConfiguration(self._config)
        self._session_factory  = SessionFactory(
            default_ttl_s    = self._config.session_ttl_s,
            default_priority = "normal",
        )
        self._session_manager  = AISessionManager(
            factory      = self._session_factory,
            max_sessions = self._config.max_sessions,
        )
        self._context_validator  = ContextValidator()
        self._context_compressor = TruncationContextCompressor()
        self._pipeline           = _LegacyPipeline(
            provider_registry = self._provider_registry,
        )
        self._health_reporter    = HealthReporter(
            component = "iios:ai:foundation",
        )
        self._logger             = StructuredLogger(__name__)

        # ── Provider Runtime wiring ──────────────────────────────────────────
        self._event_bus        = AIEventBus()
        self._runtime_metrics  = RuntimeMetrics()
        self._cost_tracker     = CostTracker(
            session_id = "container",
            budget_usd = 0.0,           # unlimited until A2 sets rates
        )
        retry  = self._retry_policy   or RetryPolicy()
        timout = self._timeout_policy or TimeoutPolicy()
        self._provider_runtime = AIProviderRuntime(
            event_bus = self._event_bus,
        )
        self._execution_runtime = ExecutionRuntime(
            provider_runtime = self._provider_runtime,
            event_bus        = self._event_bus,
            retry_policy     = retry,
            timeout_policy   = timout,
        )
        # ── End Provider Runtime ─────────────────────────────────────────────

        self._built = True
        return self

    def rebuild(self) -> "AIContainer":
        """Reload configuration and rebuild all components."""
        self._config = None
        self._built  = False
        return self.build()

    # ── Component accessors ───────────────────────────────────────────────────

    def _require_built(self) -> None:
        if not self._built:
            raise RuntimeError(
                "AIContainer has not been built. Call container.build() first."
            )

    @property
    def configuration(self) -> AIFrameworkConfiguration:
        self._require_built()
        return self._config  # type: ignore[return-value]

    @property
    def runtime_config(self) -> RuntimeConfiguration:
        self._require_built()
        return self._runtime_config  # type: ignore[return-value]

    @property
    def session_factory(self) -> SessionFactory:
        self._require_built()
        return self._session_factory  # type: ignore[return-value]

    @property
    def session_manager(self) -> AISessionManager:
        self._require_built()
        return self._session_manager  # type: ignore[return-value]

    @property
    def context_validator(self) -> ContextValidator:
        self._require_built()
        return self._context_validator  # type: ignore[return-value]

    @property
    def context_compressor(self) -> TruncationContextCompressor:
        self._require_built()
        return self._context_compressor  # type: ignore[return-value]

    @property
    def pipeline(self) -> _LegacyPipeline:
        """Legacy 6-stage pipeline.  Prefer ``execution_runtime`` for new code."""
        self._require_built()
        return self._pipeline  # type: ignore[return-value]

    @property
    def health_reporter(self) -> HealthReporter:
        self._require_built()
        return self._health_reporter  # type: ignore[return-value]

    @property
    def logger(self) -> StructuredLogger:
        self._require_built()
        return self._logger  # type: ignore[return-value]

    # ── Provider Runtime accessors ─────────────────────────────────────────

    @property
    def event_bus(self) -> AIEventBus:
        """Typed AI event bus (subscribe / publish runtime events)."""
        self._require_built()
        return self._event_bus  # type: ignore[return-value]

    @property
    def runtime_metrics(self) -> RuntimeMetrics:
        """Platform-wide runtime metrics aggregator."""
        self._require_built()
        return self._runtime_metrics  # type: ignore[return-value]

    @property
    def cost_tracker(self) -> CostTracker:
        """Per-container cost accumulator (placeholder until A2 injects rates)."""
        self._require_built()
        return self._cost_tracker  # type: ignore[return-value]

    @property
    def provider_runtime(self) -> AIProviderRuntime:
        """Provider lifecycle runtime (register/deregister AI providers)."""
        self._require_built()
        return self._provider_runtime  # type: ignore[return-value]

    @property
    def execution_runtime(self) -> ExecutionRuntime:
        """
        8-stage execution runtime.

        Must be initialized and started before calling ``.execute()``:

            container.execution_runtime.initialize()
            container.execution_runtime.start()
            response, ctx = container.execution_runtime.execute(exec_request)
        """
        self._require_built()
        return self._execution_runtime  # type: ignore[return-value]

    # ── Convenience ───────────────────────────────────────────────────────────

    def is_built(self) -> bool:
        return self._built

    def __repr__(self) -> str:
        return (
            f"<AIContainer built={self._built} "
            f"runtime={self._execution_runtime.lifecycle_state.value if self._execution_runtime else 'none'}>"
        )
