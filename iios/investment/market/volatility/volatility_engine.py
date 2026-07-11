"""iios/investment/market/volatility/volatility_engine.py
Core volatility engine: maintains a bar history, runs all registered
estimators, and produces a VolatilityProfile on each update.
"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Deque, Dict, List, Optional

from iios.investment.market.volatility.models import (
    VolatilityEstimate,
    VolatilityProfile,
    VolatilityState,
)
from iios.investment.market.volatility.estimator_registry import EstimatorRegistry
from iios.investment.market.volatility.volatility_profile import VolatilityProfileAnalyzer
from iios.investment.market.volatility.volatility_state import VolatilityStateTracker

if TYPE_CHECKING:
    from iios.investment.market.structure.models import Bar


class VolatilityEngine:
    """
    Maintains a rolling bar buffer, runs estimators, and combines their
    outputs into a VolatilityProfile.

    Parameters
    ----------
    registry:       EstimatorRegistry supplying the active estimators.
    bar_buffer_len: Maximum number of bars to retain for estimators.
    short_window:   Window for short-term vol average (default 5).
    medium_window:  Window for medium-term vol average / initialisation (default 20).
    long_window:    Window for long-term vol average (default 50).
    """

    def __init__(
        self,
        registry: EstimatorRegistry,
        bar_buffer_len: int = 100,
        short_window: int = 5,
        medium_window: int = 20,
        long_window: int = 50,
        profile_analyzer: Optional[VolatilityProfileAnalyzer] = None,
        state_tracker: Optional[VolatilityStateTracker] = None,
    ) -> None:
        self._registry = registry
        self._bar_buf: Deque["Bar"] = deque(maxlen=bar_buffer_len)
        self._profile_analyzer = profile_analyzer or VolatilityProfileAnalyzer()
        self._state_tracker = state_tracker or VolatilityStateTracker(
            short_window, medium_window, long_window
        )
        self._current_profile: Optional[VolatilityProfile] = None

    # ── Public API ─────────────────────────────────────────────────────────

    def update(self, bar: "Bar") -> VolatilityProfile:
        """Process one bar and return the updated VolatilityProfile."""
        self._bar_buf.append(bar)
        bars = list(self._bar_buf)

        estimates = self._run_estimators(bars)
        realized_vol = self._combine_estimates(estimates, bar)
        state = self._state_tracker.update(realized_vol, bar)
        profile = self._profile_analyzer.analyze(state, estimates)
        self._current_profile = profile
        return profile

    @property
    def current_profile(self) -> Optional[VolatilityProfile]:
        return self._current_profile

    @property
    def state_tracker(self) -> VolatilityStateTracker:
        return self._state_tracker

    # ── Internal ──────────────────────────────────────────────────────────

    def _run_estimators(self, bars: "List[Bar]") -> "Dict[str, VolatilityEstimate]":
        results: Dict[str, VolatilityEstimate] = {}
        for est in self._registry.all():
            if len(bars) >= est.required_bars:
                out = est.estimate(bars)
                if out is not None:
                    results[est.name] = out
        return results

    def _combine_estimates(
        self,
        estimates: "Dict[str, VolatilityEstimate]",
        bar: "Bar",
    ) -> float:
        """
        Combine all valid estimates into a single annualised-% value.

        Uses a confidence-weighted average.  Falls back to a range-proxy when
        no estimator has produced output yet.
        """
        valid = [e for e in estimates.values() if e.confidence > 0]
        if not valid:
            # Minimal fallback: use bar range / mid-price as a rough daily std proxy
            mid = (bar.high + bar.low) / 2.0
            if mid > 1e-10:
                import math
                raw = (bar.high - bar.low) / mid
                return raw * math.sqrt(252.0) * 100.0
            return 10.0  # neutral default

        total_weight = sum(e.confidence for e in valid)
        if total_weight < 1e-10:
            return sum(e.annualized_pct for e in valid) / len(valid)

        return sum(e.annualized_pct * e.confidence for e in valid) / total_weight
