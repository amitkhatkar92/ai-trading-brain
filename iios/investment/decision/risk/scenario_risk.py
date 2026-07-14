"""iios/investment/decision/risk/scenario_risk.py
ScenarioRiskAnalyzer — applies all registered stress scenarios to base risk scores.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.risk.risk_constants import (
    SCENARIO_AVERAGE_WEIGHT,
    SCENARIO_WORST_CASE_WEIGHT,
    ScenarioType,
)
from iios.investment.decision.risk.scenario_registry import ScenarioRegistry
from iios.investment.decision.risk.stress_scenarios import StressScenario


@dataclass(frozen=True)
class ScenarioRiskEntry:
    scenario_type:    str
    scenario_name:    str
    probability:      float
    stressed_risk:    float   # 0–100 overall stressed risk
    market_risk:      float
    company_risk:     float
    strategy_risk:    float
    execution_risk:   float
    confidence_risk:  float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_type":   self.scenario_type,
            "scenario_name":   self.scenario_name,
            "probability":     round(self.probability, 4),
            "stressed_risk":   round(self.stressed_risk, 2),
            "market_risk":     round(self.market_risk, 2),
            "company_risk":    round(self.company_risk, 2),
            "strategy_risk":   round(self.strategy_risk, 2),
            "execution_risk":  round(self.execution_risk, 2),
            "confidence_risk": round(self.confidence_risk, 2),
        }


@dataclass(frozen=True)
class ScenarioRiskResult:
    scenario_count:      int
    worst_case_risk:     float    # maximum stressed_risk across all scenarios
    average_risk:        float    # probability-weighted average stressed_risk
    blended_risk:        float    # SCENARIO_WORST_CASE_WEIGHT * worst + AVERAGE_WEIGHT * avg
    worst_scenario:      str      # scenario_type of worst case
    entries:             Tuple[ScenarioRiskEntry, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_count":   self.scenario_count,
            "worst_case_risk":  round(self.worst_case_risk, 2),
            "average_risk":     round(self.average_risk, 2),
            "blended_risk":     round(self.blended_risk, 2),
            "worst_scenario":   self.worst_scenario,
            "entries":          [e.to_dict() for e in self.entries],
        }


class ScenarioRiskAnalyzer:
    """
    Evaluates all stress scenarios against base risk dimension scores.
    Consumes ONLY outputs from upstream risk dimension evaluators.
    """

    def __init__(self, registry: Optional[ScenarioRegistry] = None) -> None:
        self._registry = registry or ScenarioRegistry()

    def analyze(
        self,
        market_risk:     float,
        company_risk:    float,
        strategy_risk:   float,
        execution_risk:  float,
        confidence_risk: float,
        *,
        dim_weights:     Tuple[float, ...] = (0.30, 0.25, 0.20, 0.15, 0.10),
    ) -> ScenarioRiskResult:
        scenarios = self._registry.all_scenarios()
        entries: List[ScenarioRiskEntry] = []

        mw, cw, sw, ew, cnw = dim_weights

        for sc in scenarios:
            stressed = sc.apply(
                market_risk, company_risk, strategy_risk,
                execution_risk, confidence_risk,
            )
            overall = (
                stressed["market_risk"]     * mw
                + stressed["company_risk"]  * cw
                + stressed["strategy_risk"] * sw
                + stressed["execution_risk"] * ew
                + stressed["confidence_risk"] * cnw
            )
            overall = min(100.0, max(0.0, overall))

            entries.append(ScenarioRiskEntry(
                scenario_type=sc.scenario_type.value,
                scenario_name=sc.name,
                probability=sc.probability,
                stressed_risk=round(overall, 4),
                market_risk=round(stressed["market_risk"], 4),
                company_risk=round(stressed["company_risk"], 4),
                strategy_risk=round(stressed["strategy_risk"], 4),
                execution_risk=round(stressed["execution_risk"], 4),
                confidence_risk=round(stressed["confidence_risk"], 4),
            ))

        if not entries:
            return ScenarioRiskResult(
                scenario_count=0, worst_case_risk=0.0, average_risk=0.0,
                blended_risk=0.0, worst_scenario="none", entries=(),
            )

        worst_entry = max(entries, key=lambda e: e.stressed_risk)
        worst_risk  = worst_entry.stressed_risk

        # Probability-weighted average
        total_prob   = sum(e.probability for e in entries) or 1.0
        weighted_avg = sum(e.stressed_risk * e.probability for e in entries) / total_prob

        blended = (
            worst_risk  * SCENARIO_WORST_CASE_WEIGHT
            + weighted_avg * SCENARIO_AVERAGE_WEIGHT
        )

        return ScenarioRiskResult(
            scenario_count=len(entries),
            worst_case_risk=round(worst_risk, 4),
            average_risk=round(weighted_avg, 4),
            blended_risk=round(blended, 4),
            worst_scenario=worst_entry.scenario_type,
            entries=tuple(entries),
        )
