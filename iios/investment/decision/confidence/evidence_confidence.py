"""iios/investment/decision/confidence/evidence_confidence.py
EvidenceConfidenceEstimator — aggregates source reliability, freshness, and coverage
into a single evidence confidence score (0–100).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.confidence_constants import (
    EvidenceConfidenceFactor,
)
from iios.investment.decision.confidence.coverage_analysis import (
    CoverageAnalyzer,
    CoverageResult,
)
from iios.investment.decision.confidence.freshness_analysis import (
    FreshnessAnalyzer,
    FreshnessResult,
)
from iios.investment.decision.confidence.source_reliability import (
    SourceReliabilityAnalyzer,
    SourceReliabilityScore,
)
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot


@dataclass(frozen=True)
class EvidenceConfidenceResult:
    overall:            float                      # 0–100
    coverage_score:     float                      # 0–100
    freshness_score:    float                      # 0–100
    reliability_score:  float                      # 0–100
    consistency_score:  float                      # 0–100
    coverage_detail:    CoverageResult
    freshness_detail:   FreshnessResult
    source_scores:      Tuple[SourceReliabilityScore, ...]
    factor_weights:     Tuple[Tuple[str, float], ...]
    item_count:         int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":           round(self.overall, 2),
            "coverage_score":    round(self.coverage_score, 2),
            "freshness_score":   round(self.freshness_score, 2),
            "reliability_score": round(self.reliability_score, 2),
            "consistency_score": round(self.consistency_score, 2),
            "item_count":        self.item_count,
            "coverage_detail":   self.coverage_detail.to_dict(),
            "freshness_detail":  self.freshness_detail.to_dict(),
            "source_scores":     [s.to_dict() for s in self.source_scores],
        }


# Allow mypy to be happy with the typed tuple
from typing import Tuple   # noqa: E402 (needed for the dataclass above)


class EvidenceConfidenceEstimator:
    """
    Estimates evidence-dimension confidence from an EvidenceSnapshot.
    Consumes ONLY the Evidence Collection Engine output.
    """

    def __init__(
        self,
        coverage_analyzer:  Optional[CoverageAnalyzer]  = None,
        freshness_analyzer:  Optional[FreshnessAnalyzer] = None,
        reliability_analyzer: Optional[SourceReliabilityAnalyzer] = None,
    ) -> None:
        self._cov  = coverage_analyzer   or CoverageAnalyzer()
        self._frsh = freshness_analyzer  or FreshnessAnalyzer()
        self._rel  = reliability_analyzer or SourceReliabilityAnalyzer()

    def estimate(self, snapshot: EvidenceSnapshot) -> EvidenceConfidenceResult:
        items = list(snapshot.items)

        # ── 1. Coverage ────────────────────────────────────────────────────
        cov_result  = self._cov.analyze(items)
        cov_score   = cov_result.coverage_conf

        # ── 2. Freshness ───────────────────────────────────────────────────
        frsh_result = self._frsh.analyze(items)
        frsh_score  = frsh_result.freshness_conf

        # ── 3. Source reliability ──────────────────────────────────────────
        src_scores, rel_score = self._rel.analyze(items)

        # ── 4. Consistency: use the snapshot's own quality_score ──────────
        consistency_score = snapshot.quality_score   # 0–100

        # ── 5. Weighted aggregate ──────────────────────────────────────────
        cw = EvidenceConfidenceFactor.COVERAGE.default_weight
        fw = EvidenceConfidenceFactor.FRESHNESS.default_weight
        rw = EvidenceConfidenceFactor.RELIABILITY.default_weight
        sw = EvidenceConfidenceFactor.CONSISTENCY.default_weight

        overall = (
            cov_score         * cw
            + frsh_score      * fw
            + rel_score       * rw
            + consistency_score * sw
        )
        overall = max(0.0, min(100.0, overall))

        factor_weights: Tuple[Tuple[str, float], ...] = (
            (EvidenceConfidenceFactor.COVERAGE.value,    cw),
            (EvidenceConfidenceFactor.FRESHNESS.value,   fw),
            (EvidenceConfidenceFactor.RELIABILITY.value, rw),
            (EvidenceConfidenceFactor.CONSISTENCY.value, sw),
        )

        return EvidenceConfidenceResult(
            overall=round(overall, 4),
            coverage_score=round(cov_score, 4),
            freshness_score=round(frsh_score, 4),
            reliability_score=round(rel_score, 4),
            consistency_score=round(consistency_score, 4),
            coverage_detail=cov_result,
            freshness_detail=frsh_result,
            source_scores=tuple(src_scores),
            factor_weights=factor_weights,
            item_count=len(items),
        )
