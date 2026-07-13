"""iios/investment/strategy/risk/risk_policy.py
RiskPolicy — composite policy combining limits, analysis preferences, and flags.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.strategy.risk.risk_limits import (
    RiskLimits, DEFAULT_LIMITS, CONSERVATIVE_LIMITS,
    AGGRESSIVE_LIMITS, INSTITUTIONAL_LIMITS
)
from iios.investment.strategy.risk.stress_scenarios import StressScenario, BUILTIN_SCENARIOS


@dataclass(frozen=True)
class RiskPolicy:
    """
    A named policy that bundles limits, scenario selection, and analysis flags.
    Pluggable: create custom policies for different strategy profiles.
    """
    policy_name: str = "default"
    limits:      RiskLimits = field(default_factory=lambda: DEFAULT_LIMITS)

    # Which scenarios to include in stress testing
    stress_scenarios: List[StressScenario] = field(default_factory=lambda: BUILTIN_SCENARIOS)

    # Analysis preferences
    enable_drawdown_analysis: bool = True
    enable_stress_testing:    bool = True
    enable_limit_monitoring:  bool = True

    # VaR / CVaR confidence
    var_confidence: float = 0.95   # 95% VaR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":             self.policy_name,
            "limits":                  self.limits.to_dict(),
            "scenario_count":          len(self.stress_scenarios),
            "enable_drawdown":         self.enable_drawdown_analysis,
            "enable_stress_testing":   self.enable_stress_testing,
            "enable_limit_monitoring": self.enable_limit_monitoring,
            "var_confidence":          self.var_confidence,
        }


# ── Built-in policies ─────────────────────────────────────────────────────────

DEFAULT_POLICY = RiskPolicy(policy_name="default")

CONSERVATIVE_POLICY = RiskPolicy(
    policy_name="conservative",
    limits=CONSERVATIVE_LIMITS,
)

AGGRESSIVE_POLICY = RiskPolicy(
    policy_name="aggressive",
    limits=AGGRESSIVE_LIMITS,
)

INSTITUTIONAL_POLICY = RiskPolicy(
    policy_name="institutional",
    limits=INSTITUTIONAL_LIMITS,
    var_confidence=0.99,
)
