"""iios/execution/brokers/monitoring/health_reporter.py"""
from __future__ import annotations

import time
from typing import Any

from iios.execution.brokers.connection.connection_health import ConnectionHealth


class HealthReporter:
    """Generates health summary reports from a collection of ConnectionHealth objects."""

    @staticmethod
    def report(health_map: dict[str, ConnectionHealth]) -> dict[str, Any]:
        healthy   = [h for h in health_map.values() if h.is_healthy]
        unhealthy = [h for h in health_map.values() if not h.is_healthy]
        avg_rt    = (
            sum(h.response_time_ms for h in healthy) / len(healthy)
            if healthy else 0.0
        )
        return {
            "generated_at":    time.time(),
            "total":           len(health_map),
            "healthy_count":   len(healthy),
            "unhealthy_count": len(unhealthy),
            "avg_response_ms": round(avg_rt, 2),
            "healthy_brokers": [h.broker_id for h in healthy],
            "unhealthy_brokers": [
                {"broker_id": h.broker_id, "error": h.error_message}
                for h in unhealthy
            ],
        }

    @staticmethod
    def summary(health_map: dict[str, ConnectionHealth]) -> str:
        r = HealthReporter.report(health_map)
        return (
            f"Brokers: {r['total']} total, "
            f"{r['healthy_count']} healthy, "
            f"{r['unhealthy_count']} unhealthy, "
            f"avg_rt={r['avg_response_ms']:.1f}ms"
        )
