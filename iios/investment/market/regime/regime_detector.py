"""iios/investment/market/regime/regime_detector.py
Derives RegimeObservation from MarketStructureSnapshot + optional MarketSnapshot,
then classifies the market regime.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple, TYPE_CHECKING

from iios.investment.market.market_constants import (
    TrendDirection,
    VolatilityLevel,
)
from iios.investment.market.regime.models import (
    RegimeObservation,
    RegimeType,
)

if TYPE_CHECKING:
    from iios.investment.market.structure.models import MarketStructureSnapshot
    from iios.investment.market.market_state.market_snapshot import MarketSnapshot

logger = logging.getLogger(__name__)

# Volatility inferred from structure phase when market snapshot is not provided
_PHASE_TO_VOLATILITY = {
    "compression":   VolatilityLevel.VERY_LOW,
    "contraction":   VolatilityLevel.LOW,
    "accumulation":  VolatilityLevel.LOW,
    "distribution":  VolatilityLevel.HIGH,
    "expansion":     VolatilityLevel.HIGH,
    "markup":        VolatilityLevel.MODERATE,
    "markdown":      VolatilityLevel.MODERATE,
}


class RegimeDetector:
    """Stateless regime detector: observe → detect."""

    # ── Observation ──────────────────────────────────────────────────────────

    def observe(
        self,
        structure: "MarketStructureSnapshot",
        market: Optional["MarketSnapshot"] = None,
    ) -> RegimeObservation:
        """Build RegimeObservation from structure + optional market snapshot."""
        trend      = structure.trend
        phase_str  = structure.structure_phase.value
        consol     = structure.consolidation
        breakout   = structure.active_breakout

        # Volatility: prefer market snapshot; fall back to phase inference
        if market is not None:
            volatility = market.volatility
        else:
            volatility = _PHASE_TO_VOLATILITY.get(phase_str, VolatilityLevel.MODERATE)

        # Consolidation
        in_consol         = consol is not None and consol.active
        consol_bars       = consol.bar_count if in_consol else 0
        consol_compression = consol.compression_ratio if in_consol else 1.0

        # Breakout
        has_breakout    = breakout is not None
        breakout_bullish = False
        if has_breakout and breakout is not None:
            breakout_bullish = breakout.breakout_type.value in (
                "bullish", "retest_bullish", "volume"
            )

        # Advance/decline ratio
        if market is not None:
            adr = market.advance_decline_ratio
        else:
            adr = 1.0

        return RegimeObservation(
            trend_direction=trend.direction,
            trend_confirmed=trend.confirmed,
            trend_leg_count=trend.leg_count,
            trend_strength=trend.strength.value,
            trend_phase=trend.phase.value,
            structure_phase=phase_str,
            volatility=volatility,
            in_consolidation=in_consol,
            consolidation_bars=consol_bars,
            consolidation_compression=consol_compression,
            has_active_breakout=has_breakout,
            breakout_bullish=breakout_bullish,
            advance_decline_ratio=adr,
            quality_score=structure.quality.overall,
            bar_count=structure.bar_index,
        )

    # ── Detection ────────────────────────────────────────────────────────────

    def detect(
        self,
        obs: RegimeObservation,
    ) -> Tuple[RegimeType, List[RegimeType], float]:
        """
        Returns (primary, secondary, confidence).

        Classification priority:
        1. CRISIS
        2. DISTRIBUTION
        3. ACCUMULATION
        4. BEAR
        5. BULL
        6. RECOVERY
        7. EXPANSION
        8. CONTRACTION
        9. SIDEWAYS
        10. RANGING
        11/12. VOLATILE/CALM added to secondary
        13. TRANSITION
        14. UNKNOWN
        """
        secondary: List[RegimeType] = []
        base_confidence = 0.6

        primary = self._classify_primary(obs, secondary)
        base_confidence = self._base_confidence_for(primary, obs)

        # Add volatility secondary regimes
        if primary not in (RegimeType.VOLATILE, RegimeType.CRISIS):
            if obs.volatility in (VolatilityLevel.HIGH, VolatilityLevel.EXTREME):
                if RegimeType.VOLATILE not in secondary:
                    secondary.append(RegimeType.VOLATILE)
            elif obs.volatility == VolatilityLevel.VERY_LOW:
                if RegimeType.CALM not in secondary:
                    secondary.append(RegimeType.CALM)

        # Quality scales confidence: conf *= (0.6 + 0.4 * quality/100)
        quality_scale = 0.6 + 0.4 * (obs.quality_score / 100.0)
        confidence = max(0.0, min(1.0, base_confidence * quality_scale))

        return primary, secondary, confidence

    def _classify_primary(
        self,
        obs: RegimeObservation,
        secondary: List[RegimeType],
    ) -> RegimeType:
        adr      = obs.advance_decline_ratio
        vol      = obs.volatility
        phase    = obs.structure_phase
        td       = obs.trend_direction
        t_phase  = obs.trend_phase
        confirmed = obs.trend_confirmed
        legs     = obs.trend_leg_count

        # 1. CRISIS
        if (
            vol in (VolatilityLevel.EXTREME,)
            and td == TrendDirection.DOWN
            and adr < 0.3
        ):
            return RegimeType.CRISIS

        # 2. DISTRIBUTION
        if phase == "distribution" or (
            td == TrendDirection.UP
            and vol == VolatilityLevel.HIGH
            and adr < 0.8
        ):
            return RegimeType.DISTRIBUTION

        # 3. ACCUMULATION
        if phase == "accumulation" and not (confirmed and legs >= 2):
            return RegimeType.ACCUMULATION

        # 4. BEAR: confirmed DOWN trend, leg_count >= 2
        if td == TrendDirection.DOWN and confirmed and legs >= 2:
            return RegimeType.BEAR

        # 5. BULL: confirmed UP trend, leg_count >= 2
        if td == TrendDirection.UP and confirmed and legs >= 2:
            return RegimeType.BULL

        # 5.5. EXPANSION via active breakout (before RECOVERY — breakout is a stronger signal)
        if obs.has_active_breakout:
            return RegimeType.EXPANSION

        # 6. RECOVERY: UP trend not confirmed, early stage, no active breakout
        if td == TrendDirection.UP and not confirmed:
            return RegimeType.RECOVERY

        # 7. EXPANSION: structure_phase=="expansion"
        if phase == "expansion":
            return RegimeType.EXPANSION

        # 8. CONTRACTION: phase in (contraction, compression) OR in_consolidation long
        if phase in ("contraction", "compression") or (
            obs.in_consolidation and obs.consolidation_bars >= 20
        ):
            return RegimeType.CONTRACTION

        # 9. SIDEWAYS
        if td == TrendDirection.SIDEWAYS:
            return RegimeType.SIDEWAYS

        # 10. RANGING: in_consolidation, consolidation_bars >= 10
        if obs.in_consolidation and obs.consolidation_bars >= 10:
            return RegimeType.RANGING

        # 13. TRANSITION: trend_phase == "reversal"
        if t_phase == "reversal":
            return RegimeType.TRANSITION

        # 14. UNKNOWN
        return RegimeType.UNKNOWN

    def _base_confidence_for(
        self, primary: RegimeType, obs: RegimeObservation
    ) -> float:
        conf_map = {
            RegimeType.CRISIS:       0.90,
            RegimeType.DISTRIBUTION: 0.75,
            RegimeType.ACCUMULATION: 0.70,
            RegimeType.BEAR:         0.80,
            RegimeType.BULL:         0.80,
            RegimeType.RECOVERY:     0.65,
            RegimeType.EXPANSION:    0.70,
            RegimeType.CONTRACTION:  0.65,
            RegimeType.SIDEWAYS:     0.70,
            RegimeType.RANGING:      0.65,
            RegimeType.TRANSITION:   0.60,
            RegimeType.VOLATILE:     0.70,
            RegimeType.CALM:         0.70,
            RegimeType.TRENDING:     0.70,
            RegimeType.UNKNOWN:      0.30,
        }
        return conf_map.get(primary, 0.50)
