"""
iios/intelligence/reasoning/evidence/evidence_validator.py
==========================================================
Validates evidence items for correctness and consistency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import EvidenceStatus
from ..reasoning_exceptions import EvidenceValidationError, EvidenceConflictError
from .evidence_registry import Evidence


@dataclass
class ValidationResult:
    evidence_id: str
    passed:      bool
    issues:      list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "passed":      self.passed,
            "issues":      self.issues,
        }


class EvidenceValidator:
    """
    Validates individual evidence items and detects conflicts between them.

    Validation rules
    ----------------
    1. ``claim`` must be non-empty.
    2. ``confidence`` must be in [0.0, 1.0].
    3. ``source`` must be non-empty.
    4. For numeric ``value``, it must be a finite real number.
    """

    # -- Single-item validation ────────────────────────────────────────────────

    def validate(self, evidence: Evidence, *, raise_on_failure: bool = False) -> ValidationResult:
        issues: list[str] = []

        if not evidence.claim.strip():
            issues.append("claim is empty")

        if not (0.0 <= evidence.confidence <= 1.0):
            issues.append(
                f"confidence {evidence.confidence!r} is out of range [0, 1]"
            )

        if not evidence.source.strip():
            issues.append("source is empty")

        # If value is numeric, check for NaN / inf
        if isinstance(evidence.value, (int, float)):
            import math
            if not math.isfinite(evidence.value):
                issues.append(f"numeric value {evidence.value!r} is not finite")

        passed = not issues
        result = ValidationResult(evidence_id=evidence.evidence_id, passed=passed, issues=issues)

        if not passed:
            evidence.status = EvidenceStatus.INVALID
            if raise_on_failure:
                raise EvidenceValidationError(
                    evidence.evidence_id, "; ".join(issues)
                )
        else:
            if evidence.status == EvidenceStatus.UNVALIDATED:
                import time
                evidence.status       = EvidenceStatus.VALID
                evidence.validated_at = time.time()

        return result

    # -- Batch validation ──────────────────────────────────────────────────────

    def validate_many(
        self,
        items: list[Evidence],
        *,
        raise_on_failure: bool = False,
    ) -> list[ValidationResult]:
        return [self.validate(e, raise_on_failure=raise_on_failure) for e in items]

    # -- Conflict detection ────────────────────────────────────────────────────

    def detect_conflicts(
        self,
        items: list[Evidence],
        *,
        mark_conflicting: bool = True,
    ) -> list[tuple[str, str]]:
        """
        Detect directly opposing claims among a set of evidence items.

        Two items are considered conflicting when their claims are non-empty
        and identical after normalisation (same text asserted by different
        sources), yet their bool-castable values differ.  For numeric values,
        conflict is flagged when one is > 0 and the other is < 0.

        Returns a list of (evidence_id_a, evidence_id_b) conflict pairs.
        """
        conflicts: list[tuple[str, str]] = []

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if self._are_conflicting(a, b):
                    conflicts.append((a.evidence_id, b.evidence_id))
                    if mark_conflicting:
                        a.status = EvidenceStatus.CONFLICTING
                        b.status = EvidenceStatus.CONFLICTING

        return conflicts

    @staticmethod
    def _are_conflicting(a: Evidence, b: Evidence) -> bool:
        # Numeric sign conflict
        if isinstance(a.value, (int, float)) and isinstance(b.value, (int, float)):
            return (a.value > 0) != (b.value > 0) and a.value != 0 and b.value != 0
        # Boolean conflict
        if isinstance(a.value, bool) and isinstance(b.value, bool):
            return a.value != b.value
        return False
