"""iios/investment/portfolio/rebalancing/policy_validator.py

Policy compliance validation for rebalancing plans.
"""
from __future__ import annotations

from typing import List

from iios.investment.portfolio.rebalancing.execution_estimator import ExecutionEstimate
from iios.investment.portfolio.rebalancing.rebalance_policy import RebalancePolicy
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    CurrentPosition, TargetPosition, ValidationStatus,
)
from iios.investment.portfolio.rebalancing.trade_planner import TradePlan
from iios.investment.portfolio.rebalancing.validation_report import (
    ValidationCheck, ValidationReport, build_validation_report,
)


class PolicyValidator:
    """Validates a trade plan against institutional policy constraints."""

    def validate(
        self,
        trade_plan:       TradePlan,
        policy:           RebalancePolicy,
        current:          List[CurrentPosition],
        target:           List[TargetPosition],
        execution_est:    ExecutionEstimate,
    ) -> ValidationReport:
        checks: List[ValidationCheck] = []
        params = policy.parameters

        # 1. Turnover limit
        if trade_plan.total_turnover > params.max_turnover_per_rebal:
            checks.append(ValidationCheck(
                check_id    = "turnover_limit",
                description = "Turnover within policy limit",
                status      = ValidationStatus.FAILED,
                detail      = f"Turnover {trade_plan.total_turnover:.1%} > "
                              f"limit {params.max_turnover_per_rebal:.1%}",
                severity    = "error",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "turnover_limit",
                description = "Turnover within policy limit",
                status      = ValidationStatus.PASSED,
                detail      = f"Turnover {trade_plan.total_turnover:.1%} ≤ "
                              f"limit {params.max_turnover_per_rebal:.1%}",
            ))

        # 2. Minimum trade size (no position change below minimum)
        tiny_trades = [c for c in trade_plan.changes if c.abs_change < params.min_trade_size]
        if tiny_trades:
            checks.append(ValidationCheck(
                check_id    = "min_trade_size",
                description = "No micro-trades below minimum size",
                status      = ValidationStatus.WARNING,
                detail      = f"{len(tiny_trades)} trades below min size {params.min_trade_size:.1%}",
                severity    = "warning",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "min_trade_size",
                description = "No micro-trades below minimum size",
                status      = ValidationStatus.PASSED,
            ))

        # 3. Tax-aware STCG check
        if params.tax_aware and params.avoid_stcg_sells:
            from iios.investment.portfolio.rebalancing.rebalancing_types import TradeSide
            stcg_sells = [
                c for c in trade_plan.changes
                if c.trade_side == TradeSide.SELL
                and not c.is_ltcg_eligible
                and not c.is_full_exit
            ]
            if stcg_sells:
                checks.append(ValidationCheck(
                    check_id    = "stcg_avoidance",
                    description = "Avoid STCG sells per tax-aware policy",
                    status      = ValidationStatus.WARNING,
                    detail      = f"{len(stcg_sells)} STCG sell(s) included despite avoidance policy",
                    severity    = "warning",
                ))
            else:
                checks.append(ValidationCheck(
                    check_id    = "stcg_avoidance",
                    description = "Avoid STCG sells per tax-aware policy",
                    status      = ValidationStatus.PASSED,
                ))

        # 4. Benefit-cost ratio
        estimated_benefit = _estimate_drift_reduction_benefit(trade_plan)
        cost = execution_est.total_cost_pct
        bc_ratio = estimated_benefit / max(cost, 1e-10)
        if bc_ratio < params.min_benefit_cost_ratio:
            checks.append(ValidationCheck(
                check_id    = "benefit_cost_ratio",
                description = "Benefit/cost ratio above minimum",
                status      = ValidationStatus.WARNING,
                detail      = f"B/C ratio {bc_ratio:.2f} < policy min {params.min_benefit_cost_ratio:.2f}",
                severity    = "warning",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "benefit_cost_ratio",
                description = "Benefit/cost ratio above minimum",
                status      = ValidationStatus.PASSED,
                detail      = f"B/C ratio {bc_ratio:.2f} ≥ policy min",
            ))

        # 5. Target weight integrity (weights sum to ~1.0)
        total_target_w = sum(p.target_weight for p in target)
        if abs(total_target_w - 1.0) > 0.02:
            checks.append(ValidationCheck(
                check_id    = "weight_integrity",
                description = "Target weights sum to 1.0",
                status      = ValidationStatus.FAILED,
                detail      = f"Target weights sum to {total_target_w:.4f} (expected 1.0 ± 2%)",
                severity    = "error",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "weight_integrity",
                description = "Target weights sum to 1.0",
                status      = ValidationStatus.PASSED,
            ))

        return build_validation_report(checks, trade_plan.portfolio_id)


def _estimate_drift_reduction_benefit(trade_plan: TradePlan) -> float:
    """Rough estimate: benefit ≈ turnover × 0.02 (drift × performance improvement proxy)."""
    return trade_plan.total_turnover * 0.02
