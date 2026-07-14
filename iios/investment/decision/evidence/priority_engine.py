"""iios/investment/decision/evidence/priority_engine.py
PriorityEngine — assigns a numeric priority score to each evidence item.
"""
from __future__ import annotations

from typing import List

from iios.investment.decision.evidence.evidence_item import EvidenceItem


class PriorityEngine:
    """
    Computes a composite priority score (0–100) for each EvidenceItem.
    Input items are not mutated; a sorted list is returned.
    """

    # Weight factors
    _PRIORITY_WEIGHT  = 0.50
    _REQUIRED_WEIGHT  = 0.20
    _CONFIDENCE_WEIGHT = 0.15
    _FRESHNESS_WEIGHT  = 0.15

    def score(self, item: EvidenceItem) -> float:
        prio  = item.priority.numeric / 5.0 * 100.0          # 0–100
        req   = 100.0 if item.is_required else 50.0
        conf  = item.confidence                               # 0–100
        fresh = item.freshness_score * 100.0                  # 0–100

        return round(
            prio  * self._PRIORITY_WEIGHT
            + req   * self._REQUIRED_WEIGHT
            + conf  * self._CONFIDENCE_WEIGHT
            + fresh * self._FRESHNESS_WEIGHT,
            2,
        )

    def rank(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Return items sorted by descending priority score."""
        return sorted(items, key=lambda i: self.score(i), reverse=True)
