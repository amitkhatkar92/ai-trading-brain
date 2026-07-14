"""iios/investment/portfolio/diversification/diversification_alerts.py

Threshold-based alert system for diversification monitoring.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.diversification.diversification_types import (
    AlertSeverity,
    AVG_CORR_CRITICAL,
    AVG_CORR_WARNING,
    SECTOR_CRITICAL_THRESHOLD,
    SECTOR_WARNING_THRESHOLD,
    TOP1_WARNING_THRESHOLD,
    TOP5_WARNING_THRESHOLD,
)
from iios.investment.portfolio.diversification.diversification_engine import (
    DiversificationAnalysis,
)


@dataclass(frozen=True)
class AlertThresholds:
    """Configurable thresholds for alert generation."""
    top1_warning:       float = TOP1_WARNING_THRESHOLD
    top5_warning:       float = TOP5_WARNING_THRESHOLD
    sector_warning:     float = SECTOR_WARNING_THRESHOLD
    sector_critical:    float = SECTOR_CRITICAL_THRESHOLD
    avg_corr_warning:   float = AVG_CORR_WARNING
    avg_corr_critical:  float = AVG_CORR_CRITICAL
    min_effective_n:    float = 3.0     # portfolio must have ≥ 3 effective positions
    min_entropy_ratio:  float = 0.40    # portfolio entropy should be ≥ 40% of maximum
    max_sector_hhi:     float = 0.35    # sector HHI should be ≤ 0.35
    max_overlap_risk:   str   = "moderate"   # "low" | "moderate" | "high"

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass(frozen=True)
class DiversificationAlert:
    """A single diversification alert."""

    alert_id:   str           = field(default_factory=lambda: str(uuid.uuid4()))
    severity:   AlertSeverity = AlertSeverity.INFO
    category:   str           = ""
    rule:       str           = ""
    message:    str           = ""
    actual:     float         = 0.0
    threshold:  float         = 0.0
    generated_at: float       = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id":     self.alert_id,
            "severity":     self.severity.value,
            "category":     self.category,
            "rule":         self.rule,
            "message":      self.message,
            "actual":       round(self.actual, 4),
            "threshold":    round(self.threshold, 4),
            "generated_at": self.generated_at,
        }


class DiversificationAlerter:
    """Generates DiversificationAlert list from a DiversificationAnalysis."""

    def generate(
        self,
        analysis:    DiversificationAnalysis,
        thresholds:  Optional[AlertThresholds] = None,
    ) -> Tuple[DiversificationAlert, ...]:
        t = thresholds or AlertThresholds()
        alerts: List[DiversificationAlert] = []
        pos_c  = analysis.concentration.position
        sec_c  = analysis.concentration.sector.sector
        corr_a = analysis.correlation.analysis
        overlap= analysis.correlation.overlap

        def _alert(sev, cat, rule, msg, actual, threshold):
            alerts.append(DiversificationAlert(
                severity=sev, category=cat, rule=rule,
                message=msg, actual=actual, threshold=threshold,
            ))

        # Top-1 position
        if pos_c.top1_weight >= t.top1_warning:
            sev = AlertSeverity.CRITICAL if pos_c.top1_weight >= 0.40 else AlertSeverity.WARNING
            _alert(sev, "concentration", "top1_position",
                   f"Position {pos_c.top1_symbol} is {pos_c.top1_weight:.1%} of portfolio",
                   pos_c.top1_weight, t.top1_warning)

        # Top-5 positions
        if pos_c.top5_weight >= t.top5_warning:
            _alert(AlertSeverity.WARNING, "concentration", "top5_positions",
                   f"Top-5 positions are {pos_c.top5_weight:.1%} of portfolio",
                   pos_c.top5_weight, t.top5_warning)

        # Sector concentration
        if sec_c.top1_weight >= t.sector_critical:
            _alert(AlertSeverity.CRITICAL, "sector", "sector_critical",
                   f"Sector '{sec_c.top1_bucket}' is {sec_c.top1_weight:.1%} — critical",
                   sec_c.top1_weight, t.sector_critical)
        elif sec_c.top1_weight >= t.sector_warning:
            _alert(AlertSeverity.WARNING, "sector", "sector_warning",
                   f"Sector '{sec_c.top1_bucket}' is {sec_c.top1_weight:.1%}",
                   sec_c.top1_weight, t.sector_warning)

        # Correlation
        if corr_a.avg_correlation >= t.avg_corr_critical:
            _alert(AlertSeverity.CRITICAL, "correlation", "avg_correlation_critical",
                   f"Average correlation {corr_a.avg_correlation:.2f} — extremely high",
                   corr_a.avg_correlation, t.avg_corr_critical)
        elif corr_a.avg_correlation >= t.avg_corr_warning:
            _alert(AlertSeverity.WARNING, "correlation", "avg_correlation_warning",
                   f"Average correlation {corr_a.avg_correlation:.2f}",
                   corr_a.avg_correlation, t.avg_corr_warning)

        # Effective N
        if analysis.effective_n < t.min_effective_n:
            _alert(AlertSeverity.WARNING, "diversification", "low_effective_n",
                   f"Effective-N {analysis.effective_n:.1f} below minimum {t.min_effective_n:.1f}",
                   analysis.effective_n, t.min_effective_n)

        # Entropy ratio
        if analysis.entropy_ratio < t.min_entropy_ratio:
            _alert(AlertSeverity.INFO, "diversification", "low_entropy",
                   f"Entropy ratio {analysis.entropy_ratio:.2f} below threshold {t.min_entropy_ratio:.2f}",
                   analysis.entropy_ratio, t.min_entropy_ratio)

        # Overlap risk
        overlap_risk_order = {"low": 0, "moderate": 1, "high": 2}
        if overlap_risk_order.get(overlap.overlap_risk, 0) > overlap_risk_order.get(t.max_overlap_risk, 1):
            _alert(AlertSeverity.WARNING, "overlap", "high_overlap",
                   f"Overlap risk is '{overlap.overlap_risk}'",
                   overlap.thematic_overlap, 0.0)

        # Sort: critical first
        alerts.sort(key=lambda a: (
            0 if a.severity == AlertSeverity.CRITICAL else
            1 if a.severity == AlertSeverity.WARNING else 2
        ))
        return tuple(alerts)
