"""iios/investment/strategy/debate/evidence_validator.py
Validates evidence before it enters the EvidenceRegistry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from iios.investment.strategy.debate.evidence_registry import Evidence


@dataclass(frozen=True)
class ValidationResult:
    is_valid:  bool
    issues:    Tuple[str, ...]
    warnings:  Tuple[str, ...]


class EvidenceValidator:
    """
    Validates evidence items for completeness and consistency.
    Rejects evidence that would corrupt the debate.
    """

    def validate(self, evidence: Evidence) -> ValidationResult:
        issues:   List[str] = []
        warnings: List[str] = []

        if not evidence.evidence_id:
            issues.append("evidence_id is empty")
        if not evidence.session_id:
            issues.append("session_id is empty")
        if not evidence.title:
            issues.append("title is empty")
        if not evidence.description:
            issues.append("description is empty")
        if not (0.0 <= evidence.raw_score <= 100.0):
            issues.append(f"raw_score {evidence.raw_score} out of [0, 100]")
        if not (0.0 <= evidence.relevance <= 1.0):
            issues.append(f"relevance {evidence.relevance} out of [0, 1]")

        # Warnings (not blocking)
        if evidence.evidence_ts is None:
            warnings.append("evidence_ts is None — recency score will be neutral")
        if evidence.raw_score == 50.0:
            warnings.append("raw_score is exactly 50 — evidence is directionally neutral")
        if evidence.relevance < 0.2:
            warnings.append(f"relevance {evidence.relevance:.2f} is very low")

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=tuple(issues),
            warnings=tuple(warnings),
        )

    def validate_all(self, items: List[Evidence]) -> Tuple[List[Evidence], List[Tuple[Evidence, ValidationResult]]]:
        """Returns (valid_items, rejected_items)."""
        valid: List[Evidence]                           = []
        rejected: List[Tuple[Evidence, ValidationResult]] = []
        for ev in items:
            result = self.validate(ev)
            if result.is_valid:
                valid.append(ev)
            else:
                rejected.append((ev, result))
        return valid, rejected
