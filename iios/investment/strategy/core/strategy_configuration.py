"""iios/investment/strategy/core/strategy_configuration.py
Institutional strategy configuration system.
Provides parameter specs, runtime configuration, and override support.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class ConfigurationError(Exception):
    """Raised when strategy configuration is invalid."""


@dataclass
class ParameterSpec:
    """Specification for a single configuration parameter."""
    name: str
    type: type                                  # int, float, str, bool, list, dict
    default: Any = None
    required: bool = False
    min_value: Optional[float] = None          # numeric range (lower bound, inclusive)
    max_value: Optional[float] = None          # numeric range (upper bound, inclusive)
    choices: Optional[List[Any]] = None        # enum-like restriction
    description: str = ""

    def validate(self, value: Any) -> Any:
        """Validate and coerce a value against this spec. Returns coerced value."""
        if value is None:
            if self.required:
                raise ConfigurationError(f"Parameter '{self.name}' is required.")
            return self.default

        if not isinstance(value, self.type):
            try:
                value = self.type(value)
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(
                    f"Parameter '{self.name}' must be {self.type.__name__}: {exc}"
                ) from exc

        if self.min_value is not None and isinstance(value, (int, float)):
            if value < self.min_value:
                raise ConfigurationError(
                    f"Parameter '{self.name}' = {value} is below minimum {self.min_value}."
                )
        if self.max_value is not None and isinstance(value, (int, float)):
            if value > self.max_value:
                raise ConfigurationError(
                    f"Parameter '{self.name}' = {value} exceeds maximum {self.max_value}."
                )
        if self.choices is not None and value not in self.choices:
            raise ConfigurationError(
                f"Parameter '{self.name}' = {value!r} not in choices {self.choices}."
            )
        return value


@dataclass
class StrategyConfiguration:
    """
    Runtime configuration for an institutional strategy instance.
    Supports profiles, environment-specific overrides, and parameter versioning.
    """
    strategy_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    profile: str = "default"
    environment: str = "paper"           # paper | live | backtest
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _overrides: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a parameter value, respecting runtime overrides."""
        if key in self._overrides:
            return self._overrides[key]
        return self.parameters.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.parameters[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def override(self, key: str, value: Any) -> None:
        """Apply a runtime override (highest precedence, ephemeral)."""
        self._overrides[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def clear_override(self, key: str) -> None:
        self._overrides.pop(key, None)

    def clear_all_overrides(self) -> None:
        self._overrides.clear()

    def all_parameters(self) -> Dict[str, Any]:
        """Merged view: base parameters + active overrides."""
        merged = copy.copy(self.parameters)
        merged.update(self._overrides)
        return merged

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "profile": self.profile,
            "environment": self.environment,
            "version": self.version,
            "parameters": self.all_parameters(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def copy_with(self, **updates: Any) -> "StrategyConfiguration":
        """Return a deep copy with specified fields updated."""
        cloned = copy.deepcopy(self)
        for k, v in updates.items():
            setattr(cloned, k, v)
        return cloned
