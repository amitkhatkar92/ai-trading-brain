"""iios/investment/decision/evidence/evidence_statistics.py
EvidenceStatistics — rolling statistics across evidence collection runs.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot


@dataclass(frozen=True)
class EvidenceStatistics:
    total_snapshots:    int
    total_items:        int
    avg_items_per_run:  float
    avg_quality:        float
    avg_confidence:     float
    avg_freshness:      float
    avg_duration_ms:    float
    provider_call_count: Dict[str, int]
    computed_at:        datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_snapshots":    self.total_snapshots,
            "total_items":        self.total_items,
            "avg_items_per_run":  round(self.avg_items_per_run, 1),
            "avg_quality":        round(self.avg_quality, 2),
            "avg_confidence":     round(self.avg_confidence, 2),
            "avg_freshness":      round(self.avg_freshness, 4),
            "avg_duration_ms":    round(self.avg_duration_ms, 1),
            "provider_call_count": self.provider_call_count,
            "computed_at":        self.computed_at.isoformat(),
        }


class EvidenceStatisticsTracker:
    """Thread-safe rolling statistics accumulator."""

    def __init__(self) -> None:
        self._lock          = threading.RLock()
        self._total_snaps   = 0
        self._total_items   = 0
        self._quality_sum   = 0.0
        self._conf_sum      = 0.0
        self._fresh_sum     = 0.0
        self._duration_sum  = 0.0
        self._prov_calls:   Dict[str, int] = {}

    def record(self, snapshot: EvidenceSnapshot) -> None:
        with self._lock:
            self._total_snaps  += 1
            self._total_items  += snapshot.item_count
            self._quality_sum  += snapshot.quality_score
            self._conf_sum     += snapshot.overall_confidence
            self._fresh_sum    += snapshot.overall_freshness
            self._duration_sum += snapshot.collection_duration_ms
            for src in snapshot.sources_included:
                self._prov_calls[src] = self._prov_calls.get(src, 0) + 1

    def summary(self) -> EvidenceStatistics:
        with self._lock:
            n = self._total_snaps or 1
            return EvidenceStatistics(
                total_snapshots=self._total_snaps,
                total_items=self._total_items,
                avg_items_per_run=round(self._total_items / n, 1),
                avg_quality=round(self._quality_sum / n, 2),
                avg_confidence=round(self._conf_sum / n, 2),
                avg_freshness=round(self._fresh_sum / n, 4),
                avg_duration_ms=round(self._duration_sum / n, 1),
                provider_call_count=dict(self._prov_calls),
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total_snaps = self._total_items = 0
            self._quality_sum = self._conf_sum = self._fresh_sum = self._duration_sum = 0.0
            self._prov_calls.clear()
