"""iios/investment/company/earnings/earnings_reliability.py
Aggregates consistency, persistence, and revision signals into a reliability score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_consistency import (
    EarningsConsistencyChecker, ConsistencyMetrics,
)
from iios.investment.company.earnings.earnings_persistence import (
    EarningsPersistenceAnalyzer, PersistenceMetrics,
)


@dataclass
class EarningsReliabilityScore:
    overall_score:      float = 0.0   # 0–100
    consistency_score:  float = 0.0
    persistence_score:  float = 0.0
    revision_score:     float = 100.0  # start at 100; penalise per revision
    reporting_score:    float = 100.0  # penalise for restatements

    periods_available:  int   = 0
    restatement_count:  int   = 0
    revision_count:     int   = 0

    flags: List[str] = field(default_factory=list)

    _W_CONSISTENCY  = 0.35
    _W_PERSISTENCE  = 0.35
    _W_REVISION     = 0.20
    _W_REPORTING    = 0.10

    def recompute(self) -> None:
        self.overall_score = (
            self.consistency_score  * self._W_CONSISTENCY
            + self.persistence_score * self._W_PERSISTENCE
            + self.revision_score    * self._W_REVISION
            + self.reporting_score   * self._W_REPORTING
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":     round(self.overall_score, 1),
            "consistency_score": round(self.consistency_score, 1),
            "persistence_score": round(self.persistence_score, 1),
            "revision_score":    round(self.revision_score, 1),
            "reporting_score":   round(self.reporting_score, 1),
            "periods_available": self.periods_available,
            "restatement_count": self.restatement_count,
            "revision_count":    self.revision_count,
            "flags":             self.flags,
        }


class EarningsReliabilityAnalyzer:
    """Aggregates all reliability signals."""

    _REVISION_PENALTY    = 8.0   # points per revision event
    _RESTATEMENT_PENALTY = 12.0  # points per financial restatement

    def __init__(self) -> None:
        self._consistency  = EarningsConsistencyChecker()
        self._persistence  = EarningsPersistenceAnalyzer()

    def analyze(
        self,
        history:           List[EarningsReport],
        revision_count:    int = 0,
        restatement_count: int = 0,
    ) -> EarningsReliabilityScore:
        score = EarningsReliabilityScore()
        score.periods_available  = len(history)
        score.revision_count     = revision_count
        score.restatement_count  = restatement_count

        if not history:
            score.flags.append("no_data")
            return score

        # Consistency analysis
        cm = self._consistency.analyze(history)
        score.consistency_score = cm.score
        score.flags.extend(cm.flags)

        # Persistence analysis
        pm = self._persistence.analyze(history)
        score.persistence_score = pm.score
        score.flags.extend(pm.flags)

        # Revision penalty
        rev_penalty = min(60.0, revision_count * self._REVISION_PENALTY)
        score.revision_score = max(40.0, 100.0 - rev_penalty)
        if revision_count > 3:
            score.flags.append(f"frequent_revisions:{revision_count}")

        # Restatement penalty
        rst_penalty = min(60.0, restatement_count * self._RESTATEMENT_PENALTY)
        score.reporting_score = max(40.0, 100.0 - rst_penalty)
        if restatement_count > 0:
            score.flags.append(f"restatements:{restatement_count}")

        score.recompute()
        return score
