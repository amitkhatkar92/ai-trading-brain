"""iios/investment/decision/evidence/freshness_validator.py
FreshnessValidator — validates evidence items for staleness.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from iios.investment.decision.evidence.evidence_constants import (
    EVIDENCE_FRESHNESS_STALE_SECONDS,
    EVIDENCE_FRESHNESS_WARN_SECONDS,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem


@dataclass(frozen=True)
class FreshnessReport:
    total:         int
    fresh:         int
    stale:         int
    avg_freshness: float
    stale_keys:    Tuple[str, ...]

    @property
    def stale_fraction(self) -> float:
        return self.stale / self.total if self.total else 0.0

    @property
    def is_acceptable(self) -> bool:
        return self.stale_fraction < 0.30


class FreshnessValidator:
    """Validates age of evidence items; recomputes freshness_score."""

    def __init__(
        self,
        warn_seconds:  float = EVIDENCE_FRESHNESS_WARN_SECONDS,
        stale_seconds: float = EVIDENCE_FRESHNESS_STALE_SECONDS,
    ) -> None:
        self._warn  = warn_seconds
        self._stale = stale_seconds

    def recompute_freshness(self, item: EvidenceItem) -> float:
        age = item.age_seconds
        if age <= 0:
            return 1.0
        if age >= self._stale:
            return 0.0
        if age <= self._warn:
            return 1.0
        decay = (age - self._warn) / (self._stale - self._warn)
        return max(0.0, 1.0 - decay)

    def validate(self, items: List[EvidenceItem]) -> Tuple[List[EvidenceItem], FreshnessReport]:
        refreshed: List[EvidenceItem] = []
        stale_keys: List[str] = []
        total_fresh = 0.0

        for item in items:
            new_fs = self.recompute_freshness(item)
            # Build updated item via dataclass copy trick
            updated = _replace_freshness(item, new_fs)
            refreshed.append(updated)
            total_fresh += new_fs
            if new_fs == 0.0:
                stale_keys.append(item.key)

        n = len(refreshed)
        avg = total_fresh / n if n else 0.0
        stale_count = sum(1 for i in refreshed if i.freshness_score == 0.0)
        fresh_count = n - stale_count

        report = FreshnessReport(
            total=n,
            fresh=fresh_count,
            stale=stale_count,
            avg_freshness=round(avg, 4),
            stale_keys=tuple(stale_keys),
        )
        return refreshed, report


def _replace_freshness(item: EvidenceItem, freshness: float) -> EvidenceItem:
    """Create a new EvidenceItem with updated freshness_score (frozen dataclass)."""
    from dataclasses import replace
    return replace(item, freshness_score=round(freshness, 4))
