"""
market_snapshot_validation.py — iios.market.snapshot
======================================================
Snapshot validation logic — 7 checks.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import dataclasses
from typing import List, Tuple

from .constants import SnapshotValidationCode
from .market_snapshot import MarketSnapshot


@dataclasses.dataclass(frozen=True)
class SnapshotCheckResult:
    code:    SnapshotValidationCode
    passed:  bool
    message: str = ""


@dataclasses.dataclass(frozen=True)
class SnapshotValidationResult:
    is_valid:      bool
    failed_checks: Tuple[SnapshotCheckResult, ...]
    passed_checks: Tuple[SnapshotCheckResult, ...]
    snapshot_id:   str = ""

    @property
    def failure_messages(self) -> List[str]:
        return [c.message for c in self.failed_checks]


class MarketSnapshotValidation:
    """
    Validates a :class:`~.market_snapshot.MarketSnapshot`.

    Checks
    ------
    1. IDENTIFIER_CONSISTENT  — required IDs present
    2. VERSION_CONSISTENT     — version ≥ 1
    3. ANALYTICS_CONSISTENT   — at least one summary section present
    4. FORECAST_CONSISTENT    — if forecast_summary is present, confidence in [0,1]
    5. SCORE_CONSISTENT       — if market_summary is present, score in [0,100]
    6. SNAPSHOT_COMPLETE      — snapshot_timestamp is positive
    7. METADATA_INTEGRITY     — framework_version is non-empty
    """

    def validate(self, snapshot: MarketSnapshot) -> SnapshotValidationResult:
        checks = [
            self._check_identifier_consistent(snapshot),
            self._check_version_consistent(snapshot),
            self._check_analytics_consistent(snapshot),
            self._check_forecast_consistent(snapshot),
            self._check_score_consistent(snapshot),
            self._check_snapshot_complete(snapshot),
            self._check_metadata_integrity(snapshot),
        ]
        failed = tuple(c for c in checks if not c.passed)
        passed = tuple(c for c in checks if c.passed)
        return SnapshotValidationResult(
            is_valid      = len(failed) == 0,
            failed_checks = failed,
            passed_checks = passed,
            snapshot_id   = snapshot.snapshot_id,
        )

    def validate_or_raise(self, snapshot: MarketSnapshot) -> None:
        from .exceptions import MarketSnapshotValidationError
        result = self.validate(snapshot)
        if not result.is_valid:
            raise MarketSnapshotValidationError(
                "; ".join(result.failure_messages),
                snapshot_id=snapshot.snapshot_id,
            )

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_identifier_consistent(s: MarketSnapshot) -> SnapshotCheckResult:
        ok = bool(s.snapshot_id) and bool(s.exchange)
        return SnapshotCheckResult(
            code    = SnapshotValidationCode.IDENTIFIER_CONSISTENT,
            passed  = ok,
            message = "" if ok else "snapshot_id and exchange are required",
        )

    @staticmethod
    def _check_version_consistent(s: MarketSnapshot) -> SnapshotCheckResult:
        ok = s.version >= 1
        return SnapshotCheckResult(
            code    = SnapshotValidationCode.VERSION_CONSISTENT,
            passed  = ok,
            message = "" if ok else f"version must be ≥ 1 (got {s.version})",
        )

    @staticmethod
    def _check_analytics_consistent(s: MarketSnapshot) -> SnapshotCheckResult:
        sections = [
            s.market_summary, s.regime_summary, s.trend_summary,
            s.sector_summary, s.breadth_summary, s.volatility_summary,
            s.liquidity_summary, s.correlation_summary, s.forecast_summary,
        ]
        ok = any(sec is not None for sec in sections)
        return SnapshotCheckResult(
            code    = SnapshotValidationCode.ANALYTICS_CONSISTENT,
            passed  = ok,
            message = "" if ok else "At least one analytics summary section is required",
        )

    @staticmethod
    def _check_forecast_consistent(s: MarketSnapshot) -> SnapshotCheckResult:
        if s.forecast_summary is None:
            return SnapshotCheckResult(code=SnapshotValidationCode.FORECAST_CONSISTENT, passed=True)
        ok = 0.0 <= s.forecast_summary.forecast_confidence <= 1.0
        return SnapshotCheckResult(
            code    = SnapshotValidationCode.FORECAST_CONSISTENT,
            passed  = ok,
            message = "" if ok else
                f"forecast_confidence must be in [0,1] "
                f"(got {s.forecast_summary.forecast_confidence})",
        )

    @staticmethod
    def _check_score_consistent(s: MarketSnapshot) -> SnapshotCheckResult:
        if s.market_summary is None:
            return SnapshotCheckResult(code=SnapshotValidationCode.SCORE_CONSISTENT, passed=True)
        ok = 0.0 <= s.market_summary.overall_score <= 100.0
        return SnapshotCheckResult(
            code    = SnapshotValidationCode.SCORE_CONSISTENT,
            passed  = ok,
            message = "" if ok else
                f"overall_score must be in [0,100] "
                f"(got {s.market_summary.overall_score})",
        )

    @staticmethod
    def _check_snapshot_complete(s: MarketSnapshot) -> SnapshotCheckResult:
        ok = s.snapshot_timestamp > 0.0
        return SnapshotCheckResult(
            code    = SnapshotValidationCode.SNAPSHOT_COMPLETE,
            passed  = ok,
            message = "" if ok else "snapshot_timestamp must be positive",
        )

    @staticmethod
    def _check_metadata_integrity(s: MarketSnapshot) -> SnapshotCheckResult:
        ok = bool(s.framework_version)
        return SnapshotCheckResult(
            code    = SnapshotValidationCode.METADATA_INTEGRITY,
            passed  = ok,
            message = "" if ok else "framework_version must not be empty",
        )
