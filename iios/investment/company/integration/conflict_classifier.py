"""iios/investment/company/integration/conflict_classifier.py
Classifies conflict severity and assigns resolution priority.
"""
from __future__ import annotations

from typing import List

from iios.investment.company.integration.company_state import (
    ConflictSeverity, ConflictType,
)
from iios.investment.company.integration.conflict_detector import ConflictRecord


# Priority weights for resolution ordering (higher = resolve first)
_SEVERITY_PRIORITY: dict = {
    ConflictSeverity.CRITICAL: 4,
    ConflictSeverity.HIGH:     3,
    ConflictSeverity.MEDIUM:   2,
    ConflictSeverity.LOW:      1,
    ConflictSeverity.INFO:     0,
}


def classify_severity(conflict: ConflictRecord) -> ConflictSeverity:
    """
    Re-classify the severity of a conflict based on its type and engine pair.
    Allows post-detection severity tuning without changing detection logic.
    """
    if conflict.conflict_type == ConflictType.SIGNAL_CONFLICT:
        # Signal conflicts between core engines are always at least HIGH
        core_engines = {"financials", "earnings", "business_quality"}
        if conflict.engine_a in core_engines and conflict.engine_b in core_engines:
            return max_severity(conflict.severity, ConflictSeverity.HIGH)

    if conflict.conflict_type == ConflictType.SCORE_DIVERGENCE:
        # Divergence between high-confidence core engines → upgrade severity
        if (conflict.engine_a == "financials" and conflict.engine_b == "earnings"):
            return max_severity(conflict.severity, ConflictSeverity.MEDIUM)

    return conflict.severity


def max_severity(a: ConflictSeverity, b: ConflictSeverity) -> ConflictSeverity:
    """Return the more severe of two ConflictSeverity values."""
    return a if _SEVERITY_PRIORITY[a] >= _SEVERITY_PRIORITY[b] else b


def priority_score(conflict: ConflictRecord) -> int:
    """Numeric resolution priority (higher → resolve first)."""
    return _SEVERITY_PRIORITY.get(conflict.severity, 0)


def sort_by_priority(conflicts: List[ConflictRecord]) -> List[ConflictRecord]:
    """Return *conflicts* sorted from highest to lowest priority."""
    return sorted(conflicts, key=priority_score, reverse=True)


def count_critical(conflicts: List[ConflictRecord]) -> int:
    return sum(1 for c in conflicts if c.severity == ConflictSeverity.CRITICAL)


def count_high(conflicts: List[ConflictRecord]) -> int:
    return sum(1 for c in conflicts if c.severity == ConflictSeverity.HIGH)


def conflict_summary(conflicts: List[ConflictRecord]) -> str:
    """One-line human-readable summary of detected conflicts."""
    if not conflicts:
        return "No conflicts detected."
    crit = count_critical(conflicts)
    high = count_high(conflicts)
    total = len(conflicts)
    parts = [f"{total} conflict(s)"]
    if crit:
        parts.append(f"{crit} critical")
    if high:
        parts.append(f"{high} high-severity")
    return ", ".join(parts) + "."


def reclassify_all(conflicts: List[ConflictRecord]) -> List[ConflictRecord]:
    """Apply severity reclassification to every conflict in *conflicts*."""
    for c in conflicts:
        c.severity = classify_severity(c)
    return conflicts
