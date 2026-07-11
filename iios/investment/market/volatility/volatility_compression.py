"""iios/investment/market/volatility/volatility_compression.py
Detects volatility compression: a sustained decrease in realised volatility
indicating a coiling / low-energy environment.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from iios.investment.market.volatility.models import (
    VolatilityEvent,
    VolatilityEventType,
    VolatilityState,
)


@dataclass
class CompressionState:
    is_compressing: bool
    compression_score: float   # 0-1
    bars_compressing: int
    trough_relative_vol: float
    is_deep_compression: bool  # True when vol is very low and still falling


class VolatilityCompressionDetector:
    """
    Tracks consecutive bars where short-term vol is below medium-term vol
    by a meaningful margin.

    Parameters
    ----------
    compress_threshold: relative_vol below which compression is detected
    deep_threshold:     relative_vol below which deep compression is flagged
    min_bars:           consecutive bars required to confirm compression
    """

    def __init__(
        self,
        compress_threshold: float = 0.92,
        deep_threshold: float = 0.70,
        min_bars: int = 3,
    ) -> None:
        self._compress_thr = compress_threshold
        self._deep_thr     = deep_threshold
        self._min_bars     = min_bars
        self._consecutive  = 0
        self._trough_rel   = 1.0

    # ── Public API ─────────────────────────────────────────────────────────

    def detect(
        self,
        state: VolatilityState,
        bar_index: int,
        symbol: str,
        timeframe: str,
    ) -> tuple[CompressionState, Optional[VolatilityEvent]]:
        rel = state.relative_volatility

        if rel < self._compress_thr:
            self._consecutive += 1
            self._trough_rel  = min(self._trough_rel, rel)
        else:
            self._consecutive = 0
            self._trough_rel  = rel

        is_compressing    = self._consecutive >= self._min_bars
        is_deep           = is_compressing and rel <= self._deep_thr
        score             = self._score(rel)

        comp_state = CompressionState(
            is_compressing=is_compressing,
            compression_score=score,
            bars_compressing=self._consecutive,
            trough_relative_vol=self._trough_rel,
            is_deep_compression=is_deep,
        )

        event: Optional[VolatilityEvent] = None
        if is_compressing and self._consecutive == self._min_bars:
            event = VolatilityEvent(
                event_type=VolatilityEventType.COMPRESSION_START,
                symbol=symbol,
                timeframe=timeframe,
                bar_index=bar_index,
                severity=max(0.1, 1.0 - rel),
                description=f"Compression started: relative_vol={rel:.2f}",
            )
        elif state.normalized_volatility < 0.08:
            event = VolatilityEvent(
                event_type=VolatilityEventType.DRY_UP,
                symbol=symbol,
                timeframe=timeframe,
                bar_index=bar_index,
                severity=0.3,
                description=f"Volatility dry-up: normalized={state.normalized_volatility:.2f}",
            )

        return comp_state, event

    # ── Internal ──────────────────────────────────────────────────────────

    def _score(self, rel: float) -> float:
        """0-1 score: 0 = no compression, 1 = deep compression."""
        if rel >= self._compress_thr:
            return 0.0
        return min(1.0, (self._compress_thr - rel) / (self._compress_thr - 0.30))
