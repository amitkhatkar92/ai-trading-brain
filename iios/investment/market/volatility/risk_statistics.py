"""iios/investment/market/volatility/risk_statistics.py
Tracks risk metric evolution over time.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional

from iios.investment.market.volatility.models import RiskLevel, RiskProfile


@dataclass
class RiskStats:
    total_bars: int = 0
    high_risk_bars: int = 0      # RiskLevel.HIGH, VERY_HIGH, EXTREME
    extreme_risk_bars: int = 0   # RiskLevel.EXTREME
    avg_overall_risk: float = 0.0
    max_overall_risk: float = 0.0
    current_risk_level: RiskLevel = RiskLevel.MODERATE


_HIGH_RISK_LEVELS = {RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.EXTREME}
_EXTREME_RISK_LEVELS = {RiskLevel.EXTREME}


class RiskStatistics:
    """Accumulates RiskProfile observations and exposes aggregate statistics."""

    def __init__(self, window: int = 50) -> None:
        self._window = window
        self._overall_history: Deque[float] = deque(maxlen=window)
        self._risk_level_history: Deque[RiskLevel] = deque(maxlen=window)
        self._total_bars = 0
        self._high_risk_count = 0
        self._extreme_risk_count = 0
        self._max_overall = 0.0

    def record(self, profile: RiskProfile) -> None:
        self._overall_history.append(profile.overall_risk)
        self._risk_level_history.append(profile.risk_level)
        self._total_bars += 1
        if profile.risk_level in _HIGH_RISK_LEVELS:
            self._high_risk_count += 1
        if profile.risk_level in _EXTREME_RISK_LEVELS:
            self._extreme_risk_count += 1
        self._max_overall = max(self._max_overall, profile.overall_risk)

    def stats(self) -> RiskStats:
        avg = (
            sum(self._overall_history) / len(self._overall_history)
            if self._overall_history
            else 0.0
        )
        current_level = (
            self._risk_level_history[-1]
            if self._risk_level_history
            else RiskLevel.MODERATE
        )
        return RiskStats(
            total_bars=self._total_bars,
            high_risk_bars=self._high_risk_count,
            extreme_risk_bars=self._extreme_risk_count,
            avg_overall_risk=round(avg, 4),
            max_overall_risk=round(self._max_overall, 4),
            current_risk_level=current_level,
        )

    def reset(self) -> None:
        self._overall_history.clear()
        self._risk_level_history.clear()
        self._total_bars = 0
        self._high_risk_count = 0
        self._extreme_risk_count = 0
        self._max_overall = 0.0
