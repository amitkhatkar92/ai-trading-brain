"""iios/investment/strategy/migration/compatibility_validator.py
Performs the 6-category compatibility validation checks.
"""
from __future__ import annotations

import time
import uuid
from typing import List, Tuple

from iios.investment.strategy.migration.legacy_metadata import (
    LegacyStrategyMetadata,
    LegacyStrategySource,
    LegacyStrategyType,
)
from iios.investment.strategy.migration.compatibility_layer import CompatibilityLayer
from iios.investment.strategy.migration.validation_report import (
    CheckSeverity,
    ValidationCheck,
    ValidationCheckType,
    ValidationReport,
    build_validation_report,
)


def _check(
    check_type:  ValidationCheckType,
    name:        str,
    condition:   bool,
    pass_msg:    str,
    fail_msg:    str,
    severity:    CheckSeverity = CheckSeverity.ERROR,
    detail:      str = "",
    remediation: str = "",
) -> ValidationCheck:
    return ValidationCheck(
        check_id=str(uuid.uuid4()),
        check_type=check_type,
        name=name,
        severity=CheckSeverity.PASS if condition else severity,
        message=pass_msg if condition else fail_msg,
        detail=detail,
        remediation="" if condition else remediation,
    )


class CompatibilityValidator:
    """
    Executes 6 compatibility categories for a legacy strategy migration.

    Categories:
    1. Lifecycle compatibility
    2. Configuration compatibility
    3. Signal compatibility
    4. Risk compatibility
    5. Execution compatibility
    6. Dependency compatibility
    """

    def validate(self, metadata: LegacyStrategyMetadata) -> ValidationReport:
        start = time.monotonic()
        checks: List[ValidationCheck] = []

        checks.extend(self._check_lifecycle(metadata))
        checks.extend(self._check_configuration(metadata))
        checks.extend(self._check_signal(metadata))
        checks.extend(self._check_risk(metadata))
        checks.extend(self._check_execution(metadata))
        checks.extend(self._check_dependency(metadata))

        gaps = CompatibilityLayer.check_interface_gaps(metadata)
        duration_ms = (time.monotonic() - start) * 1000

        return build_validation_report(
            strategy_id=metadata.strategy_id,
            strategy_name=metadata.strategy_name,
            checks=checks,
            gaps=gaps,
            duration_ms=duration_ms,
        )

    # ── 1. Lifecycle ──────────────────────────────────────────────────────────

    def _check_lifecycle(self, m: LegacyStrategyMetadata) -> List[ValidationCheck]:
        ct = ValidationCheckType.LIFECYCLE
        return [
            _check(ct, "identity",
                   bool(m.strategy_id) and bool(m.strategy_name),
                   "Strategy has valid ID and name",
                   "Strategy is missing ID or name",
                   detail=f"id={m.strategy_id!r} name={m.strategy_name!r}",
                   remediation="Ensure strategy_id and strategy_name are non-empty"),
            _check(ct, "source_known",
                   m.source != LegacyStrategySource.UNKNOWN,
                   f"Strategy source is known: {m.source.value}",
                   "Strategy source is UNKNOWN — provenance cannot be verified",
                   severity=CheckSeverity.WARNING,
                   remediation="Set the source field explicitly for traceability"),
            _check(ct, "lifecycle_state",
                   m.health_status.value != "archived",
                   "Strategy is not archived",
                   "Strategy is archived — migration may not be appropriate",
                   severity=CheckSeverity.WARNING,
                   remediation="Confirm migration of archived strategy is intentional"),
        ]

    # ── 2. Configuration ──────────────────────────────────────────────────────

    def _check_configuration(self, m: LegacyStrategyMetadata) -> List[ValidationCheck]:
        ct = ValidationCheckType.CONFIGURATION
        return [
            _check(ct, "min_rr_positive",
                   m.min_rr > 0,
                   f"min_rr is positive: {m.min_rr}",
                   f"min_rr must be positive; got {m.min_rr}",
                   remediation="Set min_rr to a positive value (typically 1.5–3.0)"),
            _check(ct, "max_loss_pct_valid",
                   0 < m.max_loss_pct <= 0.10,
                   f"max_loss_pct is valid: {m.max_loss_pct:.1%}",
                   f"max_loss_pct out of range (0, 10%]; got {m.max_loss_pct}",
                   remediation="Set max_loss_pct between 0.001 and 0.10"),
            _check(ct, "rr_vs_loss_consistent",
                   m.min_rr >= 1.0,
                   "min_rr meets institutional minimum (≥1.0)",
                   f"min_rr {m.min_rr} is below institutional minimum of 1.0",
                   severity=CheckSeverity.WARNING,
                   remediation="Consider setting min_rr ≥ 1.5 for institutional trading"),
            _check(ct, "params_self_consistent",
                   m.target_multiplier >= m.min_rr or m.target_multiplier == 0,
                   "target_multiplier is consistent with min_rr",
                   f"target_multiplier {m.target_multiplier} < min_rr {m.min_rr}",
                   severity=CheckSeverity.WARNING,
                   remediation="target_multiplier should equal or exceed min_rr"),
        ]

    # ── 3. Signal ─────────────────────────────────────────────────────────────

    def _check_signal(self, m: LegacyStrategyMetadata) -> List[ValidationCheck]:
        ct = ValidationCheckType.SIGNAL
        has_conditions = bool(m.entry_conditions)
        direction_valid = m.direction.upper() in ("BUY", "SELL", "NEUTRAL", "BOTH")
        return [
            _check(ct, "direction_valid",
                   direction_valid,
                   f"Signal direction is valid: {m.direction}",
                   f"Unrecognised signal direction: {m.direction!r}",
                   severity=CheckSeverity.WARNING,
                   remediation="Set direction to BUY, SELL, NEUTRAL, or BOTH"),
            _check(ct, "entry_conditions_present",
                   has_conditions or m.strategy_type.value == "code_based",
                   "Entry conditions present or strategy is code-based",
                   "JSON strategy has no entry conditions — signal cannot be verified",
                   severity=CheckSeverity.WARNING,
                   remediation="Add entry conditions to enable signal equivalence testing"),
            _check(ct, "entry_condition_operators",
                   all(c.operator in (">", ">=", "<", "<=", "==", "!=")
                       for c in m.entry_conditions),
                   "All entry condition operators are valid",
                   "One or more entry conditions use unrecognised operators",
                   severity=CheckSeverity.ERROR,
                   remediation="Use only >, >=, <, <=, ==, != as condition operators")
                   if m.entry_conditions else
                   ValidationCheck(
                       check_id=str(uuid.uuid4()),
                       check_type=ct,
                       name="entry_condition_operators",
                       severity=CheckSeverity.INFO,
                       message="No entry conditions to validate",
                   ),
        ]

    # ── 4. Risk ───────────────────────────────────────────────────────────────

    def _check_risk(self, m: LegacyStrategyMetadata) -> List[ValidationCheck]:
        ct = ValidationCheckType.RISK
        return [
            _check(ct, "risk_params_complete",
                   m.max_loss_pct > 0 and m.stop_loss_pct > 0,
                   "Risk parameters (max_loss_pct, stop_loss_pct) are complete",
                   "One or more risk parameters are missing or zero",
                   remediation="Ensure max_loss_pct and stop_loss_pct are set"),
            _check(ct, "max_drawdown_acceptable",
                   m.max_drawdown is None or m.max_drawdown <= 0.20,
                   "Max drawdown is within institutional limits (≤20%)",
                   f"Max drawdown {m.max_drawdown:.1%} exceeds 20% — review risk profile",
                   severity=CheckSeverity.WARNING,
                   remediation="Consider reducing position size or adding drawdown guardrails"),
            _check(ct, "stop_loss_tighter_than_max_loss",
                   m.stop_loss_pct <= m.max_loss_pct * 1.1,
                   "Stop-loss is consistent with max_loss_pct",
                   f"stop_loss_pct {m.stop_loss_pct} exceeds max_loss_pct {m.max_loss_pct}",
                   severity=CheckSeverity.WARNING,
                   remediation="Align stop_loss_pct with max_loss_pct"),
        ]

    # ── 5. Execution ──────────────────────────────────────────────────────────

    def _check_execution(self, m: LegacyStrategyMetadata) -> List[ValidationCheck]:
        ct = ValidationCheckType.EXECUTION
        return [
            _check(ct, "category_resolvable",
                   m.category and m.category != "unknown",
                   f"Strategy category is defined: {m.category}",
                   "Strategy category is 'unknown' — execution routing may be imprecise",
                   severity=CheckSeverity.WARNING,
                   remediation="Set category to one of: breakout, momentum, mean_reversion, options, etc."),
            _check(ct, "regime_map_available",
                   bool(m.preferred_regimes or m.compatible_regimes),
                   "Regime mapping is available",
                   "No regime mapping — strategy will be attempted in all regimes",
                   severity=CheckSeverity.INFO),
        ]

    # ── 6. Dependency ─────────────────────────────────────────────────────────

    def _check_dependency(self, m: LegacyStrategyMetadata) -> List[ValidationCheck]:
        ct = ValidationCheckType.DEPENDENCY
        base_ok = (
            not m.base_strategy   # no base = independent
            or m.base_strategy in {
                "Breakout_Volume", "Momentum_Retest", "Trend_Pullback",
                "Mean_Reversion", "Bull_Call_Spread", "Iron_Condor_Range",
                "Hedging_Model", "Short_Straddle_IV_Spike", "Long_Straddle_Pre_Event",
                "Futures_Basis_Arb", "ETF_NAV_Arb", "Equity_Breakout", "Equity_Retest",
            }
        )
        return [
            _check(ct, "base_strategy_known",
                   base_ok,
                   f"Base strategy '{m.base_strategy or 'N/A'}' is known",
                   f"Base strategy '{m.base_strategy}' is not in the known strategy catalogue",
                   severity=CheckSeverity.WARNING,
                   remediation="Register the base strategy or update the base_strategy reference"),
            _check(ct, "source_file_accessible",
                   not m.source_path or __import__("os").path.exists(m.source_path),
                   "Source file is accessible",
                   f"Source file not found: {m.source_path}",
                   severity=CheckSeverity.WARNING,
                   remediation="Verify the source_path points to an existing file"),
        ]
