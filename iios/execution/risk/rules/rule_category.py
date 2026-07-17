"""iios/execution/risk/rules/rule_category.py
==================================================
RuleCategory — classification for all execution risk rules.

Maps to M1 RiskCategory for M2 engine bridge compatibility.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

from enum import Enum

from iios.execution.risk.lifecycle import RiskCategory as LifecycleRiskCategory


class RuleCategory(str, Enum):
    """
    Category classifying what aspect of execution risk a rule evaluates.

    Categories correspond to the 9 institutional risk domains:
    Exposure, Margin, Liquidity, Position, Execution,
    Market, Compliance, Operational, Safety.
    """
    EXPOSURE    = "EXPOSURE"
    MARGIN      = "MARGIN"
    LIQUIDITY   = "LIQUIDITY"
    POSITION    = "POSITION"
    EXECUTION   = "EXECUTION"
    MARKET      = "MARKET"
    COMPLIANCE  = "COMPLIANCE"
    OPERATIONAL = "OPERATIONAL"
    SAFETY      = "SAFETY"

    # ── M1/M2 Bridge ─────────────────────────────────────────────────────────

    def to_risk_category(self) -> LifecycleRiskCategory:
        """Map M3 RuleCategory to M1 RiskCategory for engine bridge."""
        return _CATEGORY_MAP[self]


_CATEGORY_MAP: dict[RuleCategory, LifecycleRiskCategory] = {
    RuleCategory.EXPOSURE:    LifecycleRiskCategory.EXPOSURE,
    RuleCategory.MARGIN:      LifecycleRiskCategory.MARGIN,
    RuleCategory.LIQUIDITY:   LifecycleRiskCategory.LIQUIDITY,
    RuleCategory.POSITION:    LifecycleRiskCategory.CONCENTRATION,
    RuleCategory.EXECUTION:   LifecycleRiskCategory.EXECUTION,
    RuleCategory.MARKET:      LifecycleRiskCategory.PRICE,
    RuleCategory.COMPLIANCE:  LifecycleRiskCategory.COMPLIANCE,
    RuleCategory.OPERATIONAL: LifecycleRiskCategory.OPERATIONAL,
    RuleCategory.SAFETY:      LifecycleRiskCategory.OPERATIONAL,
}
