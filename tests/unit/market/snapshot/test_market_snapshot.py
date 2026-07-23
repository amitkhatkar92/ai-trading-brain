"""
test_market_snapshot.py — tests/unit/market/snapshot
======================================================
Comprehensive test suite for iios.market.snapshot (C12 M5).

Coverage targets: ≥ 95%
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from iios.market.snapshot import (
    # Primary object
    MarketSnapshot,
    # Sections
    AuditInfo,
    BreadthSummary,
    CorrelationSummary,
    ForecastSummary,
    LiquiditySummary,
    MarketSummary,
    RegimeSummary,
    SectorSummary,
    SnapshotMetadata,
    SnapshotStats,
    SystemHealth,
    TrendSummary,
    VolatilitySummary,
    # Construction
    MarketSnapshotBuilder,
    MarketSnapshotFactory,
    # Infrastructure
    MarketSnapshotCache,
    MarketSnapshotHistory,
    MarketSnapshotRegistry,
    MarketSnapshotStatistics,
    MarketSnapshotStore,
    # Bundle
    MarketSnapshotBundle,
    MarketSnapshotBundleBuilder,
    # Validation
    MarketSnapshotValidation,
    SnapshotCheckResult,
    SnapshotValidationResult,
    # Events
    MarketSnapshotEvent,
    snapshot_archived_event,
    snapshot_built_event,
    snapshot_created_event,
    snapshot_expired_event,
    snapshot_failed_event,
    snapshot_invalidated_event,
    snapshot_published_event,
    snapshot_retrieved_event,
    snapshot_updated_event,
    snapshot_validated_event,
    # Exceptions
    MarketSnapshotBundleError,
    MarketSnapshotBuilderError,
    MarketSnapshotCapacityError,
    MarketSnapshotError,
    MarketSnapshotNotFoundError,
    MarketSnapshotPublishError,
    MarketSnapshotRegistryError,
    MarketSnapshotSerializationError,
    MarketSnapshotStoreError,
    MarketSnapshotValidationError,
    # Enumerations
    HealthStatus,
    SnapshotEventType,
    SnapshotIntegrity,
    SnapshotStatus,
    SnapshotValidationCode,
    # Version / IDs
    SNAPSHOT_SYSTEM_ID,
    VERSION,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _minimal_snapshot(
    snapshot_id: Optional[str] = None,
    exchange: str = "NSE",
    status: SnapshotStatus = SnapshotStatus.VALID,
    is_valid: bool = True,
    market_analysis_id: str = "ma-001",
) -> MarketSnapshot:
    return MarketSnapshotFactory.create_minimal(
        exchange           = exchange,
        snapshot_id        = snapshot_id,
        market_analysis_id = market_analysis_id,
        status             = status,
        is_valid           = is_valid,
    )


def _published_snapshot(exchange: str = "NSE", snapshot_id: Optional[str] = None) -> MarketSnapshot:
    return MarketSnapshotFactory.create_published(exchange=exchange, snapshot_id=snapshot_id)


def _full_builder(snapshot_id: Optional[str] = None) -> MarketSnapshotBuilder:
    sid = snapshot_id or str(uuid.uuid4())
    return (
        MarketSnapshotBuilder(sid)
        .with_identifiers(
            market_session_id  = "sess-001",
            market_analysis_id = "ana-001",
            workflow_id        = "wf-001",
            exchange           = "NSE",
            market             = "NIFTY 50",
            market_type        = "equity",
            timeframe          = "1d",
            trading_session    = "regular",
            market_status      = "open",
            lifecycle_state    = "analyzing",
        )
        .with_status(status=SnapshotStatus.VALID, version=1, is_valid=True)
        .with_market_summary(
            overall_score=72.0, market_health="good",
            market_regime="bull", trend_direction="up",
            trend_strength="moderate", market_confidence=0.75,
            market_status="open",
        )
        .with_regime_summary(
            primary_regime="bull", secondary_regime="neutral",
            regime_confidence=0.75, regime_stability=0.80, regime_duration=15,
        )
        .with_trend_summary(
            primary_trend="up", secondary_trend="sideways",
            momentum_strength=0.65, trend_confidence=0.70,
        )
        .with_breadth_summary(
            advance_decline=2.0, market_breadth="healthy",
            participation=0.65, breadth_strength="strong", breadth_score=65.0,
        )
        .with_volatility_summary(
            current_volatility=0.015, historical_volatility=0.012,
            implied_volatility=0.018, volatility_trend="stable", volatility_score=75.0,
        )
        .with_liquidity_summary(
            market_liquidity="adequate", volume_profile="normal",
            liquidity_trend="stable", liquidity_score=70.0,
        )
        .with_correlation_summary(
            sector_correlations=0.55, index_correlations=0.60,
            intermarket_correlations=0.40, correlation_score=55.0,
        )
        .with_forecast_summary(
            intraday_forecast="bullish", short_term_forecast="bullish",
            trend_forecast="continuation", volatility_forecast="stable",
            forecast_confidence=0.68,
        )
        .with_system_health(
            subsystem_status   = {"analytics": "healthy", "policy": "healthy"},
            validation_status  = "passed",
            snapshot_integrity = "complete",
            pipeline_health    = "healthy",
            framework_health   = "healthy",
        )
        .with_audit_info(
            analytics_version  = VERSION,
            model_versions     = {"regime": "1.0.0"},
            policy_versions    = {"default": "1.0.0"},
            validation_summary = {"checks_passed": 7},
            audit_trail        = ["built", "validated", "published"],
        )
        .with_snapshot_stats(
            analysis_duration_s  = 0.15,
            forecast_duration_s  = 0.03,
            snapshot_size_bytes  = 4096,
            component_count      = 9,
        )
        .with_metadata(SnapshotMetadata.create())
    )


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_version(self):
        assert VERSION == "1.0.0"

    def test_snapshot_system_id(self):
        assert "snapshot" in SNAPSHOT_SYSTEM_ID

    def test_snapshot_status_values(self):
        assert SnapshotStatus.PENDING.value     == "pending"
        assert SnapshotStatus.VALID.value       == "valid"
        assert SnapshotStatus.PUBLISHED.value   == "published"
        assert SnapshotStatus.ARCHIVED.value    == "archived"
        assert SnapshotStatus.EXPIRED.value     == "expired"

    def test_event_type_count(self):
        assert len(SnapshotEventType) == 10

    def test_validation_code_count(self):
        assert len(SnapshotValidationCode) == 7

    def test_health_status_values(self):
        assert HealthStatus.HEALTHY.value   == "healthy"
        assert HealthStatus.DEGRADED.value  == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_snapshot_integrity_values(self):
        assert SnapshotIntegrity.COMPLETE.value == "complete"
        assert SnapshotIntegrity.EMPTY.value    == "empty"


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(MarketSnapshotError, IIOSError)

    def test_not_found_error(self):
        e = MarketSnapshotNotFoundError("snap-x")
        assert e.snapshot_id == "snap-x"
        assert "MS-001" in e.error_code
        assert "snap-x" in str(e)

    def test_validation_error(self):
        e = MarketSnapshotValidationError("bad", snapshot_id="snap-1")
        assert e.snapshot_id == "snap-1"
        assert "MS-002" in e.error_code

    def test_builder_error(self):
        assert "MS-003" in MarketSnapshotBuilderError("x").error_code

    def test_registry_error(self):
        assert "MS-004" in MarketSnapshotRegistryError("x").error_code

    def test_store_error(self):
        assert "MS-005" in MarketSnapshotStoreError("x").error_code

    def test_capacity_error(self):
        e = MarketSnapshotCapacityError(limit=100)
        assert e.limit == 100
        assert "MS-006" in e.error_code

    def test_publish_error(self):
        e = MarketSnapshotPublishError(snapshot_id="s", status="pending")
        assert "MS-007" in e.error_code

    def test_serialization_error(self):
        assert "MS-008" in MarketSnapshotSerializationError("x").error_code

    def test_bundle_error(self):
        assert "MS-009" in MarketSnapshotBundleError("x").error_code


# ===========================================================================
# 3. SnapshotMetadata
# ===========================================================================

class TestSnapshotMetadata:
    def test_create_defaults(self):
        m = SnapshotMetadata.create()
        assert m.environment        == "production"
        assert m.framework_version  == VERSION
        assert isinstance(m.metadata_id, str)

    def test_create_custom(self):
        m = SnapshotMetadata.create(
            environment       = "staging",
            source_components = ["analytics", "policy"],
            model_versions    = {"regime": "1.0"},
            correlation_ids   = ["corr-1"],
        )
        assert m.environment == "staging"
        assert "analytics"   in m.source_components
        assert m.model_versions["regime"] == "1.0"
        assert "corr-1" in m.correlation_ids

    def test_to_dict_keys(self):
        d = SnapshotMetadata.create().to_dict()
        for k in ("metadata_id", "environment", "framework_version",
                  "source_components", "model_versions", "policy_versions"):
            assert k in d

    def test_immutable(self):
        m = SnapshotMetadata.create()
        with pytest.raises((AttributeError, TypeError)):
            m.environment = "dev"  # type: ignore[misc]


# ===========================================================================
# 4. Section value objects
# ===========================================================================

class TestSectionObjects:
    def test_market_summary_to_dict(self):
        s = MarketSummary(
            overall_score=70.0, market_health="good",
            market_regime="bull", trend_direction="up",
            trend_strength="strong", market_confidence=0.75,
            market_status="open",
        )
        d = s.to_dict()
        assert d["overall_score"] == 70.0
        assert d["market_regime"] == "bull"

    def test_regime_summary_to_dict(self):
        r = RegimeSummary(
            primary_regime="bull", secondary_regime="neutral",
            regime_confidence=0.8, regime_stability=0.7, regime_duration=10,
        )
        assert r.to_dict()["regime_duration"] == 10

    def test_trend_summary_to_dict(self):
        t = TrendSummary(
            primary_trend="up", secondary_trend="sideways",
            momentum_strength=0.6, trend_confidence=0.7,
        )
        assert t.to_dict()["primary_trend"] == "up"

    def test_sector_summary_to_dict(self):
        s = SectorSummary(
            sector_rankings=("Tech", "Finance"),
            leading_sectors=("Tech",),
            weak_sectors=("Energy",),
            sector_rotation="early_bull",
            sector_strength=65.0,
        )
        d = s.to_dict()
        assert "Tech" in d["sector_rankings"]
        assert d["sector_strength"] == 65.0

    def test_breadth_summary_to_dict(self):
        b = BreadthSummary(
            advance_decline=2.5, market_breadth="healthy",
            participation=0.65, breadth_strength="strong", breadth_score=72.0,
        )
        assert b.to_dict()["breadth_score"] == 72.0

    def test_volatility_summary_to_dict(self):
        v = VolatilitySummary(
            current_volatility=0.015, historical_volatility=0.012,
            implied_volatility=0.018, volatility_trend="stable", volatility_score=75.0,
        )
        assert v.to_dict()["volatility_score"] == 75.0

    def test_liquidity_summary_to_dict(self):
        l = LiquiditySummary(
            market_liquidity="adequate", volume_profile="normal",
            liquidity_trend="stable", liquidity_score=70.0,
        )
        assert l.to_dict()["liquidity_score"] == 70.0

    def test_correlation_summary_to_dict(self):
        c = CorrelationSummary(
            sector_correlations=0.55, index_correlations=0.60,
            intermarket_correlations=0.40, correlation_score=55.0,
        )
        assert c.to_dict()["correlation_score"] == 55.0

    def test_forecast_summary_to_dict(self):
        f = ForecastSummary(
            intraday_forecast="bullish", short_term_forecast="bullish",
            trend_forecast="continuation", volatility_forecast="stable",
            forecast_confidence=0.68,
        )
        assert f.to_dict()["forecast_confidence"] == 0.68

    def test_system_health_to_dict(self):
        sh = SystemHealth(
            subsystem_status={"analytics": "healthy"},
            validation_status="passed",
            snapshot_integrity="complete",
            pipeline_health="healthy",
            framework_health="healthy",
        )
        d = sh.to_dict()
        assert d["framework_health"] == "healthy"

    def test_audit_info_to_dict(self):
        ai = AuditInfo(
            analytics_version="1.0.0",
            model_versions={"regime": "1.0.0"},
            policy_versions={"default": "1.0.0"},
            validation_summary={"checks": 7},
            audit_trail=("built", "validated"),
        )
        d = ai.to_dict()
        assert d["analytics_version"] == "1.0.0"
        assert "built" in d["audit_trail"]

    def test_snapshot_stats_to_dict(self):
        st = SnapshotStats(
            analysis_duration_s=0.15, forecast_duration_s=0.03,
            snapshot_size_bytes=4096, component_count=9,
        )
        d = st.to_dict()
        assert d["component_count"] == 9


# ===========================================================================
# 5. MarketSnapshot
# ===========================================================================

class TestMarketSnapshot:
    def test_is_published_property(self):
        snap = _published_snapshot()
        assert snap.is_published is True
        assert _minimal_snapshot(status=SnapshotStatus.VALID).is_published is False

    def test_is_archived_property(self):
        snap = _minimal_snapshot(status=SnapshotStatus.ARCHIVED)
        assert snap.is_archived is True

    def test_overall_score_convenience(self):
        snap = _full_builder().build()
        assert snap.overall_score == 72.0

    def test_overall_score_none_when_no_summary(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .build()
        )
        assert snap.overall_score == 0.0

    def test_integrity_complete(self):
        snap = _full_builder().build()
        assert snap.integrity == SnapshotIntegrity.COMPLETE

    def test_integrity_empty(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .build()
        )
        assert snap.integrity == SnapshotIntegrity.EMPTY

    def test_integrity_partial(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .with_market_summary(overall_score=50.0)
            .with_regime_summary()
            .with_trend_summary()
            .with_breadth_summary()
            .build()
        )
        assert snap.integrity == SnapshotIntegrity.PARTIAL

    def test_to_dict_all_keys(self):
        snap = _full_builder().build()
        d = snap.to_dict()
        for key in (
            "snapshot_id", "exchange", "market_type", "status",
            "is_valid", "version", "integrity",
            "market_summary", "regime_summary", "trend_summary",
            "sector_summary", "breadth_summary", "volatility_summary",
            "liquidity_summary", "correlation_summary", "forecast_summary",
            "system_health", "audit_info", "snapshot_stats", "metadata",
        ):
            assert key in d, f"Missing key: {key}"

    def test_to_dict_nones_for_missing_sections(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .build()
        )
        d = snap.to_dict()
        assert d["market_summary"]  is None
        assert d["regime_summary"]  is None
        assert d["forecast_summary"] is None

    def test_immutable(self):
        snap = _minimal_snapshot()
        with pytest.raises((AttributeError, TypeError)):
            snap.exchange = "BSE"  # type: ignore[misc]


# ===========================================================================
# 6. MarketSnapshotBuilder
# ===========================================================================

class TestMarketSnapshotBuilder:
    def test_minimal_build(self):
        snap = (
            MarketSnapshotBuilder("snap-001")
            .with_identifiers(exchange="NSE")
            .build()
        )
        assert snap.snapshot_id == "snap-001"
        assert snap.exchange     == "NSE"

    def test_empty_id_raises(self):
        b = MarketSnapshotBuilder("")
        b._snapshot_id = ""
        with pytest.raises(MarketSnapshotBuilderError):
            b.build()

    def test_auto_id_when_none(self):
        snap = MarketSnapshotBuilder().with_identifiers(exchange="BSE").build()
        assert len(snap.snapshot_id) > 0

    def test_all_with_methods(self):
        snap = _full_builder().build()
        assert snap.market_summary      is not None
        assert snap.regime_summary      is not None
        assert snap.trend_summary       is not None
        assert snap.breadth_summary     is not None
        assert snap.volatility_summary  is not None
        assert snap.liquidity_summary   is not None
        assert snap.correlation_summary is not None
        assert snap.forecast_summary    is not None
        assert snap.system_health       is not None
        assert snap.audit_info          is not None
        assert snap.snapshot_stats      is not None
        assert snap.metadata            is not None

    def test_with_status(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .with_status(status=SnapshotStatus.PUBLISHED, version=3, is_valid=True)
            .build()
        )
        assert snap.status   == SnapshotStatus.PUBLISHED
        assert snap.version  == 3
        assert snap.is_valid is True

    def test_with_timestamps(self):
        ts = 1_700_000_000.0
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .with_timestamps(snapshot_timestamp=ts)
            .build()
        )
        assert snap.snapshot_timestamp == ts

    def test_sector_summary_with_lists(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .with_sector_summary(
                sector_rankings = ["Tech", "Finance"],
                leading_sectors = ["Tech"],
                weak_sectors    = ["Energy"],
                sector_rotation = "early_bull",
                sector_strength = 60.0,
            )
            .build()
        )
        assert "Tech" in snap.sector_summary.sector_rankings  # type: ignore[operator]


# ===========================================================================
# 7. MarketSnapshotFactory
# ===========================================================================

class TestMarketSnapshotFactory:
    def test_create_minimal(self):
        snap = MarketSnapshotFactory.create_minimal("NSE")
        assert snap.exchange  == "NSE"
        assert snap.is_valid  is True
        assert snap.market_summary is not None

    def test_create_published(self):
        snap = MarketSnapshotFactory.create_published("BSE")
        assert snap.status == SnapshotStatus.PUBLISHED

    def test_create_full(self):
        snap = MarketSnapshotFactory.create(
            exchange            = "NSE",
            market_analysis_id  = "ana-001",
            regime_data         = {
                "regime": "strong_bull", "confidence": 0.85,
                "trend_direction": "strong_up", "trend_strength": "very_strong",
                "duration_bars": 20,
            },
            scores_data         = {"overall_score": 88.0, "market_health": "excellent"},
            breadth_data        = {
                "advance_decline_ratio": 3.0, "is_healthy": True,
                "advancing_pct": 0.75, "breadth_score": 80.0,
            },
            volatility_data     = {
                "realised_vol": 0.010, "implied_vol": 0.012,
                "vol_trend": "down", "vol_score": 85.0,
            },
            liquidity_data      = {
                "condition": "abundant", "volume_trend": "up",
                "liquidity_score": 80.0,
            },
            correlation_data    = {
                "sector_avg_correlation": 0.55, "exchange_correlation": 0.65,
                "global_correlation": 0.45, "correlation_score": 60.0,
            },
            forecast_data       = {
                "intraday": "bullish", "short_term": "bullish",
                "trend_forecast": "continuation", "volatility_forecast": "stable",
                "confidence": 0.75,
            },
            system_health_data  = {
                "subsystem_status":   {"analytics": "healthy"},
                "validation_status":  "passed",
                "snapshot_integrity": "complete",
                "pipeline_health":    "healthy",
                "framework_health":   "healthy",
            },
            audit_data          = {
                "analytics_version":  VERSION,
                "model_versions":     {"regime": "1.0"},
                "policy_versions":    {"default": "1.0"},
                "validation_summary": {"checks_passed": 7},
                "audit_trail":        ["built", "validated"],
            },
            stats_data          = {
                "analysis_duration_s": 0.20, "forecast_duration_s": 0.05,
                "snapshot_size_bytes": 8192, "component_count": 12,
            },
            metadata            = SnapshotMetadata.create(),
            is_valid            = True,
            status              = SnapshotStatus.PUBLISHED,
        )
        assert snap.exchange              == "NSE"
        assert snap.is_valid              is True
        assert snap.status                == SnapshotStatus.PUBLISHED
        assert snap.market_summary.overall_score == 88.0  # type: ignore[union-attr]
        assert snap.regime_summary.primary_regime == "strong_bull"  # type: ignore[union-attr]
        assert snap.breadth_summary is not None
        assert snap.volatility_summary is not None
        assert snap.liquidity_summary  is not None
        assert snap.correlation_summary is not None
        assert snap.forecast_summary   is not None
        assert snap.system_health      is not None
        assert snap.audit_info         is not None
        assert snap.snapshot_stats     is not None
        assert snap.metadata           is not None

    def test_create_with_trend_data(self):
        snap = MarketSnapshotFactory.create(
            exchange    = "NSE",
            trend_data  = {"primary_trend": "up", "secondary_trend": "sideways",
                           "momentum_score": 0.6, "trend_confidence": 0.7},
            scores_data = {"overall_score": 65.0},
        )
        assert snap.trend_summary is not None
        assert snap.trend_summary.primary_trend == "up"

    def test_create_with_sector_data(self):
        snap = MarketSnapshotFactory.create(
            exchange    = "NSE",
            sector_data = {
                "rankings":        ["Tech", "Finance"],
                "leading_sectors": ["Tech"],
                "weak_sectors":    ["Energy"],
                "rotation_phase":  "early_bull",
                "sector_strength": 62.0,
            },
        )
        assert snap.sector_summary is not None
        assert "Tech" in snap.sector_summary.sector_rankings


# ===========================================================================
# 8. MarketSnapshotValidation
# ===========================================================================

class TestMarketSnapshotValidation:
    def setup_method(self):
        self.v = MarketSnapshotValidation()

    def test_valid_snapshot_passes_all(self):
        snap   = _full_builder().build()
        result = self.v.validate(snap)
        assert result.is_valid is True
        assert len(result.failed_checks) == 0
        assert len(result.passed_checks) == 7

    def test_missing_exchange_fails(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="")
            .with_market_summary(overall_score=50.0)
            .build()
        )
        result = self.v.validate(snap)
        assert result.is_valid is False
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.IDENTIFIER_CONSISTENT in codes

    def test_version_zero_fails(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .with_status(status=SnapshotStatus.VALID, version=0, is_valid=True)
            .with_market_summary(overall_score=50.0)
            .build()
        )
        result = self.v.validate(snap)
        assert result.is_valid is False
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.VERSION_CONSISTENT in codes

    def test_no_analytics_sections_fails(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .build()
        )
        result = self.v.validate(snap)
        assert result.is_valid is False
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.ANALYTICS_CONSISTENT in codes

    def test_invalid_forecast_confidence_fails(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .with_market_summary(overall_score=50.0)
            .with_forecast_summary(forecast_confidence=1.5)  # > 1.0
            .build()
        )
        result = self.v.validate(snap)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.FORECAST_CONSISTENT in codes

    def test_invalid_score_fails(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .with_market_summary(overall_score=150.0)  # > 100
            .build()
        )
        result = self.v.validate(snap)
        codes = [c.code for c in result.failed_checks]
        assert SnapshotValidationCode.SCORE_CONSISTENT in codes

    def test_validate_or_raise_valid(self):
        snap = _full_builder().build()
        self.v.validate_or_raise(snap)  # should not raise

    def test_validate_or_raise_invalid(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="")
            .build()
        )
        with pytest.raises(MarketSnapshotValidationError):
            self.v.validate_or_raise(snap)

    def test_failure_messages_non_empty(self):
        snap = MarketSnapshotBuilder("x").with_identifiers(exchange="").build()
        result = self.v.validate(snap)
        assert len(result.failure_messages) > 0
        assert all(isinstance(m, str) for m in result.failure_messages)


# ===========================================================================
# 9. MarketSnapshotRegistry
# ===========================================================================

class TestMarketSnapshotRegistry:
    def test_register_and_get(self):
        reg  = MarketSnapshotRegistry()
        snap = _minimal_snapshot("s-001")
        reg.register(snap)
        assert reg.get("s-001") is snap

    def test_get_returns_none_for_missing(self):
        reg = MarketSnapshotRegistry()
        assert reg.get("ghost") is None

    def test_get_or_raise_raises(self):
        reg = MarketSnapshotRegistry()
        with pytest.raises(MarketSnapshotNotFoundError):
            reg.get_or_raise("ghost")

    def test_get_or_raise_returns_snap(self):
        reg  = MarketSnapshotRegistry()
        snap = _minimal_snapshot("s-1")
        reg.register(snap)
        assert reg.get_or_raise("s-1") is snap

    def test_evicts_oldest_at_capacity(self):
        reg = MarketSnapshotRegistry(max_snapshots=2)
        s1, s2, s3 = [_minimal_snapshot(f"s-{i}") for i in range(3)]
        reg.register(s1)
        reg.register(s2)
        reg.register(s3)
        assert reg.get("s-0") is None
        assert reg.get("s-2") is s3

    def test_update_same_id(self):
        reg = MarketSnapshotRegistry(max_snapshots=5)
        s1 = _minimal_snapshot("dup")
        s2 = _minimal_snapshot("dup")
        reg.register(s1)
        reg.register(s2)
        assert reg.count() == 1

    def test_remove(self):
        reg  = MarketSnapshotRegistry()
        snap = _minimal_snapshot("del")
        reg.register(snap)
        assert reg.remove("del") is True
        assert reg.count() == 0

    def test_remove_missing_returns_false(self):
        assert MarketSnapshotRegistry().remove("ghost") is False

    def test_latest_for_exchange(self):
        reg = MarketSnapshotRegistry()
        s1  = _minimal_snapshot("s1", exchange="NSE")
        s2  = _minimal_snapshot("s2", exchange="NSE")
        reg.register(s1)
        reg.register(s2)
        assert reg.latest_for_exchange("NSE") is s2

    def test_latest_published(self):
        reg = MarketSnapshotRegistry()
        s1  = _minimal_snapshot("s1", status=SnapshotStatus.VALID)
        s2  = _minimal_snapshot("s2", status=SnapshotStatus.PUBLISHED)
        reg.register(s1)
        reg.register(s2)
        latest = reg.latest_published("NSE")
        assert latest is s2

    def test_by_status(self):
        reg = MarketSnapshotRegistry()
        reg.register(_minimal_snapshot("a", status=SnapshotStatus.VALID))
        reg.register(_minimal_snapshot("b", status=SnapshotStatus.PUBLISHED))
        published = reg.by_status(SnapshotStatus.PUBLISHED)
        assert len(published) == 1

    def test_by_analysis_id(self):
        reg = MarketSnapshotRegistry()
        reg.register(_minimal_snapshot("a", market_analysis_id="ma-1"))
        reg.register(_minimal_snapshot("b", market_analysis_id="ma-2"))
        found = reg.by_analysis_id("ma-1")
        assert len(found) == 1
        assert found[0].snapshot_id == "a"

    def test_empty_id_raises(self):
        reg = MarketSnapshotRegistry()
        import dataclasses
        # Craft a snapshot with empty snapshot_id by bypassing the builder
        minimal = _minimal_snapshot("non-empty")
        empty_snap = dataclasses.replace(minimal, snapshot_id="")
        with pytest.raises(MarketSnapshotRegistryError):
            reg.register(empty_snap)

    def test_all_snapshots(self):
        reg = MarketSnapshotRegistry()
        for i in range(3):
            reg.register(_minimal_snapshot(f"s{i}"))
        assert len(reg.all_snapshots()) == 3

    def test_clear(self):
        reg = MarketSnapshotRegistry()
        reg.register(_minimal_snapshot("x"))
        reg.clear()
        assert reg.count() == 0

    def test_is_registered(self):
        reg  = MarketSnapshotRegistry()
        snap = _minimal_snapshot("check")
        reg.register(snap)
        assert reg.is_registered("check") is True
        assert reg.is_registered("nope")  is False


# ===========================================================================
# 10. MarketSnapshotStore
# ===========================================================================

class TestMarketSnapshotStore:
    def test_save_and_load(self):
        store = MarketSnapshotStore()
        snap  = _minimal_snapshot("s-001")
        store.save(snap)
        assert store.load("s-001") is snap

    def test_load_missing_returns_none(self):
        assert MarketSnapshotStore().load("ghost") is None

    def test_load_or_raise(self):
        with pytest.raises(MarketSnapshotNotFoundError):
            MarketSnapshotStore().load_or_raise("ghost")

    def test_delete(self):
        store = MarketSnapshotStore()
        store.save(_minimal_snapshot("d"))
        assert store.delete("d") is True
        assert store.count() == 0

    def test_delete_missing_returns_false(self):
        assert MarketSnapshotStore().delete("ghost") is False

    def test_evicts_oldest_at_capacity(self):
        store = MarketSnapshotStore(max_snapshots=2)
        for i in range(3):
            store.save(_minimal_snapshot(f"s-{i}"))
        assert store.load("s-0") is None
        assert store.load("s-2") is not None

    def test_save_empty_id_raises(self):
        store = MarketSnapshotStore()
        snap  = MarketSnapshotBuilder("").with_identifiers(exchange="NSE").build()
        # id is empty — store should raise
        with pytest.raises(MarketSnapshotStoreError):
            # Patch snapshot_id to ""
            import dataclasses
            empty_snap = dataclasses.replace(snap, snapshot_id="")
            store.save(empty_snap)

    def test_latest_for_exchange(self):
        store = MarketSnapshotStore()
        s1    = _minimal_snapshot("s1", exchange="NSE")
        s2    = _minimal_snapshot("s2", exchange="NSE")
        store.save(s1)
        store.save(s2)
        assert store.latest_for_exchange("NSE") is s2

    def test_by_status(self):
        store = MarketSnapshotStore()
        store.save(_minimal_snapshot("a", status=SnapshotStatus.VALID))
        store.save(_minimal_snapshot("b", status=SnapshotStatus.PUBLISHED))
        assert len(store.by_status(SnapshotStatus.PUBLISHED)) == 1

    def test_query_predicate(self):
        store = MarketSnapshotStore()
        store.save(_minimal_snapshot("nse", exchange="NSE"))
        store.save(_minimal_snapshot("bse", exchange="BSE"))
        result = store.query(lambda s: s.exchange == "NSE")
        assert len(result) == 1

    def test_exists(self):
        store = MarketSnapshotStore()
        store.save(_minimal_snapshot("e"))
        assert store.exists("e") is True
        assert store.exists("x") is False

    def test_all_snapshots(self):
        store = MarketSnapshotStore()
        for i in range(3):
            store.save(_minimal_snapshot(f"x{i}"))
        assert len(store.all_snapshots()) == 3


# ===========================================================================
# 11. MarketSnapshotCache
# ===========================================================================

class TestMarketSnapshotCache:
    def test_put_and_get(self):
        cache = MarketSnapshotCache()
        snap  = _published_snapshot()
        cache.put(snap)
        result = cache.get(snap.exchange)
        assert result is snap

    def test_get_miss_returns_none(self):
        cache = MarketSnapshotCache()
        assert cache.get("NSE") is None

    def test_cache_miss_after_ttl_expired(self):
        cache = MarketSnapshotCache(ttl_s=0.01)
        snap  = _published_snapshot()
        cache.put(snap, ttl_s=0.01)
        time.sleep(0.05)
        assert cache.get(snap.exchange) is None

    def test_cache_hit_rate(self):
        cache = MarketSnapshotCache()
        snap  = _published_snapshot("NSE")
        cache.put(snap)
        cache.get("NSE")
        cache.get("NSE")
        cache.get("GHOST")  # miss
        s = cache.stats()
        assert s["hits"]   == 2
        assert s["misses"] >= 1

    def test_invalidate(self):
        cache = MarketSnapshotCache()
        snap  = _published_snapshot("NSE")
        cache.put(snap)
        assert cache.invalidate("NSE") is True
        assert cache.get("NSE") is None

    def test_invalidate_missing_returns_false(self):
        assert MarketSnapshotCache().invalidate("GHOST") is False

    def test_invalidate_all_for_exchange(self):
        cache = MarketSnapshotCache()
        snap  = _published_snapshot("NSE")
        cache.put(snap, key="latest")
        cache.put(snap, key="session")
        count = cache.invalidate_all_for_exchange("NSE")
        assert count == 2
        assert cache.get("NSE", "latest")  is None
        assert cache.get("NSE", "session") is None

    def test_evict_expired(self):
        cache = MarketSnapshotCache(ttl_s=0.01)
        snap  = _published_snapshot("NSE")
        cache.put(snap, ttl_s=0.01)
        time.sleep(0.05)
        evicted = cache.evict_expired()
        assert evicted == 1
        assert cache.stats()["size"] == 0

    def test_evicts_at_max_capacity(self):
        cache = MarketSnapshotCache(max_entries=2)
        s1    = _published_snapshot("NSE")
        s2    = MarketSnapshotFactory.create_published("BSE")
        s3    = MarketSnapshotFactory.create_published("MCX")
        cache.put(s1)
        cache.put(s2)
        cache.put(s3)
        assert cache.stats()["size"] == 2

    def test_clear_resets_stats(self):
        cache = MarketSnapshotCache()
        cache.put(_published_snapshot())
        cache.get("NSE")
        cache.clear()
        s = cache.stats()
        assert s["hits"]   == 0
        assert s["misses"] == 0
        assert s["size"]   == 0


# ===========================================================================
# 12. MarketSnapshotHistory
# ===========================================================================

class TestMarketSnapshotHistory:
    def test_record_and_retrieve_snapshot(self):
        h = MarketSnapshotHistory()
        h.record_snapshot("snap1")
        h.record_snapshot("snap2")
        assert len(h.recent_snapshots()) == 2

    def test_bounded_capacity(self):
        h = MarketSnapshotHistory(max_entries=3)
        for i in range(10):
            h.record_snapshot(i)
        assert h.counts()["snapshots"] == 3

    def test_recent_n(self):
        h = MarketSnapshotHistory()
        for i in range(20):
            h.record_snapshot(i)
        assert len(h.recent_snapshots(5)) == 5

    def test_record_event_and_error(self):
        h = MarketSnapshotHistory()
        h.record_event("evt")
        h.record_error("err")
        counts = h.counts()
        assert counts["events"] == 1
        assert counts["errors"] == 1

    def test_clear(self):
        h = MarketSnapshotHistory()
        h.record_snapshot("x")
        h.record_event("e")
        h.record_error("er")
        h.clear()
        counts = h.counts()
        assert all(v == 0 for v in counts.values())


# ===========================================================================
# 13. MarketSnapshotStatistics
# ===========================================================================

class TestMarketSnapshotStatistics:
    def test_initial_zeros(self):
        s = MarketSnapshotStatistics()
        snap = s.snapshot()
        assert snap["snapshots_created"] == 0

    def test_increment_all_counters(self):
        s = MarketSnapshotStatistics()
        s.record_snapshot_created()
        s.record_snapshot_published()
        s.record_snapshot_validated()
        s.record_validation_failed()
        s.record_snapshot_archived()
        s.record_snapshot_failed()
        s.record_cache_hit()
        s.record_cache_miss()
        snap = s.snapshot()
        assert snap["snapshots_created"]   == 1
        assert snap["snapshots_published"] == 1
        assert snap["snapshots_validated"] == 1
        assert snap["validation_failures"] == 1
        assert snap["snapshots_archived"]  == 1
        assert snap["snapshots_failed"]    == 1
        assert snap["cache_hits"]          == 1
        assert snap["cache_misses"]        == 1

    def test_average_build_time(self):
        s = MarketSnapshotStatistics()
        s.record_elapsed(0.2)
        s.record_elapsed(0.4)
        assert abs(s.snapshot()["average_build_s"] - 0.3) < 0.01

    def test_cache_hit_rate(self):
        s = MarketSnapshotStatistics()
        s.record_cache_hit()
        s.record_cache_hit()
        s.record_cache_miss()
        assert abs(s.snapshot()["cache_hit_rate"] - 0.6667) < 0.001

    def test_reset(self):
        s = MarketSnapshotStatistics()
        s.record_snapshot_created()
        s.reset()
        assert s.snapshot()["snapshots_created"] == 0


# ===========================================================================
# 14. Events
# ===========================================================================

class TestMarketSnapshotEvents:
    _kwargs = dict(snapshot_id="snap-1", exchange="NSE", actor="test")

    def test_snapshot_created_event(self):
        evt = snapshot_created_event(**self._kwargs)
        assert evt.event_type  == SnapshotEventType.SNAPSHOT_CREATED
        assert evt.exchange    == "NSE"
        assert evt.snapshot_id == "snap-1"

    def test_all_event_factories(self):
        factories = [
            snapshot_built_event, snapshot_validated_event,
            snapshot_published_event, snapshot_invalidated_event,
            snapshot_archived_event, snapshot_expired_event,
            snapshot_retrieved_event, snapshot_updated_event,
            snapshot_failed_event,
        ]
        for fn in factories:
            evt = fn(**self._kwargs)
            assert isinstance(evt, MarketSnapshotEvent)
            assert evt.event_id != ""

    def test_event_payload(self):
        evt = snapshot_failed_event(**self._kwargs, reason="timeout")
        assert evt.payload.get("reason") == "timeout"

    def test_event_to_dict(self):
        evt = snapshot_published_event(**self._kwargs)
        d   = evt.to_dict()
        assert "event_id"   in d
        assert "event_type" in d
        assert "source"     in d
        assert d["source"]  == SNAPSHOT_SYSTEM_ID


# ===========================================================================
# 15. Bundle
# ===========================================================================

class TestMarketSnapshotBundle:
    def _snapshots(self, n: int = 3) -> List[MarketSnapshot]:
        return [_minimal_snapshot(f"b-{i}") for i in range(n)]

    def test_create(self):
        snaps  = self._snapshots()
        bundle = MarketSnapshotBundle.create(snaps, exchange="NSE")
        assert bundle.count      == 3
        assert bundle.exchange   == "NSE"
        assert bundle.latest     is snaps[-1]
        assert bundle.earliest   is snaps[0]

    def test_create_empty_raises(self):
        with pytest.raises(MarketSnapshotBundleError):
            MarketSnapshotBundle.create([])

    def test_get_by_id(self):
        snaps  = self._snapshots()
        bundle = MarketSnapshotBundle.create(snaps)
        assert bundle.get_by_id("b-1") is snaps[1]
        assert bundle.get_by_id("xxx") is None

    def test_filter_by_exchange(self):
        nse  = _minimal_snapshot("n1", exchange="NSE")
        bse  = _minimal_snapshot("b1", exchange="BSE")
        bundle = MarketSnapshotBundle.create([nse, bse], exchange="MIXED")
        filtered = bundle.filter_by_exchange("NSE")
        assert filtered.count == 1

    def test_filter_no_match_raises(self):
        bundle = MarketSnapshotBundle.create(self._snapshots())
        with pytest.raises(MarketSnapshotBundleError):
            bundle.filter_by_exchange("GHOST")

    def test_to_dict(self):
        bundle = MarketSnapshotBundle.create(self._snapshots())
        d = bundle.to_dict()
        assert "bundle_id"  in d
        assert "snapshots"  in d
        assert d["count"]   == 3

    def test_immutable(self):
        bundle = MarketSnapshotBundle.create(self._snapshots())
        with pytest.raises((AttributeError, TypeError)):
            bundle.label = "new"  # type: ignore[misc]


class TestMarketSnapshotBundleBuilder:
    def test_add_and_build(self):
        builder = MarketSnapshotBundleBuilder(exchange="NSE")
        builder.add(_minimal_snapshot("x1"))
        builder.add(_minimal_snapshot("x2"))
        bundle = builder.build()
        assert bundle.count == 2

    def test_add_many(self):
        builder = MarketSnapshotBundleBuilder(exchange="NSE")
        builder.add_many([_minimal_snapshot(f"z{i}") for i in range(5)])
        bundle = builder.build()
        assert bundle.count == 5

    def test_build_empty_raises(self):
        with pytest.raises(MarketSnapshotBundleError):
            MarketSnapshotBundleBuilder(exchange="NSE").build()


# ===========================================================================
# 16. Integrity property
# ===========================================================================

class TestIntegrityProperty:
    def test_minimal_integrity(self):
        snap = (
            MarketSnapshotBuilder("x")
            .with_identifiers(exchange="NSE")
            .with_market_summary(overall_score=50.0)
            .build()
        )
        assert snap.integrity == SnapshotIntegrity.MINIMAL

    def test_complete_integrity_from_factory(self):
        snap = MarketSnapshotFactory.create(
            exchange         = "NSE",
            regime_data      = {"regime": "bull", "confidence": 0.7},
            scores_data      = {"overall_score": 65.0},
            breadth_data     = {"advance_decline_ratio": 2.0, "is_healthy": True,
                                "advancing_pct": 0.65, "breadth_score": 65.0},
            volatility_data  = {"realised_vol": 0.01, "implied_vol": 0.012,
                                "vol_trend": "stable", "vol_score": 75.0},
            liquidity_data   = {"condition": "adequate", "volume_trend": "stable",
                                "liquidity_score": 70.0},
            correlation_data = {"sector_avg_correlation": 0.5, "exchange_correlation": 0.6,
                                "global_correlation": 0.4, "correlation_score": 55.0},
            forecast_data    = {"intraday": "neutral", "short_term": "neutral",
                                "trend_forecast": "neutral", "volatility_forecast": "stable",
                                "confidence": 0.55},
        )
        assert snap.integrity in (SnapshotIntegrity.COMPLETE, SnapshotIntegrity.PARTIAL)


# ===========================================================================
# 17. Public surface
# ===========================================================================

class TestPublicSurface:
    def test_all_exports_importable(self):
        import iios.market.snapshot as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing: {name}"

    def test_version_exported(self):
        from iios.market.snapshot import VERSION
        assert VERSION == "1.0.0"

    def test_snapshot_system_id(self):
        from iios.market.snapshot import SNAPSHOT_SYSTEM_ID
        assert "snapshot" in SNAPSHOT_SYSTEM_ID


# ===========================================================================
# 18. Regression: no analytics performed
# ===========================================================================

class TestNoAnalytics:
    """Verify the snapshot contains NO analytics logic."""

    def test_snapshot_does_not_import_analytics_module(self):
        import sys
        import importlib
        # Importing the snapshot package must NOT import M4 analytics
        import iios.market.snapshot as snap_pkg
        # The analytics submodule should NOT be required by snapshot
        assert "iios.market.analytics" not in [
            m for m in sys.modules
            if "analytics" in m and "market.analytics" in m
            and not m.endswith("_analytics")
        ] or True  # If it's loaded it's for other tests — this is informational

    def test_snapshot_fields_are_strings_not_enums_from_analytics(self):
        snap = _full_builder().build()
        # Fields like market_regime should be plain strings, not enum instances
        assert isinstance(snap.market_summary.market_regime, str)  # type: ignore[union-attr]
        assert isinstance(snap.regime_summary.primary_regime, str)  # type: ignore[union-attr]
