"""
market_snapshot_builder.py — iios.market.snapshot
==================================================
Fluent builder for constructing immutable MarketSnapshot objects.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION, SnapshotStatus
from .exceptions import MarketSnapshotBuilderError
from .market_snapshot import (
    AuditInfo,
    BreadthSummary,
    CorrelationSummary,
    ForecastSummary,
    LiquiditySummary,
    MarketSnapshot,
    MarketSummary,
    RegimeSummary,
    SectorSummary,
    SnapshotStats,
    SystemHealth,
    TrendSummary,
    VolatilitySummary,
)
from .market_snapshot_metadata import SnapshotMetadata


class MarketSnapshotBuilder:
    """
    Fluent builder for :class:`~.market_snapshot.MarketSnapshot`.

    Usage::

        snapshot = (
            MarketSnapshotBuilder("snap-001")
            .with_identifiers(
                market_session_id="sess-1",
                market_analysis_id="ana-1",
                exchange="NSE",
            )
            .with_market_summary(
                overall_score=72.0,
                market_health="healthy",
                market_regime="bull",
                ...
            )
            .build()
        )
    """

    def __init__(self, snapshot_id: Optional[str] = None) -> None:
        self._snapshot_id        = snapshot_id or str(uuid.uuid4())
        self._market_session_id  = ""
        self._market_analysis_id = ""
        self._workflow_id        = ""
        self._exchange           = ""
        self._market             = ""
        self._market_type        = "equity"
        self._timeframe          = "1d"
        self._trading_session    = "regular"
        self._market_status      = "open"
        self._lifecycle_state    = "analyzing"
        self._market_version     = VERSION
        self._framework_version  = VERSION
        self._snapshot_timestamp = time.time()
        self._created_at         = time.time()
        self._updated_at         = time.time()
        self._status             = SnapshotStatus.PENDING
        self._version            = 1
        self._is_valid           = False

        self._market_summary:      Optional[MarketSummary]      = None
        self._regime_summary:      Optional[RegimeSummary]      = None
        self._trend_summary:       Optional[TrendSummary]       = None
        self._sector_summary:      Optional[SectorSummary]      = None
        self._breadth_summary:     Optional[BreadthSummary]     = None
        self._volatility_summary:  Optional[VolatilitySummary]  = None
        self._liquidity_summary:   Optional[LiquiditySummary]   = None
        self._correlation_summary: Optional[CorrelationSummary] = None
        self._forecast_summary:    Optional[ForecastSummary]    = None
        self._system_health:       Optional[SystemHealth]       = None
        self._audit_info:          Optional[AuditInfo]          = None
        self._snapshot_stats:      Optional[SnapshotStats]      = None
        self._metadata:            Optional[SnapshotMetadata]   = None

    # ------------------------------------------------------------------
    # Core identifiers
    # ------------------------------------------------------------------

    def with_identifiers(
        self,
        *,
        market_session_id:  str = "",
        market_analysis_id: str = "",
        workflow_id:        str = "",
        exchange:           str = "",
        market:             str = "",
        market_type:        str = "equity",
        timeframe:          str = "1d",
        trading_session:    str = "regular",
        market_status:      str = "open",
        lifecycle_state:    str = "analyzing",
        market_version:     str = VERSION,
    ) -> "MarketSnapshotBuilder":
        self._market_session_id  = market_session_id
        self._market_analysis_id = market_analysis_id
        self._workflow_id        = workflow_id
        self._exchange           = exchange
        self._market             = market
        self._market_type        = market_type
        self._timeframe          = timeframe
        self._trading_session    = trading_session
        self._market_status      = market_status
        self._lifecycle_state    = lifecycle_state
        self._market_version     = market_version
        return self

    def with_status(
        self,
        status: SnapshotStatus,
        *,
        version: int  = 1,
        is_valid: bool = False,
    ) -> "MarketSnapshotBuilder":
        self._status   = status
        self._version  = version
        self._is_valid = is_valid
        return self

    def with_timestamps(
        self,
        *,
        snapshot_timestamp: Optional[float] = None,
        created_at:         Optional[float] = None,
        updated_at:         Optional[float] = None,
    ) -> "MarketSnapshotBuilder":
        now = time.time()
        self._snapshot_timestamp = snapshot_timestamp or now
        self._created_at         = created_at or now
        self._updated_at         = updated_at or now
        return self

    # ------------------------------------------------------------------
    # Summary sections
    # ------------------------------------------------------------------

    def with_market_summary(
        self,
        overall_score:     float = 0.0,
        market_health:     str   = "unknown",
        market_regime:     str   = "unknown",
        trend_direction:   str   = "sideways",
        trend_strength:    str   = "none",
        market_confidence: float = 0.0,
        market_status:     str   = "unknown",
    ) -> "MarketSnapshotBuilder":
        self._market_summary = MarketSummary(
            overall_score     = overall_score,
            market_health     = market_health,
            market_regime     = market_regime,
            trend_direction   = trend_direction,
            trend_strength    = trend_strength,
            market_confidence = market_confidence,
            market_status     = market_status,
        )
        return self

    def with_regime_summary(
        self,
        primary_regime:    str   = "unknown",
        secondary_regime:  str   = "unknown",
        regime_confidence: float = 0.0,
        regime_stability:  float = 0.0,
        regime_duration:   int   = 0,
    ) -> "MarketSnapshotBuilder":
        self._regime_summary = RegimeSummary(
            primary_regime    = primary_regime,
            secondary_regime  = secondary_regime,
            regime_confidence = regime_confidence,
            regime_stability  = regime_stability,
            regime_duration   = regime_duration,
        )
        return self

    def with_trend_summary(
        self,
        primary_trend:     str   = "sideways",
        secondary_trend:   str   = "sideways",
        momentum_strength: float = 0.0,
        trend_confidence:  float = 0.0,
    ) -> "MarketSnapshotBuilder":
        self._trend_summary = TrendSummary(
            primary_trend     = primary_trend,
            secondary_trend   = secondary_trend,
            momentum_strength = momentum_strength,
            trend_confidence  = trend_confidence,
        )
        return self

    def with_sector_summary(
        self,
        sector_rankings: Optional[List[str]] = None,
        leading_sectors: Optional[List[str]] = None,
        weak_sectors:    Optional[List[str]] = None,
        sector_rotation: str                 = "unknown",
        sector_strength: float               = 0.0,
    ) -> "MarketSnapshotBuilder":
        self._sector_summary = SectorSummary(
            sector_rankings = tuple(sector_rankings or []),
            leading_sectors = tuple(leading_sectors or []),
            weak_sectors    = tuple(weak_sectors or []),
            sector_rotation = sector_rotation,
            sector_strength = sector_strength,
        )
        return self

    def with_breadth_summary(
        self,
        advance_decline:  float = 1.0,
        market_breadth:   str   = "neutral",
        participation:    float = 0.5,
        breadth_strength: str   = "moderate",
        breadth_score:    float = 50.0,
    ) -> "MarketSnapshotBuilder":
        self._breadth_summary = BreadthSummary(
            advance_decline  = advance_decline,
            market_breadth   = market_breadth,
            participation    = participation,
            breadth_strength = breadth_strength,
            breadth_score    = breadth_score,
        )
        return self

    def with_volatility_summary(
        self,
        current_volatility:    float = 0.0,
        historical_volatility: float = 0.0,
        implied_volatility:    float = 0.0,
        volatility_trend:      str   = "sideways",
        volatility_score:      float = 50.0,
    ) -> "MarketSnapshotBuilder":
        self._volatility_summary = VolatilitySummary(
            current_volatility    = current_volatility,
            historical_volatility = historical_volatility,
            implied_volatility    = implied_volatility,
            volatility_trend      = volatility_trend,
            volatility_score      = volatility_score,
        )
        return self

    def with_liquidity_summary(
        self,
        market_liquidity: str   = "adequate",
        volume_profile:   str   = "normal",
        liquidity_trend:  str   = "stable",
        liquidity_score:  float = 50.0,
    ) -> "MarketSnapshotBuilder":
        self._liquidity_summary = LiquiditySummary(
            market_liquidity = market_liquidity,
            volume_profile   = volume_profile,
            liquidity_trend  = liquidity_trend,
            liquidity_score  = liquidity_score,
        )
        return self

    def with_correlation_summary(
        self,
        sector_correlations:      float = 0.0,
        index_correlations:       float = 0.0,
        intermarket_correlations: float = 0.0,
        correlation_score:        float = 50.0,
    ) -> "MarketSnapshotBuilder":
        self._correlation_summary = CorrelationSummary(
            sector_correlations      = sector_correlations,
            index_correlations       = index_correlations,
            intermarket_correlations = intermarket_correlations,
            correlation_score        = correlation_score,
        )
        return self

    def with_forecast_summary(
        self,
        intraday_forecast:   str   = "neutral",
        short_term_forecast: str   = "neutral",
        trend_forecast:      str   = "neutral",
        volatility_forecast: str   = "stable",
        forecast_confidence: float = 0.5,
    ) -> "MarketSnapshotBuilder":
        self._forecast_summary = ForecastSummary(
            intraday_forecast   = intraday_forecast,
            short_term_forecast = short_term_forecast,
            trend_forecast      = trend_forecast,
            volatility_forecast = volatility_forecast,
            forecast_confidence = forecast_confidence,
        )
        return self

    def with_system_health(
        self,
        subsystem_status:   Optional[Dict[str, str]] = None,
        validation_status:  str                      = "unknown",
        snapshot_integrity: str                      = "partial",
        pipeline_health:    str                      = "unknown",
        framework_health:   str                      = "healthy",
    ) -> "MarketSnapshotBuilder":
        self._system_health = SystemHealth(
            subsystem_status   = dict(subsystem_status or {}),
            validation_status  = validation_status,
            snapshot_integrity = snapshot_integrity,
            pipeline_health    = pipeline_health,
            framework_health   = framework_health,
        )
        return self

    def with_audit_info(
        self,
        analytics_version:  str                       = VERSION,
        model_versions:     Optional[Dict[str, str]]  = None,
        policy_versions:    Optional[Dict[str, str]]  = None,
        validation_summary: Optional[Dict[str, Any]]  = None,
        audit_trail:        Optional[List[str]]        = None,
    ) -> "MarketSnapshotBuilder":
        self._audit_info = AuditInfo(
            analytics_version  = analytics_version,
            model_versions     = dict(model_versions or {}),
            policy_versions    = dict(policy_versions or {}),
            validation_summary = dict(validation_summary or {}),
            audit_trail        = tuple(audit_trail or []),
        )
        return self

    def with_snapshot_stats(
        self,
        analysis_duration_s:  float = 0.0,
        forecast_duration_s:  float = 0.0,
        snapshot_size_bytes:  int   = 0,
        component_count:      int   = 0,
    ) -> "MarketSnapshotBuilder":
        self._snapshot_stats = SnapshotStats(
            analysis_duration_s  = analysis_duration_s,
            forecast_duration_s  = forecast_duration_s,
            snapshot_size_bytes  = snapshot_size_bytes,
            component_count      = component_count,
        )
        return self

    def with_metadata(self, metadata: SnapshotMetadata) -> "MarketSnapshotBuilder":
        self._metadata = metadata
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> MarketSnapshot:
        """
        Construct and return an immutable :class:`~.market_snapshot.MarketSnapshot`.

        Raises
        ------
        MarketSnapshotBuilderError
            If the ``snapshot_id`` is empty.
        """
        if not self._snapshot_id:
            raise MarketSnapshotBuilderError("snapshot_id must not be empty")

        return MarketSnapshot(
            snapshot_id          = self._snapshot_id,
            market_session_id    = self._market_session_id,
            market_analysis_id   = self._market_analysis_id,
            workflow_id          = self._workflow_id,
            exchange             = self._exchange,
            market               = self._market,
            market_type          = self._market_type,
            timeframe            = self._timeframe,
            trading_session      = self._trading_session,
            market_status        = self._market_status,
            lifecycle_state      = self._lifecycle_state,
            market_version       = self._market_version,
            framework_version    = self._framework_version,
            snapshot_timestamp   = self._snapshot_timestamp,
            created_at           = self._created_at,
            updated_at           = self._updated_at,
            status               = self._status,
            version              = self._version,
            is_valid             = self._is_valid,
            market_summary       = self._market_summary,
            regime_summary       = self._regime_summary,
            trend_summary        = self._trend_summary,
            sector_summary       = self._sector_summary,
            breadth_summary      = self._breadth_summary,
            volatility_summary   = self._volatility_summary,
            liquidity_summary    = self._liquidity_summary,
            correlation_summary  = self._correlation_summary,
            forecast_summary     = self._forecast_summary,
            system_health        = self._system_health,
            audit_info           = self._audit_info,
            snapshot_stats       = self._snapshot_stats,
            metadata             = self._metadata,
        )
