"""iios/execution/monitoring/metrics/metrics_validation.py
==================================================
MetricsValidator — stateless validator for metric requests, contexts,
and snapshots.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .constants import MetricType, WindowSize


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid:  bool
    errors:    List[str] = field(default_factory=list)
    warnings:  List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   self.errors,
            "warnings": self.warnings,
        }


class MetricsValidator:
    """Stateless validator.  Create once and reuse."""

    # ── Context validation ────────────────────────────────────────────────────

    def validate_context(self, context) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not context.session_id:
            result.add_error("session_id is required.")
        if not context.portfolio_id:
            result.add_error("portfolio_id is required.")
        if not isinstance(context.default_window, WindowSize):
            result.add_error("default_window must be a WindowSize enum value.")
        return result

    # ── Request validation ────────────────────────────────────────────────────

    def validate_request(self, request) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not request.request_id:
            result.add_error("request_id is required.")
        if not request.session_id:
            result.add_error("session_id is required.")
        if not request.metric_types:
            result.add_error("metric_types must not be empty.")
        for mt in request.metric_types:
            if not isinstance(mt, MetricType):
                result.add_error(f"Unknown metric_type: {mt!r}.")
        if not isinstance(request.window_size, WindowSize):
            result.add_error("window_size must be a WindowSize enum value.")
        if (request.from_timestamp is not None and
                request.to_timestamp is not None and
                request.from_timestamp >= request.to_timestamp):
            result.add_error("from_timestamp must be before to_timestamp.")
        return result

    # ── Snapshot validation ───────────────────────────────────────────────────

    def validate_snapshot(self, snapshot) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not snapshot.snapshot_id:
            result.add_error("snapshot_id is required.")
        if not snapshot.session_id:
            result.add_error("session_id is required.")
        if not snapshot.portfolio_id:
            result.add_error("portfolio_id is required.")
        if snapshot.snapshot_version < 1:
            result.add_error("snapshot_version must be >= 1.")
        if snapshot.created_at <= 0:
            result.add_error("created_at must be a positive timestamp.")
        for k, v in snapshot.metrics.items():
            if not isinstance(v, (int, float)):
                result.add_error(f"Metric '{k}' has non-numeric value: {v!r}.")
        return result

    # ── Metric consistency ────────────────────────────────────────────────────

    def validate_metric_value(
        self, metric_type: str, value: float
    ) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        # Rate metrics must be in [0, 1]
        rate_metrics = {
            "success_rate", "failure_rate", "cancellation_rate",
            "retry_rate", "timeout_rate", "broker_utilization",
        }
        if metric_type in rate_metrics:
            if not (0.0 <= value <= 1.0):
                result.add_warning(
                    f"Rate metric '{metric_type}' value {value:.4f} is outside "
                    f"[0, 1] — verify source data."
                )
        # Latency / time metrics must be non-negative
        time_metrics = {
            "average_execution_time", "median_execution_time",
            "p95_latency", "p99_latency", "max_latency", "min_latency",
            "queue_wait_time", "dispatch_time", "monitoring_cycle_time",
        }
        if metric_type in time_metrics and value < 0:
            result.add_error(
                f"Time metric '{metric_type}' has negative value {value}."
            )
        # Count / throughput must be non-negative
        count_metrics = {"execution_count", "gateway_throughput"}
        if metric_type in count_metrics and value < 0:
            result.add_error(
                f"Count metric '{metric_type}' has negative value {value}."
            )
        return result

    # ── Window consistency ────────────────────────────────────────────────────

    def validate_window_metrics(self, window_metrics: dict) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        valid_windows = {w.value for w in WindowSize}
        for window_key in window_metrics:
            if window_key not in valid_windows:
                result.add_warning(
                    f"Unknown window key: '{window_key}'. "
                    f"Known windows: {sorted(valid_windows)}."
                )
        return result

    # ── Aggregation consistency ───────────────────────────────────────────────

    def validate_aggregation_result(
        self, values: list, result_value: float
    ) -> ValidationResult:
        vr = ValidationResult(is_valid=True)
        if not values:
            vr.add_warning("Aggregation result computed from empty value list.")
        return vr
