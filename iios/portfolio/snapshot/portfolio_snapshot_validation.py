"""
portfolio_snapshot_validation.py — iios.portfolio.snapshot
===========================================================
PortfolioSnapshotValidator — executes twelve deterministic checks
against a PortfolioSnapshot and returns an immutable result.

The validator performs NO mutation, NO I/O, and NO policy evaluation.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

from .constants import (
    VERSION,
    SNAPSHOT_SYSTEM_ID,
    SnapshotValidationCode,
    SnapshotStatus,
    PortfolioHealth,
)
from .portfolio_snapshot import PortfolioSnapshot


# ---------------------------------------------------------------------------
# Result value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SnapshotValidationCheckResult:
    """Outcome of a single validation check."""
    code:    str   # SnapshotValidationCode.value
    passed:  bool
    message: str


@dataclass(frozen=True)
class SnapshotValidationResult:
    """Aggregate outcome of all twelve validation checks."""
    is_valid:       bool
    checks:         tuple   # Tuple[SnapshotValidationCheckResult, ...]
    failed_checks:  tuple   # Tuple[SnapshotValidationCheckResult, ...]
    passed_count:   int
    failed_count:   int
    error_messages: tuple   # Tuple[str, ...]
    duration_s:     float

    @classmethod
    def from_checks(
        cls,
        checks:     Tuple[SnapshotValidationCheckResult, ...],
        duration_s: float,
    ) -> "SnapshotValidationResult":
        passed = tuple(c for c in checks if c.passed)
        failed = tuple(c for c in checks if not c.passed)
        return cls(
            is_valid       = len(failed) == 0,
            checks         = checks,
            failed_checks  = failed,
            passed_count   = len(passed),
            failed_count   = len(failed),
            error_messages = tuple(c.message for c in failed),
            duration_s     = duration_s,
        )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class PortfolioSnapshotValidator:
    """
    Executes the twelve canonical validation checks against a
    PortfolioSnapshot.

    Checks
    ------
    1.  IDENTIFIER_CONSISTENCY
    2.  LIFECYCLE_CONSISTENCY
    3.  ALLOCATION_CONSISTENCY
    4.  EXPOSURE_CONSISTENCY
    5.  DIVERSIFICATION_CONSISTENCY
    6.  OPTIMIZATION_CONSISTENCY
    7.  CONSTRAINT_CONSISTENCY
    8.  PORTFOLIO_CONSISTENCY
    9.  SNAPSHOT_COMPLETENESS
    10. VERSION_COMPATIBILITY
    11. TIMESTAMP_CONSISTENCY
    12. AUDIT_CONSISTENCY
    """

    _VALID_LIFECYCLE_STATES = frozenset({
        "initialising", "running", "paused", "stopped", "error",
        "active", "inactive", "pending",   # common aliases
    })

    _VALID_HEALTH_VALUES = frozenset(h.value for h in PortfolioHealth)
    _VALID_STATUS_VALUES = frozenset(s.value for s in SnapshotStatus)

    def __init__(self) -> None:
        self._checks: List[Callable[[PortfolioSnapshot], SnapshotValidationCheckResult]] = [
            self._check_identifier_consistency,
            self._check_lifecycle_consistency,
            self._check_allocation_consistency,
            self._check_exposure_consistency,
            self._check_diversification_consistency,
            self._check_optimization_consistency,
            self._check_constraint_consistency,
            self._check_portfolio_consistency,
            self._check_snapshot_completeness,
            self._check_version_compatibility,
            self._check_timestamp_consistency,
            self._check_audit_consistency,
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, snapshot: PortfolioSnapshot) -> SnapshotValidationResult:
        start = time.perf_counter()
        results: List[SnapshotValidationCheckResult] = []
        for check_fn in self._checks:
            results.append(check_fn(snapshot))
        duration = time.perf_counter() - start
        return SnapshotValidationResult.from_checks(tuple(results), duration)

    # ------------------------------------------------------------------
    # Check 1 — Identifier consistency
    # ------------------------------------------------------------------

    def _check_identifier_consistency(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.IDENTIFIER_CONSISTENCY.value
        if not snap.snapshot_id:
            return _fail(code, "snapshot_id must not be empty")
        if not snap.portfolio_id:
            return _fail(code, "portfolio_id must not be empty")
        # Metadata must reference the same IDs
        if snap.portfolio_metadata.snapshot_id != snap.snapshot_id:
            return _fail(code, "portfolio_metadata.snapshot_id does not match snapshot_id")
        if snap.portfolio_metadata.portfolio_id != snap.portfolio_id:
            return _fail(code, "portfolio_metadata.portfolio_id does not match portfolio_id")
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 2 — Lifecycle consistency
    # ------------------------------------------------------------------

    def _check_lifecycle_consistency(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.LIFECYCLE_CONSISTENCY.value
        if not snap.lifecycle_state:
            return _fail(code, "lifecycle_state must not be empty")
        if snap.lifecycle_state.lower() not in self._VALID_LIFECYCLE_STATES:
            return _fail(
                code,
                f"lifecycle_state {snap.lifecycle_state!r} is not a recognised value",
            )
        if snap.snapshot_status not in self._VALID_STATUS_VALUES:
            return _fail(
                code,
                f"snapshot_status {snap.snapshot_status!r} is not a recognised value",
            )
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 3 — Allocation consistency
    # ------------------------------------------------------------------

    def _check_allocation_consistency(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.ALLOCATION_CONSISTENCY.value
        # All allocation weights must be non-negative
        for label, alloc in (
            ("sector",   snap.sector_allocation),
            ("industry", snap.industry_allocation),
            ("asset",    snap.asset_allocation),
            ("strategy", snap.strategy_allocation),
            ("regional", snap.regional_allocation),
            ("currency", snap.currency_allocation),
        ):
            for k, w in alloc.items():
                if w < 0:
                    return _fail(code, f"{label}_allocation[{k!r}] is negative ({w})")
        # cash_balance and reserved_capital must be non-negative
        if snap.cash_balance < 0:
            return _fail(code, f"cash_balance is negative ({snap.cash_balance})")
        if snap.reserved_capital < 0:
            return _fail(code, f"reserved_capital is negative ({snap.reserved_capital})")
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 4 — Exposure consistency
    # ------------------------------------------------------------------

    def _check_exposure_consistency(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.EXPOSURE_CONSISTENCY.value
        em = snap.exposure_metrics
        for metric in ("gross_exposure", "net_exposure"):
            if metric in em and not isinstance(em[metric], (int, float)):
                return _fail(
                    code,
                    f"exposure_metrics[{metric!r}] must be numeric, got {type(em[metric]).__name__}",
                )
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 5 — Diversification consistency
    # ------------------------------------------------------------------

    def _check_diversification_consistency(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.DIVERSIFICATION_CONSISTENCY.value
        ds = snap.diversification_summary
        if "concentration" in ds:
            c = ds["concentration"]
            if not isinstance(c, (int, float)):
                return _fail(code, f"diversification_summary[concentration] must be numeric")
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 6 — Optimization consistency
    # ------------------------------------------------------------------

    def _check_optimization_consistency(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.OPTIMIZATION_CONSISTENCY.value
        os_ = snap.optimization_summary
        if "status" in os_:
            s = os_["status"]
            if not isinstance(s, str):
                return _fail(code, "optimization_summary[status] must be a string")
        if "objective_value" in os_:
            ov = os_["objective_value"]
            if not isinstance(ov, (int, float)):
                return _fail(code, "optimization_summary[objective_value] must be numeric")
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 7 — Constraint consistency
    # ------------------------------------------------------------------

    def _check_constraint_consistency(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.CONSTRAINT_CONSISTENCY.value
        cs = snap.constraint_summary
        if "violations" in cs:
            v = cs["violations"]
            if not isinstance(v, (int, list)):
                return _fail(
                    code,
                    "constraint_summary[violations] must be an int or list",
                )
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 8 — Portfolio consistency
    # ------------------------------------------------------------------

    def _check_portfolio_consistency(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.PORTFOLIO_CONSISTENCY.value
        if snap.position_count < 0:
            return _fail(code, f"position_count is negative ({snap.position_count})")
        if snap.position_count != len(snap.current_holdings):
            return _fail(
                code,
                f"position_count ({snap.position_count}) does not match "
                f"len(current_holdings) ({len(snap.current_holdings)})",
            )
        if snap.portfolio_health not in self._VALID_HEALTH_VALUES:
            return _fail(
                code,
                f"portfolio_health {snap.portfolio_health!r} is not a recognised value",
            )
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 9 — Snapshot completeness
    # ------------------------------------------------------------------

    def _check_snapshot_completeness(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.SNAPSHOT_COMPLETENESS.value
        if not snap.portfolio_name:
            return _fail(code, "portfolio_name must not be empty")
        if not snap.portfolio_currency:
            return _fail(code, "portfolio_currency must not be empty")
        if snap.snapshot_version < 1:
            return _fail(code, f"snapshot_version must be ≥ 1 (got {snap.snapshot_version})")
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 10 — Version compatibility
    # ------------------------------------------------------------------

    def _check_version_compatibility(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.VERSION_COMPATIBILITY.value
        if not snap.framework_version:
            return _fail(code, "framework_version must not be empty")
        if snap.portfolio_metadata.framework_version != snap.framework_version:
            return _fail(
                code,
                "portfolio_metadata.framework_version does not match snapshot.framework_version",
            )
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 11 — Timestamp consistency
    # ------------------------------------------------------------------

    def _check_timestamp_consistency(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.TIMESTAMP_CONSISTENCY.value
        if snap.timestamp <= 0:
            return _fail(code, f"timestamp must be positive (got {snap.timestamp})")
        if snap.audit_metadata.built_at <= 0:
            return _fail(code, "audit_metadata.built_at must be positive")
        if snap.audit_metadata.built_at > time.time() + 60:
            return _fail(code, "audit_metadata.built_at is in the future")
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 12 — Audit consistency
    # ------------------------------------------------------------------

    def _check_audit_consistency(
        self, snap: PortfolioSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.AUDIT_CONSISTENCY.value
        if not snap.audit_metadata.built_by:
            return _fail(code, "audit_metadata.built_by must not be empty")
        if not snap.audit_metadata.framework_version:
            return _fail(code, "audit_metadata.framework_version must not be empty")
        return _pass(code)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pass(code: str) -> SnapshotValidationCheckResult:
    return SnapshotValidationCheckResult(code=code, passed=True, message="")


def _fail(code: str, msg: str) -> SnapshotValidationCheckResult:
    return SnapshotValidationCheckResult(code=code, passed=False, message=msg)
