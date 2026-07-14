"""iios/investment/portfolio/construction/constraint_validator.py

Concrete ConstraintChecker implementations for each ConstraintType.
Each checker takes a ConstraintDefinition and a PortfolioBlueprint
and returns a ConstraintCheckRecord.
"""
from __future__ import annotations

import abc
import time
import uuid
from typing import Any, Dict, List, Optional, Type

from iios.investment.portfolio.construction.constraint_history import ConstraintCheckRecord
from iios.investment.portfolio.construction.construction_constraints import (
    AssetClassLimitConstraint,
    CashReserveConstraint,
    ConstraintDefinition,
    ESGConstraint,
    IndustryLimitConstraint,
    LeverageConstraint,
    MarketCapConstraint,
    MaxHoldingsConstraint,
    MaxSingleWeightConstraint,
    MinHoldingsConstraint,
    MinSingleWeightConstraint,
    SectorLimitConstraint,
    CustomConstraint,
)
from iios.investment.portfolio.construction.construction_types import (
    ConstraintOutcome,
    ConstraintSeverity,
    ConstraintType,
)


# ---------------------------------------------------------------------------
# Abstract checker
# ---------------------------------------------------------------------------

class ConstraintChecker(abc.ABC):
    """Evaluates a ConstraintDefinition against a PortfolioBlueprint."""

    @property
    @abc.abstractmethod
    def constraint_type(self) -> ConstraintType: ...

    @abc.abstractmethod
    def check(
        self,
        constraint: ConstraintDefinition,
        blueprint: Any,
    ) -> ConstraintCheckRecord: ...

    # ------------------------------------------------------------------
    # Helpers shared by subclasses
    # ------------------------------------------------------------------

    def _pass(
        self, c: ConstraintDefinition, blueprint: Any, msg: str = ""
    ) -> ConstraintCheckRecord:
        return ConstraintCheckRecord(
            constraint_name=c.name,
            constraint_type=c.constraint_type.value,
            severity=c.severity,
            outcome=ConstraintOutcome.PASSED,
            message=msg or f"{c.name}: passed",
            blueprint_id=blueprint.blueprint_id,
            portfolio_id=blueprint.portfolio_id,
        )

    def _fail(
        self, c: ConstraintDefinition, blueprint: Any, msg: str, details: Dict[str, Any] | None = None
    ) -> ConstraintCheckRecord:
        return ConstraintCheckRecord(
            constraint_name=c.name,
            constraint_type=c.constraint_type.value,
            severity=c.severity,
            outcome=ConstraintOutcome.VIOLATED,
            message=msg,
            blueprint_id=blueprint.blueprint_id,
            portfolio_id=blueprint.portfolio_id,
            details=details or {},
        )

    def _warn(
        self, c: ConstraintDefinition, blueprint: Any, msg: str, details: Dict[str, Any] | None = None
    ) -> ConstraintCheckRecord:
        return ConstraintCheckRecord(
            constraint_name=c.name,
            constraint_type=c.constraint_type.value,
            severity=c.severity,
            outcome=ConstraintOutcome.WARNING,
            message=msg,
            blueprint_id=blueprint.blueprint_id,
            portfolio_id=blueprint.portfolio_id,
            details=details or {},
        )


# ---------------------------------------------------------------------------
# Concrete checkers
# ---------------------------------------------------------------------------

class MaxHoldingsChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.MAX_HOLDINGS

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: MaxHoldingsConstraint
        n = blueprint.total_slots
        if n > c.max_holdings:
            return self._fail(
                c, blueprint,
                f"Holdings count {n} exceeds max {c.max_holdings}",
                {"count": n, "limit": c.max_holdings},
            )
        return self._pass(c, blueprint, f"Holdings count {n} ≤ {c.max_holdings}")


class MinHoldingsChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.MIN_HOLDINGS

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: MinHoldingsConstraint
        n = blueprint.total_slots
        if n < c.min_holdings:
            return self._fail(
                c, blueprint,
                f"Holdings count {n} below min {c.min_holdings}",
                {"count": n, "limit": c.min_holdings},
            )
        return self._pass(c, blueprint, f"Holdings count {n} ≥ {c.min_holdings}")


class MaxSingleWeightChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.MAX_WEIGHT

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: MaxSingleWeightConstraint
        violators = [
            s for s in blueprint.slots if abs(s.target_weight) > c.max_weight + 1e-9
        ]
        if violators:
            top = max(violators, key=lambda s: abs(s.target_weight))
            return self._fail(
                c, blueprint,
                f"{len(violators)} position(s) exceed max weight {c.max_weight:.4f}; "
                f"worst: {top.symbol} @ {abs(top.target_weight):.4f}",
                {"violators": [s.symbol for s in violators]},
            )
        return self._pass(c, blueprint)


class MinSingleWeightChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.MIN_WEIGHT

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: MinSingleWeightConstraint
        violators = [
            s for s in blueprint.slots if abs(s.target_weight) < c.min_weight - 1e-9
        ]
        if violators:
            return self._fail(
                c, blueprint,
                f"{len(violators)} position(s) below min weight {c.min_weight:.4f}",
                {"violators": [s.symbol for s in violators]},
            )
        return self._pass(c, blueprint)


class SectorLimitChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.SECTOR_LIMIT

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: SectorLimitConstraint
        violations: List[str] = []

        if c.sector:
            # Check one specific sector
            w = blueprint.sector_weights.get(c.sector, 0.0)
            if w > c.max_weight + 1e-9:
                violations.append(f"sector '{c.sector}' weight {w:.4f} > {c.max_weight:.4f}")
        else:
            # Check ALL sectors
            for sector, w in blueprint.sector_weights.items():
                if sector in c.excluded_sectors:
                    continue
                if w > c.max_weight + 1e-9:
                    violations.append(f"sector '{sector}' weight {w:.4f} > {c.max_weight:.4f}")

        if violations:
            return self._fail(
                c, blueprint,
                "; ".join(violations),
                {"violations": violations},
            )
        return self._pass(c, blueprint)


class IndustryLimitChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.INDUSTRY_LIMIT

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: IndustryLimitConstraint
        violations: List[str] = []

        for industry, w in blueprint.industry_weights.items():
            if c.industry and industry != c.industry:
                continue
            if w > c.max_weight + 1e-9:
                violations.append(f"industry '{industry}' weight {w:.4f} > {c.max_weight:.4f}")

        if violations:
            return self._fail(c, blueprint, "; ".join(violations), {"violations": violations})
        return self._pass(c, blueprint)


class AssetClassLimitChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.ASSET_CLASS_LIMIT

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: AssetClassLimitConstraint
        w = blueprint.asset_class_weights.get(c.asset_class.value, 0.0)
        if w > c.max_weight + 1e-9:
            return self._fail(
                c, blueprint,
                f"Asset class '{c.asset_class.value}' weight {w:.4f} > {c.max_weight:.4f}",
                {"asset_class": c.asset_class.value, "weight": w, "limit": c.max_weight},
            )
        return self._pass(c, blueprint)


class CashReserveChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.CASH_RESERVE

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: CashReserveConstraint
        cash = blueprint.cash_weight
        if cash < c.min_cash_pct - 1e-9:
            return self._fail(
                c, blueprint,
                f"Cash {cash:.4f} below minimum {c.min_cash_pct:.4f}",
                {"cash": cash, "min": c.min_cash_pct},
            )
        if cash > c.max_cash_pct + 1e-9:
            return self._warn(
                c, blueprint,
                f"Cash {cash:.4f} above recommended maximum {c.max_cash_pct:.4f}",
                {"cash": cash, "max": c.max_cash_pct},
            )
        return self._pass(c, blueprint)


class MarketCapChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.MARKET_CAP

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: MarketCapConstraint
        violators: List[str] = []
        for slot in blueprint.slots:
            mc = slot.market_cap_category
            if c.excluded_market_caps and mc in c.excluded_market_caps:
                violators.append(f"{slot.symbol}: {mc.value} is excluded")
            elif c.allowed_market_caps and mc not in c.allowed_market_caps:
                violators.append(f"{slot.symbol}: {mc.value} not in allowed set")
        if violators:
            return self._fail(c, blueprint, "; ".join(violators[:5]), {"violations": violators})
        return self._pass(c, blueprint)


class ESGChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.ESG

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: ESGConstraint
        violators = [s.symbol for s in blueprint.slots if s.symbol in c.excluded_symbols]
        if violators:
            return self._fail(
                c, blueprint,
                f"ESG-excluded symbols in portfolio: {', '.join(violators)}",
                {"excluded": violators},
            )
        return self._pass(c, blueprint)


class LeverageChecker(ConstraintChecker):
    @property
    def constraint_type(self) -> ConstraintType:
        return ConstraintType.LEVERAGE

    def check(self, constraint: ConstraintDefinition, blueprint: Any) -> ConstraintCheckRecord:
        c = constraint  # type: LeverageConstraint
        gross = blueprint.gross_exposure
        net   = abs(blueprint.net_exposure)
        if gross > c.max_gross_exposure + 1e-9:
            return self._fail(
                c, blueprint,
                f"Gross exposure {gross:.4f} > max {c.max_gross_exposure:.4f}",
                {"gross": gross, "limit": c.max_gross_exposure},
            )
        if net > c.max_net_exposure + 1e-9:
            return self._fail(
                c, blueprint,
                f"Net exposure {net:.4f} > max {c.max_net_exposure:.4f}",
                {"net": net, "limit": c.max_net_exposure},
            )
        return self._pass(c, blueprint)


# ---------------------------------------------------------------------------
# Checker registry
# ---------------------------------------------------------------------------

_DEFAULT_CHECKERS: Dict[ConstraintType, ConstraintChecker] = {
    ConstraintType.MAX_HOLDINGS:      MaxHoldingsChecker(),
    ConstraintType.MIN_HOLDINGS:      MinHoldingsChecker(),
    ConstraintType.MAX_WEIGHT:        MaxSingleWeightChecker(),
    ConstraintType.MIN_WEIGHT:        MinSingleWeightChecker(),
    ConstraintType.SECTOR_LIMIT:      SectorLimitChecker(),
    ConstraintType.INDUSTRY_LIMIT:    IndustryLimitChecker(),
    ConstraintType.ASSET_CLASS_LIMIT: AssetClassLimitChecker(),
    ConstraintType.CASH_RESERVE:      CashReserveChecker(),
    ConstraintType.MARKET_CAP:        MarketCapChecker(),
    ConstraintType.ESG:               ESGChecker(),
    ConstraintType.LEVERAGE:          LeverageChecker(),
}


def get_checker(ctype: ConstraintType) -> Optional[ConstraintChecker]:
    return _DEFAULT_CHECKERS.get(ctype)


def register_checker(ctype: ConstraintType, checker: ConstraintChecker) -> None:
    """Register a custom checker, overriding any existing one."""
    _DEFAULT_CHECKERS[ctype] = checker
