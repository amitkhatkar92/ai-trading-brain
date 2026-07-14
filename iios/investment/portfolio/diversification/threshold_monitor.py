"""iios/investment/portfolio/diversification/threshold_monitor.py

Threshold monitoring: checks individual diversification metrics against limits.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.diversification.diversification_alerts import AlertThresholds
from iios.investment.portfolio.diversification.diversification_engine import (
    DiversificationAnalysis,
)
from iios.investment.portfolio.diversification.diversification_types import AlertSeverity


@dataclass(frozen=True)
class ThresholdCheck:
    check_id:   str           = field(default_factory=lambda: str(uuid.uuid4()))
    check_name: str           = ""
    breached:   bool          = False
    actual:     float         = 0.0
    threshold:  float         = 0.0
    severity:   AlertSeverity = AlertSeverity.INFO
    message:    str           = ""
    checked_at: float         = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":   self.check_id,
            "check_name": self.check_name,
            "breached":   self.breached,
            "actual":     round(self.actual, 4),
            "threshold":  round(self.threshold, 4),
            "severity":   self.severity.value,
            "message":    self.message,
        }


@dataclass(frozen=True)
class ThresholdReport:
    report_id:   str                     = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:str                     = ""
    checks:      Tuple[ThresholdCheck, ...]  = field(default_factory=tuple)
    total:       int                     = 0
    breached:    int                     = 0
    critical:    int                     = 0
    warnings:    int                     = 0
    all_passed:  bool                    = True
    checked_at:  float                   = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":   self.report_id,
            "portfolio_id":self.portfolio_id,
            "total":       self.total,
            "breached":    self.breached,
            "critical":    self.critical,
            "warnings":    self.warnings,
            "all_passed":  self.all_passed,
            "checks":      [c.to_dict() for c in self.checks],
        }


def _check(name: str, actual: float, threshold: float, *, upper: bool = True,
           severity: AlertSeverity = AlertSeverity.WARNING) -> ThresholdCheck:
    """Create a threshold check (upper = actual must be below threshold)."""
    breached = (actual > threshold) if upper else (actual < threshold)
    direction = "exceeds" if upper else "below"
    return ThresholdCheck(
        check_name = name,
        breached   = breached,
        actual     = actual,
        threshold  = threshold,
        severity   = severity if breached else AlertSeverity.INFO,
        message    = (
            f"{name}: {actual:.4f} {direction} {threshold:.4f}"
            if breached else f"{name}: OK ({actual:.4f})"
        ),
    )


class ThresholdMonitor:
    """Runs all threshold checks against a DiversificationAnalysis."""

    def monitor(
        self,
        analysis:    DiversificationAnalysis,
        thresholds:  Optional[AlertThresholds] = None,
        portfolio_id:str = "",
    ) -> ThresholdReport:
        t = thresholds or AlertThresholds()
        pos_c  = analysis.concentration.position
        sec_c  = analysis.concentration.sector.sector
        corr_a = analysis.correlation.analysis

        checks = [
            _check("top1_weight",       pos_c.top1_weight,        t.top1_warning,
                   severity=AlertSeverity.WARNING),
            _check("top5_weight",       pos_c.top5_weight,        t.top5_warning,
                   severity=AlertSeverity.WARNING),
            _check("sector_top1",       sec_c.top1_weight,        t.sector_warning,
                   severity=AlertSeverity.WARNING),
            _check("sector_top1_crit",  sec_c.top1_weight,        t.sector_critical,
                   severity=AlertSeverity.CRITICAL),
            _check("avg_correlation",   corr_a.avg_correlation,   t.avg_corr_warning,
                   severity=AlertSeverity.WARNING),
            _check("avg_correlation_crit", corr_a.avg_correlation, t.avg_corr_critical,
                   severity=AlertSeverity.CRITICAL),
            _check("sector_hhi",        analysis.sector_hhi,      t.max_sector_hhi,
                   severity=AlertSeverity.WARNING),
            _check("effective_n",       analysis.effective_n,     t.min_effective_n,
                   upper=False, severity=AlertSeverity.WARNING),
            _check("entropy_ratio",     analysis.entropy_ratio,   t.min_entropy_ratio,
                   upper=False, severity=AlertSeverity.INFO),
        ]

        breached  = sum(1 for c in checks if c.breached)
        critical  = sum(1 for c in checks if c.breached and c.severity == AlertSeverity.CRITICAL)
        warnings  = sum(1 for c in checks if c.breached and c.severity == AlertSeverity.WARNING)

        return ThresholdReport(
            portfolio_id = portfolio_id or analysis.portfolio_id,
            checks       = tuple(checks),
            total        = len(checks),
            breached     = breached,
            critical     = critical,
            warnings     = warnings,
            all_passed   = breached == 0,
        )
