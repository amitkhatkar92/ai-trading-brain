"""iios/investment/portfolio/rebalancing/policy_engine.py

Policy engine: evaluates which rebalancing policies are triggered.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.rebalancing.allocation_drift import AllocationDrift
from iios.investment.portfolio.rebalancing.rebalance_policy import (
    PolicyEvalResult, RebalancePolicy,
)
from iios.investment.portfolio.rebalancing.rebalance_rules import (
    evaluate_benefit_cost_rule, evaluate_calendar_rule,
    evaluate_cashflow_rule, evaluate_risk_rule,
    evaluate_tax_rule, evaluate_threshold_rule, evaluate_volatility_rule,
)
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    CurrentPosition, PolicyType, RebalanceTrigger, now_utc,
)
from iios.investment.portfolio.rebalancing.risk_drift import RiskDrift


@dataclass(frozen=True)
class PolicyEngineResult:
    """Result of policy engine evaluation."""

    eval_id:             str  = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:          str  = field(default_factory=now_utc)
    policy_id:           str  = ""
    policy_name:         str  = ""
    triggered:           bool = False
    trigger:             RebalanceTrigger = RebalanceTrigger.NONE
    confidence:          float = 0.0
    reasons:             tuple = field(default_factory=tuple)
    blocking_reasons:    tuple = field(default_factory=tuple)
    individual_results:  tuple = field(default_factory=tuple)   # PolicyEvalResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":   self.policy_id,
            "triggered":   self.triggered,
            "trigger":     self.trigger.value,
            "confidence":  round(self.confidence, 4),
            "reasons":     list(self.reasons),
            "blocking":    list(self.blocking_reasons),
        }


class PolicyEngine:
    """Evaluates rebalancing policies against current portfolio state."""

    def evaluate(
        self,
        policy:               RebalancePolicy,
        allocation_drift:     AllocationDrift,
        risk_drift:           RiskDrift,
        current_positions:    List[CurrentPosition],
        *,
        days_since_rebalance: int   = 999,
        portfolio_vol:        float = 0.15,
        net_cash_flow_pct:    float = 0.0,
        estimated_cost:       float = 0.0,
        expected_benefit:     float = 0.0,
    ) -> PolicyEngineResult:
        """
        Evaluate a single policy against portfolio state.

        Returns PolicyEngineResult describing whether rebalancing is triggered.
        """
        params   = policy.parameters
        reasons: List[str]  = []
        blocking: List[str] = []

        # Always check benefit-cost first as a blocker
        bc_ok, bc_reason = evaluate_benefit_cost_rule(
            expected_benefit, estimated_cost, params.min_benefit_cost_ratio
        )
        if estimated_cost > 1e-10 and not bc_ok:
            blocking.append(bc_reason)

        # Evaluate primary rule based on policy type
        primary_triggered = False
        primary_trigger   = RebalanceTrigger.NONE

        ptype = policy.policy_type

        if ptype in (PolicyType.THRESHOLD, PolicyType.DRIFT_BASED):
            ok, reason = evaluate_threshold_rule(allocation_drift, params.drift_threshold)
            if ok:
                primary_triggered = True
                primary_trigger   = RebalanceTrigger.THRESHOLD
                reasons.append(reason)
            else:
                reasons.append(reason)

        if ptype == PolicyType.CALENDAR:
            ok, reason = evaluate_calendar_rule(
                days_since_rebalance,
                params.calendar_frequency_days,
                params.min_days_since_rebalance,
            )
            if ok:
                primary_triggered = True
                primary_trigger   = RebalanceTrigger.CALENDAR
                reasons.append(reason)
            else:
                reasons.append(reason)

        if ptype == PolicyType.RISK_BASED:
            ok, reason = evaluate_risk_rule(
                risk_drift, params.max_portfolio_risk, params.min_liquidity
            )
            if ok:
                primary_triggered = True
                primary_trigger   = RebalanceTrigger.RISK_BASED
                reasons.append(reason)
            else:
                reasons.append(reason)

        if ptype == PolicyType.TAX_AWARE:
            ok, reason = evaluate_tax_rule(
                current_positions, params.min_tax_saving_to_harvest, params.avoid_stcg_sells
            )
            if ok:
                primary_triggered = True
                primary_trigger   = RebalanceTrigger.TAX_AWARE
                reasons.append(reason)
            else:
                reasons.append(reason)

        if ptype == PolicyType.VOLATILITY:
            ok, reason = evaluate_volatility_rule(portfolio_vol, params.max_portfolio_risk)
            if ok:
                primary_triggered = True
                primary_trigger   = RebalanceTrigger.VOLATILITY
                reasons.append(reason)
            else:
                reasons.append(reason)

        if ptype == PolicyType.HYBRID:
            # Threshold sub-rule
            ok, reason = evaluate_threshold_rule(allocation_drift, params.drift_threshold)
            if ok:
                primary_triggered = True
                primary_trigger   = RebalanceTrigger.THRESHOLD
                reasons.append(reason)
            else:
                reasons.append(reason)

            # Calendar sub-rule (if configured)
            if params.calendar_frequency_days > 0:
                ok, reason = evaluate_calendar_rule(
                    days_since_rebalance,
                    params.calendar_frequency_days,
                    params.min_days_since_rebalance,
                )
                if ok:
                    primary_triggered = True
                    primary_trigger   = RebalanceTrigger.CALENDAR
                    reasons.append(reason)
                else:
                    reasons.append(reason)

            # Tax sub-rule
            if params.tax_aware:
                ok, reason = evaluate_tax_rule(
                    current_positions,
                    params.min_tax_saving_to_harvest,
                    params.avoid_stcg_sells,
                )
                reasons.append(reason)

        # Apply blocker: if cost-ineffective, override trigger
        if blocking and primary_triggered:
            primary_triggered = False

        # Confidence: based on drift severity and trigger clarity
        confidence = _compute_confidence(allocation_drift, primary_triggered)

        return PolicyEngineResult(
            policy_id          = policy.policy_id,
            policy_name        = policy.name,
            triggered          = primary_triggered,
            trigger            = primary_trigger if primary_triggered else RebalanceTrigger.NONE,
            confidence         = round(confidence, 4),
            reasons            = tuple(reasons),
            blocking_reasons   = tuple(blocking),
        )


def _compute_confidence(drift: AllocationDrift, triggered: bool) -> float:
    """Confidence [0,1] in the rebalancing decision."""
    if not triggered:
        return 0.0
    # Higher drift → higher confidence
    drift_score = min(1.0, drift.max_abs_drift / 0.15)
    n_score     = min(1.0, drift.n_requires_rebalance / max(drift.n_positions_current, 1))
    return 0.6 * drift_score + 0.4 * n_score
