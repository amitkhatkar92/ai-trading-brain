"""iios/investment/strategy/core/configuration_engine.py
Configuration engine: orchestrates parameter declaration, validation, and versioning.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .configuration_version import ConfigurationVersionStore
from .parameter_registry import ParameterRegistry
from .parameter_validation import ParameterValidator, ValidationResult
from .strategy_configuration import ConfigurationError, ParameterSpec, StrategyConfiguration

logger = logging.getLogger(__name__)


class ConfigurationEngine:
    """
    Central configuration service for the institutional strategy framework.
    Combines ParameterRegistry + ParameterValidator + ConfigurationVersionStore
    into a single cohesive API.
    """

    def __init__(self, max_versions: int = 20) -> None:
        self._param_registry = ParameterRegistry()
        self._validator = ParameterValidator(self._param_registry)
        self._version_store = ConfigurationVersionStore(max_versions=max_versions)

    # ── Parameter declaration ─────────────────────────────────────────────────

    def declare_parameter(
        self, strategy_id: str, spec: ParameterSpec
    ) -> None:
        self._param_registry.register(strategy_id, spec)

    def declare_parameters(
        self, strategy_id: str, specs: List[ParameterSpec]
    ) -> None:
        self._param_registry.register_all(strategy_id, specs)

    # ── Configuration lifecycle ───────────────────────────────────────────────

    def build(
        self,
        strategy_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        profile: str = "default",
        environment: str = "paper",
    ) -> StrategyConfiguration:
        """Build a new configuration seeded from declared spec defaults."""
        specs = self._param_registry.specs_for(strategy_id)
        params: Dict[str, Any] = {
            name: spec.default
            for name, spec in specs.items()
            if spec.default is not None
        }
        if parameters:
            params.update(parameters)

        return StrategyConfiguration(
            strategy_id=strategy_id,
            parameters=params,
            profile=profile,
            environment=environment,
        )

    def validate(self, config: StrategyConfiguration) -> ValidationResult:
        return self._validator.validate(config)

    def validate_strict(self, config: StrategyConfiguration) -> None:
        self._validator.validate_strict(config)

    def apply(
        self,
        config: StrategyConfiguration,
        reason: str = "",
        validate: bool = True,
    ) -> StrategyConfiguration:
        """
        Optionally validate, persist a versioned snapshot, and return config.
        Raises ConfigurationError on validation failure when validate=True.
        """
        if validate:
            result = self._validator.validate_and_apply(config)
            if not result.passed:
                raise ConfigurationError(
                    f"Configuration for '{config.strategy_id}' invalid: "
                    + "; ".join(result.errors)
                )

        self._version_store.save(config, reason=reason)
        logger.info(
            "Applied config v%d for strategy '%s'",
            self._version_store.current_version_number(config.strategy_id),
            config.strategy_id,
        )
        return config

    def update_parameter(
        self,
        config: StrategyConfiguration,
        key: str,
        value: Any,
        reason: str = "",
    ) -> StrategyConfiguration:
        """Update a single parameter and persist a new version."""
        config.set(key, value)
        return self.apply(
            config,
            reason=reason or f"Updated '{key}'",
            validate=True,
        )

    # ── History ───────────────────────────────────────────────────────────────

    def config_history(self, strategy_id: str, n: int = 10):
        return self._version_store.history(strategy_id, n)

    def latest_config(
        self, strategy_id: str
    ) -> Optional[StrategyConfiguration]:
        cv = self._version_store.latest(strategy_id)
        return cv.config if cv else None

    def current_version(self, strategy_id: str) -> int:
        return self._version_store.current_version_number(strategy_id)

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def parameter_registry(self) -> ParameterRegistry:
        return self._param_registry
