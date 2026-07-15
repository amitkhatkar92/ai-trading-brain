"""iios/investment/portfolio/rebalancing/cost_validator.py

Cost effectiveness validation for rebalancing plans.
"""
from __future__ import annotations

from typing import Any, List

from iios.investment.portfolio.rebalancing.allocation_drift import AllocationDrift
from iios.investment.portfolio.rebalancing.execution_estimator import ExecutionEstimate
from iios.investment.portfolio.rebalancing.rebalancing_types import ValidationStatus
from iios.investment.portfolio.rebalancing.trade_planner import TradePlan
from iios.investment.portfolio.rebalancing.validation_report import (
    ValidationCheck, ValidationReport, build_validation_report,
)


# Cost caps as fraction of portfolio value
MAX_ACCEPTABLE_COST_PCT   = 0.010   # 1.0% total rebalancing cost
WARNING_COST_PCT          = 0.005   # 0.5% triggers warning
MAX_TAX_COST_PCT          = 0.005   # 0.5% tax cap


class CostValidator:
    """Validates the cost effectiveness of a rebalancing plan."""

    def validate(
        self,
        trade_plan:    TradePlan,
        execution_est: Any,
        alloc_drift:   AllocationDrift,
        portfolio_id:  str = "",
    ) -> ValidationReport:
        checks: List[ValidationCheck] = []

        # Normalise None execution_est to an empty estimate
        if execution_est is None:
            execution_est = ExecutionEstimate()

        # 1. Total cost cap
        total_cost = execution_est.total_cost_pct
        if total_cost > MAX_ACCEPTABLE_COST_PCT:
            checks.append(ValidationCheck(
                check_id    = "total_cost_cap",
                description = "Total rebalancing cost within acceptable range",
                status      = ValidationStatus.FAILED,
                detail      = f"Total cost {total_cost:.3%} exceeds cap {MAX_ACCEPTABLE_COST_PCT:.3%}",
                severity    = "error",
            ))
        elif total_cost > WARNING_COST_PCT:
            checks.append(ValidationCheck(
                check_id    = "total_cost_cap",
                description = "Total rebalancing cost within acceptable range",
                status      = ValidationStatus.WARNING,
                detail      = f"Total cost {total_cost:.3%} approaching cap {MAX_ACCEPTABLE_COST_PCT:.3%}",
                severity    = "warning",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "total_cost_cap",
                description = "Total rebalancing cost within acceptable range",
                status      = ValidationStatus.PASSED,
                detail      = f"Total cost {total_cost:.3%} within acceptable range",
            ))

        # 2. Tax cost sanity
        if execution_est.total_tax_cost > MAX_TAX_COST_PCT:
            checks.append(ValidationCheck(
                check_id    = "tax_cost_cap",
                description = "Tax cost within acceptable range",
                status      = ValidationStatus.WARNING,
                detail      = f"Tax cost {execution_est.total_tax_cost:.3%} > {MAX_TAX_COST_PCT:.3%}",
                severity    = "warning",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "tax_cost_cap",
                description = "Tax cost within acceptable range",
                status      = ValidationStatus.PASSED,
            ))

        # 3. Drift vs cost proportionality
        # Expected reduction: drift × 0.3 benefit factor
        expected_reduction = alloc_drift.total_abs_drift * 0.3
        if total_cost > 0 and expected_reduction < total_cost:
            checks.append(ValidationCheck(
                check_id    = "drift_cost_proportion",
                description = "Drift reduction justifies cost",
                status      = ValidationStatus.WARNING,
                detail      = f"Expected reduction {expected_reduction:.3%} < cost {total_cost:.3%}",
                severity    = "warning",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "drift_cost_proportion",
                description = "Drift reduction justifies cost",
                status      = ValidationStatus.PASSED,
            ))

        # 4. Market impact check
        if execution_est.total_market_impact > execution_est.total_transaction_cost:
            checks.append(ValidationCheck(
                check_id    = "market_impact",
                description = "Market impact within normal range",
                status      = ValidationStatus.WARNING,
                detail      = f"Market impact {execution_est.total_market_impact:.4%} "
                              f"> transaction cost {execution_est.total_transaction_cost:.4%}",
                severity    = "warning",
            ))
        else:
            checks.append(ValidationCheck(
                check_id    = "market_impact",
                description = "Market impact within normal range",
                status      = ValidationStatus.PASSED,
            ))

        return build_validation_report(checks, portfolio_id)
