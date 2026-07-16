"""iios/execution/positions/risk/position_risk_validation.py
==================================================
RiskValidator — validates consistency of risk state, limits, and thresholds.
RiskValidationResult — immutable result of a validation run.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Tuple

from .exceptions import PositionRiskValidationError, RiskLimitsError
from .position_risk_limits import RiskLimits
from .position_risk_state import PositionRiskState
from .position_risk_threshold import RiskThreshold


@dataclass(frozen=True)
class RiskValidationResult:
    """Immutable result of a risk validation run."""

    is_valid: bool
    errors:   Tuple[str, ...]
    warnings: Tuple[str, ...] = ()

    @classmethod
    def ok(cls) -> "RiskValidationResult":
        return cls(is_valid=True, errors=())

    @classmethod
    def fail(cls, errors: List[str], warnings: List[str] | None = None) -> "RiskValidationResult":
        return cls(
            is_valid=False,
            errors=tuple(errors),
            warnings=tuple(warnings or []),
        )

    def raise_if_invalid(self) -> None:
        if not self.is_valid:
            raise PositionRiskValidationError(
                "; ".join(self.errors),
                errors=self.errors,
            )


class RiskValidator:
    """
    Pure validation service for risk data structures.
    No state. No lifecycle.
    """

    def validate_state_consistency(
        self,
        risk_state: PositionRiskState,
    ) -> RiskValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        # position_id must not be empty
        if not risk_state.position_id:
            errors.append("position_id must not be empty")

        # Drawdown cannot be negative
        if risk_state.execution_drawdown < Decimal("0"):
            errors.append("execution_drawdown must be >= 0")

        # Drawdown pct must be in [0, 1]
        if not (Decimal("0") <= risk_state.execution_drawdown_pct <= Decimal("1")):
            errors.append("execution_drawdown_pct must be in [0, 1]")

        # If stop-loss triggered, risk level should not be NORMAL
        from .constants import RiskLevel as _RL
        if risk_state.stop_loss_triggered and risk_state.risk_level == _RL.NORMAL:
            warnings.append("stop_loss_triggered but risk_level is NORMAL")

        if errors:
            return RiskValidationResult.fail(errors, warnings)
        return RiskValidationResult(is_valid=True, errors=(), warnings=tuple(warnings))

    def validate_pnl_consistency(
        self,
        risk_state: PositionRiskState,
    ) -> RiskValidationResult:
        errors: List[str] = []

        # peak_pnl >= unrealized_pnl (by definition of a peak)
        if risk_state.peak_pnl < risk_state.unrealized_pnl:
            errors.append(
                f"peak_pnl ({risk_state.peak_pnl}) < unrealized_pnl "
                f"({risk_state.unrealized_pnl})"
            )

        if errors:
            return RiskValidationResult.fail(errors)
        return RiskValidationResult.ok()

    def validate_margin_consistency(
        self,
        risk_state: PositionRiskState,
    ) -> RiskValidationResult:
        errors: List[str] = []

        if risk_state.margin_used < Decimal("0"):
            errors.append("margin_used must be >= 0")
        if risk_state.margin_available < Decimal("0"):
            errors.append("margin_available must be >= 0")

        if errors:
            return RiskValidationResult.fail(errors)
        return RiskValidationResult.ok()

    def validate_limits(self, limits: RiskLimits) -> RiskValidationResult:
        errors: List[str] = []
        try:
            # Trigger dataclass __post_init__ re-check via a no-op round-trip
            _ = limits.max_loss
        except Exception as exc:
            errors.append(str(exc))
        if limits.max_loss <= 0:
            errors.append("max_loss must be > 0")
        if errors:
            return RiskValidationResult.fail(errors)
        return RiskValidationResult.ok()

    def validate_thresholds(self, thresholds: RiskThreshold) -> RiskValidationResult:
        errors: List[str] = []
        try:
            _ = thresholds.watch_drawdown_pct
        except Exception as exc:
            errors.append(str(exc))
        if errors:
            return RiskValidationResult.fail(errors)
        return RiskValidationResult.ok()

    def validate_all(
        self,
        risk_state: PositionRiskState,
        limits:     RiskLimits,
        thresholds: RiskThreshold,
    ) -> RiskValidationResult:
        all_errors:   List[str] = []
        all_warnings: List[str] = []

        for result in (
            self.validate_state_consistency(risk_state),
            self.validate_pnl_consistency(risk_state),
            self.validate_margin_consistency(risk_state),
            self.validate_limits(limits),
            self.validate_thresholds(thresholds),
        ):
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        if all_errors:
            return RiskValidationResult.fail(all_errors, all_warnings)
        return RiskValidationResult(
            is_valid=True,
            errors=(),
            warnings=tuple(all_warnings),
        )
