"""iios/investment/market/volatility/volatility_expansion.py
Detects volatility expansion: a sustained increase in realised volatility
relative to its own recent history.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional

from iios.investment.market.volatility.models import (
    VolatilityEvent,
    VolatilityEventType,
    VolatilityRegimeType,
    VolatilityState,
)


@dataclass
class ExpansionState:
    is_expanding: bool
    expansion_score: float   # 0-1
    bars_expanding: int
    peak_relative_vol: float
    is_climax: bool          # True when expansion is extreme and accelerating


class VolatilityExpansionDetector:
    """
    Tracks consecutive bars where short-term vol exceeds medium-term vol
    by a meaningful margin.

    Parameters
    ----------
    expand_threshold:   relative_vol ratio above which expansion is detected
    climax_threshold:   relative_vol above which a climax is flagged
    min_bars:           consecutive bars required to confirm expansion
    window:             look-back for scoring
    """

    def __init__(
        self,
        expand_threshold: float = 1.10,
        climax_threshold: float = 1.50,
        min_bars: int = 2,
        window: int = 20,
    ) -> None:
        self._expand_thr = expand_threshold
        self._climax_thr = climax_threshold
        self._min_bars   = min_bars
        self._window     = window
        self._consecutive = 0
        self._peak_rel_vol = 1.0
        self._rel_vol_history: Deque[float] = deque(maxlen=window)

    # ── Public API ─────────────────────────────────────────────────────────

    def detect(
        self,
        state: VolatilityState,
        bar_index: int,
        symbol: str,
        timeframe: str,
    ) -> tuple[ExpansionState, Optional[VolatilityEvent]]:
        rel = state.relative_volatility
        self._rel_vol_history.append(rel)

        if rel > self._expand_thr:
            self._consecutive += 1
            self._peak_rel_vol = max(self._peak_rel_vol, rel)
        else:
            self._consecutive = 0
            self._peak_rel_vol = rel

        is_expanding = self._consecutive >= self._min_bars
        is_climax    = is_expanding and rel >= self._climax_thr

        score = self._score(rel)
        expansion_state = ExpansionState(
            is_expanding=is_expanding,
            expansion_score=score,
            bars_expanding=self._consecutive,
            peak_relative_vol=self._peak_rel_vol,
            is_climax=is_climax,
        )

        event: Optional[VolatilityEvent] = None
        if is_climax:
            event = VolatilityEvent(
                event_type=VolatilityEventType.CLIMAX,
                symbol=symbol,
                timeframe=timeframe,
                bar_index=bar_index,
                severity=min(1.0, (rel - 1.0) / 2.0),
                description=f"Volatility climax: relative_vol={rel:.2f}",
            )
        elif is_expanding and self._consecutive == self._min_bars:
            event = VolatilityEvent(
                event_type=VolatilityEventType.EXPANSION_START,
                symbol=symbol,
                timeframe=timeframe,
                bar_index=bar_index,
                severity=min(1.0, (rel - 1.0) / 1.0),
                description=f"Expansion started: relative_vol={rel:.2f}",
            )

        return expansion_state, event

    # ── Internal ──────────────────────────────────────────────────────────

    def _score(self, rel: float) -> float:
        """0-1 score: 0 = no expansion, 1 = extreme expansion."""
        if rel <= 1.0:
            return 0.0
        return min(1.0, (rel - 1.0) / (self._climax_thr - 1.0))
