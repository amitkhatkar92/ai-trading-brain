"""iios/investment/strategy/core/parameter_validation.py
Validates strategy configuration parameters against registered specs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .parameter_registry import ParameterRegistry
from .strategy_configuration import ConfigurationError, StrategyConfiguration


@dataclass
class ValidationResult:
    """Outcome of a parameter validation run."""
    strategy_id: str
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    coerced: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "coerced_count": len(self.coerced),
        }


class ParameterValidator:
    """
    Validates and coerces parameters in a StrategyConfiguration
    against specs stored in the ParameterRegistry.
    """

    def __init__(self, registry: ParameterRegistry) -> None:
        self._registry = registry

    def validate(self, config: StrategyConfiguration) -> ValidationResult:
        sid = config.strategy_id
        result = ValidationResult(strategy_id=sid)
        specs = self._registry.specs_for(sid)
        params = config.all_parameters()

        for name, spec in specs.items():
            value = params.get(name)
            try:
                coerced = spec.validate(value)
                if coerced is not None and coerced != value:
                    result.coerced[name] = coerced
            except ConfigurationError as exc:
                result.add_error(str(exc))

        for name in params:
            if name not in specs:
                result.add_warning(
                    f"Unknown parameter '{name}' for strategy '{sid}'."
                )

        return result

    def validate_and_apply(
        self, config: StrategyConfiguration
    ) -> ValidationResult:
        """Validate, then write coerced values back to config."""
        result = self.validate(config)
        for name, value in result.coerced.items():
            config.set(name, value)
        return result

    def validate_strict(self, config: StrategyConfiguration) -> None:
        """Validate and raise ConfigurationError if any errors exist."""
        result = self.validate(config)
        if not result.passed:
            raise ConfigurationError(
                f"Configuration for '{config.strategy_id}' invalid: "
                + "; ".join(result.errors)
            )
