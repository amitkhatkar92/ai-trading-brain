"""iios/investment/decision/risk/concentration_analysis.py
ConcentrationAnalyzer — measures evidence-source concentration risk.
Uses Herfindahl-Hirschman Index (HHI) as concentration measure.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot


@dataclass(frozen=True)
class ConcentrationResult:
    source_count:        int       # number of distinct evidence sources
    herfindahl_index:    float     # 0–1 (1 = complete concentration)
    concentration_score: float     # 0–100 risk score
    dominant_source:     str       # source with highest fraction of evidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_count":        self.source_count,
            "herfindahl_index":    round(self.herfindahl_index, 4),
            "concentration_score": round(self.concentration_score, 2),
            "dominant_source":     self.dominant_source,
        }


class ConcentrationAnalyzer:
    """
    Derives evidence concentration risk from EvidenceSnapshot.
    High HHI (single source dominates) → high concentration risk.
    """

    def analyze(self, snapshot: EvidenceSnapshot) -> ConcentrationResult:
        items = snapshot.items
        if not items:
            return ConcentrationResult(
                source_count=0, herfindahl_index=1.0,
                concentration_score=100.0, dominant_source="none",
            )

        # Aggregate by source type
        counts = Counter(i.source_type.value for i in items)
        total  = len(items)
        hhi    = sum((c / total) ** 2 for c in counts.values())

        dominant = counts.most_common(1)[0][0]

        # Minimum HHI for a perfectly diversified n-source set = 1/n
        n   = len(counts)
        min_hhi = 1.0 / n if n > 0 else 1.0
        # Normalise concentration risk: 0 = perfectly even, 100 = all one source
        normalised = (hhi - min_hhi) / max(1.0 - min_hhi, 1e-9)
        concentration_score = min(100.0, max(0.0, normalised * 100.0))

        return ConcentrationResult(
            source_count=n,
            herfindahl_index=round(hhi, 6),
            concentration_score=round(concentration_score, 4),
            dominant_source=dominant,
        )
