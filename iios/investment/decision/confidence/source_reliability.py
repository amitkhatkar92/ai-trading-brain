"""iios/investment/decision/confidence/source_reliability.py
SourceReliabilityAnalyzer — assigns reliability scores to each evidence source type.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.evidence.evidence_item import EvidenceItem


# ── Baseline reliability scores per source type (0-100) ──────────────────────
_SOURCE_BASE_RELIABILITY: Dict[str, float] = {
    "market":     85.0,
    "company":    80.0,
    "strategy":   75.0,
    "risk":       88.0,
    "knowledge":  70.0,
    "research":   72.0,
    "historical": 78.0,
    "external":   60.0,
}


@dataclass(frozen=True)
class SourceReliabilityScore:
    source_type:      str
    base_reliability: float   # 0–100 prior from type
    item_count:       int
    avg_confidence:   float   # 0–100 average reported confidence of items
    freshness_bonus:  float   # 0–10 extra when all items are fresh
    final_score:      float   # 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type":      self.source_type,
            "base_reliability": round(self.base_reliability, 2),
            "item_count":       self.item_count,
            "avg_confidence":   round(self.avg_confidence, 2),
            "freshness_bonus":  round(self.freshness_bonus, 2),
            "final_score":      round(self.final_score, 2),
        }


class SourceReliabilityAnalyzer:
    """
    Computes per-source-type reliability from the items in an EvidenceSnapshot.
    Does NOT access markets or external systems.
    """

    def analyze(
        self,
        items: List[EvidenceItem],
    ) -> Tuple[List[SourceReliabilityScore], float]:
        """
        Returns (per_source_scores, overall_reliability_0_100).
        overall_reliability is the weighted average across sources
        where weight is proportional to source importance.
        """
        if not items:
            return [], 0.0

        by_source: Dict[str, List[EvidenceItem]] = {}
        for item in items:
            key = item.source_type.value
            by_source.setdefault(key, []).append(item)

        scores: List[SourceReliabilityScore] = []
        weighted_sum = 0.0
        weight_total = 0.0

        for src, src_items in by_source.items():
            base = _SOURCE_BASE_RELIABILITY.get(src, 65.0)
            avg_conf = statistics.mean(i.confidence for i in src_items)
            avg_fresh = statistics.mean(i.freshness_score for i in src_items)
            freshness_bonus = avg_fresh * 10.0   # up to +10

            # Blend base (60 %) with reported confidence (40 %)
            raw = base * 0.60 + avg_conf * 0.40
            final = min(100.0, max(0.0, raw + freshness_bonus))

            score = SourceReliabilityScore(
                source_type=src,
                base_reliability=base,
                item_count=len(src_items),
                avg_confidence=avg_conf,
                freshness_bonus=freshness_bonus,
                final_score=round(final, 4),
            )
            scores.append(score)

            # Weight by source weight from EvidenceSourceType
            try:
                src_enum = EvidenceSourceType(src)
                w = src_enum.default_weight
            except ValueError:
                w = 1.0
            weighted_sum += final * w
            weight_total += w

        overall = weighted_sum / weight_total if weight_total > 0 else 0.0
        return scores, round(overall, 4)
