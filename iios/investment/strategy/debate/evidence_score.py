"""iios/investment/strategy/debate/evidence_score.py
Evidence scoring and composite weight computation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from iios.investment.strategy.debate.debate_constants import (
    EvidenceReliability,
    EvidenceWeight,
)


@dataclass(frozen=True)
class EvidenceScore:
    """Computed composite score for a single piece of evidence."""
    evidence_id:    str
    raw_score:      float   # 0–100  (how bullish/bearish the signal is)
    reliability:    float   # 0–1    (source trustworthiness)
    recency:        float   # 0–1    (freshness)
    relevance:      float   # 0–1    (how relevant to current context)
    weight:         float   # weight multiplier from EvidenceWeight
    weighted_score: float   # final composite 0–100

    def to_dict(self) -> dict:
        return {
            "evidence_id":    self.evidence_id,
            "raw_score":      round(self.raw_score, 2),
            "reliability":    round(self.reliability, 3),
            "recency":        round(self.recency, 3),
            "relevance":      round(self.relevance, 3),
            "weight":         round(self.weight, 3),
            "weighted_score": round(self.weighted_score, 2),
        }


# ── Recency decay ─────────────────────────────────────────────────────────────
def _recency_score(evidence_ts: Optional[datetime], decay_hours: float = 24.0) -> float:
    """Linear decay from 1.0 (now) to 0.1 (decay_hours old)."""
    if evidence_ts is None:
        return 0.5
    age = (datetime.now(timezone.utc) - evidence_ts).total_seconds() / 3600
    score = max(0.1, 1.0 - (age / decay_hours) * 0.9)
    return round(min(score, 1.0), 4)


def compute_evidence_score(
    evidence_id:   str,
    raw_score:     float,
    reliability:   EvidenceReliability,
    weight:        EvidenceWeight,
    evidence_ts:   Optional[datetime] = None,
    relevance:     float = 0.7,
    decay_hours:   float = 24.0,
) -> EvidenceScore:
    """
    Compute a composite EvidenceScore.

    weighted_score = raw_score × (0.40×reliability + 0.30×recency + 0.30×relevance) × weight_multiplier
    Result is capped at 100.
    """
    rel_val    = reliability.score
    rec_val    = _recency_score(evidence_ts, decay_hours)
    rel_capped = min(max(relevance, 0.0), 1.0)
    composite  = 0.40 * rel_val + 0.30 * rec_val + 0.30 * rel_capped
    w          = weight.multiplier
    weighted   = min(raw_score * composite * w, 100.0)

    return EvidenceScore(
        evidence_id=evidence_id,
        raw_score=round(raw_score, 2),
        reliability=round(rel_val, 4),
        recency=round(rec_val, 4),
        relevance=round(rel_capped, 4),
        weight=round(w, 4),
        weighted_score=round(weighted, 2),
    )
