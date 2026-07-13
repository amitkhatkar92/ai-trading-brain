"""iios/investment/strategy/evaluation/trade_quality.py
TradeQualityReport — orchestrates trade statistics, execution, and distribution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
from iios.investment.strategy.evaluation.trade_statistics import (
    TradeStatistics, TradeStatisticsCalculator
)
from iios.investment.strategy.evaluation.execution_quality import (
    ExecutionMetrics, ExecutionQualityAnalyzer
)
from iios.investment.strategy.evaluation.trade_distribution import (
    TradeDistribution, TradeDistributionAnalyzer
)


@dataclass(frozen=True)
class TradeQualityReport:
    statistics:  TradeStatistics
    execution:   ExecutionMetrics
    distribution: TradeDistribution

    # Flat convenience properties
    @property
    def win_rate(self) -> float:
        return self.statistics.win_rate

    @property
    def risk_reward_ratio(self) -> float:
        return self.statistics.risk_reward_ratio

    @property
    def execution_efficiency(self) -> float:
        return self.execution.execution_efficiency

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statistics":   self.statistics.to_dict(),
            "execution":    self.execution.to_dict(),
            "distribution": self.distribution.to_dict(),
        }


class TradeQualityAnalyzer:

    def __init__(self) -> None:
        self._stats = TradeStatisticsCalculator()
        self._exec = ExecutionQualityAnalyzer()
        self._dist = TradeDistributionAnalyzer()

    def analyze(self, inp: EvaluationInput) -> TradeQualityReport:
        trades = inp.trades
        stats = self._stats.compute(trades)
        exec_ = self._exec.analyze(trades)
        dist = self._dist.analyze(trades)
        return TradeQualityReport(
            statistics=stats, execution=exec_, distribution=dist
        )
