"""features/feature_validator.py — Validates records against FeatureDefinitions."""
from __future__ import annotations

from typing import Any

from iios.integration.research.learning.features.feature_definition import FeatureDefinition
from iios.integration.research.learning.features.feature_registry   import FeatureRegistry


class FeatureValidator:
    """
    Validates individual records against a set of FeatureDefinitions.

    Can operate with an explicit list of definitions or by looking them up
    from a FeatureRegistry.
    """

    def __init__(
        self,
        registry: FeatureRegistry,
        required_names: list[str],
    ) -> None:
        self._registry       = registry
        self._required_names = required_names

    def validate_record(self, record: dict[str, Any]) -> list[str]:
        """Return all validation error messages for a single record."""
        errors: list[str] = []
        for name in self._required_names:
            if not self._registry.has_name(name):
                errors.append(f"Feature definition not found for '{name}'")
                continue
            feat_def = self._registry.get_by_name(name)
            val = record.get(name)
            errors.extend(feat_def.validate_value(val))
        return errors

    def validate_batch(
        self,
        records: list[dict[str, Any]],
        *,
        fail_fast: bool = False,
    ) -> dict[int, list[str]]:
        """Return {row_index: [errors]} for rows with validation errors."""
        result: dict[int, list[str]] = {}
        for i, rec in enumerate(records):
            errs = self.validate_record(rec)
            if errs:
                result[i] = errs
                if fail_fast:
                    return result
        return result

    def is_valid(self, record: dict[str, Any]) -> bool:
        return len(self.validate_record(record)) == 0
