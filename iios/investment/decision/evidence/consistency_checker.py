"""iios/investment/decision/evidence/consistency_checker.py
ConsistencyChecker — detects conflicting evidence items.
Two items conflict when they share the same key but have very different numeric values.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.evidence.evidence_item import EvidenceItem


@dataclass(frozen=True)
class Conflict:
    key:          str
    item_a_id:    str
    item_b_id:    str
    value_a:      Any
    value_b:      Any
    deviation_pct: float     # % deviation between the two numeric values


@dataclass(frozen=True)
class ConsistencyReport:
    total_checked:    int
    conflict_count:   int
    conflicts:        Tuple[Conflict, ...]
    consistency_score: float   # 0–100 (100 = no conflicts)

    @property
    def is_acceptable(self) -> bool:
        return self.conflict_count == 0 or self.consistency_score >= 60.0


class ConsistencyChecker:
    """Flags pairs of evidence items with the same key but divergent numeric values."""

    def __init__(self, tolerance_pct: float = 15.0) -> None:
        self._tolerance = tolerance_pct  # % difference considered a conflict

    def check(self, items: List[EvidenceItem]) -> ConsistencyReport:
        by_key: Dict[str, List[EvidenceItem]] = {}
        for item in items:
            by_key.setdefault(item.key, []).append(item)

        conflicts: List[Conflict] = []
        total_pairs = 0

        for key, group in by_key.items():
            if len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    conflict = self._compare(a, b)
                    total_pairs += 1
                    if conflict:
                        conflicts.append(conflict)

        penalty = 20.0 * len(conflicts)
        score   = max(0.0, 100.0 - penalty)

        return ConsistencyReport(
            total_checked=total_pairs,
            conflict_count=len(conflicts),
            conflicts=tuple(conflicts),
            consistency_score=round(score, 2),
        )

    def _compare(self, a: EvidenceItem, b: EvidenceItem) -> Conflict | None:
        try:
            va = float(a.value)
            vb = float(b.value)
        except (TypeError, ValueError):
            return None  # non-numeric values skipped

        avg = (abs(va) + abs(vb)) / 2.0
        if avg == 0.0:
            return None
        dev = abs(va - vb) / avg * 100.0
        if dev > self._tolerance:
            return Conflict(
                key=a.key,
                item_a_id=a.evidence_id,
                item_b_id=b.evidence_id,
                value_a=a.value,
                value_b=b.value,
                deviation_pct=round(dev, 2),
            )
        return None
