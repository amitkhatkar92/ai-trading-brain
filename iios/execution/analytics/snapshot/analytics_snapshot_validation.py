"""
iios/execution/analytics/snapshot/analytics_snapshot_validation.py
===================================================================
AnalyticsSnapshotValidator — validates ExecutionAnalyticsSnapshot
objects and the inputs used to build them.

Validation checks:
  1. Identifier consistency — required IDs must be non-empty
  2. Lifecycle consistency — lifecycle_state must be coherent with status
  3. Performance consistency — scores/rates in valid ranges
  4. Prediction consistency — confidence values in [0, 1]
  5. Trend consistency — dominant_trend is a valid string
  6. Benchmark consistency — scores in valid ranges
  7. Forecast consistency — forecasted values non-negative
  8. Snapshot completeness — at minimum, identifiers present
  9. Version compatibility — framework_version must match expected
 10. Timestamp consistency — timestamp must be positive

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from .constants import SNAPSHOT_FRAMEWORK_VERSION, SnapshotLifecycleState
from .exceptions import SnapshotValidationError
from .execution_analytics_snapshot import ExecutionAnalyticsSnapshot


@dataclass(frozen=True)
class SnapshotValidationResult:
    """Result of a snapshot validation pass."""

    is_valid: bool
    errors:   Tuple[str, ...]

    @classmethod
    def ok(cls) -> "SnapshotValidationResult":
        return cls(is_valid=True, errors=())

    @classmethod
    def fail(cls, errors: List[str]) -> "SnapshotValidationResult":
        return cls(is_valid=False, errors=tuple(errors))


class AnalyticsSnapshotValidator:
    """
    Validates ExecutionAnalyticsSnapshot objects and build inputs.

    Stateless — no lifecycle required.
    """

    # 1. Identifier consistency
    def _check_identifiers(self, snap: ExecutionAnalyticsSnapshot, errs: List[str]) -> None:
        if not snap.snapshot_id.strip():
            errs.append("snapshot_id must not be blank.")
        if not snap.analytics_session_id.strip():
            errs.append("analytics_session_id must not be blank.")
        if not snap.execution_session_id.strip():
            errs.append("execution_session_id must not be blank.")
        if not snap.snapshot_version.strip():
            errs.append("snapshot_version must not be blank.")

    # 2. Lifecycle consistency
    def _check_lifecycle(self, snap: ExecutionAnalyticsSnapshot, errs: List[str]) -> None:
        invalid_states = {SnapshotLifecycleState.BUILDING, SnapshotLifecycleState.INVALID}
        if snap.lifecycle_state in invalid_states:
            errs.append(
                f"lifecycle_state {snap.lifecycle_state.value!r} is not valid for a "
                f"completed snapshot."
            )

    # 3. Performance consistency
    def _check_performance(self, snap: ExecutionAnalyticsSnapshot, errs: List[str]) -> None:
        ps = snap.performance_summary
        if ps is None:
            return
        if not (0.0 <= ps.success_rate <= 1.0):
            errs.append(f"performance_summary.success_rate out of range: {ps.success_rate}")
        if not (0.0 <= ps.win_rate <= 1.0):
            errs.append(f"performance_summary.win_rate out of range: {ps.win_rate}")
        if not (0.0 <= ps.fill_rate <= 1.0):
            errs.append(f"performance_summary.fill_rate out of range: {ps.fill_rate}")
        if ps.avg_execution_time_ms < 0.0:
            errs.append(f"performance_summary.avg_execution_time_ms must be >= 0.")
        sc = snap.performance_scorecard
        if sc is not None:
            for name, val in [
                ("overall_score", sc.overall_score),
                ("execution_score", sc.execution_score),
                ("risk_score", sc.risk_score),
                ("efficiency_score", sc.efficiency_score),
            ]:
                if not (0.0 <= val <= 1.0):
                    errs.append(f"performance_scorecard.{name} out of range: {val}")

    # 4. Prediction consistency
    def _check_predictions(self, snap: ExecutionAnalyticsSnapshot, errs: List[str]) -> None:
        ps = snap.prediction_summary
        if ps is None:
            return
        if not (0.0 <= ps.avg_confidence <= 1.0):
            errs.append(f"prediction_summary.avg_confidence out of range: {ps.avg_confidence}")
        cs = snap.confidence_summary
        if cs is not None:
            for name, val in [
                ("overall_confidence",     cs.overall_confidence),
                ("performance_confidence", cs.performance_confidence),
                ("prediction_confidence",  cs.prediction_confidence),
                ("risk_confidence",        cs.risk_confidence),
            ]:
                if not (0.0 <= val <= 1.0):
                    errs.append(f"confidence_summary.{name} out of range: {val}")

    # 5. Trend consistency
    def _check_trends(self, snap: ExecutionAnalyticsSnapshot, errs: List[str]) -> None:
        ts = snap.trend_summary
        if ts is None:
            return
        if not isinstance(ts.dominant_trend, str) or not ts.dominant_trend.strip():
            errs.append("trend_summary.dominant_trend must be a non-empty string.")
        if ts.trend_count < 0:
            errs.append(f"trend_summary.trend_count must be >= 0, got {ts.trend_count}.")

    # 6. Benchmark consistency
    def _check_benchmarks(self, snap: ExecutionAnalyticsSnapshot, errs: List[str]) -> None:
        bm = snap.benchmark_summary
        if bm is None:
            return
        if not (0.0 <= bm.overall_score <= 1.0):
            errs.append(f"benchmark_summary.overall_score out of range: {bm.overall_score}")

    # 7. Forecast consistency
    def _check_forecasts(self, snap: ExecutionAnalyticsSnapshot, errs: List[str]) -> None:
        cf = snap.capacity_forecast
        if cf is not None:
            if not (0.0 <= cf.forecasted_utilization <= 1.0):
                errs.append(
                    f"capacity_forecast.forecasted_utilization out of range: "
                    f"{cf.forecasted_utilization}"
                )
            if not (0.0 <= cf.bottleneck_risk <= 1.0):
                errs.append(
                    f"capacity_forecast.bottleneck_risk out of range: {cf.bottleneck_risk}"
                )
        rf = snap.risk_forecast
        if rf is not None:
            if not (0.0 <= rf.risk_score <= 1.0):
                errs.append(f"risk_forecast.risk_score out of range: {rf.risk_score}")
            if not (0.0 <= rf.confidence <= 1.0):
                errs.append(f"risk_forecast.confidence out of range: {rf.confidence}")

    # 8. Snapshot completeness
    def _check_completeness(self, snap: ExecutionAnalyticsSnapshot, errs: List[str]) -> None:
        # At minimum identifiers must be present — already handled by _check_identifiers
        if not (0.0 <= snap.operational_health_score <= 1.0):
            errs.append(
                f"operational_health_score out of range: {snap.operational_health_score}"
            )

    # 9. Version compatibility
    def _check_version(self, snap: ExecutionAnalyticsSnapshot, errs: List[str]) -> None:
        if snap.framework_version != SNAPSHOT_FRAMEWORK_VERSION:
            errs.append(
                f"framework_version {snap.framework_version!r} does not match expected "
                f"{SNAPSHOT_FRAMEWORK_VERSION!r}."
            )

    # 10. Timestamp consistency
    def _check_timestamp(self, snap: ExecutionAnalyticsSnapshot, errs: List[str]) -> None:
        if snap.timestamp <= 0.0:
            errs.append(f"timestamp must be positive, got {snap.timestamp}.")

    # ── Public API ────────────────────────────────────────────────────────────

    def validate(self, snapshot: ExecutionAnalyticsSnapshot) -> SnapshotValidationResult:
        """Run all 10 validation checks against a snapshot."""
        errs: List[str] = []
        self._check_identifiers(snapshot, errs)
        self._check_lifecycle(snapshot, errs)
        self._check_performance(snapshot, errs)
        self._check_predictions(snapshot, errs)
        self._check_trends(snapshot, errs)
        self._check_benchmarks(snapshot, errs)
        self._check_forecasts(snapshot, errs)
        self._check_completeness(snapshot, errs)
        self._check_version(snapshot, errs)
        self._check_timestamp(snapshot, errs)
        return SnapshotValidationResult.ok() if not errs else SnapshotValidationResult.fail(errs)

    def validate_and_raise(self, snapshot: ExecutionAnalyticsSnapshot) -> None:
        """Validate and raise SnapshotValidationError on failure."""
        result = self.validate(snapshot)
        if not result.is_valid:
            raise SnapshotValidationError(errors=result.errors)

    def validate_build_inputs(
        self,
        *,
        analytics_session_id: str,
        execution_session_id: str,
    ) -> SnapshotValidationResult:
        """Validate the minimum required build inputs."""
        errs: List[str] = []
        if not analytics_session_id or not analytics_session_id.strip():
            errs.append("analytics_session_id is required for snapshot build.")
        if not execution_session_id or not execution_session_id.strip():
            errs.append("execution_session_id is required for snapshot build.")
        return SnapshotValidationResult.ok() if not errs else SnapshotValidationResult.fail(errs)
