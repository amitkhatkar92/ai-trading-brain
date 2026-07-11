"""iios/investment/market/sector_rotation/rotation_statistics.py
Statistical aggregates over the rotation history buffer.
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.sector_rotation.models import RotationSignal, RotationType
from iios.investment.market.sector_rotation.rotation_history import RotationHistory


def rotation_frequency(history: RotationHistory, window: int = 20) -> Dict[str, float]:
    """Frequency (events per bar) of each rotation type over last *window* records."""
    recent = history.recent(window)
    counts: Dict[str, int] = {}
    for sig in recent:
        key = sig.rotation_type.value
        counts[key] = counts.get(key, 0) + 1
    n = max(len(recent), 1)
    return {k: v / n for k, v in counts.items()}


def avg_confidence(history: RotationHistory, window: int = 10) -> float:
    """Average confidence of last *window* confirmed rotation signals."""
    confirmed = history.confirmed_signals()[-window:]
    if not confirmed:
        return 0.0
    return sum(s.confidence for s in confirmed) / len(confirmed)


def dominant_rotation_type(
    history: RotationHistory, window: int = 20
) -> RotationType:
    freq = rotation_frequency(history, window)
    if not freq:
        return RotationType.NO_ROTATION
    best_key = max(freq, key=freq.__getitem__)
    try:
        return RotationType(best_key)
    except ValueError:
        return RotationType.NO_ROTATION


def sectors_most_often_rising(
    history: RotationHistory, window: int = 20
) -> List[str]:
    """Return sectors that appear most in 'to_sectors' lists."""
    recent = history.recent(window)
    counts: Dict[str, int] = {}
    for sig in recent:
        for s in sig.to_sectors:
            counts[s] = counts.get(s, 0) + 1
    return sorted(counts, key=counts.__getitem__, reverse=True)


def sectors_most_often_falling(
    history: RotationHistory, window: int = 20
) -> List[str]:
    recent = history.recent(window)
    counts: Dict[str, int] = {}
    for sig in recent:
        for s in sig.from_sectors:
            counts[s] = counts.get(s, 0) + 1
    return sorted(counts, key=counts.__getitem__, reverse=True)
