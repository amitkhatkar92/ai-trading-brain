"""iios/investment/strategy/portfolio/portfolio_monitor.py
PortfolioMonitor — watches active portfolios and raises health alerts.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioState
)
from iios.investment.strategy.portfolio.portfolio_registry import PortfolioRegistry
from iios.investment.strategy.portfolio.portfolio_events import (
    PortfolioEvent, PortfolioEventType, PortfolioEventBus
)
from iios.investment.strategy.portfolio.construction_constraints import ConstructionConstraints, DEFAULT_CONSTRAINTS


class AlertSeverity(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class PortfolioAlert:
    alert_id:     str
    portfolio_id: str
    severity:     AlertSeverity
    message:      str
    details:      Dict[str, Any]
    raised_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id":     self.alert_id,
            "portfolio_id": self.portfolio_id,
            "severity":     self.severity.value,
            "message":      self.message,
            "details":      self.details,
            "raised_at":    self.raised_at.isoformat(),
        }


class PortfolioMonitor:
    """
    Checks active portfolios against health criteria and emits alerts.
    Intended to be called periodically (e.g. every N seconds).
    """

    def __init__(
        self,
        registry:    PortfolioRegistry,
        event_bus:   Optional[PortfolioEventBus] = None,
        constraints: ConstructionConstraints = DEFAULT_CONSTRAINTS,
    ) -> None:
        self._registry    = registry
        self._bus         = event_bus or PortfolioEventBus()
        self._constraints = constraints
        self._lock        = threading.RLock()
        self._alert_log:  List[PortfolioAlert] = []

    def run_health_check(self) -> List[PortfolioAlert]:
        """
        Scan all active portfolios for anomalies.
        Returns list of new alerts generated this cycle.
        """
        new_alerts: List[PortfolioAlert] = []
        active = self._registry.active()

        for portfolio in active:
            alerts = self._check_portfolio(portfolio)
            new_alerts.extend(alerts)
            for alert in alerts:
                self._emit_alert(portfolio, alert)

        with self._lock:
            self._alert_log.extend(new_alerts)

        return new_alerts

    def _check_portfolio(self, portfolio: StrategyPortfolio) -> List[PortfolioAlert]:
        alerts: List[PortfolioAlert] = []
        pid    = portfolio.portfolio_id

        # Check total weight drift from 1.0
        tw = portfolio.total_weight
        if abs(tw - 1.0) > 0.02:
            alerts.append(self._alert(
                pid, AlertSeverity.WARNING,
                f"Total weight {tw:.4f} deviates from 1.0",
                {"total_weight": tw},
            ))

        # Check max single weight drift
        max_drift = portfolio.max_drift
        if max_drift > self._constraints.rebalance_threshold:
            alerts.append(self._alert(
                pid, AlertSeverity.WARNING,
                f"Max weight drift {max_drift:.4f} exceeds threshold {self._constraints.rebalance_threshold:.4f}",
                {"max_drift": max_drift, "threshold": self._constraints.rebalance_threshold},
            ))

        # Check active strategy count
        n = portfolio.active_count
        if n < self._constraints.min_strategies:
            alerts.append(self._alert(
                pid, AlertSeverity.CRITICAL,
                f"Only {n} active strategies — below minimum {self._constraints.min_strategies}",
                {"active_count": n, "min_strategies": self._constraints.min_strategies},
            ))

        return alerts

    def _alert(
        self, portfolio_id: str, severity: AlertSeverity, msg: str, details: Dict
    ) -> PortfolioAlert:
        return PortfolioAlert(
            alert_id=str(uuid.uuid4()),
            portfolio_id=portfolio_id,
            severity=severity,
            message=msg,
            details=details,
        )

    def _emit_alert(self, portfolio: StrategyPortfolio, alert: PortfolioAlert) -> None:
        event = PortfolioEvent(
            event_id=str(uuid.uuid4()),
            event_type=PortfolioEventType.HEALTH_ALERT,
            portfolio_id=portfolio.portfolio_id,
            payload=alert.to_dict(),
        )
        self._bus.emit(event)

    def alert_history(self, portfolio_id: Optional[str] = None, n: int = 50) -> List[PortfolioAlert]:
        with self._lock:
            alerts = self._alert_log if portfolio_id is None else [
                a for a in self._alert_log if a.portfolio_id == portfolio_id
            ]
            return alerts[-n:]
