"""iios/execution/monitoring/analytics/execution_analytics.py"""
from __future__ import annotations

import time
from typing import Any

from iios.execution.monitoring.monitoring_constants import ExecutionRecordStatus
from iios.execution.monitoring.analytics.quality_metrics import QualityMetrics
from iios.execution.monitoring.tracking.execution_metrics import ExecutionMetrics


class ExecutionAnalytics:
    """
    Computes aggregate statistics over a list of ExecutionRecord objects.

    Stateless: all methods take the record list as input.
    """

    # ── Core metrics ──────────────────────────────────────────────────────────

    def compute_metrics(
        self,
        records:          list[Any],   # list[ExecutionRecord]
        latency_values:   list[float] = [],
        period_start:     float | None = None,
        period_end:       float | None = None,
    ) -> ExecutionMetrics:
        n = len(records)
        if n == 0 and not latency_values:
            return ExecutionMetrics(
                period_start=period_start,
                period_end=period_end or time.time(),
            )

        fully_filled    = sum(1 for r in records if r.status == ExecutionRecordStatus.FULLY_FILLED)
        partially_filled = sum(1 for r in records if r.status == ExecutionRecordStatus.PARTIALLY_FILLED)
        cancelled       = sum(1 for r in records if r.status == ExecutionRecordStatus.CANCELLED)
        rejected        = sum(1 for r in records if r.status == ExecutionRecordStatus.REJECTED)
        failed          = sum(1 for r in records if r.status == ExecutionRecordStatus.FAILED)
        terminal        = fully_filled + cancelled + rejected + failed
        completed       = fully_filled + partially_filled

        avg_fill_ratio  = sum(r.fill_ratio() for r in records) / n if n else 0.0
        total_volume    = sum(r.filled_quantity for r in records)
        total_notional  = sum(r.notional_value() for r in records)

        success_rate      = fully_filled / n if n else 0.0
        rejection_rate    = rejected / n if n else 0.0
        cancellation_rate = cancelled / n if n else 0.0

        # Latency percentiles
        sorted_lat      = sorted(latency_values)
        avg_lat         = sum(sorted_lat) / len(sorted_lat) if sorted_lat else 0.0
        p50             = self._percentile(sorted_lat, 50)
        p75             = self._percentile(sorted_lat, 75)
        p95             = self._percentile(sorted_lat, 95)
        p99             = self._percentile(sorted_lat, 99)
        max_lat         = sorted_lat[-1] if sorted_lat else 0.0

        eqi = self._execution_quality_index(
            fill_ratio=avg_fill_ratio,
            rejection_rate=rejection_rate,
            cancellation_rate=cancellation_rate,
            avg_latency_ms=avg_lat,
        )

        return ExecutionMetrics(
            total_executions=n,
            completed=completed,
            partially_filled=partially_filled,
            fully_filled=fully_filled,
            cancelled=cancelled,
            rejected=rejected,
            failed=failed,
            total_orders=n,
            total_fills=sum(r.fill_count for r in records),
            total_volume=total_volume,
            total_notional=total_notional,
            avg_fill_ratio=avg_fill_ratio,
            success_rate=success_rate,
            rejection_rate=rejection_rate,
            cancellation_rate=cancellation_rate,
            avg_latency_ms=avg_lat,
            p50_latency_ms=p50,
            p75_latency_ms=p75,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            max_latency_ms=max_lat,
            execution_quality_index=eqi,
            period_start=period_start,
            period_end=period_end or time.time(),
        )

    # ── Broker-level quality ──────────────────────────────────────────────────

    def broker_quality(
        self,
        records:        list[Any],
        latency_values: list[float] = [],
    ) -> dict[str, QualityMetrics]:
        """Return QualityMetrics per broker_id."""
        by_broker: dict[str, list] = {}
        for rec in records:
            by_broker.setdefault(rec.broker_id, []).append(rec)

        result: dict[str, QualityMetrics] = {}
        for broker_id, recs in by_broker.items():
            n         = len(recs)
            rejected  = sum(1 for r in recs if r.status == ExecutionRecordStatus.REJECTED)
            cancelled = sum(1 for r in recs if r.status == ExecutionRecordStatus.CANCELLED)
            fill_ratio = sum(r.fill_ratio() for r in recs) / n if n else 0.0
            avg_lat    = sum(latency_values) / len(latency_values) if latency_values else 0.0
            p95_lat    = self._percentile(sorted(latency_values), 95)
            rej_rate   = rejected / n if n else 0.0
            can_rate   = cancelled / n if n else 0.0
            eqi = self._execution_quality_index(fill_ratio, rej_rate, can_rate, avg_lat)
            result[broker_id] = QualityMetrics(
                broker_id=broker_id,
                fill_ratio=fill_ratio,
                rejection_rate=rej_rate,
                cancellation_rate=can_rate,
                avg_latency_ms=avg_lat,
                p95_latency_ms=p95_lat,
                order_count=n,
                execution_quality_index=eqi,
            )
        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _percentile(sorted_values: list[float], pct: int) -> float:
        if not sorted_values:
            return 0.0
        idx = int(len(sorted_values) * pct / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    @staticmethod
    def _execution_quality_index(
        fill_ratio:        float,
        rejection_rate:    float,
        cancellation_rate: float,
        avg_latency_ms:    float,
        max_latency_ms:    float = 5_000.0,
    ) -> float:
        """
        Composite EQI = weighted average of four normalised sub-scores.
        Score range: 0.0 (worst) → 1.0 (best).
        """
        latency_score = max(0.0, 1.0 - avg_latency_ms / max(max_latency_ms, 1.0))
        eqi = (
            0.40 * fill_ratio
            + 0.30 * (1.0 - rejection_rate)
            + 0.20 * (1.0 - cancellation_rate)
            + 0.10 * latency_score
        )
        return max(0.0, min(1.0, eqi))
