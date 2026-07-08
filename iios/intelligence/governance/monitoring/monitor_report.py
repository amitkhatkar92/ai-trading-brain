"""
iios/intelligence/governance/monitoring/monitor_report.py
=========================================================
MonitorReport — snapshot of monitoring state for a source.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .drift_detector import DriftAlert
from .performance_tracker import MetricSample


@dataclass
class MonitorReport:
    """Snapshot of monitoring health for a specific source."""

    report_id:    str              = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:    str              = ""
    avg_quality:  float            = 0.0
    avg_confidence: float          = 0.0
    quality_trend: str             = "stable"  # improving | degrading | stable
    drift_alerts: list[dict[str, Any]] = field(default_factory=list)
    total_samples: int             = 0
    alert_count:  int              = 0
    generated_at: float            = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":     self.report_id,
            "source_id":     self.source_id,
            "avg_quality":   round(self.avg_quality, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "quality_trend": self.quality_trend,
            "drift_alerts":  self.drift_alerts,
            "total_samples": self.total_samples,
            "alert_count":   self.alert_count,
            "generated_at":  self.generated_at,
        }


def build_monitor_report(
    source_id:      str,
    quality_samples: list[MetricSample],
    confidence_samples: list[MetricSample],
    alerts:         list[DriftAlert],
) -> MonitorReport:
    avg_q  = (
        sum(s.value for s in quality_samples) / len(quality_samples)
        if quality_samples else 0.0
    )
    avg_c  = (
        sum(s.value for s in confidence_samples) / len(confidence_samples)
        if confidence_samples else 0.0
    )

    # Simple trend: compare second half to first half
    trend = "stable"
    if len(quality_samples) >= 4:
        half   = len(quality_samples) // 2
        first  = sum(s.value for s in quality_samples[:half]) / half
        second = sum(s.value for s in quality_samples[half:]) / (len(quality_samples) - half)
        if second - first > 0.02:
            trend = "improving"
        elif first - second > 0.02:
            trend = "degrading"

    return MonitorReport(
        source_id          = source_id,
        avg_quality        = avg_q,
        avg_confidence     = avg_c,
        quality_trend      = trend,
        drift_alerts       = [a.to_dict() for a in alerts],
        total_samples      = len(quality_samples),
        alert_count        = len(alerts),
    )
