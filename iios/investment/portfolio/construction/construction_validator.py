"""iios/investment/portfolio/construction/construction_validator.py

Validates that a PortfolioBlueprint is consistent with the ConstructionRequest
that generated it — checks policy compliance, recommendation alignment, and
construction-type-specific rules.
"""
from __future__ import annotations

import time
from typing import Any, List

from iios.investment.portfolio.construction.construction_types import (
    ConstructionType,
    ValidationCategory,
)
from iios.investment.portfolio.construction.validation_report import (
    ValidationFinding,
    ValidationReport,
    _fail,
    _pass,
    _warn,
    build_report,
)


class ConstructionValidator:
    """
    Cross-checks the blueprint against the ConstructionRequest:

    • Holdings count within [min_holdings, max_holdings]
    • No SHORT slots when allow_short=False
    • Market-neutral: long exposure ≈ short exposure
    • Single-weight bounds from request respected
    • Sector / asset class weight limits not exceeded
    • Blueprint construction_type matches request
    • Cash weight within [min_cash, 1.0]
    """

    VALIDATOR_NAME = "construction_validator"

    def validate(self, blueprint: Any, request: Any) -> ValidationReport:
        t0 = time.monotonic()
        findings: List[ValidationFinding] = []

        findings.extend(self._check_holdings_count(blueprint, request))
        findings.extend(self._check_direction_policy(blueprint, request))
        findings.extend(self._check_market_neutral(blueprint, request))
        findings.extend(self._check_single_weight_bounds(blueprint, request))
        findings.extend(self._check_sector_limit(blueprint, request))
        findings.extend(self._check_asset_class_limit(blueprint, request))
        findings.extend(self._check_cash_weight(blueprint, request))
        findings.extend(self._check_construction_type(blueprint, request))
        findings.extend(self._check_recommendation_alignment(blueprint, request))

        duration_ms = (time.monotonic() - t0) * 1000.0
        return build_report(
            findings,
            validator=self.VALIDATOR_NAME,
            blueprint_id=blueprint.blueprint_id,
            portfolio_id=blueprint.portfolio_id,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def _check_holdings_count(self, bp: Any, req: Any) -> List[ValidationFinding]:
        n = bp.total_slots
        if n < req.min_holdings:
            return [_fail(
                ValidationCategory.COMPLETENESS,
                "holdings_count_min",
                f"Holdings count {n} below min {req.min_holdings}",
                actual=n, expected=req.min_holdings,
            )]
        if n > req.max_holdings:
            return [_fail(
                ValidationCategory.COMPLETENESS,
                "holdings_count_max",
                f"Holdings count {n} exceeds max {req.max_holdings}",
                actual=n, expected=req.max_holdings,
            )]
        return [_pass(
            ValidationCategory.COMPLETENESS,
            "holdings_count",
            f"Holdings count {n} in [{req.min_holdings}, {req.max_holdings}]",
        )]

    def _check_direction_policy(self, bp: Any, req: Any) -> List[ValidationFinding]:
        if not req.allow_short and bp.short_count > 0:
            return [_fail(
                ValidationCategory.POLICY_COMPLIANCE,
                "no_short_positions",
                f"Blueprint contains {bp.short_count} short position(s) but allow_short=False",
                actual=bp.short_count, expected=0,
            )]
        return [_pass(ValidationCategory.POLICY_COMPLIANCE, "direction_policy")]

    def _check_market_neutral(self, bp: Any, req: Any) -> List[ValidationFinding]:
        if req.construction_type != ConstructionType.MARKET_NEUTRAL:
            return []
        net = abs(bp.net_exposure)
        if net > 0.05:   # 5% tolerance
            return [_warn(
                ValidationCategory.POLICY_COMPLIANCE,
                "market_neutral_exposure",
                f"Net exposure {net:.4f} > 5% tolerance for MARKET_NEUTRAL construction",
                actual=net, expected=0.0,
            )]
        return [_pass(ValidationCategory.POLICY_COMPLIANCE, "market_neutral_exposure")]

    def _check_single_weight_bounds(self, bp: Any, req: Any) -> List[ValidationFinding]:
        findings: List[ValidationFinding] = []
        for slot in bp.slots:
            aw = abs(slot.target_weight)
            if aw > req.max_single_weight + 1e-9:
                findings.append(_fail(
                    ValidationCategory.CONSTRAINT_COMPLIANCE,
                    "max_single_weight",
                    f"{slot.symbol}: weight {aw:.4f} > max {req.max_single_weight:.4f}",
                    symbol=slot.symbol, actual=aw, expected=req.max_single_weight,
                ))
        if not findings:
            findings.append(_pass(
                ValidationCategory.CONSTRAINT_COMPLIANCE, "single_weight_bounds"
            ))
        return findings

    def _check_sector_limit(self, bp: Any, req: Any) -> List[ValidationFinding]:
        violations: List[str] = []
        for sector, w in bp.sector_weights.items():
            if w > req.max_sector_weight + 1e-9:
                violations.append(f"'{sector}': {w:.4f} > {req.max_sector_weight:.4f}")
        if violations:
            return [_fail(
                ValidationCategory.CONSTRAINT_COMPLIANCE,
                "sector_weight_limit",
                f"Sector weight exceeded: {'; '.join(violations)}",
                details={"violations": violations},
            )]
        return [_pass(ValidationCategory.CONSTRAINT_COMPLIANCE, "sector_weight_limit")]

    def _check_asset_class_limit(self, bp: Any, req: Any) -> List[ValidationFinding]:
        violations: List[str] = []
        for ac, w in bp.asset_class_weights.items():
            if w > req.max_asset_class_weight + 1e-9:
                violations.append(f"'{ac}': {w:.4f} > {req.max_asset_class_weight:.4f}")
        if violations:
            return [_fail(
                ValidationCategory.CONSTRAINT_COMPLIANCE,
                "asset_class_weight_limit",
                f"Asset class weight exceeded: {'; '.join(violations)}",
                details={"violations": violations},
            )]
        return [_pass(ValidationCategory.CONSTRAINT_COMPLIANCE, "asset_class_weight_limit")]

    def _check_cash_weight(self, bp: Any, req: Any) -> List[ValidationFinding]:
        cash = bp.cash_weight
        if cash < req.target_cash_pct - 0.01:   # 1% tolerance
            return [_warn(
                ValidationCategory.CONSTRAINT_COMPLIANCE,
                "cash_weight",
                f"Cash {cash:.4f} below target {req.target_cash_pct:.4f} (−1% tol)",
                actual=cash, expected=req.target_cash_pct,
            )]
        return [_pass(
            ValidationCategory.CONSTRAINT_COMPLIANCE, "cash_weight",
            f"Cash weight {cash:.4f} ≥ target {req.target_cash_pct:.4f}",
        )]

    def _check_construction_type(self, bp: Any, req: Any) -> List[ValidationFinding]:
        if bp.construction_type != req.construction_type:
            return [_fail(
                ValidationCategory.CONSISTENCY,
                "construction_type_match",
                f"Blueprint type {bp.construction_type.value} != request type {req.construction_type.value}",
                actual=bp.construction_type.value,
                expected=req.construction_type.value,
            )]
        return [_pass(ValidationCategory.CONSISTENCY, "construction_type_match")]

    def _check_recommendation_alignment(self, bp: Any, req: Any) -> List[ValidationFinding]:
        """Warn if no recommendation_ids are recorded in the blueprint."""
        if not bp.recommendation_ids:
            return [_warn(
                ValidationCategory.INTEGRITY,
                "recommendation_ids_present",
                "Blueprint has no recommendation_ids — cannot trace to source decisions",
                field_name="recommendation_ids",
            )]
        return [_pass(
            ValidationCategory.INTEGRITY,
            "recommendation_ids_present",
            f"Blueprint traces {len(bp.recommendation_ids)} recommendation(s)",
        )]
