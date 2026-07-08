"""
iios/intelligence/reasoning/evidence/evidence_ranker.py
=======================================================
Ranks evidence items by composite quality score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import EvidenceStatus
from .evidence_registry import Evidence


@dataclass
class RankedEvidence:
    evidence_id:     str
    rank:            int
    score:           float
    strength_score:  float
    confidence_score: float
    freshness_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id":      self.evidence_id,
            "rank":             self.rank,
            "score":            round(self.score, 4),
            "strength_score":   round(self.strength_score, 4),
            "confidence_score": round(self.confidence_score, 4),
            "freshness_score":  round(self.freshness_score, 4),
        }


class EvidenceRanker:
    """
    Ranks evidence items by a weighted composite score.

    Score = w_strength × (strength / 5)
          + w_confidence × confidence
          + w_freshness × freshness_score
    """

    DEFAULT_W_STRENGTH   = 0.40
    DEFAULT_W_CONFIDENCE = 0.40
    DEFAULT_W_FRESHNESS  = 0.20

    def rank(
        self,
        items: list[Evidence],
        *,
        w_strength:   float = DEFAULT_W_STRENGTH,
        w_confidence: float = DEFAULT_W_CONFIDENCE,
        w_freshness:  float = DEFAULT_W_FRESHNESS,
        valid_only:   bool  = False,
        top_n:        int   | None = None,
    ) -> list[RankedEvidence]:
        """
        Return items sorted by descending composite score.

        Parameters
        ----------
        items        : Evidence list to rank.
        w_strength   : Weight for evidence strength component.
        w_confidence : Weight for source confidence component.
        w_freshness  : Weight for recency component.
        valid_only   : If True, skip INVALID evidence.
        top_n        : If set, return only the top *n* results.
        """
        if not items:
            return []

        if valid_only:
            items = [e for e in items if e.status != EvidenceStatus.INVALID]

        import time
        now = time.time()
        oldest = min(e.created_at for e in items) if items else now
        newest = max(e.created_at for e in items) if items else now
        age_range = max(newest - oldest, 1.0)

        scored: list[tuple[float, Evidence]] = []
        for e in items:
            s_score = e.numeric_strength / 5.0
            c_score = max(0.0, min(1.0, e.confidence))
            f_score = (e.created_at - oldest) / age_range  # 0=oldest, 1=newest
            total   = (
                w_strength   * s_score
                + w_confidence * c_score
                + w_freshness  * f_score
            )
            scored.append((total, e))

        scored.sort(key=lambda t: t[0], reverse=True)

        results = [
            RankedEvidence(
                evidence_id      = e.evidence_id,
                rank             = i + 1,
                score            = score,
                strength_score   = e.numeric_strength / 5.0,
                confidence_score = max(0.0, min(1.0, e.confidence)),
                freshness_score  = (e.created_at - oldest) / age_range,
            )
            for i, (score, e) in enumerate(scored)
        ]

        return results[:top_n] if top_n is not None else results
