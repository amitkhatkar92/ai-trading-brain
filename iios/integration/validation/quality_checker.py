"""iios/integration/validation/quality_checker.py

Computes a quality score (0–1) for DataRecord batches.
"""
from __future__ import annotations

from typing import Any

from iios.integration.integration_constants import DataQualityLevel
from iios.integration.core.data_record import DataRecord


class QualityChecker:
    """
    Scores data quality based on completeness, freshness, and consistency.

    Quality score formula:
      score = 0.5*completeness + 0.3*freshness + 0.2*consistency
    """

    def __init__(
        self,
        required_fields:     list[str] = [],
        max_staleness_sec:   float     = 3600.0,
        min_quality_score:   float     = 0.6,
    ) -> None:
        self._required_fields   = required_fields
        self._max_staleness_sec = max_staleness_sec
        self._min_quality_score = min_quality_score

    def score_record(self, record: DataRecord, now: float | None = None) -> float:
        import time
        if now is None:
            now = time.time()

        # Completeness: fraction of required_fields present
        if self._required_fields:
            present   = sum(1 for f in self._required_fields if record.payload.get(f) is not None)
            completeness = present / len(self._required_fields)
        else:
            completeness = 1.0

        # Freshness: based on record age
        age_sec = now - record.timestamp if record.timestamp > 0 else self._max_staleness_sec
        freshness = max(0.0, 1.0 - age_sec / self._max_staleness_sec)

        # Consistency: basic checks (non-negative numeric values)
        numeric_vals = [v for v in record.payload.values() if isinstance(v, (int, float))]
        negative_count = sum(1 for v in numeric_vals if v < 0)
        consistency = 1.0 - (negative_count / max(len(numeric_vals), 1))

        return 0.5 * completeness + 0.3 * freshness + 0.2 * consistency

    def score_batch(
        self,
        records: list[DataRecord],
        now: float | None = None,
    ) -> dict[str, float]:
        """Return {record_id: score} for each record."""
        return {r.record_id: self.score_record(r, now) for r in records}

    def batch_avg_score(self, records: list[DataRecord], now: float | None = None) -> float:
        if not records:
            return 1.0
        scores = list(self.score_batch(records, now).values())
        return sum(scores) / len(scores)

    def quality_level(self, score: float) -> DataQualityLevel:
        if score >= 0.85:
            return DataQualityLevel.HIGH
        if score >= 0.60:
            return DataQualityLevel.MEDIUM
        if score >= 0.0:
            return DataQualityLevel.LOW
        return DataQualityLevel.UNKNOWN

    def annotate_records(self, records: list[DataRecord], now: float | None = None) -> list[DataRecord]:
        """Set quality_score and quality on each record (in-place mutation)."""
        import copy
        result = []
        for rec in records:
            r = copy.copy(rec)
            r.quality_score = self.score_record(r, now)
            r.quality = self.quality_level(r.quality_score)
            result.append(r)
        return result
