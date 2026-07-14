"""iios/investment/portfolio/construction/constraint_engine.py

Orchestrates constraint registration, evaluation, and reporting.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.construction.constraint_history import (
    ConstraintCheckRecord,
    ConstraintHistory,
)
from iios.investment.portfolio.construction.constraint_registry import ConstraintRegistry
from iios.investment.portfolio.construction.constraint_validator import (
    ConstraintChecker,
    get_checker,
    register_checker,
)
from iios.investment.portfolio.construction.construction_constraints import ConstraintDefinition
from iios.investment.portfolio.construction.construction_types import (
    ConstraintOutcome,
    ConstraintSeverity,
    ConstraintType,
)


# ---------------------------------------------------------------------------
# ConstraintReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConstraintReport:
    """
    Immutable report produced by ConstraintEngine.evaluate().

    One ConstraintCheckRecord per constraint; summary fields for
    quick-access in downstream validators and quality scorers.
    """

    report_id:        str                            = field(default_factory=lambda: str(uuid.uuid4()))
    blueprint_id:     str                            = ""
    portfolio_id:     str                            = ""

    # Per-constraint results (one per active constraint)
    checks:           Tuple[ConstraintCheckRecord, ...]= field(default_factory=tuple)

    # Counts
    total_checked:    int                            = 0
    passed_count:     int                            = 0
    warning_count:    int                            = 0
    violated_count:   int                            = 0
    hard_violated:    int                            = 0   # HARD severity violations
    soft_violated:    int                            = 0   # SOFT severity violations

    # Verdict
    is_compliant:     bool                           = True   # True when hard_violated == 0
    evaluated_at:     float                          = field(default_factory=time.time)
    duration_ms:      float                          = 0.0

    @property
    def compliance_rate(self) -> float:
        return self.passed_count / self.total_checked if self.total_checked > 0 else 1.0

    @property
    def violations(self) -> Tuple[ConstraintCheckRecord, ...]:
        return tuple(c for c in self.checks if c.violated)

    @property
    def warnings(self) -> Tuple[ConstraintCheckRecord, ...]:
        return tuple(c for c in self.checks if c.outcome == ConstraintOutcome.WARNING)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":       self.report_id,
            "blueprint_id":    self.blueprint_id,
            "portfolio_id":    self.portfolio_id,
            "total_checked":   self.total_checked,
            "passed_count":    self.passed_count,
            "warning_count":   self.warning_count,
            "violated_count":  self.violated_count,
            "hard_violated":   self.hard_violated,
            "soft_violated":   self.soft_violated,
            "is_compliant":    self.is_compliant,
            "compliance_rate": round(self.compliance_rate, 4),
            "duration_ms":     round(self.duration_ms, 2),
            "evaluated_at":    self.evaluated_at,
            "checks":          [c.to_dict() for c in self.checks],
        }


# ---------------------------------------------------------------------------
# ConstraintEngine
# ---------------------------------------------------------------------------

class ConstraintEngine:
    """
    Evaluates a PortfolioBlueprint against all active constraints in the
    ConstraintRegistry and returns a ConstraintReport.

    Thread-safe: all mutations go through the registry (which has its own lock).
    The engine itself holds no mutable per-call state.
    """

    def __init__(
        self,
        registry: Optional[ConstraintRegistry] = None,
        history:  Optional[ConstraintHistory]  = None,
    ) -> None:
        self._registry = registry or ConstraintRegistry()
        self._history  = history  or ConstraintHistory()

    # ------------------------------------------------------------------
    # Registry proxies (convenience)
    # ------------------------------------------------------------------

    def register(
        self,
        constraint: ConstraintDefinition,
        *,
        overwrite: bool = False,
    ) -> ConstraintDefinition:
        return self._registry.register(constraint, overwrite=overwrite)

    def unregister(self, name: str) -> bool:
        return self._registry.unregister(name)

    def add_custom_checker(self, ctype: ConstraintType, checker: ConstraintChecker) -> None:
        register_checker(ctype, checker)

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------

    def evaluate(self, blueprint: Any) -> ConstraintReport:
        """
        Evaluate all active constraints against *blueprint*.

        Parameters
        ----------
        blueprint : PortfolioBlueprint

        Returns
        -------
        ConstraintReport
        """
        t0     = time.monotonic()
        checks: List[ConstraintCheckRecord] = []

        for constraint in self._registry.active():
            checker = get_checker(constraint.constraint_type)
            if checker is None:
                # No checker registered for this type — skip with NOT_CHECKED record
                checks.append(ConstraintCheckRecord(
                    constraint_name=constraint.name,
                    constraint_type=constraint.constraint_type.value,
                    severity=constraint.severity,
                    outcome=ConstraintOutcome.NOT_CHECKED,
                    message=f"No checker for type {constraint.constraint_type.value}",
                    blueprint_id=blueprint.blueprint_id,
                    portfolio_id=blueprint.portfolio_id,
                ))
                continue

            record = checker.check(constraint, blueprint)
            checks.append(record)

        self._history.add_many(checks)

        passed   = sum(1 for c in checks if c.passed)
        warnings = sum(1 for c in checks if c.outcome == ConstraintOutcome.WARNING)
        violated = sum(1 for c in checks if c.violated)
        hard_v   = sum(1 for c in checks if c.violated and c.severity == ConstraintSeverity.HARD)
        soft_v   = sum(1 for c in checks if c.violated and c.severity == ConstraintSeverity.SOFT)

        duration_ms = (time.monotonic() - t0) * 1000.0

        return ConstraintReport(
            blueprint_id=blueprint.blueprint_id,
            portfolio_id=blueprint.portfolio_id,
            checks=tuple(checks),
            total_checked=len(checks),
            passed_count=passed,
            warning_count=warnings,
            violated_count=violated,
            hard_violated=hard_v,
            soft_violated=soft_v,
            is_compliant=hard_v == 0,
            duration_ms=duration_ms,
        )

    def is_compliant(self, blueprint: Any) -> bool:
        """Quick compliance check — returns True if no HARD constraints are violated."""
        report = self.evaluate(blueprint)
        return report.is_compliant

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def registry(self) -> ConstraintRegistry:
        return self._registry

    @property
    def history(self) -> ConstraintHistory:
        return self._history

    def stats(self) -> Dict[str, Any]:
        return {
            "registered_constraints": self._registry.count(),
            "active_constraints":     self._registry.active_count(),
            "history_count":          self._history.count(),
            "violation_rate":         round(self._history.violation_rate(), 4),
        }
