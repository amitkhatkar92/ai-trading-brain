"""iios/investment/strategy/migration/migration_validator.py
Orchestrates all validation checks for a migration session.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.legacy_metadata import LegacyStrategyMetadata
from iios.investment.strategy.migration.compatibility_validator import CompatibilityValidator
from iios.investment.strategy.migration.validation_report import (
    ValidationReport,
    ValidationCheck,
    CheckSeverity,
    ValidationCheckType,
    build_validation_report,
)
from iios.investment.strategy.migration.strategy_adapter import LegacyStrategyAdapter


@dataclass(frozen=True)
class AdapterValidationResult:
    """Result of validating a created adapter against its metadata."""
    adapter_id:    str
    strategy_name: str
    is_valid:      bool
    issues:        List[str]
    warnings:      List[str]
    checked_at:    datetime


class MigrationValidator:
    """
    Full migration validation: runs compatibility checks and adapter validation.
    Returns a consolidated ValidationReport.
    """

    def __init__(self) -> None:
        self._compat_validator = CompatibilityValidator()

    def validate_metadata(self, metadata: LegacyStrategyMetadata) -> ValidationReport:
        """Run full compatibility validation for a legacy strategy."""
        return self._compat_validator.validate(metadata)

    def validate_adapter(self, adapter: LegacyStrategyAdapter) -> AdapterValidationResult:
        """Validate that a created adapter correctly represents its legacy strategy."""
        issues:   List[str] = []
        warnings: List[str] = []

        meta = adapter.metadata

        # Check strategy_id consistency
        if adapter.strategy_id != meta.strategy_id:
            issues.append(
                f"strategy_id mismatch: adapter={adapter.strategy_id} "
                f"vs metadata={meta.strategy_id}"
            )

        # Check name consistency
        if adapter.name != meta.strategy_name:
            issues.append(
                f"name mismatch: adapter.name={adapter.name!r} "
                f"vs metadata.strategy_name={meta.strategy_name!r}"
            )

        # Check definition was built
        try:
            definition = adapter.get_definition()
            if not definition.name:
                issues.append("adapter.get_definition() returned empty name")
        except Exception as exc:
            issues.append(f"adapter.get_definition() raised: {exc}")

        # Check risk params preserved
        try:
            rp = adapter.get_risk_params()
            if abs(rp.get("min_rr", 0) - meta.min_rr) > 1e-6:
                issues.append(f"min_rr not preserved: {rp.get('min_rr')} vs {meta.min_rr}")
            if abs(rp.get("max_loss_pct", 0) - meta.max_loss_pct) > 1e-6:
                issues.append(f"max_loss_pct not preserved: {rp.get('max_loss_pct')} vs {meta.max_loss_pct}")
        except Exception as exc:
            issues.append(f"get_risk_params() raised: {exc}")

        # Check entry conditions preserved
        if meta.entry_conditions:
            try:
                test_features = {
                    c.feature: c.threshold for c in meta.entry_conditions
                }
                result = adapter.evaluate_entry(test_features)
                if result is None:
                    warnings.append("Entry condition evaluation returned None for threshold values")
            except Exception as exc:
                issues.append(f"evaluate_entry() raised: {exc}")

        return AdapterValidationResult(
            adapter_id=adapter.strategy_id,
            strategy_name=meta.strategy_name,
            is_valid=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            checked_at=datetime.now(timezone.utc),
        )

    def validate_and_create_report(
        self,
        metadata: LegacyStrategyMetadata,
        adapter:  Optional[LegacyStrategyAdapter] = None,
    ) -> ValidationReport:
        """
        Run full validation pipeline:
        1. Metadata compatibility checks
        2. Adapter validation (if adapter provided)
        Returns a consolidated ValidationReport.
        """
        start = time.monotonic()

        # Step 1: compatibility checks
        compat_report = self._compat_validator.validate(metadata)
        checks = list(compat_report.checks)

        # Step 2: adapter validation
        if adapter is not None:
            adapter_result = self.validate_adapter(adapter)
            for issue in adapter_result.issues:
                checks.append(ValidationCheck(
                    check_id=str(uuid.uuid4()),
                    check_type=ValidationCheckType.BEHAVIOR,
                    name="adapter_integrity",
                    severity=CheckSeverity.ERROR,
                    message=issue,
                ))
            for warning in adapter_result.warnings:
                checks.append(ValidationCheck(
                    check_id=str(uuid.uuid4()),
                    check_type=ValidationCheckType.BEHAVIOR,
                    name="adapter_warning",
                    severity=CheckSeverity.WARNING,
                    message=warning,
                ))

        duration_ms = (time.monotonic() - start) * 1000
        return build_validation_report(
            strategy_id=metadata.strategy_id,
            strategy_name=metadata.strategy_name,
            checks=checks,
            gaps=compat_report.interface_gaps,
            duration_ms=duration_ms,
        )
