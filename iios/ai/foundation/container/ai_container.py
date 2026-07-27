"""
ai_container.py -- iios.ai.foundation.container
================================================
:class:`AIContainer` -- lightweight dependency injection container.

Wires all A1 AI Foundation infrastructure components together using
constructor injection.  No global singletons.

Usage::

    from iios.ai.foundation.container import AIContainer

    container = AIContainer()
    container.configure(loader=EnvironmentConfigurationLoader())
    container.build()

    session_manager = container.session_manager
    pipeline        = container.pipeline

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
from ..pipeline.execution_pipeline import ExecutionPipeline
from ..health.health_models     import HealthReporter
from ..observability.observability import StructuredLogger


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
    ) -> None:
        self._loader:           ConfigurationLoader      = loader or EnvironmentConfigurationLoader()
        self._config:           Optional[AIFrameworkConfiguration] = config
        self._provider_registry: Optional[Any]           = provider_registry
        self._runtime_config:   Optional[RuntimeConfiguration] = None

        # Lazily built components
        self._session_factory:  Optional[SessionFactory]     = None
        self._session_manager:  Optional[AISessionManager]   = None
        self._context_validator: Optional[ContextValidator]  = None
        self._context_compressor: Optional[TruncationContextCompressor] = None
        self._pipeline:         Optional[ExecutionPipeline]  = None
        self._health_reporter:  Optional[HealthReporter]     = None
        self._logger:           Optional[StructuredLogger]   = None
        self._built:            bool                         = False

    # ── Construction ──────────────────────────────────────────────────────────

    def build(self) -> "AIContainer":
        """
        Load configuration and construct all components.

        Must be called before accessing any component property.
        Returns ``self`` for chaining.
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
        self._pipeline           = ExecutionPipeline(
            provider_registry = self._provider_registry,
        )
        self._health_reporter    = HealthReporter(
            component = "iios:ai:foundation",
        )
        self._logger             = StructuredLogger(__name__)
        self._built              = True
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
    def pipeline(self) -> ExecutionPipeline:
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

    # ── Convenience ───────────────────────────────────────────────────────────

    def is_built(self) -> bool:
        return self._built

    def __repr__(self) -> str:
        return f"<AIContainer built={self._built}>"
