"""iios/investment/decision/evidence/evidence_ranker.py
EvidenceRanker — orchestrates priority, relevance, and confidence ranking.
"""
from __future__ import annotations

from typing import List

from iios.investment.decision.evidence.evidence_item import EvidenceItem
from iios.investment.decision.evidence.priority_engine import PriorityEngine
from iios.investment.decision.evidence.relevance_engine import RelevanceEngine
from iios.investment.decision.evidence.confidence_engine import ConfidenceEngine


class EvidenceRanker:
    """
    Three-pass ranking:
      1. Filter low-confidence items (ConfidenceEngine)
      2. Compute composite score = priority * 0.40 + relevance * 0.30 + confidence * 0.30
      3. Return sorted descending
    """

    def __init__(
        self,
        priority_engine:   PriorityEngine  | None = None,
        relevance_engine:  RelevanceEngine | None = None,
        confidence_engine: ConfidenceEngine | None = None,
    ) -> None:
        self._priority   = priority_engine   or PriorityEngine()
        self._relevance  = relevance_engine  or RelevanceEngine()
        self._confidence = confidence_engine or ConfidenceEngine()

    def rank(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        # 1 — filter
        filtered = self._confidence.filter_low_confidence(items)

        # 2 — compute composite score
        def composite(item: EvidenceItem) -> float:
            p = self._priority.score(item)
            r = self._relevance.score(item)
            c = self._confidence.adjust(item)
            return p * 0.40 + r * 0.30 + c * 0.30

        # 3 — sort
        return sorted(filtered, key=composite, reverse=True)
