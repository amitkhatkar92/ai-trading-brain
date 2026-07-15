"""iios/investment/portfolio/recommendation/recommendation_registry.py

Built-in institutional recommendation policies with stable IDs.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.portfolio.recommendation.recommendation_policies import (
    InstitutionalPolicy, PolicyParameters,
)
from iios.investment.portfolio.recommendation.recommendation_types import PolicyType

# Stable fixed IDs
_BALANCED_ID       = "00000000-0000-0000-0000-000000000101"
_CONSERVATIVE_ID   = "00000000-0000-0000-0000-000000000102"
_AGGRESSIVE_ID     = "00000000-0000-0000-0000-000000000103"
_INCOME_ID         = "00000000-0000-0000-0000-000000000104"
_GROWTH_ID         = "00000000-0000-0000-0000-000000000105"
_RISK_FIRST_ID     = "00000000-0000-0000-0000-000000000106"
_QUALITY_DRIVEN_ID = "00000000-0000-0000-0000-000000000107"


BUILT_IN_POLICIES: Dict[str, InstitutionalPolicy] = {
    "balanced": InstitutionalPolicy(
        policy_id    = _BALANCED_ID,
        name         = "Balanced Institutional Policy",
        description  = "Moderate risk tolerance; balanced between growth and capital preservation",
        policy_type  = PolicyType.BALANCED,
        parameters   = PolicyParameters(),   # all defaults
        is_default   = True,
    ),
    "conservative": InstitutionalPolicy(
        policy_id    = _CONSERVATIVE_ID,
        name         = "Conservative Institutional Policy",
        description  = "Low risk tolerance; capital preservation priority",
        policy_type  = PolicyType.CONSERVATIVE,
        parameters   = PolicyParameters(
            risk_budget_high_threshold   = 0.70,   # more sensitive to risk
            drawdown_severe_threshold    = 0.08,   # trigger defence earlier
            equity_overweight_threshold  = 0.07,
            equity_underweight_threshold = 0.07,
            hhi_concentrated_threshold   = 0.20,
            sharpe_poor_threshold        = 0.50,
            min_confidence_to_publish    = 0.60,
            require_approval_for_high_risk = True,
            default_expiry_hours         = 12.0,
        ),
    ),
    "aggressive": InstitutionalPolicy(
        policy_id    = _AGGRESSIVE_ID,
        name         = "Aggressive Growth Policy",
        description  = "High risk tolerance; maximum return focus",
        policy_type  = PolicyType.AGGRESSIVE,
        parameters   = PolicyParameters(
            risk_budget_high_threshold   = 0.95,   # tolerate higher risk
            drawdown_severe_threshold    = 0.25,
            equity_underweight_threshold = 0.15,
            cash_high_threshold          = 0.10,   # deploy cash faster
            sharpe_poor_threshold        = 0.10,
            min_confidence_to_publish    = 0.40,
            default_expiry_hours         = 8.0,
        ),
    ),
    "income": InstitutionalPolicy(
        policy_id    = _INCOME_ID,
        name         = "Income-Focused Policy",
        description  = "Yield and income generation; lower equity / higher bond preference",
        policy_type  = PolicyType.INCOME,
        parameters   = PolicyParameters(
            equity_overweight_threshold  = 0.08,
            equity_underweight_threshold = 0.05,   # quick to add equity if yield low
            sharpe_poor_threshold        = 0.20,
            construction_quality_min     = 0.50,
            optimization_quality_min     = 0.50,
        ),
    ),
    "growth": InstitutionalPolicy(
        policy_id    = _GROWTH_ID,
        name         = "Growth-Oriented Policy",
        description  = "Equity-heavy; performance and optimization-driven triggers",
        policy_type  = PolicyType.GROWTH,
        parameters   = PolicyParameters(
            equity_underweight_threshold = 0.08,
            optimization_quality_min     = 0.60,   # higher quality gate
            sharpe_poor_threshold        = 0.40,
            cash_high_threshold          = 0.12,   # deploy cash into equities faster
        ),
    ),
    "risk_first": InstitutionalPolicy(
        policy_id    = _RISK_FIRST_ID,
        name         = "Risk-First Policy",
        description  = "Risk metrics dominate all recommendation triggers",
        policy_type  = PolicyType.RISK_FIRST,
        parameters   = PolicyParameters(
            risk_budget_high_threshold   = 0.75,
            var_critical_threshold       = 0.80,
            drawdown_severe_threshold    = 0.10,
            require_approval_for_high_risk = True,
            min_confidence_to_publish    = 0.55,
        ),
    ),
    "quality_driven": InstitutionalPolicy(
        policy_id    = _QUALITY_DRIVEN_ID,
        name         = "Quality-Driven Policy",
        description  = "Construction and optimization quality drive recommendations",
        policy_type  = PolicyType.QUALITY_DRIVEN,
        parameters   = PolicyParameters(
            construction_quality_min     = 0.60,
            optimization_quality_min     = 0.60,
            sharpe_poor_threshold        = 0.50,
            min_confidence_to_publish    = 0.55,
        ),
    ),
}


class RecommendationPolicyRegistry:
    """Thread-safe registry for institutional recommendation policies."""

    def __init__(self) -> None:
        self._lock     = threading.RLock()
        self._policies = dict(BUILT_IN_POLICIES)

    def get(self, policy_id: str) -> Optional[InstitutionalPolicy]:
        with self._lock:
            return self._policies.get(policy_id)

    def get_or_default(self, policy_id: Optional[str]) -> InstitutionalPolicy:
        with self._lock:
            if policy_id:
                if policy_id in self._policies:
                    return self._policies[policy_id]
                # Fall back to UUID lookup across all policy values
                for p in self._policies.values():
                    if p.policy_id == policy_id:
                        return p
            return self.default_policy()

    def default_policy(self) -> InstitutionalPolicy:
        with self._lock:
            for p in self._policies.values():
                if p.is_default:
                    return p
            return next(iter(self._policies.values()))

    def register(self, policy: InstitutionalPolicy) -> None:
        with self._lock:
            self._policies[policy.policy_id] = policy

    def list_ids(self) -> List[str]:
        with self._lock:
            return list(self._policies.keys())

    def all(self) -> List[InstitutionalPolicy]:
        with self._lock:
            return list(self._policies.values())
