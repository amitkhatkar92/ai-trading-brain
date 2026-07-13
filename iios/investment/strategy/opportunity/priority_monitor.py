"""iios/investment/strategy/opportunity/priority_monitor.py
PriorityMonitor — watches high-priority active opportunities and flags
degradation in their ranking or suitability scores.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from iios.investment.strategy.opportunity.strategy_opportunity import (
    StrategyOpportunity, OpportunityState
)
from iios.investment.strategy.opportunity.strategy_alerts import (
    AlertRegistry, AlertSeverity, AlertType, StrategyAlert
)


@dataclass
class MonitorRecord:
    opportunity_id:    str
    strategy_id:       str
    last_ranking_score: float
    last_suitability:  float
    baseline_composite: float
    monitored_since:   datetime
    last_checked_at:   datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    check_count:       int = 0


class PriorityMonitor:
    """
    Tracks composite score degradation for RECOMMENDED / APPROVED / MONITORING
    opportunities.  Issues alerts when scores drop significantly from baseline.
    """

    _DEGRADATION_MINOR    = 10.0   # points
    _DEGRADATION_MODERATE = 20.0
    _DEGRADATION_MAJOR    = 35.0

    def __init__(self, alert_registry: AlertRegistry) -> None:
        self._registry = alert_registry
        self._records:  Dict[str, MonitorRecord] = {}
        self._lock      = threading.RLock()

    def register(self, opp: StrategyOpportunity) -> None:
        """Start monitoring an opportunity."""
        with self._lock:
            if opp.opportunity_id in self._records:
                return
            self._records[opp.opportunity_id] = MonitorRecord(
                opportunity_id=opp.opportunity_id,
                strategy_id=opp.strategy_id,
                last_ranking_score=opp.ranking_score,
                last_suitability=opp.suitability_score,
                baseline_composite=opp.composite_score(),
                monitored_since=datetime.now(timezone.utc),
            )

    def deregister(self, opportunity_id: str) -> None:
        with self._lock:
            self._records.pop(opportunity_id, None)

    def check(self, opp: StrategyOpportunity) -> List[StrategyAlert]:
        """Compare current scores vs baseline and emit alerts for degradation."""
        with self._lock:
            rec = self._records.get(opp.opportunity_id)
            if rec is None:
                return []

        alerts: List[StrategyAlert] = []
        current_composite = opp.composite_score()
        delta = rec.baseline_composite - current_composite  # positive = degradation

        if delta >= self._DEGRADATION_MAJOR:
            alert = StrategyAlert.create(
                alert_type=AlertType.RANKING_DEGRADATION,
                severity=AlertSeverity.CRITICAL,
                strategy_id=opp.strategy_id,
                opportunity_id=opp.opportunity_id,
                title="Major opportunity score degradation",
                description=(
                    f"Composite score dropped {delta:.1f} pts from baseline "
                    f"({rec.baseline_composite:.1f} → {current_composite:.1f})"
                ),
                action_required=True,
                suggested_action="Review opportunity immediately; consider archiving.",
            )
            self._registry.add(alert)
            alerts.append(alert)

        elif delta >= self._DEGRADATION_MODERATE:
            alert = StrategyAlert.create(
                alert_type=AlertType.RANKING_DEGRADATION,
                severity=AlertSeverity.MAJOR,
                strategy_id=opp.strategy_id,
                opportunity_id=opp.opportunity_id,
                title="Moderate opportunity score degradation",
                description=f"Composite score dropped {delta:.1f} pts from baseline",
                action_required=False,
                suggested_action="Monitor closely; re-evaluate if trend continues.",
            )
            self._registry.add(alert)
            alerts.append(alert)

        elif delta >= self._DEGRADATION_MINOR:
            alert = StrategyAlert.create(
                alert_type=AlertType.RANKING_DEGRADATION,
                severity=AlertSeverity.WARNING,
                strategy_id=opp.strategy_id,
                opportunity_id=opp.opportunity_id,
                title="Minor opportunity score degradation",
                description=f"Composite score dropped {delta:.1f} pts from baseline",
                action_required=False,
            )
            self._registry.add(alert)
            alerts.append(alert)

        # Update record
        with self._lock:
            if opp.opportunity_id in self._records:
                rec = self._records[opp.opportunity_id]
                self._records[opp.opportunity_id] = MonitorRecord(
                    opportunity_id=rec.opportunity_id,
                    strategy_id=rec.strategy_id,
                    last_ranking_score=opp.ranking_score,
                    last_suitability=opp.suitability_score,
                    baseline_composite=rec.baseline_composite,
                    monitored_since=rec.monitored_since,
                    last_checked_at=datetime.now(timezone.utc),
                    check_count=rec.check_count + 1,
                )

        return alerts

    def monitored_ids(self) -> List[str]:
        with self._lock:
            return list(self._records.keys())

    def record(self, opportunity_id: str) -> Optional[MonitorRecord]:
        with self._lock:
            return self._records.get(opportunity_id)
