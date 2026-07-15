"""iios/investment/portfolio/rebalancing/policy_registry.py

Built-in institutional rebalancing policies.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.portfolio.rebalancing.rebalance_policy import (
    PolicyParameters, RebalancePolicy,
)
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    CALENDAR_ANNUAL_DAYS, CALENDAR_MONTHLY_DAYS, CALENDAR_QUARTERLY_DAYS,
    DRIFT_THRESHOLD_CRITICAL, DRIFT_THRESHOLD_MODERATE, DRIFT_THRESHOLD_SIGNIFICANT,
    PolicyType, RebalanceTrigger,
)

# Fixed UUIDs so policies are stable across runs
_THRESHOLD_ID    = "00000000-0000-0000-0000-000000000001"
_MONTHLY_ID      = "00000000-0000-0000-0000-000000000002"
_QUARTERLY_ID    = "00000000-0000-0000-0000-000000000003"
_ANNUAL_ID       = "00000000-0000-0000-0000-000000000004"
_RISK_BASED_ID   = "00000000-0000-0000-0000-000000000005"
_DRIFT_BASED_ID  = "00000000-0000-0000-0000-000000000006"
_TAX_AWARE_ID    = "00000000-0000-0000-0000-000000000007"
_HYBRID_ID       = "00000000-0000-0000-0000-000000000008"
_CONSERVATIVE_ID = "00000000-0000-0000-0000-000000000009"
_AGGRESSIVE_ID   = "00000000-0000-0000-0000-000000000010"


BUILT_IN_POLICIES: Dict[str, RebalancePolicy] = {
    "threshold": RebalancePolicy(
        policy_id   = _THRESHOLD_ID,
        name        = "Threshold Rebalancing",
        description = "Rebalance when any position drifts ≥ 5% from target",
        policy_type = PolicyType.THRESHOLD,
        trigger     = RebalanceTrigger.THRESHOLD,
        parameters  = PolicyParameters(
            drift_threshold         = DRIFT_THRESHOLD_MODERATE,
            calendar_frequency_days = 0,   # not calendar-driven
            tax_aware               = True,
        ),
        is_default  = True,
    ),
    "calendar_monthly": RebalancePolicy(
        policy_id   = _MONTHLY_ID,
        name        = "Monthly Calendar Rebalancing",
        description = "Rebalance on the first business day of each month",
        policy_type = PolicyType.CALENDAR,
        trigger     = RebalanceTrigger.CALENDAR,
        parameters  = PolicyParameters(
            drift_threshold         = 0.15,  # only check cost; calendar drives it
            calendar_frequency_days = CALENDAR_MONTHLY_DAYS,
            max_turnover_per_rebal  = 0.20,
        ),
    ),
    "calendar_quarterly": RebalancePolicy(
        policy_id   = _QUARTERLY_ID,
        name        = "Quarterly Calendar Rebalancing",
        description = "Rebalance every quarter",
        policy_type = PolicyType.CALENDAR,
        trigger     = RebalanceTrigger.CALENDAR,
        parameters  = PolicyParameters(
            drift_threshold         = 0.15,
            calendar_frequency_days = CALENDAR_QUARTERLY_DAYS,
            max_turnover_per_rebal  = 0.25,
        ),
    ),
    "calendar_annual": RebalancePolicy(
        policy_id   = _ANNUAL_ID,
        name        = "Annual Calendar Rebalancing",
        description = "Rebalance once per year",
        policy_type = PolicyType.CALENDAR,
        trigger     = RebalanceTrigger.CALENDAR,
        parameters  = PolicyParameters(
            drift_threshold         = 0.20,
            calendar_frequency_days = CALENDAR_ANNUAL_DAYS,
            max_turnover_per_rebal  = 0.40,
        ),
    ),
    "risk_based": RebalancePolicy(
        policy_id   = _RISK_BASED_ID,
        name        = "Risk-Based Rebalancing",
        description = "Rebalance when portfolio risk exceeds target risk by > 10%",
        policy_type = PolicyType.RISK_BASED,
        trigger     = RebalanceTrigger.RISK_BASED,
        parameters  = PolicyParameters(
            drift_threshold     = DRIFT_THRESHOLD_SIGNIFICANT,
            max_portfolio_risk  = 0.65,
            min_liquidity       = 0.50,
        ),
    ),
    "drift_based": RebalancePolicy(
        policy_id   = _DRIFT_BASED_ID,
        name        = "Drift-Based Rebalancing",
        description = "Rebalance when total allocation drift exceeds 8%",
        policy_type = PolicyType.DRIFT_BASED,
        trigger     = RebalanceTrigger.DRIFT_BASED,
        parameters  = PolicyParameters(
            drift_threshold     = DRIFT_THRESHOLD_SIGNIFICANT,
            max_position_drift  = DRIFT_THRESHOLD_CRITICAL,
        ),
    ),
    "tax_aware": RebalancePolicy(
        policy_id   = _TAX_AWARE_ID,
        name        = "Tax-Aware Rebalancing",
        description = "Rebalance minimising tax impact; prefer LTCG positions for selling",
        policy_type = PolicyType.TAX_AWARE,
        trigger     = RebalanceTrigger.TAX_AWARE,
        parameters  = PolicyParameters(
            drift_threshold         = DRIFT_THRESHOLD_MODERATE,
            tax_aware               = True,
            avoid_stcg_sells        = True,
            min_tax_saving_to_harvest = 0.005,
        ),
    ),
    "hybrid": RebalancePolicy(
        policy_id   = _HYBRID_ID,
        name        = "Hybrid Rebalancing",
        description = "Combines threshold + calendar + tax-aware triggers",
        policy_type = PolicyType.HYBRID,
        trigger     = RebalanceTrigger.HYBRID,
        parameters  = PolicyParameters(
            drift_threshold         = DRIFT_THRESHOLD_MODERATE,
            calendar_frequency_days = CALENDAR_QUARTERLY_DAYS,
            tax_aware               = True,
            avoid_stcg_sells        = True,
            min_benefit_cost_ratio  = 1.5,
        ),
    ),
    "conservative": RebalancePolicy(
        policy_id   = _CONSERVATIVE_ID,
        name        = "Conservative Institutional Policy",
        description = "Low turnover, high cost threshold, LTCG-only sells",
        policy_type = PolicyType.HYBRID,
        trigger     = RebalanceTrigger.HYBRID,
        parameters  = PolicyParameters(
            drift_threshold         = DRIFT_THRESHOLD_CRITICAL,
            calendar_frequency_days = CALENDAR_ANNUAL_DAYS,
            max_turnover_per_rebal  = 0.15,
            tax_aware               = True,
            avoid_stcg_sells        = True,
            min_benefit_cost_ratio  = 2.0,
        ),
    ),
    "aggressive": RebalancePolicy(
        policy_id   = _AGGRESSIVE_ID,
        name        = "Active Management Policy",
        description = "Low threshold, frequent rebalancing for high-conviction portfolios",
        policy_type = PolicyType.THRESHOLD,
        trigger     = RebalanceTrigger.THRESHOLD,
        parameters  = PolicyParameters(
            drift_threshold         = 0.03,   # 3% threshold
            calendar_frequency_days = CALENDAR_MONTHLY_DAYS,
            max_turnover_per_rebal  = 0.40,
            min_benefit_cost_ratio  = 1.2,
            tax_aware               = False,
        ),
    ),
}


class PolicyRegistry:
    """Registry of built-in and custom rebalancing policies."""

    def __init__(self) -> None:
        self._store: Dict[str, RebalancePolicy] = dict(BUILT_IN_POLICIES)

    def get(self, policy_id: str) -> Optional[RebalancePolicy]:
        return self._store.get(policy_id)

    def get_or_default(self, policy_id: str = "threshold") -> RebalancePolicy:
        return self._store.get(policy_id, BUILT_IN_POLICIES["threshold"])

    def register(self, policy: RebalancePolicy) -> None:
        self._store[policy.policy_id] = policy

    def list_ids(self) -> List[str]:
        return list(self._store.keys())

    def all(self) -> Dict[str, RebalancePolicy]:
        return dict(self._store)

    def default_policy(self) -> RebalancePolicy:
        return BUILT_IN_POLICIES["threshold"]
