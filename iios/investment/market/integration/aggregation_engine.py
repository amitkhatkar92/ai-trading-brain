"""iios/investment/market/integration/aggregation_engine.py
Core aggregation logic: extracts normalised signals from IntelligenceBundle.

Uses duck-typing so it works with ANY upstream engine output type — no imports
from upstream packages required.
"""
from __future__ import annotations

import logging
from typing import List

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.models import EngineSource, IntelligenceBundle

log = logging.getLogger(__name__)

# Canonical engine names that this engine knows how to extract from.
# New engines can be added to KNOWN_ENGINES without changing this class.
KNOWN_ENGINES: List[str] = [
    "market_structure",
    "market_regime",
    "trend",
    "volume_liquidity",
    "volatility",
    "breadth",
    "correlation",
    "sector_rotation",
    "opportunity",
]


class AggregationEngine:
    """Builds an AggregationState from an IntelligenceBundle.

    Extraction strategy:
    - Uses EnginePayload.get_attr() with multiple fallback field names.
    - Logs warnings for unrecognised payloads; never raises.
    - Each extraction method is isolated so partial data never corrupts state.
    """

    def aggregate(self, bundle: IntelligenceBundle) -> AggregationState:
        state = AggregationState(
            bar_index=bundle.bar_index,
            timestamp=bundle.timestamp,
        )
        for name, payload in bundle.payloads.items():
            try:
                self._extract(state, name, payload.source, payload)
                state.engines_received.add(name)
            except Exception:
                log.exception("aggregation error for engine %s", name)

        missing = set(KNOWN_ENGINES) - state.engines_received
        state.missing_engines = missing
        return state

    # ── per-source extractors ─────────────────────────────────────────────────

    def _extract(self, state: AggregationState, name: str, source: EngineSource, p) -> None:
        if source is EngineSource.MARKET_REGIME or name == "market_regime":
            self._from_regime(state, p)
        elif source is EngineSource.TREND or name == "trend":
            self._from_trend(state, p)
        elif source is EngineSource.VOLATILITY or name == "volatility":
            self._from_volatility(state, p)
        elif source is EngineSource.BREADTH or name == "breadth":
            self._from_breadth(state, p)
        elif source is EngineSource.CORRELATION or name == "correlation":
            self._from_correlation(state, p)
        elif source is EngineSource.VOLUME_LIQUIDITY or name == "volume_liquidity":
            self._from_liquidity(state, p)
        elif source is EngineSource.SECTOR_ROTATION or name == "sector_rotation":
            self._from_sector_rotation(state, p)
        elif source is EngineSource.OPPORTUNITY or name == "opportunity":
            self._from_opportunity(state, p)
        elif source is EngineSource.MARKET_STRUCTURE or name == "market_structure":
            self._from_market_structure(state, p)
        else:
            log.debug("no extractor for engine '%s' (source=%s)", name, source)

    def _from_regime(self, state: AggregationState, p) -> None:
        state.market_regime = p.get_attr(
            "regime", "market_regime", "regime_label", "label",
            default=state.market_regime,
        )

    def _from_trend(self, state: AggregationState, p) -> None:
        state.trend_direction = p.get_attr(
            "trend_direction", "direction", "trend",
            default=state.trend_direction,
        )
        raw_strength = p.get_attr(
            "trend_strength", "strength", "score",
            default=state.trend_strength,
        )
        if isinstance(raw_strength, (int, float)):
            state.trend_strength = float(raw_strength)
        state.trend_stage = p.get_attr(
            "trend_stage", "stage", default=state.trend_stage,
        )

    def _from_volatility(self, state: AggregationState, p) -> None:
        state.volatility_regime = p.get_attr(
            "volatility_regime", "vol_regime", "regime",
            default=state.volatility_regime,
        )
        raw_pct = p.get_attr(
            "volatility_percentile", "vol_percentile", "percentile",
            default=state.volatility_percentile,
        )
        if isinstance(raw_pct, (int, float)):
            state.volatility_percentile = float(raw_pct)
        vix = p.get_attr("vix_equivalent", "vix", "implied_vol", default=None)
        if isinstance(vix, (int, float)):
            state.vix_equivalent = float(vix)

    def _from_breadth(self, state: AggregationState, p) -> None:
        state.breadth_regime = p.get_attr(
            "breadth_regime", "regime", default=state.breadth_regime,
        )
        raw_score = p.get_attr(
            "breadth_score", "score", default=state.breadth_score,
        )
        if isinstance(raw_score, (int, float)):
            state.breadth_score = float(raw_score)
        raw_adr = p.get_attr(
            "advance_decline_ratio", "ad_ratio", default=state.advance_decline_ratio,
        )
        if isinstance(raw_adr, (int, float)):
            state.advance_decline_ratio = float(raw_adr)

    def _from_correlation(self, state: AggregationState, p) -> None:
        state.correlation_regime = p.get_attr(
            "correlation_regime", "regime", default=state.correlation_regime,
        )
        raw_corr = p.get_attr(
            "avg_correlation", "average_correlation", default=state.avg_correlation,
        )
        if isinstance(raw_corr, (int, float)):
            state.avg_correlation = float(raw_corr)

    def _from_liquidity(self, state: AggregationState, p) -> None:
        state.liquidity_regime = p.get_attr(
            "liquidity_regime", "regime", default=state.liquidity_regime,
        )
        raw_liq = p.get_attr(
            "liquidity_score", "score", default=state.liquidity_score,
        )
        if isinstance(raw_liq, (int, float)):
            state.liquidity_score = float(raw_liq)

    def _from_sector_rotation(self, state: AggregationState, p) -> None:
        state.sector_rotation_phase = p.get_attr(
            "sector_rotation_phase", "rotation_phase", "phase",
            default=state.sector_rotation_phase,
        )
        leading = p.get_attr("leading_sectors", "leaders", default=[])
        lagging = p.get_attr("lagging_sectors", "laggers", default=[])
        if isinstance(leading, list):
            state.leading_sectors = leading
        if isinstance(lagging, list):
            state.lagging_sectors = lagging

    def _from_opportunity(self, state: AggregationState, p) -> None:
        total = p.get_attr(
            "total_active", "active_opportunities", "count", default=0,
        )
        if isinstance(total, int):
            state.active_opportunities = total
        top = p.get_attr(
            "top_opportunity_symbols", "top_symbols", default=[],
        )
        if isinstance(top, list):
            state.top_opportunity_symbols = top
        hp = p.get_attr("high_priority_count", default=0)
        if isinstance(hp, int):
            state.high_priority_count = hp

    def _from_market_structure(self, state: AggregationState, p) -> None:
        sup = p.get_attr("support_level", "support", default=None)
        if isinstance(sup, (int, float)):
            state.support_level = float(sup)
        res = p.get_attr("resistance_level", "resistance", default=None)
        if isinstance(res, (int, float)):
            state.resistance_level = float(res)
        nkl = p.get_attr("near_key_level", default=False)
        if isinstance(nkl, bool):
            state.near_key_level = nkl
