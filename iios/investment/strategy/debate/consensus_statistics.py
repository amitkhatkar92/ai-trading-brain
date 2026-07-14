"""iios/investment/strategy/debate/consensus_statistics.py
Thread-safe rolling consensus statistics tracker.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.strategy.debate.debate_constants import ConsensusLevel
from iios.investment.strategy.debate.consensus_engine import ConsensusResult


@dataclass(frozen=True)
class ConsensusStatistics:
    total_debates:           int
    consensus_achieved:      int
    consensus_rate:          float          # fraction
    avg_confidence:          float
    avg_agreement_fraction:  float
    by_level:                Dict[str, int]
    computed_at:             datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_debates":          self.total_debates,
            "consensus_achieved":     self.consensus_achieved,
            "consensus_rate":         round(self.consensus_rate, 4),
            "avg_confidence":         round(self.avg_confidence, 2),
            "avg_agreement_fraction": round(self.avg_agreement_fraction, 4),
            "by_level":               self.by_level,
            "computed_at":            self.computed_at.isoformat(),
        }


class ConsensusStatisticsTracker:
    """Thread-safe rolling accumulator for consensus outcomes."""

    def __init__(self) -> None:
        self._lock            = threading.RLock()
        self._total:          int          = 0
        self._achieved:       int          = 0
        self._conf_sum:       float        = 0.0
        self._agree_sum:      float        = 0.0
        self._by_level:       Dict[str, int] = {lvl.value: 0 for lvl in ConsensusLevel}

    def record(self, result: ConsensusResult) -> None:
        with self._lock:
            self._total    += 1
            self._conf_sum  += result.confidence_score
            self._agree_sum += result.agreement_metrics.agreement_fraction
            if result.consensus_reached:
                self._achieved += 1
            lvl = result.consensus_level.value
            self._by_level[lvl] = self._by_level.get(lvl, 0) + 1

    def summary(self) -> ConsensusStatistics:
        with self._lock:
            n = self._total or 1  # avoid division by zero
            return ConsensusStatistics(
                total_debates=self._total,
                consensus_achieved=self._achieved,
                consensus_rate=round(self._achieved / n, 4),
                avg_confidence=round(self._conf_sum / n, 2),
                avg_agreement_fraction=round(self._agree_sum / n, 4),
                by_level=dict(self._by_level),
                computed_at=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._total    = 0
            self._achieved = 0
            self._conf_sum  = 0.0
            self._agree_sum = 0.0
            self._by_level  = {lvl.value: 0 for lvl in ConsensusLevel}
