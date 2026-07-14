"""iios/investment/portfolio/allocation/allocation_validator.py

Validates AllocationPlan completeness and capital-conservation integrity.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.allocation.allocation_plan import AllocationPlan
from iios.investment.portfolio.allocation.allocation_types import CAPITAL_CONSERVATION_TOLERANCE


class FindingOutcome(str, Enum):
    PASSED  = "passed"
    WARNING = "warning"
    FAILED  = "failed"


@dataclass(frozen=True)
class AllocationFinding:
    """A single validation finding."""

    finding_id: str           = field(default_factory=lambda: str(uuid.uuid4()))
    category:   str           = ""      # e.g. "capital_conservation", "position_count"
    outcome:    FindingOutcome= FindingOutcome.PASSED
    rule:       str           = ""      # Human-readable rule name
    message:    str           = ""
    symbol:     str           = ""      # If applicable
    actual:     float         = 0.0
    expected:   float         = 0.0
    details:    Dict[str, Any]= field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.outcome == FindingOutcome.PASSED

    @property
    def is_warning(self) -> bool:
        return self.outcome == FindingOutcome.WARNING

    @property
    def is_blocking(self) -> bool:
        return self.outcome == FindingOutcome.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "category":   self.category,
            "outcome":    self.outcome.value,
            "rule":       self.rule,
            "message":    self.message,
            "symbol":     self.symbol,
            "actual":     round(self.actual, 4),
            "expected":   round(self.expected, 4),
            "details":    dict(self.details),
        }


@dataclass(frozen=True)
class AllocationValidationReport:
    """Summary of all validation checks on an AllocationPlan."""

    report_id:   str                          = field(default_factory=lambda: str(uuid.uuid4()))
    validator:   str                          = "AllocationValidator"
    portfolio_id:str                          = ""
    plan_id:     str                          = ""
    findings:    Tuple[AllocationFinding, ...] = field(default_factory=tuple)
    total:       int                          = 0
    passed:      int                          = 0
    warnings:    int                          = 0
    failures:    int                          = 0
    is_valid:    bool                         = False
    duration_ms: float                        = 0.0
    validated_at:float                        = field(default_factory=time.time)

    @property
    def failed_findings(self) -> Tuple[AllocationFinding, ...]:
        return tuple(f for f in self.findings if f.is_blocking)

    @property
    def warning_findings(self) -> Tuple[AllocationFinding, ...]:
        return tuple(f for f in self.findings if f.is_warning)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":    self.report_id,
            "validator":    self.validator,
            "portfolio_id": self.portfolio_id,
            "plan_id":      self.plan_id,
            "total":        self.total,
            "passed":       self.passed,
            "warnings":     self.warnings,
            "failures":     self.failures,
            "is_valid":     self.is_valid,
            "pass_rate":    round(self.pass_rate, 4),
            "duration_ms":  round(self.duration_ms, 2),
            "validated_at": self.validated_at,
            "findings":     [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def build_allocation_report(
    findings:     List[AllocationFinding],
    *,
    validator:    str = "AllocationValidator",
    plan_id:      str = "",
    portfolio_id: str = "",
    duration_ms:  float = 0.0,
) -> AllocationValidationReport:
    total    = len(findings)
    passed   = sum(1 for f in findings if f.passed)
    warnings = sum(1 for f in findings if f.is_warning)
    failures = sum(1 for f in findings if f.is_blocking)
    return AllocationValidationReport(
        validator    = validator,
        portfolio_id = portfolio_id,
        plan_id      = plan_id,
        findings     = tuple(findings),
        total        = total,
        passed       = passed,
        warnings     = warnings,
        failures     = failures,
        is_valid     = failures == 0,
        duration_ms  = duration_ms,
    )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class AllocationValidator:
    """
    Validates AllocationPlan integrity without consulting market data.
    Checks:
      1. Capital conservation — sum of positions + cash ≈ total_capital
      2. No negative long allocations
      3. Position count non-zero (unless intentionally empty)
      4. Weight sum sanity
      5. Cash adequacy (cash ≥ reserve)
    """

    def validate(self, plan: AllocationPlan) -> AllocationValidationReport:
        t0       = time.time()
        findings: List[AllocationFinding] = []

        # --- 1. Capital conservation -----------------------------------
        position_total = sum(abs(a.allocated_capital) for a in plan.allocations)
        capital_sum    = position_total + plan.cash_capital
        delta          = abs(capital_sum - plan.total_capital)

        if delta <= CAPITAL_CONSERVATION_TOLERANCE:
            findings.append(AllocationFinding(
                category = "capital_conservation",
                outcome  = FindingOutcome.PASSED,
                rule     = "capital_conservation",
                message  = f"Capital conserved: positions ${position_total:.2f} + cash ${plan.cash_capital:.2f} = ${capital_sum:.2f}",
                actual   = capital_sum,
                expected = plan.total_capital,
            ))
        else:
            findings.append(AllocationFinding(
                category = "capital_conservation",
                outcome  = FindingOutcome.FAILED,
                rule     = "capital_conservation",
                message  = (
                    f"Capital not conserved: positions ${position_total:.2f} + "
                    f"cash ${plan.cash_capital:.2f} = ${capital_sum:.2f}, "
                    f"expected ${plan.total_capital:.2f} (delta ${delta:.2f})"
                ),
                actual   = capital_sum,
                expected = plan.total_capital,
                details  = {"delta": delta, "tolerance": CAPITAL_CONSERVATION_TOLERANCE},
            ))

        # --- 2. No negative longs -----------------------------------
        neg_longs = [a for a in plan.allocations if a.is_long and a.allocated_capital < 0]
        if neg_longs:
            for a in neg_longs:
                findings.append(AllocationFinding(
                    category = "position_integrity",
                    outcome  = FindingOutcome.FAILED,
                    rule     = "no_negative_longs",
                    message  = f"{a.symbol} is LONG but has negative allocation ${a.allocated_capital:.2f}",
                    symbol   = a.symbol,
                    actual   = a.allocated_capital,
                    expected = 0.0,
                ))
        else:
            findings.append(AllocationFinding(
                category = "position_integrity",
                outcome  = FindingOutcome.PASSED,
                rule     = "no_negative_longs",
                message  = "All long positions have positive allocated capital",
            ))

        # --- 3. Position count --------------------------------------
        n_pos = len(plan.allocations)
        if n_pos == 0 and plan.total_capital > 0:
            findings.append(AllocationFinding(
                category = "position_count",
                outcome  = FindingOutcome.WARNING,
                rule     = "has_positions",
                message  = "No positions allocated; full capital held as cash",
                actual   = 0,
                expected = 1,
            ))
        else:
            findings.append(AllocationFinding(
                category = "position_count",
                outcome  = FindingOutcome.PASSED,
                rule     = "has_positions",
                message  = f"{n_pos} position(s) allocated",
                actual   = n_pos,
                expected = n_pos,
            ))

        # --- 4. Utilisation sanity ----------------------------------
        utilisation = plan.utilisation_rate
        if utilisation > 1.02:   # > 102% → over-leveraged
            findings.append(AllocationFinding(
                category = "capital_utilisation",
                outcome  = FindingOutcome.FAILED,
                rule     = "max_utilisation",
                message  = f"Capital utilisation {utilisation:.1%} exceeds 100%",
                actual   = utilisation,
                expected = 1.0,
            ))
        elif utilisation > 1.0:
            findings.append(AllocationFinding(
                category = "capital_utilisation",
                outcome  = FindingOutcome.WARNING,
                rule     = "max_utilisation",
                message  = f"Capital utilisation {utilisation:.1%} slightly over 100%",
                actual   = utilisation,
                expected = 1.0,
            ))
        else:
            findings.append(AllocationFinding(
                category = "capital_utilisation",
                outcome  = FindingOutcome.PASSED,
                rule     = "max_utilisation",
                message  = f"Capital utilisation {utilisation:.1%} within bounds",
                actual   = utilisation,
                expected = utilisation,
            ))

        # --- 5. Cash adequacy ---------------------------------------
        if plan.cash_capital < 0:
            findings.append(AllocationFinding(
                category = "cash_adequacy",
                outcome  = FindingOutcome.FAILED,
                rule     = "non_negative_cash",
                message  = f"Negative cash ${plan.cash_capital:.2f}",
                actual   = plan.cash_capital,
                expected = 0.0,
            ))
        else:
            findings.append(AllocationFinding(
                category = "cash_adequacy",
                outcome  = FindingOutcome.PASSED,
                rule     = "non_negative_cash",
                message  = f"Cash position ${plan.cash_capital:.2f} is non-negative",
                actual   = plan.cash_capital,
                expected = plan.cash_capital,
            ))

        duration_ms = (time.time() - t0) * 1000

        return build_allocation_report(
            findings,
            plan_id      = plan.plan_id,
            portfolio_id = plan.portfolio_id,
            duration_ms  = duration_ms,
        )
