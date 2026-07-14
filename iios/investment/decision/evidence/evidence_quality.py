"""iios/investment/decision/evidence/evidence_quality.py
EvidenceQuality — 5-dimension quality scorer orchestrator.
"""
from __future__ import annotations

from typing import Any, Dict, List

from iios.investment.decision.evidence.evidence_item import EvidenceItem
from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.evidence.consistency_checker import ConsistencyChecker
from iios.investment.decision.evidence.quality_score import QualityScore, compute_quality_score
from iios.investment.decision.evidence.quality_statistics import QualityStatisticsTracker
from iios.investment.decision.evidence.quality_history import QualityHistory


class EvidenceQuality:
    """
    5-dimension evidence quality scorer:
      1. Coverage     (0.30) — fraction of source types present (0–100)
      2. Freshness    (0.25) — average freshness_score of items (0–100)
      3. Consistency  (0.20) — 100 - conflict penalties
      4. Reliability  (0.15) — average confidence of items
      5. Completeness (0.10) — required items present (0 or 100)
    """

    def __init__(
        self,
        stats_tracker: QualityStatisticsTracker | None = None,
        history:       QualityHistory           | None = None,
    ) -> None:
        self._stats   = stats_tracker or QualityStatisticsTracker()
        self._history = history       or QualityHistory()
        self._checker = ConsistencyChecker()

    def score(self, items: List[EvidenceItem], subject_id: str = "") -> QualityScore:
        n = len(items)
        if n == 0:
            return compute_quality_score(0, 0, 100, 0, 0)

        # 1 — Coverage
        present       = {i.source_type for i in items}
        all_types     = list(EvidenceSourceType)
        coverage_raw  = len(present) / len(all_types) * 100.0 if all_types else 0.0

        # 2 — Freshness
        freshness_raw = sum(i.freshness_score for i in items) / n * 100.0

        # 3 — Consistency
        report        = self._checker.check(items)
        consistency   = report.consistency_score

        # 4 — Reliability
        reliability   = sum(i.confidence for i in items) / n

        # 5 — Completeness (all required present)
        required = [i for i in items if i.is_required]
        completeness = 100.0 if not required else (len(required) / n * 100.0 if required else 0.0)

        qs = compute_quality_score(
            coverage=coverage_raw,
            freshness=freshness_raw,
            consistency=consistency,
            reliability=reliability,
            completeness=completeness,
        )

        self._stats.record(qs)
        if subject_id:
            self._history.record(subject_id, qs)

        return qs

    def stats(self) -> Dict[str, Any]:
        return self._stats.summary().to_dict()

    def history(self, subject_id: str, last_n: int = 20) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._history.get(subject_id, last_n)]

    def trend(self, subject_id: str, window: int = 10) -> float | None:
        return self._history.trend(subject_id, window)
