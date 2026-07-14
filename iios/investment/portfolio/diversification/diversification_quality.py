"""iios/investment/portfolio/diversification/diversification_quality.py

Five-dimension quality assessment for a DiversificationAnalysis.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.diversification.diversification_types import (
    DiversificationGrade,
    SECTOR_WARNING_THRESHOLD,
    TOP1_WARNING_THRESHOLD,
    TOP5_WARNING_THRESHOLD,
)
from iios.investment.portfolio.diversification.diversification_engine import (
    DiversificationAnalysis,
)


def _grade(score: float) -> DiversificationGrade:
    if score >= 0.85:
        return DiversificationGrade.A
    if score >= 0.70:
        return DiversificationGrade.B
    if score >= 0.55:
        return DiversificationGrade.C
    if score >= 0.40:
        return DiversificationGrade.D
    return DiversificationGrade.F


@dataclass(frozen=True)
class DiversificationDimensionScore:
    dimension: str   = ""
    score:     float = 0.0    # [0, 1]
    passed:    bool  = False
    message:   str   = ""
    weight:    float = 0.20   # relative weight in overall score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score":     round(self.score, 4),
            "passed":    self.passed,
            "message":   self.message,
        }


@dataclass(frozen=True)
class DiversificationQualityReport:
    """Full quality assessment for one DiversificationAnalysis."""

    report_id:       str                              = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str                              = ""
    analysis_id:     str                              = ""
    dimension_scores:Tuple[DiversificationDimensionScore, ...] = field(default_factory=tuple)
    overall_score:   float                            = 0.0
    grade:           DiversificationGrade             = DiversificationGrade.F
    is_acceptable:   bool                             = False
    threshold:       float                            = 0.55
    # Dimension sub-scores for fast access
    position_score:  float = 0.0
    sector_score:    float = 0.0
    correlation_score:float= 0.0
    concentration_score:float=0.0
    resilience_score:float = 0.0
    assessed_at:     float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":        self.report_id,
            "portfolio_id":     self.portfolio_id,
            "analysis_id":      self.analysis_id,
            "overall_score":    round(self.overall_score, 4),
            "grade":            self.grade.value,
            "is_acceptable":    self.is_acceptable,
            "threshold":        self.threshold,
            "position_score":   round(self.position_score, 4),
            "sector_score":     round(self.sector_score, 4),
            "correlation_score":round(self.correlation_score, 4),
            "concentration_score":round(self.concentration_score, 4),
            "resilience_score": round(self.resilience_score, 4),
            "dimension_scores": [d.to_dict() for d in self.dimension_scores],
            "assessed_at":      self.assessed_at,
        }


class DiversificationQualityAssessor:
    """
    Computes a DiversificationQualityReport from a DiversificationAnalysis.

    Dimension weights:
        position_diversity   30%
        sector_diversity     25%
        correlation_quality  20%
        concentration        15%
        resilience           10%
    """

    _WEIGHTS = {
        "position_diversity":  0.30,
        "sector_diversity":    0.25,
        "correlation_quality": 0.20,
        "concentration":       0.15,
        "resilience":          0.10,
    }

    def __init__(self, acceptable_threshold: float = 0.55) -> None:
        self._threshold = acceptable_threshold

    def assess(self, analysis: DiversificationAnalysis) -> DiversificationQualityReport:
        d_scores: List[DiversificationDimensionScore] = []

        # 1. Position diversity: entropy_ratio + effective_n relative to n_positions
        if analysis.n_positions > 0:
            eff_n_norm = min(1.0, analysis.effective_n / max(analysis.n_positions, 1))
            pos_score  = 0.5 * analysis.entropy_ratio + 0.5 * eff_n_norm
        else:
            pos_score = 0.0
        d_scores.append(DiversificationDimensionScore(
            dimension = "position_diversity",
            score     = round(pos_score, 4),
            passed    = pos_score >= 0.50,
            message   = f"Entropy ratio {analysis.entropy_ratio:.2f}, effective-N {analysis.effective_n:.1f}/{analysis.n_positions}",
            weight    = self._WEIGHTS["position_diversity"],
        ))

        # 2. Sector diversity: sector_entropy_ratio + (1 - top_sector_weight)
        sec_concentration_pen = max(0.0, analysis.top_sector_weight - SECTOR_WARNING_THRESHOLD)
        sec_score = (
            0.6 * analysis.sector_entropy_ratio +
            0.4 * max(0.0, 1.0 - analysis.top_sector_weight / max(0.01, 1.0 - SECTOR_WARNING_THRESHOLD + analysis.top_sector_weight))
        )
        sec_score = max(0.0, min(1.0, sec_score - sec_concentration_pen))
        d_scores.append(DiversificationDimensionScore(
            dimension = "sector_diversity",
            score     = round(sec_score, 4),
            passed    = sec_score >= 0.50,
            message   = f"Top sector {analysis.top_sector_weight:.1%}, {analysis.n_sectors} sectors",
            weight    = self._WEIGHTS["sector_diversity"],
        ))

        # 3. Correlation quality: penalise high avg correlation
        avg_c = analysis.correlation.analysis.avg_correlation
        corr_score = max(0.0, 1.0 - (avg_c / 0.80))
        # Bonus for high diversification ratio
        dr = min(analysis.diversification_ratio, 2.0)
        corr_score = min(1.0, corr_score * 0.70 + (dr - 1.0) * 0.30)
        d_scores.append(DiversificationDimensionScore(
            dimension = "correlation_quality",
            score     = round(corr_score, 4),
            passed    = corr_score >= 0.40,
            message   = f"Avg correlation {avg_c:.2f}, diversification ratio {analysis.diversification_ratio:.2f}",
            weight    = self._WEIGHTS["correlation_quality"],
        ))

        # 4. Concentration: penalise top1 and top5
        pos_conc = analysis.concentration.position
        t1_pen = max(0.0, pos_conc.top1_weight - TOP1_WARNING_THRESHOLD)
        t5_pen = max(0.0, pos_conc.top5_weight - TOP5_WARNING_THRESHOLD)
        conc_score = max(0.0, 1.0 - 2 * t1_pen - t5_pen)
        d_scores.append(DiversificationDimensionScore(
            dimension = "concentration",
            score     = round(conc_score, 4),
            passed    = conc_score >= 0.60,
            message   = f"Top-1 {pos_conc.top1_weight:.1%}, top-5 {pos_conc.top5_weight:.1%}",
            weight    = self._WEIGHTS["concentration"],
        ))

        # 5. Resilience: based on overlap risk + hidden dependencies
        overlap_pen = {
            "low": 0.0, "moderate": 0.20, "high": 0.45
        }.get(analysis.correlation.overlap.overlap_risk, 0.0)
        dep_pen = min(0.30, analysis.correlation.dependency.hidden_dependency_count * 0.05)
        resil_score = max(0.0, 1.0 - overlap_pen - dep_pen)
        d_scores.append(DiversificationDimensionScore(
            dimension = "resilience",
            score     = round(resil_score, 4),
            passed    = resil_score >= 0.50,
            message   = f"Overlap risk '{analysis.correlation.overlap.overlap_risk}', "
                       f"{analysis.correlation.dependency.hidden_dependency_count} hidden deps",
            weight    = self._WEIGHTS["resilience"],
        ))

        # Weighted overall
        overall = sum(d.score * d.weight for d in d_scores)
        grade   = _grade(overall)

        scores = {d.dimension: d.score for d in d_scores}
        return DiversificationQualityReport(
            portfolio_id     = analysis.portfolio_id,
            analysis_id      = analysis.analysis_id,
            dimension_scores = tuple(d_scores),
            overall_score    = round(overall, 4),
            grade            = grade,
            is_acceptable    = overall >= self._threshold,
            threshold        = self._threshold,
            position_score   = scores.get("position_diversity", 0.0),
            sector_score     = scores.get("sector_diversity", 0.0),
            correlation_score= scores.get("correlation_quality", 0.0),
            concentration_score=scores.get("concentration", 0.0),
            resilience_score = scores.get("resilience", 0.0),
        )
