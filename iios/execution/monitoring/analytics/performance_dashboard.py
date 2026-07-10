"""iios/execution/monitoring/analytics/performance_dashboard.py"""
from __future__ import annotations

import time
from typing import Any

from iios.execution.monitoring.analytics.execution_analytics import ExecutionAnalytics
from iios.execution.monitoring.analytics.sla_monitor import SLAMonitor


class PerformanceDashboard:
    """
    Generates a comprehensive performance snapshot.

    Accepts the major monitoring components and returns a single unified
    dict suitable for display or downstream telemetry.
    """

    def __init__(
        self,
        analytics: ExecutionAnalytics | None = None,
        sla_monitor: SLAMonitor | None = None,
    ) -> None:
        self._analytics  = analytics  or ExecutionAnalytics()
        self._sla_monitor = sla_monitor or SLAMonitor()

    def generate(
        self,
        records:          list[Any] = [],
        latency_values:   list[float] = [],
        recon_reports:    list[Any] = [],
        active_alerts:    list[Any] = [],
    ) -> dict[str, Any]:
        metrics = self._analytics.compute_metrics(records, latency_values)
        sla     = self._sla_monitor.report(records, latency_values)

        # Reconciliation summary
        recon_clean     = sum(1 for r in recon_reports if r.is_clean())
        recon_discrepant = len(recon_reports) - recon_clean

        return {
            "generated_at":      time.time(),
            "execution_metrics": metrics.to_dict(),
            "sla":               sla,
            "reconciliation": {
                "total_runs":    len(recon_reports),
                "clean":         recon_clean,
                "discrepant":    recon_discrepant,
            },
            "alerts": {
                "active":   len([a for a in active_alerts if a.is_active()]),
                "total":    len(active_alerts),
            },
            "broker_quality": {
                bid: qm.to_dict()
                for bid, qm in self._analytics.broker_quality(records, latency_values).items()
            },
        }
