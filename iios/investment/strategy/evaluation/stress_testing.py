"""iios/investment/strategy/evaluation/stress_testing.py
Stress-test a strategy against predefined adverse market scenarios.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.strategy.evaluation.trade import Trade
from iios.investment.strategy.evaluation.performance_statistics import safe_mean


@dataclass(frozen=True)
class StressScenario:
    name: str
    description: str
    # Market-shock multiplier applied to losing-trade PnL (e.g., 1.5 = 50 % worse)
    loss_multiplier: float = 1.5
    # Win-rate reduction fraction (e.g., 0.20 = reduce win rate by 20 pp)
    win_rate_reduction: float = 0.10


@dataclass(frozen=True)
class ScenarioResult:
    scenario_name: str
    stressed_win_rate:   float = 0.0
    stressed_net_pnl:    float = 0.0
    stressed_profit_factor: float = 0.0
    survived: bool = True   # True if stressed PnL > 0


@dataclass(frozen=True)
class StressTestReport:
    scenarios_run:      int = 0
    scenarios_survived: int = 0
    survival_rate:      float = 0.0
    worst_net_pnl:      float = 0.0
    stress_score:       float = 0.0   # 0–1; proportion of scenarios survived
    results: List[ScenarioResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenarios_run":       self.scenarios_run,
            "scenarios_survived":  self.scenarios_survived,
            "survival_rate":       self.survival_rate,
            "worst_net_pnl":       self.worst_net_pnl,
            "stress_score":        self.stress_score,
            "results": [
                {
                    "name":    r.scenario_name,
                    "pnl":     r.stressed_net_pnl,
                    "survived": r.survived,
                }
                for r in self.results
            ],
        }


_DEFAULT_SCENARIOS: List[StressScenario] = [
    StressScenario("bear_market",         "Losses 50 % larger",              loss_multiplier=1.5,  win_rate_reduction=0.10),
    StressScenario("crash",               "Losses doubled, 20 pp win-rate drop", loss_multiplier=2.0, win_rate_reduction=0.20),
    StressScenario("liquidity_crisis",    "Losses 30 % larger",              loss_multiplier=1.3,  win_rate_reduction=0.05),
    StressScenario("high_volatility",     "Losses 80 % larger",              loss_multiplier=1.8,  win_rate_reduction=0.15),
    StressScenario("regime_change",       "Win-rate halved",                 loss_multiplier=1.0,  win_rate_reduction=0.25),
]


class StressTester:

    def __init__(
        self, scenarios: Optional[List[StressScenario]] = None
    ) -> None:
        self._scenarios = scenarios or _DEFAULT_SCENARIOS

    def test(self, trades: List[Trade]) -> StressTestReport:
        if not trades:
            return StressTestReport()

        results: List[ScenarioResult] = []
        for sc in self._scenarios:
            res = self._run_scenario(trades, sc)
            results.append(res)

        survived = sum(1 for r in results if r.survived)
        worst_pnl = min((r.stressed_net_pnl for r in results), default=0.0)
        n = len(results)

        return StressTestReport(
            scenarios_run=n,
            scenarios_survived=survived,
            survival_rate=survived / n if n else 0.0,
            worst_net_pnl=worst_pnl,
            stress_score=survived / n if n else 0.0,
            results=results,
        )

    def _run_scenario(
        self, trades: List[Trade], sc: StressScenario
    ) -> ScenarioResult:
        orig_win_rate = sum(1 for t in trades if t.is_winner) / len(trades)
        stressed_wr = max(0.0, orig_win_rate - sc.win_rate_reduction)

        # Re-price trades: winners kept, some converted to losers,
        # and all losses amplified.
        stressed_pnl = 0.0
        wins, losses = [], []
        for t in trades:
            if t.is_winner:
                wins.append(t.net_pnl)
            else:
                losses.append(t.net_pnl * sc.loss_multiplier)

        # Demote fraction of winners equal to win_rate_reduction
        n_demote = round(len(wins) * sc.win_rate_reduction)
        demoted = wins[:n_demote]
        remaining_wins = wins[n_demote:]

        stressed_pnl = (
            sum(remaining_wins)
            + sum(losses)
            + sum(-abs(w) for w in demoted)   # demoted winners become small losses
        )

        gross_p = sum(remaining_wins)
        gross_l = abs(sum(losses) + sum(-abs(w) for w in demoted))
        pf = gross_p / gross_l if gross_l > 0 else math.inf
        if not math.isfinite(pf):
            pf = 0.0

        return ScenarioResult(
            scenario_name=sc.name,
            stressed_win_rate=stressed_wr,
            stressed_net_pnl=stressed_pnl,
            stressed_profit_factor=pf,
            survived=stressed_pnl > 0.0,
        )
