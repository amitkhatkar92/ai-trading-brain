"""iios/investment/portfolio/diversification/diversification_monitor.py

Monitoring orchestrator: combines alerts + threshold checks + trend analysis.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.diversification.diversification_alerts import (
    AlertThresholds,
    DiversificationAlert,
    DiversificationAlerter,
)
from iios.investment.portfolio.diversification.diversification_engine import (
    DiversificationAnalysis,
)
from iios.investment.portfolio.diversification.diversification_profile import (
    DiversificationProfile,
)
from iios.investment.portfolio.diversification.diversification_trends import (
    TrendAnalyzer,
    TrendsReport,
)
from iios.investment.portfolio.diversification.threshold_monitor import (
    ThresholdMonitor,
    ThresholdReport,
)
from iios.investment.portfolio.diversification.diversification_types import AlertSeverity


@dataclass(frozen=True)
class MonitoringReport:
    """Combined result of all monitoring checks."""

    report_id:         str                          = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str                          = ""
    alerts:            Tuple[DiversificationAlert,...] = field(default_factory=tuple)
    threshold_report:  ThresholdReport              = field(default_factory=ThresholdReport)
    trend_report:      TrendsReport                 = field(default_factory=TrendsReport)
    n_alerts:          int                          = 0
    n_critical_alerts: int                          = 0
    n_warnings:        int                          = 0
    has_critical:      bool                         = False
    requires_attention:bool                         = False
    generated_at:      float                        = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":         self.report_id,
            "portfolio_id":      self.portfolio_id,
            "n_alerts":          self.n_alerts,
            "n_critical_alerts": self.n_critical_alerts,
            "n_warnings":        self.n_warnings,
            "has_critical":      self.has_critical,
            "requires_attention":self.requires_attention,
            "alerts":            [a.to_dict() for a in self.alerts],
            "threshold_report":  self.threshold_report.to_dict(),
            "trend_report":      self.trend_report.to_dict(),
            "generated_at":      self.generated_at,
        }


class DiversificationMonitor:
    """Orchestrates all monitoring for a portfolio's diversification."""

    def __init__(
        self,
        thresholds:   Optional[AlertThresholds] = None,
    ) -> None:
        self._alerter   = DiversificationAlerter()
        self._threshold = ThresholdMonitor()
        self._trends    = TrendAnalyzer()
        self._thresholds= thresholds

    def monitor(
        self,
        analysis:      DiversificationAnalysis,
        history:       Optional[Any] = None,   # DiversificationHistory (duck-typed)
        portfolio_id:  str = "",
    ) -> MonitoringReport:
        t = self._thresholds

        # Alerts
        alerts = self._alerter.generate(analysis, t)

        # Threshold checks
        threshold_rpt = self._threshold.monitor(
            analysis, t, portfolio_id or analysis.portfolio_id
        )

        # Trends (from history if available)
        if history is not None and hasattr(history, "metric_series") and history.count() >= 2:
            key_metrics = [
                "overall_score", "hhi", "entropy_ratio",
                "avg_correlation", "effective_n", "top_sector_weight",
            ]
            series = {m: history.metric_series(m) for m in key_metrics}
            trend_rpt = self._trends.analyze(series, portfolio_id or analysis.portfolio_id)
        else:
            trend_rpt = TrendsReport(portfolio_id=portfolio_id or analysis.portfolio_id)

        n_alerts   = len(alerts)
        n_critical = sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL)
        n_warn     = sum(1 for a in alerts if a.severity == AlertSeverity.WARNING)
        has_crit   = n_critical > 0
        requires   = has_crit or threshold_rpt.critical > 0

        return MonitoringReport(
            portfolio_id      = portfolio_id or analysis.portfolio_id,
            alerts            = alerts,
            threshold_report  = threshold_rpt,
            trend_report      = trend_rpt,
            n_alerts          = n_alerts,
            n_critical_alerts = n_critical,
            n_warnings        = n_warn,
            has_critical      = has_crit,
            requires_attention= requires,
        )
