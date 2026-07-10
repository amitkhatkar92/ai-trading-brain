"""iios/execution/monitoring/analytics/sla_monitor.py"""
from __future__ import annotations

import time
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    DEFAULT_FILL_SLA_SEC,
    DEFAULT_LATENCY_SLA_MS,
    ExecutionRecordStatus,
    SLAStatus,
)


class SLAMonitor:
    """
    Monitors SLA compliance across the execution layer.

    Two primary SLAs:
    1. Latency SLA  — average execution latency must be below *latency_sla_ms*.
    2. Fill SLA     — orders must be filled within *fill_sla_sec* of acceptance.
    """

    def __init__(
        self,
        latency_sla_ms: float = DEFAULT_LATENCY_SLA_MS,
        fill_sla_sec:   float = DEFAULT_FILL_SLA_SEC,
        at_risk_factor: float = 0.80,   # flag AT_RISK when within 80% of threshold
    ) -> None:
        self.latency_sla_ms = latency_sla_ms
        self.fill_sla_sec   = fill_sla_sec
        self._at_risk_factor = at_risk_factor

    # ── Latency SLA ───────────────────────────────────────────────────────────

    def check_latency_sla(self, latency_values_ms: list[float]) -> SLAStatus:
        if not latency_values_ms:
            return SLAStatus.NO_DATA
        avg = sum(latency_values_ms) / len(latency_values_ms)
        if avg >= self.latency_sla_ms:
            return SLAStatus.BREACHED
        if avg >= self.latency_sla_ms * self._at_risk_factor:
            return SLAStatus.AT_RISK
        return SLAStatus.WITHIN_SLA

    # ── Fill SLA ──────────────────────────────────────────────────────────────

    def check_fill_sla(self, records: list[Any]) -> SLAStatus:
        """Check that accepted orders were filled within *fill_sla_sec*."""
        if not records:
            return SLAStatus.NO_DATA
        breached = 0
        at_risk  = 0
        checked  = 0
        now      = time.time()
        for rec in records:
            if rec.status == ExecutionRecordStatus.ACCEPTED and rec.accepted_at is not None:
                age = now - rec.accepted_at
                checked += 1
                if age >= self.fill_sla_sec:
                    breached += 1
                elif age >= self.fill_sla_sec * self._at_risk_factor:
                    at_risk += 1
        if checked == 0:
            return SLAStatus.NO_DATA
        if breached > 0:
            return SLAStatus.BREACHED
        if at_risk > 0:
            return SLAStatus.AT_RISK
        return SLAStatus.WITHIN_SLA

    # ── Combined report ───────────────────────────────────────────────────────

    def report(
        self,
        records:          list[Any],
        latency_values_ms: list[float] = [],
    ) -> dict[str, Any]:
        lat_status  = self.check_latency_sla(latency_values_ms)
        fill_status = self.check_fill_sla(records)
        avg_lat     = (
            sum(latency_values_ms) / len(latency_values_ms)
            if latency_values_ms else 0.0
        )
        return {
            "latency_sla_status": lat_status.value,
            "fill_sla_status":    fill_status.value,
            "avg_latency_ms":     round(avg_lat, 2),
            "latency_sla_ms":     self.latency_sla_ms,
            "fill_sla_sec":       self.fill_sla_sec,
            "overall_sla":        (
                "BREACHED" if SLAStatus.BREACHED in (lat_status, fill_status)
                else "AT_RISK" if SLAStatus.AT_RISK in (lat_status, fill_status)
                else "WITHIN_SLA" if SLAStatus.NO_DATA not in (lat_status, fill_status)
                else "NO_DATA"
            ),
            "generated_at": time.time(),
        }
