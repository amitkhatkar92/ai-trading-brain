"""iios/investment/market/volatility/regime_transition.py
Tracks regime changes and maintains a transition history.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional

from iios.investment.market.volatility.models import (
    VolatilityEvent,
    VolatilityEventType,
    VolatilityRegimeType,
)


@dataclass
class RegimeTransition:
    bar_index: int
    from_regime: VolatilityRegimeType
    to_regime: VolatilityRegimeType
    severity: float  # 0-1


class RegimeTransitionDetector:
    """
    Detects regime changes, computes transition severity, and generates
    VolatilityEvents.

    Also tracks how many bars the engine has been in the current regime so
    that the RegimeClassifier can use this for confidence / probability.
    """

    def __init__(self, history_size: int = 100) -> None:
        self._current: Optional[VolatilityRegimeType] = None
        self._duration: int = 0
        self._history: Deque[RegimeTransition] = deque(maxlen=history_size)

    # ── Public API ─────────────────────────────────────────────────────────

    def update(
        self,
        regime: VolatilityRegimeType,
        bar_index: int,
        symbol: str,
        timeframe: str,
    ) -> Optional[VolatilityEvent]:
        """
        Update current regime.  Returns a VolatilityEvent if a transition
        occurred, else None.
        """
        if self._current is None:
            self._current = regime
            self._duration = 1
            return None

        if regime == self._current:
            self._duration += 1
            return None

        # Transition detected
        transition = RegimeTransition(
            bar_index=bar_index,
            from_regime=self._current,
            to_regime=regime,
            severity=self._transition_severity(self._current, regime),
        )
        self._history.append(transition)
        event = VolatilityEvent(
            event_type=VolatilityEventType.REGIME_CHANGE,
            symbol=symbol,
            timeframe=timeframe,
            bar_index=bar_index,
            severity=transition.severity,
            from_regime=self._current,
            to_regime=regime,
            description=f"Regime: {self._current.value} → {regime.value}",
        )
        self._current = regime
        self._duration = 1
        return event

    @property
    def current_regime(self) -> Optional[VolatilityRegimeType]:
        return self._current

    @property
    def duration_bars(self) -> int:
        return self._duration

    @property
    def previous_regime(self) -> Optional[VolatilityRegimeType]:
        if self._history:
            return self._history[-1].from_regime
        return None

    def recent_transitions(self, n: int = 10) -> List[RegimeTransition]:
        return list(self._history)[-n:]

    # ── Internal ──────────────────────────────────────────────────────────

    _SEVERITY_ORDER = {
        VolatilityRegimeType.VERY_LOW:    0,
        VolatilityRegimeType.LOW:         1,
        VolatilityRegimeType.COMPRESSION: 1,
        VolatilityRegimeType.NORMAL:      2,
        VolatilityRegimeType.ELEVATED:    3,
        VolatilityRegimeType.EXPANSION:   4,
        VolatilityRegimeType.HIGH:        5,
        VolatilityRegimeType.RECOVERY:    4,
        VolatilityRegimeType.EXTREME:     6,
        VolatilityRegimeType.SHOCK:       7,
        VolatilityRegimeType.UNKNOWN:     2,
    }

    def _transition_severity(
        self,
        from_regime: VolatilityRegimeType,
        to_regime: VolatilityRegimeType,
    ) -> float:
        f = self._SEVERITY_ORDER.get(from_regime, 2)
        t = self._SEVERITY_ORDER.get(to_regime, 2)
        delta = abs(t - f)
        max_delta = 7  # max possible steps
        return min(1.0, delta / max_delta + 0.1)
