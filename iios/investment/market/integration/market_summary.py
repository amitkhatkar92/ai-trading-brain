"""iios/investment/market/integration/market_summary.py
Builds a human-readable market summary string from integrated state.
"""
from __future__ import annotations

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.models import (
    ConflictSummary,
    MarketStateLabel,
    QualityScore,
)


class MarketSummaryBuilder:
    """Generates one-line and multi-line market summary text."""

    def build(
        self,
        state:    AggregationState,
        label:    MarketStateLabel,
        quality:  QualityScore,
        conflicts: ConflictSummary,
    ) -> str:
        parts = []

        # State
        parts.append(f"State: {label.value.upper()}")

        # Regime + trend
        if state.market_regime:
            parts.append(f"Regime: {state.market_regime}")
        if state.trend_direction:
            parts.append(
                f"Trend: {state.trend_direction} ({state.trend_strength:.0f}/100)"
            )

        # Volatility
        if state.volatility_regime:
            vol_str = state.volatility_regime
            if state.vix_equivalent is not None:
                vol_str += f" (VIX≈{state.vix_equivalent:.1f})"
            parts.append(f"Vol: {vol_str}")

        # Breadth
        if state.breadth_regime:
            parts.append(
                f"Breadth: {state.breadth_regime} ({state.breadth_score:.0f}/100)"
            )

        # Opportunities
        if state.active_opportunities > 0:
            parts.append(f"Opps: {state.active_opportunities} active")

        # Conflicts
        if conflicts.total > 0:
            parts.append(
                f"Conflicts: {conflicts.total} "
                f"({conflicts.unresolved} unresolved)"
            )

        # Quality
        parts.append(f"Quality: {quality.overall:.0f}/100")

        return " | ".join(parts)

    def build_detail(
        self,
        state:     AggregationState,
        label:     MarketStateLabel,
        quality:   QualityScore,
        conflicts: ConflictSummary,
    ) -> str:
        lines = [
            f"Market State: {label.value}",
            f"  Regime:       {state.market_regime or 'N/A'}",
            f"  Trend:        {state.trend_direction or 'N/A'} strength={state.trend_strength:.1f}",
            f"  Volatility:   {state.volatility_regime or 'N/A'} ({state.volatility_percentile:.0f}th pctile)",
            f"  Breadth:      {state.breadth_regime or 'N/A'} score={state.breadth_score:.1f}",
            f"  Correlation:  {state.correlation_regime or 'N/A'}",
            f"  Liquidity:    {state.liquidity_regime or 'N/A'}",
            f"  Sector Phase: {state.sector_rotation_phase or 'N/A'}",
            f"  Opportunities:{state.active_opportunities}",
            f"  Quality:      {quality.overall:.1f}/100 "
            f"(compl={quality.completeness:.0f} cons={quality.consistency:.0f} "
            f"fresh={quality.freshness:.0f} rel={quality.reliability:.0f})",
            f"  Conflicts:    total={conflicts.total} critical={conflicts.critical} "
            f"unresolved={conflicts.unresolved}",
            f"  Engines:      {len(state.engines_received)} received, "
            f"{len(state.missing_engines)} missing",
        ]
        if state.leading_sectors:
            lines.append(f"  Leading:      {', '.join(state.leading_sectors[:3])}")
        if state.lagging_sectors:
            lines.append(f"  Lagging:      {', '.join(state.lagging_sectors[:3])}")
        return "\n".join(lines)
