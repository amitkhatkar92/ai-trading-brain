"""iios/investment/decision/confidence/freshness_analysis.py
FreshnessAnalyzer — quantifies evidence staleness using time-decay.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.confidence.confidence_constants import (
    FRESHNESS_DECAY_HALF_LIFE_HOURS,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem


@dataclass(frozen=True)
class FreshnessResult:
    item_count:       int
    avg_freshness:    float   # 0–1 from source confidence field
    decayed_score:    float   # 0–100 time-decay adjusted
    stale_items:      int     # freshness < 0.40
    fresh_items:      int     # freshness >= 0.80
    freshness_conf:   float   # 0–100 confidence contribution from freshness

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_count":     self.item_count,
            "avg_freshness":  round(self.avg_freshness, 4),
            "decayed_score":  round(self.decayed_score, 2),
            "stale_items":    self.stale_items,
            "fresh_items":    self.fresh_items,
            "freshness_conf": round(self.freshness_conf, 2),
        }


class FreshnessAnalyzer:
    """
    Computes a freshness confidence score from evidence items.
    Uses exponential decay over age_seconds and the item's own freshness_score.
    """

    def __init__(self, half_life_hours: float = FRESHNESS_DECAY_HALF_LIFE_HOURS) -> None:
        self._half_life_secs = half_life_hours * 3600.0

    def _time_decay(self, age_seconds: float) -> float:
        """Exponential decay: value = e^(-λ·t), λ = ln(2)/half_life."""
        if self._half_life_secs <= 0 or age_seconds < 0:
            return 1.0
        lam = math.log(2) / self._half_life_secs
        return math.exp(-lam * age_seconds)

    def analyze(self, items: List[EvidenceItem]) -> FreshnessResult:
        if not items:
            return FreshnessResult(
                item_count=0,
                avg_freshness=0.0,
                decayed_score=0.0,
                stale_items=0,
                fresh_items=0,
                freshness_conf=0.0,
            )

        # Compute decay-adjusted freshness per item
        decayed: List[float] = []
        for item in items:
            age = item.age_seconds
            decay = self._time_decay(age)
            # Blend source-reported freshness with time-decay
            blended = (item.freshness_score * 0.5 + decay * 0.5)
            decayed.append(blended)

        avg_freshness = statistics.mean(i.freshness_score for i in items)
        avg_decayed   = statistics.mean(decayed)
        decayed_score = avg_decayed * 100.0

        stale = sum(1 for i in items if i.freshness_score < 0.40)
        fresh = sum(1 for i in items if i.freshness_score >= 0.80)

        # Penalty for stale proportion
        stale_penalty = (stale / len(items)) * 20.0
        freshness_conf = max(0.0, decayed_score - stale_penalty)

        return FreshnessResult(
            item_count=len(items),
            avg_freshness=round(avg_freshness, 4),
            decayed_score=round(decayed_score, 4),
            stale_items=stale,
            fresh_items=fresh,
            freshness_conf=round(freshness_conf, 4),
        )
