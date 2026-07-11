"""iios/investment/market/volatility/volatility_cycles.py
Tracks the full volatility cycle: expansion → peak → contraction → trough.

Also computes persistence (autocorrelation), acceleration / deceleration,
and assembles the final BehaviourSnapshot.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, List

from iios.investment.market.volatility.models import (
    BehaviourSnapshot,
    VolatilityBehaviour,
    VolatilityState,
)
from iios.investment.market.volatility.volatility_expansion import ExpansionState
from iios.investment.market.volatility.volatility_compression import CompressionState


class VolatilityCycleAnalyzer:
    """
    Synthesises expansion, compression and persistence signals into a
    BehaviourSnapshot that describes what volatility is currently doing.

    Cycle phases:
        "expansion"   – vol actively rising
        "peak"        – expansion climax / extreme high
        "contraction" – vol actively falling
        "trough"      – compression / extreme low
    """

    def __init__(self, window: int = 10) -> None:
        self._window = window
        self._rel_vol_buf: Deque[float] = deque(maxlen=window)
        self._phase = "unknown"
        self._bars_in_phase = 0
        self._prev_phase = "unknown"

    # ── Public API ─────────────────────────────────────────────────────────

    def analyze(
        self,
        state: VolatilityState,
        expansion: ExpansionState,
        compression: CompressionState,
    ) -> BehaviourSnapshot:
        self._rel_vol_buf.append(state.relative_volatility)

        acceleration = self._compute_acceleration()
        behaviour    = self._determine_behaviour(state, expansion, compression, acceleration)
        phase        = self._determine_phase(state, expansion, compression)
        persistence  = state.volatility_persistence

        if phase != self._phase:
            self._prev_phase  = self._phase
            self._phase       = phase
            self._bars_in_phase = 1
        else:
            self._bars_in_phase += 1

        return BehaviourSnapshot(
            behaviour=behaviour,
            expansion_score=expansion.expansion_score,
            compression_score=compression.compression_score,
            persistence_score=persistence,
            acceleration=round(acceleration, 4),
            cycle_phase=self._phase,
            bars_in_phase=self._bars_in_phase,
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _compute_acceleration(self) -> float:
        """Rate of change of relative_vol over the window."""
        vals = list(self._rel_vol_buf)
        if len(vals) < 3:
            return 0.0
        recent   = vals[-1]
        lookback = vals[max(0, len(vals) - 5)]
        if lookback < 1e-10:
            return 0.0
        return (recent - lookback) / lookback

    def _determine_behaviour(
        self,
        state: VolatilityState,
        expansion: ExpansionState,
        compression: CompressionState,
        acceleration: float,
    ) -> VolatilityBehaviour:
        if expansion.is_climax:
            return VolatilityBehaviour.CLIMAX

        # Cooling: previously was climax/shock and vol is now falling fast
        if (
            state.relative_volatility < 0.90
            and acceleration < -0.10
            and state.normalized_volatility > 0.50
        ):
            return VolatilityBehaviour.COOLING

        if expansion.is_expanding:
            if acceleration > 0.15:
                return VolatilityBehaviour.ACCELERATING
            return VolatilityBehaviour.EXPANDING

        if compression.is_compressing:
            if acceleration < -0.10:
                return VolatilityBehaviour.DECELERATING
            return VolatilityBehaviour.COMPRESSING

        if state.volatility_persistence > 0.70:
            return VolatilityBehaviour.PERSISTENT

        if acceleration > 0.10:
            return VolatilityBehaviour.ACCELERATING
        if acceleration < -0.10:
            return VolatilityBehaviour.DECELERATING

        return VolatilityBehaviour.STABLE

    def _determine_phase(
        self,
        state: VolatilityState,
        expansion: ExpansionState,
        compression: CompressionState,
    ) -> str:
        if expansion.is_climax or state.normalized_volatility >= 0.85:
            return "peak"
        if expansion.is_expanding:
            return "expansion"
        if compression.is_deep_compression or state.normalized_volatility <= 0.10:
            return "trough"
        if compression.is_compressing:
            return "contraction"
        return "expansion" if state.relative_volatility > 1.0 else "contraction"
