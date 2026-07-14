"""iios/investment/decision/core/parameter_validation.py
ParameterRule and ParameterValidator — validate configuration parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ValidationResult:
    key:     str
    value:   Any
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key":     self.key,
            "value":   self.value,
            "passed":  self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class ParameterRule:
    """A single validation rule for one parameter."""
    rule_id:   str
    rule_name: str
    predicate: Callable[[Any], bool]  # returns True if value is valid
    message:   str                    # shown when predicate returns False

    def check(self, key: str, value: Any) -> ValidationResult:
        try:
            passed = self.predicate(value)
        except Exception:
            passed = False
        return ValidationResult(
            key=key,
            value=value,
            passed=passed,
            message="" if passed else self.message,
        )


# Built-in rules
def _range_rule(min_val: float, max_val: float) -> ParameterRule:
    return ParameterRule(
        rule_id=f"range_{min_val}_{max_val}",
        rule_name=f"range [{min_val}, {max_val}]",
        predicate=lambda v: min_val <= float(v) <= max_val,
        message=f"Value must be between {min_val} and {max_val}.",
    )


def _positive_rule() -> ParameterRule:
    return ParameterRule(
        rule_id="positive",
        rule_name="positive",
        predicate=lambda v: float(v) > 0,
        message="Value must be positive.",
    )


def _non_negative_rule() -> ParameterRule:
    return ParameterRule(
        rule_id="non_negative",
        rule_name="non-negative",
        predicate=lambda v: float(v) >= 0,
        message="Value must be non-negative.",
    )


def _type_rule(expected_type) -> ParameterRule:
    return ParameterRule(
        rule_id=f"type_{expected_type.__name__}",
        rule_name=f"type:{expected_type.__name__}",
        predicate=lambda v: isinstance(v, expected_type),
        message=f"Value must be of type {expected_type.__name__}.",
    )


class ParameterValidator:
    """Applies a set of ParameterRules to a key/value pair."""

    def __init__(self) -> None:
        self._rules: Dict[str, List[ParameterRule]] = {}

    def add_rule(self, key: str, rule: ParameterRule) -> None:
        self._rules.setdefault(key, []).append(rule)

    def add_range(self, key: str, min_val: float, max_val: float) -> None:
        self.add_rule(key, _range_rule(min_val, max_val))

    def add_positive(self, key: str) -> None:
        self.add_rule(key, _positive_rule())

    def add_type(self, key: str, expected_type) -> None:
        self.add_rule(key, _type_rule(expected_type))

    def validate(self, key: str, value: Any) -> List[ValidationResult]:
        rules = self._rules.get(key, [])
        return [r.check(key, value) for r in rules]

    def validate_all(self, params: Dict[str, Any]) -> Dict[str, List[ValidationResult]]:
        return {k: self.validate(k, v) for k, v in params.items()}

    def is_valid(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Returns (all_valid, list_of_failure_messages)."""
        failures = []
        for key, value in params.items():
            for result in self.validate(key, value):
                if not result.passed:
                    failures.append(f"{key}: {result.message}")
        return len(failures) == 0, failures
