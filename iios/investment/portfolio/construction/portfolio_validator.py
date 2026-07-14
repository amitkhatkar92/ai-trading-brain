"""iios/investment/portfolio/construction/portfolio_validator.py

Validates the structural completeness and integrity of a PortfolioBlueprint.
Does not check constraint compliance (that is the ConstraintEngine's job).
"""
from __future__ import annotations

import time
from typing import Any, List

from iios.investment.portfolio.construction.construction_types import (
    WEIGHT_SUM_TOLERANCE,
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


class PortfolioValidator:
    """
    Validates blueprint structural completeness and integrity:

    • At least one position
    • No duplicate symbols
    • Weights are finite, non-negative for longs, non-positive for shorts
    • Long weights sum to approximately (1 − cash_weight)
    • No slot has an empty symbol
    • Blueprint metadata is populated
    """

    VALIDATOR_NAME = "portfolio_validator"

    def validate(self, blueprint: Any) -> ValidationReport:
        t0 = time.monotonic()
        findings: List[ValidationFinding] = []

        findings.extend(self._check_non_empty(blueprint))
        findings.extend(self._check_no_duplicate_symbols(blueprint))
        findings.extend(self._check_slot_symbols(blueprint))
        findings.extend(self._check_weight_signs(blueprint))
        findings.extend(self._check_weight_sum(blueprint))
        findings.extend(self._check_metadata(blueprint))
        findings.extend(self._check_traceability(blueprint))

        duration_ms = (time.monotonic() - t0) * 1000.0
        return build_report(
            findings,
            validator=self.VALIDATOR_NAME,
            blueprint_id=blueprint.blueprint_id,
            portfolio_id=blueprint.portfolio_id,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_non_empty(self, bp: Any) -> List[ValidationFinding]:
        if bp.is_empty:
            return [_fail(
                ValidationCategory.COMPLETENESS,
                "non_empty_blueprint",
                "Blueprint contains no positions",
                field_name="slots",
            )]
        return [_pass(
            ValidationCategory.COMPLETENESS,
            "non_empty_blueprint",
            f"Blueprint contains {bp.total_slots} position(s)",
        )]

    def _check_no_duplicate_symbols(self, bp: Any) -> List[ValidationFinding]:
        symbols = [s.symbol for s in bp.slots]
        seen: set = set()
        dupes: list = []
        for sym in symbols:
            if sym in seen:
                dupes.append(sym)
            seen.add(sym)
        if dupes:
            return [_fail(
                ValidationCategory.INTEGRITY,
                "no_duplicate_symbols",
                f"Duplicate symbols found: {', '.join(sorted(set(dupes)))}",
                details={"duplicates": sorted(set(dupes))},
            )]
        return [_pass(ValidationCategory.INTEGRITY, "no_duplicate_symbols")]

    def _check_slot_symbols(self, bp: Any) -> List[ValidationFinding]:
        empty = [i for i, s in enumerate(bp.slots) if not s.symbol.strip()]
        if empty:
            return [_fail(
                ValidationCategory.INTEGRITY,
                "all_slots_have_symbols",
                f"Slots at indices {empty} have empty symbols",
                field_name="symbol",
                details={"indices": empty},
            )]
        return [_pass(ValidationCategory.INTEGRITY, "all_slots_have_symbols")]

    def _check_weight_signs(self, bp: Any) -> List[ValidationFinding]:
        findings: List[ValidationFinding] = []
        for slot in bp.slots:
            if slot.is_long and slot.target_weight < -1e-9:
                findings.append(_fail(
                    ValidationCategory.INTEGRITY,
                    "long_slot_positive_weight",
                    f"{slot.symbol}: LONG slot has negative weight {slot.target_weight:.6f}",
                    symbol=slot.symbol,
                    actual=slot.target_weight,
                ))
            if slot.is_short and slot.target_weight > 1e-9:
                findings.append(_fail(
                    ValidationCategory.INTEGRITY,
                    "short_slot_negative_weight",
                    f"{slot.symbol}: SHORT slot has positive weight {slot.target_weight:.6f}",
                    symbol=slot.symbol,
                    actual=slot.target_weight,
                ))
            if not (-1.0 - 1e-9 <= slot.target_weight <= 1.0 + 1e-9):
                findings.append(_fail(
                    ValidationCategory.INTEGRITY,
                    "weight_in_range",
                    f"{slot.symbol}: weight {slot.target_weight:.6f} outside [-1, 1]",
                    symbol=slot.symbol,
                    actual=slot.target_weight,
                ))
        if not findings:
            findings.append(_pass(ValidationCategory.INTEGRITY, "weight_signs"))
        return findings

    def _check_weight_sum(self, bp: Any) -> List[ValidationFinding]:
        findings: List[ValidationFinding] = []
        expected_long = 1.0 - bp.cash_weight
        actual_long   = bp.long_weight_sum
        diff = abs(actual_long - expected_long)
        if diff > WEIGHT_SUM_TOLERANCE:
            findings.append(_warn(
                ValidationCategory.CONSISTENCY,
                "long_weight_sum",
                f"Long weight sum {actual_long:.6f} deviates from expected "
                f"{expected_long:.6f} (diff={diff:.8f})",
                field_name="long_weight_sum",
                actual=actual_long,
                expected=expected_long,
            ))
        else:
            findings.append(_pass(
                ValidationCategory.CONSISTENCY,
                "long_weight_sum",
                f"Long weight sum {actual_long:.6f} ≈ {expected_long:.6f}",
            ))
        return findings

    def _check_metadata(self, bp: Any) -> List[ValidationFinding]:
        findings: List[ValidationFinding] = []
        if not bp.portfolio_id:
            findings.append(_fail(
                ValidationCategory.COMPLETENESS, "portfolio_id_present",
                "Blueprint missing portfolio_id", field_name="portfolio_id",
            ))
        else:
            findings.append(_pass(ValidationCategory.COMPLETENESS, "portfolio_id_present"))
        if not bp.blueprint_id:
            findings.append(_fail(
                ValidationCategory.COMPLETENESS, "blueprint_id_present",
                "Blueprint missing blueprint_id", field_name="blueprint_id",
            ))
        else:
            findings.append(_pass(ValidationCategory.COMPLETENESS, "blueprint_id_present"))
        return findings

    def _check_traceability(self, bp: Any) -> List[ValidationFinding]:
        """Warn if any slot is missing a recommendation_id."""
        missing = [s.symbol for s in bp.slots if not s.recommendation_id]
        if missing:
            return [_warn(
                ValidationCategory.INTEGRITY,
                "slot_traceability",
                f"{len(missing)} slot(s) missing recommendation_id: "
                f"{', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}",
                details={"missing": missing},
            )]
        return [_pass(ValidationCategory.INTEGRITY, "slot_traceability")]
