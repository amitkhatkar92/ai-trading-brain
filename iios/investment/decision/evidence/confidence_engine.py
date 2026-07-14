"""iios/investment/decision/evidence/confidence_engine.py
ConfidenceEngine — normalises and adjusts item confidence scores.
"""
from __future__ import annotations

from typing import List

from iios.investment.decision.evidence.evidence_constants import MIN_CONFIDENCE_THRESHOLD
from iios.investment.decision.evidence.evidence_item import EvidenceItem


class ConfidenceEngine:
    """
    Normalises confidence scores and filters out low-confidence items.
    Adjusts confidence based on freshness decay.
    """

    def __init__(self, min_threshold: float = MIN_CONFIDENCE_THRESHOLD) -> None:
        self._min = min_threshold

    def adjust(self, item: EvidenceItem) -> float:
        """
        Adjusted confidence = confidence * freshness_score (freshness acts as multiplier).
        Result clamped to [0, 100].
        """
        adjusted = item.confidence * item.freshness_score
        return round(min(100.0, max(0.0, adjusted)), 2)

    def filter_low_confidence(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Remove items whose adjusted confidence falls below the threshold."""
        return [i for i in items if self.adjust(i) >= self._min]

    def rank(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        return sorted(items, key=lambda i: self.adjust(i), reverse=True)
