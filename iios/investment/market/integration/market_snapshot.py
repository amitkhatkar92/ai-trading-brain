"""iios/investment/market/integration/market_snapshot.py
Assembles MarketIntelligenceSnapshot from all processed sub-results.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.models import (
    ConflictSummary,
    EngineHealthRecord,
    MarketIntelligenceSnapshot,
    MarketStateLabel,
    QualityScore,
    ValidationReport,
)


class SnapshotBuilder:
    """Immutable assembler — no side effects."""

    def build(
        self,
        state:         AggregationState,
        label:         MarketStateLabel,
        quality:       QualityScore,
        confidence:    float,
        validation:    ValidationReport,
        conflicts:     ConflictSummary,
        engine_health: Dict[str, EngineHealthRecord],
        summary_text:  str,
    ) -> MarketIntelligenceSnapshot:
        return MarketIntelligenceSnapshot(
            snapshot_id=str(uuid.uuid4()),
            bar_index=state.bar_index,
            timestamp=state.timestamp,
            market_state_label=label,
            market_regime=state.market_regime,
            trend_direction=state.trend_direction,
            trend_strength=state.trend_strength,
            volatility_regime=state.volatility_regime,
            breadth_regime=state.breadth_regime,
            correlation_regime=state.correlation_regime,
            liquidity_regime=state.liquidity_regime,
            sector_rotation_phase=state.sector_rotation_phase,
            leading_sectors=list(state.leading_sectors),
            lagging_sectors=list(state.lagging_sectors),
            active_opportunities=state.active_opportunities,
            top_opportunity_symbols=list(state.top_opportunity_symbols),
            overall_confidence=confidence,
            quality=quality,
            validation=validation,
            conflicts=conflicts,
            engine_health=dict(engine_health),
            engines_received=sorted(state.engines_received),
            missing_engines=sorted(state.missing_engines),
            summary_text=summary_text,
        )
