"""iios/decision_evaluation/criteria/criteria_validator.py"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..evaluation_context import Alternative
from .criterion import Criterion


@dataclass
class ValidationResult:
    valid:    bool
    errors:   list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"valid": self.valid, "errors": self.errors, "warnings": self.warnings}


class CriteriaValidator:
    """Validates criteria configuration before evaluation."""

    def validate_criteria(self, criteria: list[Criterion]) -> ValidationResult:
        errors:   list[str] = []
        warnings: list[str] = []

        if not criteria:
            errors.append("criteria list is empty")
            return ValidationResult(valid=False, errors=errors)

        seen_ids: set[str] = set()
        for c in criteria:
            if not c.criterion_id:
                errors.append("criterion with empty ID found")
            if c.criterion_id in seen_ids:
                errors.append(f"duplicate criterion ID: {c.criterion_id!r}")
            seen_ids.add(c.criterion_id)
            if c.weight <= 0:
                errors.append(f"criterion {c.criterion_id!r} has non-positive weight: {c.weight}")
            if not c.name:
                warnings.append(f"criterion {c.criterion_id!r} has no name")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_alternatives(self, alternatives: list[Alternative]) -> ValidationResult:
        errors:   list[str] = []
        warnings: list[str] = []

        if not alternatives:
            errors.append("alternatives list is empty")
            return ValidationResult(valid=False, errors=errors)

        seen_ids: set[str] = set()
        for a in alternatives:
            if a.alternative_id in seen_ids:
                errors.append(f"duplicate alternative ID: {a.alternative_id!r}")
            seen_ids.add(a.alternative_id)

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_weights(
        self,
        criterion_ids: list[str],
        weights:       dict[str, float],
    ) -> ValidationResult:
        errors:   list[str] = []
        warnings: list[str] = []

        for cid in criterion_ids:
            w = weights.get(cid, 0.0)
            if w < 0:
                errors.append(f"negative weight for criterion {cid!r}: {w}")

        total = sum(weights.get(cid, 0.0) for cid in criterion_ids)
        if criterion_ids and abs(total - 1.0) > 0.01:
            warnings.append(f"weights sum to {total:.4f} (expected 1.0)")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
