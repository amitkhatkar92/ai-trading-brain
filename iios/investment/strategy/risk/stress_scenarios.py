"""iios/investment/strategy/risk/stress_scenarios.py
Built-in stress scenarios for strategy risk stress testing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class StressScenario:
    """
    A stress scenario definition.
    Multipliers are applied to base risk scores in the ScenarioEngine.
    """
    name:                  str
    description:           str
    vol_multiplier:        float   # how much vol increases
    drawdown_multiplier:   float   # how much max_drawdown amplifies
    liquidity_multiplier:  float   # how much liquidity risk worsens
    execution_multiplier:  float   # how much execution risk worsens
    regime_impact:         str     # "adversarial" | "neutral" | "favorable"
    probability:           float   # estimated annual probability (0–1)
    tags:                  List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":                 self.name,
            "description":          self.description,
            "vol_multiplier":       self.vol_multiplier,
            "drawdown_multiplier":  self.drawdown_multiplier,
            "liquidity_multiplier": self.liquidity_multiplier,
            "execution_multiplier": self.execution_multiplier,
            "regime_impact":        self.regime_impact,
            "probability":          self.probability,
            "tags":                 self.tags,
        }


# ── Built-in scenario library ─────────────────────────────────────────────────

MARKET_CRASH = StressScenario(
    name="market_crash",
    description="Severe market sell-off: vol doubles, drawdowns amplify 2×",
    vol_multiplier=2.5,
    drawdown_multiplier=2.0,
    liquidity_multiplier=2.5,
    execution_multiplier=1.8,
    regime_impact="adversarial",
    probability=0.10,
    tags=["crash", "bear", "systemic"],
)

VOLATILITY_SPIKE = StressScenario(
    name="volatility_spike",
    description="VIX-like spike: vol triples, execution degrades sharply",
    vol_multiplier=3.0,
    drawdown_multiplier=1.5,
    liquidity_multiplier=1.8,
    execution_multiplier=2.5,
    regime_impact="adversarial",
    probability=0.15,
    tags=["vol_spike", "vix"],
)

LIQUIDITY_SHOCK = StressScenario(
    name="liquidity_shock",
    description="Market freezes: spreads widen 3×, fills degrade",
    vol_multiplier=1.5,
    drawdown_multiplier=1.3,
    liquidity_multiplier=3.5,
    execution_multiplier=2.0,
    regime_impact="adversarial",
    probability=0.08,
    tags=["liquidity", "freeze", "credit"],
)

GAP_EVENT = StressScenario(
    name="gap_event",
    description="Overnight gap: price jumps beyond stop-loss levels",
    vol_multiplier=1.8,
    drawdown_multiplier=1.8,
    liquidity_multiplier=1.2,
    execution_multiplier=1.5,
    regime_impact="adversarial",
    probability=0.20,
    tags=["gap", "overnight"],
)

CORRELATION_BREAKDOWN = StressScenario(
    name="correlation_breakdown",
    description="Historical correlations collapse: diversification fails",
    vol_multiplier=1.6,
    drawdown_multiplier=1.6,
    liquidity_multiplier=1.4,
    execution_multiplier=1.3,
    regime_impact="adversarial",
    probability=0.12,
    tags=["correlation", "diversification"],
)

EXTREME_TREND = StressScenario(
    name="extreme_trend",
    description="Strong sustained trend: favors momentum, hurts reversal",
    vol_multiplier=1.2,
    drawdown_multiplier=0.7,
    liquidity_multiplier=0.8,
    execution_multiplier=1.1,
    regime_impact="favorable",
    probability=0.20,
    tags=["trend", "momentum"],
)

EXTREME_RANGE = StressScenario(
    name="extreme_range",
    description="Choppy sideways: hurts momentum, favors mean-reversion",
    vol_multiplier=1.3,
    drawdown_multiplier=1.2,
    liquidity_multiplier=0.9,
    execution_multiplier=1.2,
    regime_impact="neutral",
    probability=0.25,
    tags=["range", "sideways", "mean_reversion"],
)

FLASH_CRASH = StressScenario(
    name="flash_crash",
    description="Instantaneous price dislocation and rapid recovery",
    vol_multiplier=4.0,
    drawdown_multiplier=2.5,
    liquidity_multiplier=4.0,
    execution_multiplier=3.5,
    regime_impact="adversarial",
    probability=0.05,
    tags=["flash", "hft", "structural"],
)

# Complete built-in library
BUILTIN_SCENARIOS: List[StressScenario] = [
    MARKET_CRASH,
    VOLATILITY_SPIKE,
    LIQUIDITY_SHOCK,
    GAP_EVENT,
    CORRELATION_BREAKDOWN,
    EXTREME_TREND,
    EXTREME_RANGE,
    FLASH_CRASH,
]
