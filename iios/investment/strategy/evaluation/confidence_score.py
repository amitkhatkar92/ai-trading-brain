"""iios/investment/strategy/evaluation/confidence_score.py
Confidence score: how much trust to place in the evaluation given data quality.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.strategy.evaluation.performance_statistics import clamp


@dataclass(frozen=True)
class ConfidenceFactors:
    trade_count_score:  float = 0.0   # 0–1; saturates at 200+ trades
    duration_score:     float = 0.0   # 0–1; saturates at 3+ years
    consistency_score:  float = 0.0   # 0–1; from trade consistency metric
    data_quality_score: float = 0.0   # 0–1; placeholder for data completeness
    overall: float = 0.0              # weighted composite 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_count_score":  self.trade_count_score,
            "duration_score":     self.duration_score,
            "consistency_score":  self.consistency_score,
            "data_quality_score": self.data_quality_score,
            "overall":            self.overall,
        }


class ConfidenceScoreCalculator:
    """
    Computes a confidence score (0–100) for the evaluation.
    Higher score → more data → more reliable evaluation.
    """

    # Targets for full confidence
    _TARGET_TRADES   = 200
    _TARGET_YEARS    = 3.0

    def compute(
        self,
        n_trades: int,
        duration_years: float,
        trade_consistency: float = 0.5,
        data_quality: float = 1.0,
    ) -> ConfidenceFactors:
        # Trade count: logarithmic saturation
        if n_trades <= 0:
            tc_score = 0.0
        else:
            tc_score = clamp(
                math.log(1.0 + n_trades) / math.log(1.0 + self._TARGET_TRADES),
                0.0, 1.0,
            )

        # Duration: linear saturation
        dur_score = clamp(duration_years / self._TARGET_YEARS, 0.0, 1.0)

        # Consistency: already in [0, 1]
        cons_score = clamp(trade_consistency, 0.0, 1.0)

        # Data quality: external signal
        dq_score = clamp(data_quality, 0.0, 1.0)

        # Weighted composite
        overall = (
            0.35 * tc_score
            + 0.30 * dur_score
            + 0.20 * cons_score
            + 0.15 * dq_score
        ) * 100.0

        return ConfidenceFactors(
            trade_count_score=tc_score,
            duration_score=dur_score,
            consistency_score=cons_score,
            data_quality_score=dq_score,
            overall=round(overall, 2),
        )
