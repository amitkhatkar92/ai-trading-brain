"""iios/investment/strategy/opportunity/strategy_alerts.py
StrategyAlert — alert type and thread-safe registry.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AlertSeverity(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    MAJOR    = "major"
    CRITICAL = "critical"


class AlertType(str, Enum):
    REGIME_SHIFT         = "regime_shift"
    VOLATILITY_SPIKE     = "volatility_spike"
    CONFIDENCE_DROP      = "confidence_drop"
    DIRECTION_FLIP       = "direction_flip"
    RANKING_DEGRADATION  = "ranking_degradation"
    STRATEGY_DEGRADATION = "strategy_degradation"
    OPPORTUNITY_EXPIRING = "opportunity_expiring"
    RECOMMENDATION_STALE = "recommendation_stale"
    CUSTOM               = "custom"


@dataclass(frozen=True)
class StrategyAlert:
    alert_id:       str
    alert_type:     AlertType
    severity:       AlertSeverity
    strategy_id:    str
    opportunity_id: str
    title:          str
    description:    str
    action_required: bool
    suggested_action: str
    raised_at:      datetime
    metadata:       Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        alert_type: AlertType,
        severity: AlertSeverity,
        strategy_id: str,
        opportunity_id: str,
        title: str,
        description: str,
        action_required: bool = False,
        suggested_action: str = "",
        metadata: Dict[str, Any] | None = None,
    ) -> "StrategyAlert":
        return cls(
            alert_id=str(uuid.uuid4()),
            alert_type=alert_type,
            severity=severity,
            strategy_id=strategy_id,
            opportunity_id=opportunity_id,
            title=title,
            description=description,
            action_required=action_required,
            suggested_action=suggested_action,
            raised_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id":        self.alert_id,
            "alert_type":      self.alert_type.value,
            "severity":        self.severity.value,
            "strategy_id":     self.strategy_id,
            "opportunity_id":  self.opportunity_id,
            "title":           self.title,
            "description":     self.description,
            "action_required": self.action_required,
            "suggested_action": self.suggested_action,
            "raised_at":       self.raised_at.isoformat(),
        }


class AlertRegistry:
    """Thread-safe append-only store of StrategyAlert objects."""

    def __init__(self, max_alerts: int = 5_000) -> None:
        from collections import deque
        self._max    = max_alerts
        self._alerts: List[StrategyAlert] = []
        self._by_opp: Dict[str, List[StrategyAlert]] = {}
        self._lock   = threading.RLock()

    def add(self, alert: StrategyAlert) -> None:
        with self._lock:
            self._alerts.append(alert)
            if len(self._alerts) > self._max:
                removed = self._alerts.pop(0)
                opp_list = self._by_opp.get(removed.opportunity_id, [])
                if removed in opp_list:
                    opp_list.remove(removed)
            self._by_opp.setdefault(alert.opportunity_id, []).append(alert)

    def for_opportunity(self, opportunity_id: str) -> List[StrategyAlert]:
        with self._lock:
            return list(self._by_opp.get(opportunity_id, []))

    def for_strategy(self, strategy_id: str) -> List[StrategyAlert]:
        with self._lock:
            return [a for a in self._alerts if a.strategy_id == strategy_id]

    def critical(self) -> List[StrategyAlert]:
        with self._lock:
            return [a for a in self._alerts if a.severity == AlertSeverity.CRITICAL]

    def action_required(self) -> List[StrategyAlert]:
        with self._lock:
            return [a for a in self._alerts if a.action_required]

    def recent(self, n: int = 50) -> List[StrategyAlert]:
        with self._lock:
            return list(self._alerts[-n:])

    def count(self) -> int:
        with self._lock:
            return len(self._alerts)
