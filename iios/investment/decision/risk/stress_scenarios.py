"""iios/investment/decision/risk/stress_scenarios.py
Stress scenario definitions with risk multipliers per dimension.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.decision.risk.risk_constants import ScenarioType


@dataclass(frozen=True)
class StressScenario:
    """
    Defines how a market scenario modifies each risk dimension.
    Multipliers > 1.0 amplify risk; < 1.0 reduce risk.
    """
    scenario_type:        ScenarioType
    name:                 str
    description:          str
    probability:          float    # 0–1 estimated occurrence probability
    market_multiplier:    float    # applied to market_risk
    company_multiplier:   float    # applied to company_risk
    strategy_multiplier:  float    # applied to strategy_risk
    execution_multiplier: float    # applied to execution_risk
    confidence_multiplier: float   # applied to confidence_risk

    def apply(
        self,
        market_risk:     float,
        company_risk:    float,
        strategy_risk:   float,
        execution_risk:  float,
        confidence_risk: float,
    ) -> Dict[str, float]:
        """Return scenario-stressed risk scores (clamped 0–100)."""
        return {
            "market_risk":     min(100.0, market_risk     * self.market_multiplier),
            "company_risk":    min(100.0, company_risk    * self.company_multiplier),
            "strategy_risk":   min(100.0, strategy_risk   * self.strategy_multiplier),
            "execution_risk":  min(100.0, execution_risk  * self.execution_multiplier),
            "confidence_risk": min(100.0, confidence_risk * self.confidence_multiplier),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_type":        self.scenario_type.value,
            "name":                 self.name,
            "probability":          self.probability,
            "market_multiplier":    self.market_multiplier,
            "company_multiplier":   self.company_multiplier,
            "strategy_multiplier":  self.strategy_multiplier,
            "execution_multiplier": self.execution_multiplier,
        }


# ── Default scenario library ──────────────────────────────────────────────────

DEFAULT_SCENARIOS: List[StressScenario] = [
    StressScenario(
        scenario_type=ScenarioType.BASE_CASE,
        name="Base Case",
        description="Current regime — no additional stress applied.",
        probability=0.50,
        market_multiplier=1.00, company_multiplier=1.00,
        strategy_multiplier=1.00, execution_multiplier=1.00,
        confidence_multiplier=1.00,
    ),
    StressScenario(
        scenario_type=ScenarioType.BULL_MARKET,
        name="Bull Market",
        description="Sustained rising market with positive momentum.",
        probability=0.15,
        market_multiplier=0.70, company_multiplier=0.80,
        strategy_multiplier=0.75, execution_multiplier=0.85,
        confidence_multiplier=0.80,
    ),
    StressScenario(
        scenario_type=ScenarioType.BEAR_MARKET,
        name="Bear Market",
        description="Sustained declining market with negative momentum.",
        probability=0.10,
        market_multiplier=1.40, company_multiplier=1.30,
        strategy_multiplier=1.35, execution_multiplier=1.20,
        confidence_multiplier=1.25,
    ),
    StressScenario(
        scenario_type=ScenarioType.SIDEWAYS_MARKET,
        name="Sideways / Range-Bound",
        description="Low-trend, choppy, range-bound market.",
        probability=0.15,
        market_multiplier=0.90, company_multiplier=0.95,
        strategy_multiplier=1.10, execution_multiplier=1.05,
        confidence_multiplier=1.00,
    ),
    StressScenario(
        scenario_type=ScenarioType.VOLATILITY_SPIKE,
        name="Volatility Spike",
        description="Sudden spike in market volatility (VIX-type event).",
        probability=0.05,
        market_multiplier=1.60, company_multiplier=1.20,
        strategy_multiplier=1.50, execution_multiplier=1.70,
        confidence_multiplier=1.40,
    ),
    StressScenario(
        scenario_type=ScenarioType.FLASH_CRASH,
        name="Flash Crash",
        description="Rapid, severe, short-duration market crash.",
        probability=0.02,
        market_multiplier=1.80, company_multiplier=1.40,
        strategy_multiplier=1.60, execution_multiplier=2.00,
        confidence_multiplier=1.50,
    ),
    StressScenario(
        scenario_type=ScenarioType.LIQUIDITY_CRISIS,
        name="Liquidity Crisis",
        description="Widespread liquidity shortage, wide bid-ask spreads.",
        probability=0.02,
        market_multiplier=1.70, company_multiplier=1.50,
        strategy_multiplier=1.40, execution_multiplier=1.90,
        confidence_multiplier=1.60,
    ),
    StressScenario(
        scenario_type=ScenarioType.MACRO_SHOCK,
        name="Macro Shock",
        description="Unexpected macro event (rate hike, geopolitical, etc.).",
        probability=0.03,
        market_multiplier=1.50, company_multiplier=1.30,
        strategy_multiplier=1.30, execution_multiplier=1.40,
        confidence_multiplier=1.30,
    ),
    StressScenario(
        scenario_type=ScenarioType.SECTOR_SHOCK,
        name="Sector Shock",
        description="Concentrated shock to a specific sector.",
        probability=0.04,
        market_multiplier=1.20, company_multiplier=1.60,
        strategy_multiplier=1.40, execution_multiplier=1.20,
        confidence_multiplier=1.20,
    ),
]
