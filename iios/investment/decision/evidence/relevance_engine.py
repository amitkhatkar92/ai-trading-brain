"""iios/investment/decision/evidence/relevance_engine.py
RelevanceEngine — scores how relevant an evidence item is to the decision subject.
"""
from __future__ import annotations

from typing import List

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.evidence.evidence_item import EvidenceItem


# Source-type weights per subject_type
_EQUITY_WEIGHTS = {
    EvidenceSourceType.MARKET:    1.5,
    EvidenceSourceType.COMPANY:   1.5,
    EvidenceSourceType.STRATEGY:  1.3,
    EvidenceSourceType.RISK:      1.4,
    EvidenceSourceType.KNOWLEDGE: 0.9,
    EvidenceSourceType.RESEARCH:  1.0,
    EvidenceSourceType.HISTORICAL: 0.7,
    EvidenceSourceType.EXTERNAL:  0.5,
}
_PORTFOLIO_WEIGHTS = {
    EvidenceSourceType.MARKET:    1.2,
    EvidenceSourceType.COMPANY:   0.7,
    EvidenceSourceType.STRATEGY:  1.4,
    EvidenceSourceType.RISK:      1.6,
    EvidenceSourceType.KNOWLEDGE: 0.8,
    EvidenceSourceType.RESEARCH:  0.8,
    EvidenceSourceType.HISTORICAL: 0.9,
    EvidenceSourceType.EXTERNAL:  0.5,
}
_DEFAULT_WEIGHTS = {st: 1.0 for st in EvidenceSourceType}


class RelevanceEngine:
    """Computes a relevance score (0–100) based on subject_type and source_type."""

    def score(self, item: EvidenceItem) -> float:
        weights = {
            "equity":    _EQUITY_WEIGHTS,
            "portfolio": _PORTFOLIO_WEIGHTS,
        }.get(item.subject_type.lower(), _DEFAULT_WEIGHTS)

        w = weights.get(item.source_type, 1.0)
        raw = item.confidence * w
        return round(min(100.0, raw), 2)

    def rank(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        return sorted(items, key=lambda i: self.score(i), reverse=True)
