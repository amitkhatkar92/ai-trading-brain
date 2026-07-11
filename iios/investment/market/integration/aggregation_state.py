"""iios/investment/market/integration/aggregation_state.py
AggregationState — central mutable state built by AggregationEngine.
All downstream components (validation, conflict, quality, snapshot) read this.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class AggregationState:
    """Normalised intelligence extracted from all upstream engine payloads."""
    bar_index:   int
    timestamp:   float

    # ── Regime ────────────────────────────────────────────────────────────────
    market_regime: Optional[str] = None      # "bull" | "bear" | "neutral" | "crisis"

    # ── Trend ─────────────────────────────────────────────────────────────────
    trend_direction: Optional[str] = None    # "up" | "down" | "sideways"
    trend_strength:  float = 50.0            # 0-100
    trend_stage:     Optional[str] = None    # "early" | "mature" | "late" | "reversal"

    # ── Volatility ────────────────────────────────────────────────────────────
    volatility_regime:     Optional[str] = None   # "low" | "normal" | "elevated" | "extreme"
    volatility_percentile: float = 50.0
    vix_equivalent:        Optional[float] = None

    # ── Breadth ───────────────────────────────────────────────────────────────
    breadth_regime:       Optional[str] = None   # "positive" | "negative" | "neutral"
    breadth_score:        float = 50.0
    advance_decline_ratio: float = 1.0

    # ── Correlation ───────────────────────────────────────────────────────────
    correlation_regime: Optional[str] = None   # "normal" | "elevated" | "crisis"
    avg_correlation:    float = 0.0

    # ── Liquidity / Volume ────────────────────────────────────────────────────
    liquidity_regime: Optional[str] = None    # "abundant" | "normal" | "tight" | "crisis"
    liquidity_score:  float = 50.0

    # ── Sector Rotation ───────────────────────────────────────────────────────
    sector_rotation_phase: Optional[str] = None
    leading_sectors:       List[str] = field(default_factory=list)
    lagging_sectors:       List[str] = field(default_factory=list)

    # ── Opportunities ─────────────────────────────────────────────────────────
    active_opportunities:    int = 0
    top_opportunity_symbols: List[str] = field(default_factory=list)
    high_priority_count:     int = 0

    # ── Market Structure ──────────────────────────────────────────────────────
    support_level:    Optional[float] = None
    resistance_level: Optional[float] = None
    near_key_level:   bool = False

    # ── Coverage meta ─────────────────────────────────────────────────────────
    engines_received: Set[str] = field(default_factory=set)
    missing_engines:  Set[str] = field(default_factory=set)

    # ── Risk signals ──────────────────────────────────────────────────────────
    systemic_risk_score: float = 0.0    # 0-100; 0 = no risk, 100 = crisis

    def has_engine(self, name: str) -> bool:
        return name in self.engines_received

    def coverage_ratio(self, expected: int) -> float:
        if expected == 0:
            return 1.0
        return len(self.engines_received) / expected
