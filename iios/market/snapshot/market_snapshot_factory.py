"""
market_snapshot_factory.py — iios.market.snapshot
==================================================
Factory helpers for assembling MarketSnapshot objects from component outputs.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import VERSION, SnapshotStatus
from .market_snapshot import MarketSnapshot
from .market_snapshot_builder import MarketSnapshotBuilder
from .market_snapshot_metadata import SnapshotMetadata


class MarketSnapshotFactory:
    """
    Factory that assembles :class:`~.market_snapshot.MarketSnapshot` objects
    from raw component output dictionaries.

    All parameters arrive as plain dicts — the factory does NOT import
    from the Analytics, Policy, or Lifecycle modules (no circular deps).
    """

    # ------------------------------------------------------------------
    # Primary factory method
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        snapshot_id:         Optional[str]            = None,
        market_session_id:   str                      = "",
        market_analysis_id:  str                      = "",
        workflow_id:         str                      = "",
        exchange:            str                      = "",
        market:              str                      = "",
        market_type:         str                      = "equity",
        timeframe:           str                      = "1d",
        trading_session:     str                      = "regular",
        market_status:       str                      = "open",
        lifecycle_state:     str                      = "analyzing",
        market_version:      str                      = VERSION,
        # Analytics outputs (plain dicts)
        regime_data:         Optional[Dict[str, Any]] = None,
        trend_data:          Optional[Dict[str, Any]] = None,
        sector_data:         Optional[Dict[str, Any]] = None,
        breadth_data:        Optional[Dict[str, Any]] = None,
        volatility_data:     Optional[Dict[str, Any]] = None,
        liquidity_data:      Optional[Dict[str, Any]] = None,
        correlation_data:    Optional[Dict[str, Any]] = None,
        forecast_data:       Optional[Dict[str, Any]] = None,
        scores_data:         Optional[Dict[str, Any]] = None,
        system_health_data:  Optional[Dict[str, Any]] = None,
        audit_data:          Optional[Dict[str, Any]] = None,
        stats_data:          Optional[Dict[str, Any]] = None,
        metadata:            Optional[SnapshotMetadata] = None,
        version:             int                      = 1,
        is_valid:            bool                     = False,
        status:              SnapshotStatus           = SnapshotStatus.PENDING,
    ) -> MarketSnapshot:
        sid = snapshot_id or str(uuid.uuid4())
        builder = MarketSnapshotBuilder(sid)

        builder.with_identifiers(
            market_session_id  = market_session_id,
            market_analysis_id = market_analysis_id,
            workflow_id        = workflow_id,
            exchange           = exchange,
            market             = market,
            market_type        = market_type,
            timeframe          = timeframe,
            trading_session    = trading_session,
            market_status      = market_status,
            lifecycle_state    = lifecycle_state,
            market_version     = market_version,
        )

        builder.with_status(status=status, version=version, is_valid=is_valid)

        # -- Market summary from scores + regime + trend ---------
        if scores_data or regime_data:
            rd = regime_data or {}
            sd = scores_data or {}
            builder.with_market_summary(
                overall_score     = sd.get("overall_score",    0.0),
                market_health     = sd.get("market_health",    "unknown"),
                market_regime     = rd.get("regime",           "unknown"),
                trend_direction   = rd.get("trend_direction",  "sideways"),
                trend_strength    = rd.get("trend_strength",   "none"),
                market_confidence = rd.get("confidence",       0.0),
                market_status     = market_status,
            )

        # -- Regime ------------------------------------------
        if regime_data:
            rd = regime_data
            builder.with_regime_summary(
                primary_regime    = rd.get("regime",          "unknown"),
                secondary_regime  = rd.get("secondary",       "unknown"),
                regime_confidence = rd.get("confidence",      0.0),
                regime_stability  = rd.get("stability",       0.0),
                regime_duration   = rd.get("duration_bars",   0),
            )

        # -- Trend -------------------------------------------
        if trend_data:
            td = trend_data
            builder.with_trend_summary(
                primary_trend     = td.get("primary_trend",     "sideways"),
                secondary_trend   = td.get("secondary_trend",   "sideways"),
                momentum_strength = td.get("momentum_score",    0.0),
                trend_confidence  = td.get("trend_confidence",  0.0),
            )

        # -- Sector ------------------------------------------
        if sector_data:
            sc = sector_data
            builder.with_sector_summary(
                sector_rankings = sc.get("rankings",         []),
                leading_sectors = sc.get("leading_sectors",  []),
                weak_sectors    = sc.get("weak_sectors",     []),
                sector_rotation = sc.get("rotation_phase",  "unknown"),
                sector_strength = sc.get("sector_strength",  0.0),
            )

        # -- Breadth -----------------------------------------
        if breadth_data:
            bd = breadth_data
            adr = bd.get("advance_decline_ratio", 1.0)
            is_healthy = bd.get("is_healthy", True)
            builder.with_breadth_summary(
                advance_decline  = adr,
                market_breadth   = "healthy" if is_healthy else "unhealthy",
                participation    = bd.get("advancing_pct",   0.5),
                breadth_strength = bd.get("breadth_strength", "moderate"),
                breadth_score    = bd.get("breadth_score",   50.0),
            )

        # -- Volatility --------------------------------------
        if volatility_data:
            vd = volatility_data
            builder.with_volatility_summary(
                current_volatility    = vd.get("realised_vol",   0.0),
                historical_volatility = vd.get("realised_vol",   0.0),
                implied_volatility    = vd.get("implied_vol",    0.0),
                volatility_trend      = vd.get("vol_trend",      "sideways"),
                volatility_score      = vd.get("vol_score",      50.0),
            )

        # -- Liquidity ---------------------------------------
        if liquidity_data:
            ld = liquidity_data
            builder.with_liquidity_summary(
                market_liquidity = ld.get("condition",       "adequate"),
                volume_profile   = ld.get("volume_trend",   "stable"),
                liquidity_trend  = ld.get("volume_trend",   "stable"),
                liquidity_score  = ld.get("liquidity_score", 50.0),
            )

        # -- Correlation -------------------------------------
        if correlation_data:
            cd = correlation_data
            builder.with_correlation_summary(
                sector_correlations      = cd.get("sector_avg_correlation", 0.0),
                index_correlations       = cd.get("exchange_correlation",   0.0),
                intermarket_correlations = cd.get("global_correlation",     0.0),
                correlation_score        = cd.get("correlation_score",      50.0),
            )

        # -- Forecast ----------------------------------------
        if forecast_data:
            fd = forecast_data
            builder.with_forecast_summary(
                intraday_forecast   = fd.get("intraday",            "neutral"),
                short_term_forecast = fd.get("short_term",          "neutral"),
                trend_forecast      = fd.get("trend_forecast",      "neutral"),
                volatility_forecast = fd.get("volatility_forecast", "stable"),
                forecast_confidence = fd.get("confidence",          0.5),
            )

        # -- System health -----------------------------------
        if system_health_data:
            sh = system_health_data
            builder.with_system_health(
                subsystem_status   = sh.get("subsystem_status",   {}),
                validation_status  = sh.get("validation_status",  "unknown"),
                snapshot_integrity = sh.get("snapshot_integrity", "partial"),
                pipeline_health    = sh.get("pipeline_health",    "unknown"),
                framework_health   = sh.get("framework_health",   "healthy"),
            )

        # -- Audit -------------------------------------------
        if audit_data:
            ad = audit_data
            builder.with_audit_info(
                analytics_version  = ad.get("analytics_version",  VERSION),
                model_versions     = ad.get("model_versions",     {}),
                policy_versions    = ad.get("policy_versions",    {}),
                validation_summary = ad.get("validation_summary", {}),
                audit_trail        = ad.get("audit_trail",        []),
            )

        # -- Stats -------------------------------------------
        if stats_data:
            st = stats_data
            builder.with_snapshot_stats(
                analysis_duration_s  = st.get("analysis_duration_s",  0.0),
                forecast_duration_s  = st.get("forecast_duration_s",  0.0),
                snapshot_size_bytes  = st.get("snapshot_size_bytes",  0),
                component_count      = st.get("component_count",      0),
            )

        # -- Metadata ----------------------------------------
        if metadata:
            builder.with_metadata(metadata)

        return builder.build()

    # ------------------------------------------------------------------
    # Convenience: minimal valid snapshot for tests
    # ------------------------------------------------------------------

    @classmethod
    def create_minimal(
        cls,
        exchange: str = "NSE",
        *,
        snapshot_id: Optional[str] = None,
        market_analysis_id: str    = "",
        status: SnapshotStatus     = SnapshotStatus.VALID,
        is_valid: bool             = True,
    ) -> MarketSnapshot:
        return cls.create(
            snapshot_id        = snapshot_id,
            exchange           = exchange,
            market_analysis_id = market_analysis_id,
            status             = status,
            is_valid           = is_valid,
            regime_data        = {"regime": "bull", "confidence": 0.7},
            scores_data        = {"overall_score": 65.0, "market_health": "good"},
        )

    @classmethod
    def create_published(
        cls,
        exchange: str = "NSE",
        *,
        snapshot_id: Optional[str] = None,
        market_analysis_id: str    = "",
    ) -> MarketSnapshot:
        return cls.create_minimal(
            exchange           = exchange,
            snapshot_id        = snapshot_id,
            market_analysis_id = market_analysis_id,
            status             = SnapshotStatus.PUBLISHED,
            is_valid           = True,
        )
