"""
configuration_loader.py -- iios.ai.model_management.configuration
===================================================================
:class:`ConfigurationLoader` — loads per-model configurations and global
runtime settings.  Supports dependency injection via overrides.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from typing import Dict, Optional

from .model_configuration import ModelConfiguration
from .runtime_settings    import RuntimeSettings


class ConfigurationLoader:
    """
    Loads :class:`ModelConfiguration` and :class:`RuntimeSettings`.

    Usage::

        loader = ConfigurationLoader()
        loader.with_override(ModelConfiguration("my-model-id", timeout_ms=5_000))
        config = loader.load_for_model("my-model-id")
    """

    def __init__(self, runtime_settings: Optional[RuntimeSettings] = None) -> None:
        self._runtime: RuntimeSettings              = runtime_settings or RuntimeSettings()
        self._overrides: Dict[str, ModelConfiguration] = {}

    def load_for_model(self, model_id: str) -> ModelConfiguration:
        """Return per-model config; defaults if no override exists."""
        if model_id in self._overrides:
            return self._overrides[model_id]
        return ModelConfiguration(
            model_id    = model_id,
            timeout_ms  = self._runtime.default_timeout_ms,
            retry_count = self._runtime.max_retries,
        )

    def load_runtime_settings(self) -> RuntimeSettings:
        """Return the global runtime settings."""
        return self._runtime

    def with_override(self, config: ModelConfiguration) -> "ConfigurationLoader":
        """Register a per-model config override; returns self for chaining."""
        self._overrides[config.model_id] = config
        return self
