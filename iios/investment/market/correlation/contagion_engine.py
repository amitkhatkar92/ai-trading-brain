"""iios/investment/market/correlation/contagion_engine.py
Contagion risk analysis: tracks risk elevation and patterns over time.
"""
from __future__ import annotations

from collections import deque
from typing import List, Optional

from iios.investment.market.correlation.models import (
    CorrelationEvent,
    CorrelationEventType,
    CorrelationMatrix,
    RiskLevel,
    SystemicRiskMetrics,
)


_CONTAGION_THRESHOLD = 0.70  # systemic score above which contagion is flagged


class ContagionEngine:
    """
    Monitors systemic risk metrics over time and emits CorrelationEvents
    when contagion risk becomes elevated.
    """

    def __init__(self, window: int = 20) -> None:
        self._window       = window
        self._score_history: deque = deque(maxlen=window)
        self._prev_level:  Optional[RiskLevel] = None

    def update(
        self,
        systemic: SystemicRiskMetrics,
        bar_index: int,
    ) -> List[CorrelationEvent]:
        self._score_history.append(systemic.systemic_risk_score)
        events: List[CorrelationEvent] = []

        # Emit contagion event on risk escalation
        if self._prev_level is not None:
            if self._has_escalated(self._prev_level, systemic.risk_level):
                events.append(CorrelationEvent(
                    event_type=CorrelationEventType.CONTAGION_DETECTED,
                    bar_index=bar_index,
                    severity=systemic.systemic_risk_score / 100,
                    description=(
                        f"Systemic risk escalated to {systemic.risk_level.value} "
                        f"(score={systemic.systemic_risk_score:.1f})"
                    ),
                ))

            if systemic.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                events.append(CorrelationEvent(
                    event_type=CorrelationEventType.SYSTEMIC_RISK_ELEVATED,
                    bar_index=bar_index,
                    severity=systemic.systemic_risk_score / 100,
                    description=f"Systemic risk: {systemic.risk_level.value}",
                ))

        self._prev_level = systemic.risk_level
        return events

    def rolling_avg_score(self) -> float:
        if not self._score_history:
            return 0.0
        return sum(self._score_history) / len(self._score_history)

    def is_elevated(self) -> bool:
        return self.rolling_avg_score() >= _CONTAGION_THRESHOLD * 100

    # ── Internal ──────────────────────────────────────────────────────────

    _RISK_ORDER = {
        RiskLevel.LOW:      0,
        RiskLevel.MODERATE: 1,
        RiskLevel.ELEVATED: 2,
        RiskLevel.HIGH:     3,
        RiskLevel.CRITICAL: 4,
    }

    def _has_escalated(self, prev: RiskLevel, current: RiskLevel) -> bool:
        return self._RISK_ORDER.get(current, 0) > self._RISK_ORDER.get(prev, 0)
