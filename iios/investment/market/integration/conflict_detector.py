"""iios/investment/market/integration/conflict_detector.py
Translates ValidationIssues into Conflict objects.
"""
from __future__ import annotations

from typing import List

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.models import Conflict, ValidationReport


class ConflictDetector:
    """Creates Conflict instances from a ValidationReport."""

    def detect(
        self, state: AggregationState, report: ValidationReport
    ) -> List[Conflict]:
        conflicts: List[Conflict] = []
        for issue in report.issues:
            # Build contextual signal strings from state
            engine_a_signal, engine_b_signal = self._extract_signals(issue.engines_involved, state)
            conflict = Conflict.new(
                conflict_type=issue.conflict_type,
                severity=issue.severity,
                engines=issue.engines_involved,
                description=issue.description,
                engine_a_signal=engine_a_signal,
                engine_b_signal=engine_b_signal,
            )
            conflicts.append(conflict)
        return conflicts

    # ── helpers ───────────────────────────────────────────────────────────────

    def _extract_signals(self, engines: List[str], state: AggregationState):
        """Return (signal_a, signal_b) strings for the first two engines."""
        signals = []
        for engine in engines[:2]:
            signals.append(self._signal_for(engine, state))
        while len(signals) < 2:
            signals.append("")
        return signals[0], signals[1]

    @staticmethod
    def _signal_for(engine: str, state: AggregationState) -> str:
        m = {
            "market_regime":  lambda: state.market_regime or "unknown",
            "trend":          lambda: f"{state.trend_direction}@{state.trend_strength:.0f}",
            "volatility":     lambda: f"{state.volatility_regime}@{state.volatility_percentile:.0f}%",
            "breadth":        lambda: f"{state.breadth_regime}@{state.breadth_score:.0f}",
            "correlation":    lambda: state.correlation_regime or "unknown",
            "volume_liquidity": lambda: f"{state.liquidity_regime}@{state.liquidity_score:.0f}",
            "sector_rotation": lambda: state.sector_rotation_phase or "unknown",
            "opportunity":    lambda: f"{state.active_opportunities} active",
        }
        fn = m.get(engine)
        return fn() if fn else engine
