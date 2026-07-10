"""iios/investment/market/regime/transition_statistics.py
Per-regime duration and transition count statistics.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from iios.investment.market.regime.models import RegimeType


@dataclass
class RegimeStats:
    """Aggregated statistics for a single regime type."""

    regime:             RegimeType
    count:              int                  # complete regime instances
    avg_duration_bars:  float
    min_duration:       int
    max_duration:       int
    total_bars:         int
    transition_counts:  Dict[str, int] = field(default_factory=dict)  # to_regime.value → count


class TransitionStatistics:
    """Tracks regime duration and regime-to-regime transition counts."""

    def __init__(self) -> None:
        # duration data per regime
        self._durations:   Dict[RegimeType, List[int]] = defaultdict(list)
        # transition counts: from → to → count
        self._transitions: Dict[RegimeType, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record_regime_end(self, regime: RegimeType, duration_bars: int) -> None:
        """Call when a regime ends. Record its duration."""
        self._durations[regime].append(duration_bars)

    def record_transition(self, from_regime: RegimeType, to_regime: RegimeType) -> None:
        """Record a regime-to-regime transition."""
        self._transitions[from_regime][to_regime.value] += 1

    def stats_for(self, regime: RegimeType) -> RegimeStats:
        """Return statistics for one regime. Returns zero-stats if no data."""
        durations = self._durations.get(regime, [])
        if not durations:
            return RegimeStats(
                regime=regime,
                count=0,
                avg_duration_bars=0.0,
                min_duration=0,
                max_duration=0,
                total_bars=0,
                transition_counts={},
            )
        return RegimeStats(
            regime=regime,
            count=len(durations),
            avg_duration_bars=sum(durations) / len(durations),
            min_duration=min(durations),
            max_duration=max(durations),
            total_bars=sum(durations),
            transition_counts=dict(self._transitions.get(regime, {})),
        )

    def all_stats(self) -> Dict[RegimeType, RegimeStats]:
        """Return stats for every regime type."""
        return {r: self.stats_for(r) for r in RegimeType}

    def avg_duration(self, regime: RegimeType) -> float:
        """Average duration in bars, or 0.0 if no data."""
        durations = self._durations.get(regime, [])
        if not durations:
            return 0.0
        return sum(durations) / len(durations)

    def total_regimes_observed(self) -> int:
        """Total regime instances recorded across all types."""
        return sum(len(d) for d in self._durations.values())

    def most_common_regime(self) -> Optional[RegimeType]:
        """Regime with most recorded instances."""
        if not self._durations:
            return None
        return max(self._durations, key=lambda r: len(self._durations[r]))
