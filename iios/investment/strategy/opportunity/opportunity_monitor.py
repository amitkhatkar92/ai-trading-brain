"""iios/investment/strategy/opportunity/opportunity_monitor.py
OpportunityMonitor — orchestrates all monitoring subsystems:
ChangeDetector, PriorityMonitor, and AlertRegistry.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, List, Optional, Union

from iios.investment.strategy.opportunity.market_opportunity import MarketOpportunity
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.strategy.opportunity.strategy_opportunity import (
    StrategyOpportunity, OpportunityState
)
from iios.investment.strategy.opportunity.change_detector import ChangeDetector, ChangeEvent
from iios.investment.strategy.opportunity.priority_monitor import PriorityMonitor
from iios.investment.strategy.opportunity.strategy_alerts import (
    AlertRegistry, AlertSeverity, AlertType, StrategyAlert
)

logger = logging.getLogger(__name__)

AlertCallback = Callable[[StrategyAlert], None]


class OpportunityMonitor:
    """
    Central monitoring hub.

    Usage::

        monitor = OpportunityMonitor()

        # Register strategies for priority monitoring
        monitor.register(opportunity)

        # Feed updated market snapshots
        changes = monitor.update_market(previous_opp, current_opp)

        # Check active opportunity scores
        alerts = monitor.check_opportunity(opp)

        # Query alerts
        critical = monitor.alert_registry.critical()
    """

    def __init__(self) -> None:
        self._change_detector = ChangeDetector()
        self._alert_registry  = AlertRegistry()
        self._priority        = PriorityMonitor(self._alert_registry)
        self._lock            = threading.RLock()
        self._callbacks: List[AlertCallback] = []

        # Snapshot store for previous market opportunities (for diff detection)
        self._market_snapshots:  Dict[str, MarketOpportunity]  = {}
        self._company_snapshots: Dict[str, CompanyOpportunity] = {}

        logger.info("OpportunityMonitor initialised")

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def alert_registry(self) -> AlertRegistry:
        return self._alert_registry

    def register(self, opp: StrategyOpportunity) -> None:
        """Register an opportunity for priority score monitoring."""
        if opp.state in (OpportunityState.RECOMMENDED, OpportunityState.APPROVED,
                         OpportunityState.MONITORING):
            self._priority.register(opp)

    def deregister(self, opportunity_id: str) -> None:
        self._priority.deregister(opportunity_id)

    def subscribe_alerts(self, callback: AlertCallback) -> None:
        """Register a callback to be invoked for every new alert."""
        with self._lock:
            self._callbacks.append(callback)

    # ── market intelligence updates ───────────────────────────────────────────

    def update_market(
        self, current: MarketOpportunity
    ) -> List[ChangeEvent]:
        """
        Feed a fresh market opportunity snapshot.
        Compares against previous snapshot; emits ChangeEvents for significant diffs.
        """
        with self._lock:
            prev = self._market_snapshots.get(current.opportunity_id)
            self._market_snapshots[current.opportunity_id] = current

        if prev is None:
            return []

        changes = self._change_detector.detect_market_changes(prev, current)
        for change in changes:
            if change.severity in ("major", "critical"):
                alert = StrategyAlert.create(
                    alert_type=AlertType.REGIME_SHIFT if change.change_type == "regime_shift"
                              else AlertType.VOLATILITY_SPIKE if "vol" in change.change_type
                              else AlertType.CUSTOM,
                    severity=AlertSeverity.MAJOR if change.severity == "major" else AlertSeverity.CRITICAL,
                    strategy_id="market",
                    opportunity_id=current.opportunity_id,
                    title=f"Market change: {change.change_type}",
                    description=change.description,
                    action_required=change.requires_reeval,
                    suggested_action="Re-evaluate active strategy recommendations" if change.requires_reeval else "",
                )
                self._alert_registry.add(alert)
                self._dispatch(alert)

        return changes

    def update_company(
        self, current: CompanyOpportunity
    ) -> List[ChangeEvent]:
        """Feed a fresh company opportunity snapshot."""
        with self._lock:
            prev = self._company_snapshots.get(current.opportunity_id)
            self._company_snapshots[current.opportunity_id] = current

        if prev is None:
            return []

        changes = self._change_detector.detect_company_changes(prev, current)
        for change in changes:
            if change.requires_reeval:
                alert = StrategyAlert.create(
                    alert_type=AlertType.CONFIDENCE_DROP,
                    severity=AlertSeverity.MAJOR,
                    strategy_id="company",
                    opportunity_id=current.opportunity_id,
                    title=f"Company intelligence change: {change.change_type}",
                    description=change.description,
                    action_required=True,
                    suggested_action="Re-evaluate strategy recommendations for this company",
                )
                self._alert_registry.add(alert)
                self._dispatch(alert)

        return changes

    def check_opportunity(self, opp: StrategyOpportunity) -> List[StrategyAlert]:
        """Check a live opportunity against its priority monitoring baseline."""
        alerts = self._priority.check(opp)
        for a in alerts:
            self._dispatch(a)
        return alerts

    def check_expiring(
        self, opps: List[StrategyOpportunity], warn_minutes: int = 30
    ) -> List[StrategyAlert]:
        """Emit alerts for opportunities that are about to expire."""
        from datetime import timedelta
        alerts: List[StrategyAlert] = []
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        threshold = now + timedelta(minutes=warn_minutes)

        for opp in opps:
            if opp.expires_at and opp.is_active() and opp.expires_at <= threshold:
                minutes_left = max(0, int((opp.expires_at - now).total_seconds() / 60))
                alert = StrategyAlert.create(
                    alert_type=AlertType.OPPORTUNITY_EXPIRING,
                    severity=AlertSeverity.WARNING,
                    strategy_id=opp.strategy_id,
                    opportunity_id=opp.opportunity_id,
                    title="Opportunity expiring soon",
                    description=f"Opportunity expires in ~{minutes_left} min",
                    action_required=opp.state == OpportunityState.RECOMMENDED,
                    suggested_action="Review and approve or archive before expiry",
                )
                self._alert_registry.add(alert)
                self._dispatch(alert)
                alerts.append(alert)

        return alerts

    # ── internals ─────────────────────────────────────────────────────────────

    def _dispatch(self, alert: StrategyAlert) -> None:
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(alert)
            except Exception:
                logger.exception("Alert callback raised")
