"""iios/investment/portfolio/integration/conflict_classifier.py

Classifies detected conflicts by category and sets action_required flag.
"""
from __future__ import annotations

from typing import Any, Dict, List

from iios.investment.portfolio.integration.conflict_detector import DetectedConflict
from iios.investment.portfolio.integration.integration_types import ConflictSeverity


_CATEGORY_DESCRIPTIONS: Dict[str, str] = {
    "direction_conflict":      "Engines are giving opposing directional signals",
    "value_mismatch":          "Engines report significantly different values for the same metric",
    "internal_inconsistency":  "An engine's internal data is self-contradictory",
    "stale_vs_fresh":          "One engine's data is significantly older than another's",
    "threshold_violation":     "A value exceeds an institutional governance threshold",
}

_SEVERITY_ORDER: Dict[ConflictSeverity, int] = {
    ConflictSeverity.CRITICAL: 0,
    ConflictSeverity.HIGH:     1,
    ConflictSeverity.MEDIUM:   2,
    ConflictSeverity.LOW:      3,
    ConflictSeverity.INFO:     4,
}


class ClassifiedConflict:
    """Wraps a DetectedConflict with classification metadata."""

    def __init__(
        self,
        conflict:        DetectedConflict,
        category:        str,
        category_desc:   str,
        action_required: bool,
    ) -> None:
        self.conflict        = conflict
        self.category        = category
        self.category_desc   = category_desc
        self.action_required = action_required

    @property
    def conflict_id(self) -> str:
        return self.conflict.conflict_id

    @property
    def severity(self) -> ConflictSeverity:
        return self.conflict.severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.conflict.to_dict(),
            "category":        self.category,
            "category_desc":   self.category_desc,
            "action_required": self.action_required,
        }


class ConflictClassifier:
    """Assigns category descriptions and action flags to detected conflicts."""

    def classify(
        self,
        conflicts: List[DetectedConflict],
    ) -> List[ClassifiedConflict]:
        classified: List[ClassifiedConflict] = []
        for conflict in conflicts:
            cat  = conflict.conflict_type
            desc = _CATEGORY_DESCRIPTIONS.get(cat, f"Unknown conflict type: {cat}")
            act  = conflict.severity in (ConflictSeverity.CRITICAL, ConflictSeverity.HIGH)
            classified.append(ClassifiedConflict(
                conflict        = conflict,
                category        = cat,
                category_desc   = desc,
                action_required = act,
            ))
        # Highest severity first
        classified.sort(key=lambda c: _SEVERITY_ORDER.get(c.severity, 99))
        return classified
