"""iios/investment/strategy/risk/limit_monitor.py
LimitMonitor — continuously watches risk levels against limits.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from iios.investment.strategy.risk.risk_constraints import (
    RiskConstraints, ConstraintCheckResult, ConstraintStatus
)
from iios.investment.strategy.risk.risk_limits import RiskLimits, DEFAULT_LIMITS
from iios.investment.strategy.risk.risk_input import StrategyRiskInput


@dataclass(frozen=True)
class LimitBreachEvent:
    event_id:    str
    strategy_id: str
    breach_type: str   # constraint name that was breached
    actual:      float
    limit:       float
    is_emergency: bool
    timestamp:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "strategy_id": self.strategy_id,
            "breach_type": self.breach_type,
            "actual":      round(self.actual, 6),
            "limit":       round(self.limit, 6),
            "is_emergency": self.is_emergency,
            "timestamp":   self.timestamp.isoformat(),
        }


class LimitMonitor:
    """
    Thread-safe monitor for risk limit breaches.
    Stores breach events in a ring buffer per strategy.
    """

    def __init__(
        self,
        limits:             RiskLimits = DEFAULT_LIMITS,
        max_events_per_sid: int = 200,
    ) -> None:
        self._limits      = limits
        self._constraints = RiskConstraints()
        self._max         = max_events_per_sid
        self._store:  Dict[str, Deque[LimitBreachEvent]] = {}
        self._lock = threading.RLock()

    def check_and_record(
        self,
        inp:             StrategyRiskInput,
        risk_score:      float,
        stress_pass_rate: float = 1.0,
        stress_agg_score: float = 0.0,
    ) -> ConstraintCheckResult:
        """
        Evaluate limits and record any breach events.
        Returns the full ConstraintCheckResult.
        """
        result = self._constraints.check(
            inp, risk_score, stress_pass_rate, stress_agg_score, self._limits
        )
        if not result.all_passed or result.emergency_stop:
            self._record_events(result)
        return result

    def _record_events(self, result: ConstraintCheckResult) -> None:
        sid = result.strategy_id
        with self._lock:
            if sid not in self._store:
                self._store[sid] = deque(maxlen=self._max)
            for breach in result.breaches:
                evt = LimitBreachEvent(
                    event_id=str(uuid.uuid4()),
                    strategy_id=sid,
                    breach_type=breach.name,
                    actual=breach.actual,
                    limit=breach.limit,
                    is_emergency=result.emergency_stop,
                )
                self._store[sid].append(evt)

    def breach_history(self, strategy_id: str, n: int = 50) -> List[LimitBreachEvent]:
        with self._lock:
            return list(self._store.get(strategy_id, []))[-n:]

    def latest_breach(self, strategy_id: str) -> Optional[LimitBreachEvent]:
        with self._lock:
            buf = self._store.get(strategy_id)
            return buf[-1] if buf else None

    def total_breach_count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._store.get(strategy_id, []))

    def all_strategy_ids_with_breaches(self) -> List[str]:
        with self._lock:
            return [sid for sid, buf in self._store.items() if buf]
