"""iios/investment/portfolio/integration/consistency_validator.py

Runs all cross-engine consistency rules and returns a ConsistencyValidationReport.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.portfolio.integration.consistency_rules import (
    check_allocation_weights_sum,
    check_construction_allocation_position_count,
    check_diversification_hhi,
    check_optimization_vs_construction_quality,
    check_rebalancing_vs_allocation_drift,
    check_recommendation_vs_risk_budget,
    check_risk_performance_drawdown,
)
from iios.investment.portfolio.integration.integration_types import (
    IntegrationParameters, ValidationStatus,
)
from iios.investment.portfolio.integration.validation_report import (
    ConsistencyValidationReport, ValidationCheck,
)


def _build_report(
    checks:       List[ValidationCheck],
    portfolio_id: str = "",
) -> ConsistencyValidationReport:
    n_passed   = sum(1 for c in checks if c.status == ValidationStatus.PASSED)
    n_warnings = sum(1 for c in checks if c.status == ValidationStatus.WARNING)
    n_failed   = sum(1 for c in checks if c.status == ValidationStatus.FAILED)
    n_total    = len(checks)

    if n_failed > 0:
        overall = ValidationStatus.FAILED
    elif n_warnings > 0:
        overall = ValidationStatus.WARNING
    else:
        overall = ValidationStatus.PASSED

    score    = (n_passed + 0.5 * n_warnings) / n_total if n_total > 0 else 1.0
    failures = [c.detail for c in checks if c.status == ValidationStatus.FAILED]
    warns    = [c.detail for c in checks if c.status == ValidationStatus.WARNING]

    return ConsistencyValidationReport(
        portfolio_id      = portfolio_id,
        overall_status    = overall,
        is_consistent     = n_failed == 0,
        checks            = tuple(checks),
        n_passed          = n_passed,
        n_warnings        = n_warnings,
        n_failed          = n_failed,
        consistency_score = round(score, 4),
        primary_issue     = failures[0] if failures else None,
        warnings          = tuple(warns),
    )


class ConsistencyValidator:
    """Validates cross-engine consistency using pure rule functions."""

    def __init__(self, params: Optional[IntegrationParameters] = None) -> None:
        self._params = params or IntegrationParameters()

    def validate(
        self,
        merged:       Dict[str, Any],
        portfolio_id: str = "",
    ) -> ConsistencyValidationReport:
        checks: List[ValidationCheck] = []

        alloc  = merged.get("allocation",      {})
        constr = merged.get("construction",    {})
        optim  = merged.get("optimization",    {})
        risk   = merged.get("risk",            {})
        perf   = merged.get("performance",     {})
        rebal  = merged.get("rebalancing",     {})
        rec    = merged.get("recommendation",  {})
        div    = merged.get("diversification", {})

        # 1. Allocation weights sum to 1.0
        if alloc:
            triggered, detail = check_allocation_weights_sum(alloc, tolerance=0.02)
            checks.append(ValidationCheck(
                check_id    = "alloc_weights_sum",
                description = "Allocation weights sum to 1.0",
                engine_pair = "allocation",
                status      = ValidationStatus.FAILED  if triggered else ValidationStatus.PASSED,
                detail      = detail,
                severity    = "error" if triggered else "info",
            ))

        # 2. Construction vs Allocation position count
        if constr and alloc:
            triggered, detail = check_construction_allocation_position_count(
                construction_n_positions = constr.get("n_positions", 0),
                allocation_n_positions   = alloc.get("n_positions"),
                tolerance                = 5,
            )
            checks.append(ValidationCheck(
                check_id    = "construction_allocation_positions",
                description = "Construction and allocation agree on position count",
                engine_pair = "construction:allocation",
                status      = ValidationStatus.WARNING if triggered else ValidationStatus.PASSED,
                detail      = detail,
                severity    = "warning" if triggered else "info",
            ))

        # 3. Optimization quality vs Construction quality
        if optim and constr:
            triggered, detail = check_optimization_vs_construction_quality(
                optimization_quality = optim.get("optimization_quality", 1.0),
                construction_quality = constr.get("construction_quality", 1.0),
                max_gap              = 0.40,
            )
            checks.append(ValidationCheck(
                check_id    = "optimization_construction_quality",
                description = "Optimization quality consistent with construction quality",
                engine_pair = "construction:optimization",
                status      = ValidationStatus.WARNING if triggered else ValidationStatus.PASSED,
                detail      = detail,
                severity    = "warning" if triggered else "info",
            ))

        # 4. Risk vs Performance drawdown
        if risk and perf:
            triggered, detail = check_risk_performance_drawdown(
                risk_max_drawdown        = risk.get("max_drawdown", 0.0),
                performance_max_drawdown = perf.get("max_drawdown", 0.0),
                tolerance                = 0.05,
            )
            checks.append(ValidationCheck(
                check_id    = "risk_performance_drawdown",
                description = "Risk and performance engines agree on drawdown",
                engine_pair = "risk:performance",
                status      = ValidationStatus.WARNING if triggered else ValidationStatus.PASSED,
                detail      = detail,
                severity    = "warning" if triggered else "info",
            ))

        # 5. Rebalancing vs Allocation drift alignment
        if rebal and alloc:
            triggered, detail = check_rebalancing_vs_allocation_drift(
                rebalancing_drift_level  = rebal.get("drift_level", "minor"),
                allocation_equity_drift  = alloc.get("equity_drift", 0.0),
                significant_threshold    = 0.05,
            )
            checks.append(ValidationCheck(
                check_id    = "rebalancing_allocation_drift",
                description = "Rebalancing acknowledges allocation drift",
                engine_pair = "allocation:rebalancing",
                status      = ValidationStatus.WARNING if triggered else ValidationStatus.PASSED,
                detail      = detail,
                severity    = "warning" if triggered else "info",
            ))

        # 6. Recommendation vs Risk budget alignment
        if rec and risk:
            triggered, detail = check_recommendation_vs_risk_budget(
                recommendation_action    = rec.get("primary_action", "no_action"),
                risk_budget_utilization  = risk.get("risk_budget_utilization", 0.0),
                risk_threshold           = 0.90,
            )
            checks.append(ValidationCheck(
                check_id    = "recommendation_risk_alignment",
                description = "Recommendation aligned with risk budget posture",
                engine_pair = "risk:recommendation",
                status      = ValidationStatus.FAILED  if triggered else ValidationStatus.PASSED,
                detail      = detail,
                severity    = "error" if triggered else "info",
            ))

        # 7. Diversification HHI
        if div:
            triggered, detail = check_diversification_hhi(
                hhi           = div.get("hhi", 0.0),
                hhi_threshold = 0.40,
            )
            checks.append(ValidationCheck(
                check_id    = "diversification_hhi",
                description = "Portfolio concentration within acceptable range",
                engine_pair = "diversification",
                status      = ValidationStatus.WARNING if triggered else ValidationStatus.PASSED,
                detail      = detail,
                severity    = "warning" if triggered else "info",
            ))

        if not checks:
            checks.append(ValidationCheck(
                check_id    = "no_data",
                description = "Insufficient engine data for consistency checks",
                status      = ValidationStatus.WARNING,
                detail      = "No engine contributions available",
                severity    = "warning",
            ))

        return _build_report(checks, portfolio_id)
