"""iios/investment/market/opportunity/opportunity_monitor.py
Full opportunity monitor — orchestrates change detection, alerts, priorities.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from iios.investment.market.opportunity.alert_engine import AlertEngine
from iios.investment.market.opportunity.change_detector import ChangeDetector
from iios.investment.market.opportunity.models import (
    Opportunity,
    OpportunityAlert,
)
from iios.investment.market.opportunity.priority_monitor import PriorityMonitor

log = logging.getLogger(__name__)


class OpportunityMonitor:
    """Orchestrates monitoring of all active opportunities."""

    def __init__(self) -> None:
        self._change_detector = ChangeDetector()
        self._alert_engine    = AlertEngine()
        self._priority_monitor = PriorityMonitor()

        # External callbacks
        self.on_alert:           Optional[Callable[[OpportunityAlert], None]] = None
        self.on_new_critical:    Optional[Callable[[List[str]], None]] = None
        self._alert_engine.on_alert = self._dispatch_alert

    # ── update ────────────────────────────────────────────────────────────────

    def update(
        self,
        opportunities: List[Opportunity],
        bar_index: int,
    ) -> List[OpportunityAlert]:
        """Detect changes, publish alerts, update priority buckets."""
        alerts = self._change_detector.detect(opportunities, bar_index)
        self._alert_engine.publish(alerts)
        self._priority_monitor.update(opportunities)

        new_critical = self._priority_monitor.new_critical()
        if new_critical and self.on_new_critical:
            try:
                self.on_new_critical(new_critical)
            except Exception:
                log.exception("on_new_critical callback error")

        return alerts

    # ── queries ───────────────────────────────────────────────────────────────

    def recent_alerts(self, n: int = 20) -> List[OpportunityAlert]:
        return self._alert_engine.recent(n)

    def high_priority_opportunities(self) -> List[Opportunity]:
        return self._priority_monitor.high_and_above()

    def critical_opportunities(self) -> List[Opportunity]:
        return self._priority_monitor.critical()

    def alert_engine(self) -> AlertEngine:
        return self._alert_engine

    def priority_monitor(self) -> PriorityMonitor:
        return self._priority_monitor

    # ── internal ─────────────────────────────────────────────────────────────

    def _dispatch_alert(self, alert: OpportunityAlert) -> None:
        if self.on_alert:
            try:
                self.on_alert(alert)
            except Exception:
                log.exception("on_alert callback error")
