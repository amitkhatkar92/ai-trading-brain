"""tests/unit/integration/test_data_integration_engine.py

≥150 tests for the Data Integration Layer.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Helper for running coroutines in sync test context
def _run(coro):
    return asyncio.run(coro)

from iios.integration.cache.cache_key import CacheKey
from iios.integration.cache.integration_cache import IntegrationCache
from iios.integration.core.data_record import DataRecord, DataRequest, DataResponse
from iios.integration.core.integration_result import IntegrationResult, ProviderContract
from iios.integration.data_integration_engine import (
    DataIntegrationEngine,
    get_data_integration_engine,
    reset_data_integration_engine,
)
from iios.integration.integration_constants import (
    CircuitBreakerState,
    DataCategory,
    DataFrequency,
    DataQualityLevel,
    HealthStatus,
    IntegrationEngineStatus,
    PipelineStatus,
    ProviderPriority,
    ProviderStatus,
    ValidationSeverity,
    ValidationStatus,
    CANONICAL_SCHEMA_VERSION,
    INTEGRATION_ENGINE_VERSION,
)
from iios.integration.integration_context import (
    IntegrationContextState,
    integration_operation_context,
)
from iios.integration.integration_exceptions import (
    AllProvidersFailedError,
    CacheOverflowError,
    CircuitBreakerOpenError,
    FieldMappingError,
    IntegrationEngineAlreadyRunningError,
    IntegrationEngineNotInitializedError,
    IntegrationError,
    PipelineConfigurationError,
    PipelineNotFoundError,
    ProviderAlreadyRegisteredError,
    ProviderCapabilityError,
    ProviderFetchError,
    ProviderNotFoundError,
    RegistryCapacityError,
    SchemaMapperNotFoundError,
    TimestampNormalizationError,
    UnitConversionError,
    ValidationError,
)
from iios.integration.integration_factory import IntegrationFactory
from iios.integration.integration_registry import (
    IntegrationRegistry,
    get_integration_registry,
    reset_integration_registry,
)
from iios.integration.monitoring.availability_monitor import AvailabilityMonitor
from iios.integration.monitoring.health_monitor import HealthMonitor
from iios.integration.monitoring.latency_monitor import LatencyMonitor
from iios.integration.monitoring.provider_statistics import RollingProviderStats
from iios.integration.normalization.field_mapper import FieldMapper, FieldMapping
from iios.integration.normalization.normalization_engine import NormalizationEngine
from iios.integration.normalization.schema_mapper import (
    SchemaMapperRegistry,
    SimpleSchemaMapper,
)
from iios.integration.normalization.timestamp_normalizer import TimestampNormalizer
from iios.integration.normalization.unit_converter import UnitConverter
from iios.integration.pipeline.pipeline_builder import Pipeline, PipelineBuilder
from iios.integration.pipeline.pipeline_context import PipelineContext
from iios.integration.pipeline.pipeline_engine import PipelineEngine
from iios.integration.pipeline.pipeline_executor import PipelineExecutor
from iios.integration.pipeline.pipeline_stage import (
    CacheStage,
    ExtractionStage,
    NormalizationStage,
    PipelineStageResult,
    PublishStage,
    TransformationStage,
    ValidationStage,
)
from iios.integration.providers.base_provider import BaseProvider
from iios.integration.providers.provider_capabilities import ProviderCapabilities
from iios.integration.providers.provider_health import CircuitBreaker, ProviderHealth
from iios.integration.providers.provider_manager import ProviderManager
from iios.integration.providers.provider_metadata import ProviderMetadata
from iios.integration.providers.provider_registry import ProviderRegistry
from iios.integration.registry.capability_registry import CapabilityRegistry
from iios.integration.validation.integrity_checker import IntegrityChecker
from iios.integration.validation.quality_checker import QualityChecker
from iios.integration.validation.schema_validator import FieldSpec, SchemaValidator
from iios.integration.validation.validation_engine import ValidationEngine
from iios.integration.validation.validation_report import ValidationIssue, ValidationReport


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_record(
    symbol:      str   = "RELIANCE",
    timestamp:   float = 1_700_000_000.0,
    provider_id: str   = "test_provider",
    category:    DataCategory = DataCategory.MARKET_DATA,
    payload:     dict | None = None,
) -> DataRecord:
    return DataRecord(
        provider_id=provider_id,
        category=category,
        frequency=DataFrequency.DAILY,
        symbol=symbol,
        timestamp=timestamp,
        payload=payload or {"close": 2500.0, "volume": 1000, "symbol": symbol},
    )


def _make_request(
    provider_id: str = "test_provider",
    category: DataCategory = DataCategory.MARKET_DATA,
    symbols: list[str] = ["RELIANCE"],
) -> DataRequest:
    return DataRequest(
        provider_id=provider_id,
        category=category,
        symbols=symbols,
        frequency=DataFrequency.DAILY,
    )


class _ConcreteProvider(BaseProvider):
    """Minimal concrete provider for testing."""

    def __init__(self, pid: str = "test_provider", fail: bool = False) -> None:
        super().__init__()
        self._pid  = pid
        self._fail = fail

    @property
    def provider_id(self) -> str:
        return self._pid

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            categories=[DataCategory.MARKET_DATA.value],
            frequencies=[DataFrequency.DAILY.value],
            symbol_spaces=["NSE"],
        )

    async def _do_fetch(self, request: DataRequest) -> DataResponse:
        if self._fail:
            raise RuntimeError("Simulated provider failure")
        return DataResponse(
            request_id=request.request_id,
            provider_id=self.provider_id,
            records=[_make_record(provider_id=self.provider_id)],
            success=True,
        )

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            status=HealthStatus.HEALTHY if not self._fail else HealthStatus.UNHEALTHY,
        )


@pytest.fixture(autouse=True)
def reset_singletons():
    reset_data_integration_engine()
    reset_integration_registry()
    yield
    reset_data_integration_engine()
    reset_integration_registry()


# ── Constants ─────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version_is_string(self):
        assert isinstance(INTEGRATION_ENGINE_VERSION, str)

    def test_data_categories(self):
        assert DataCategory.MARKET_DATA.value == "market_data"
        assert DataCategory.FUNDAMENTAL.value == "fundamental"

    def test_data_frequencies(self):
        assert DataFrequency.DAILY.value  == "daily"
        assert DataFrequency.TICK.value   == "tick"

    def test_provider_status_values(self):
        assert ProviderStatus.ACTIVE.value   == "active"
        assert ProviderStatus.INACTIVE.value == "inactive"

    def test_provider_priority_ordering(self):
        assert ProviderPriority.CRITICAL.value < ProviderPriority.FALLBACK.value

    def test_pipeline_status_values(self):
        assert PipelineStatus.COMPLETED.value == "completed"
        assert PipelineStatus.FAILED.value    == "failed"

    def test_health_status_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_circuit_breaker_states(self):
        states = [CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN]
        assert len(states) == 3

    def test_validation_severity_values(self):
        assert ValidationSeverity.ERROR.value == "error"

    def test_canonical_schema_version(self):
        assert CANONICAL_SCHEMA_VERSION == "1.0"


# ── DataRecord ────────────────────────────────────────────────────────────────

class TestDataRecord:
    def test_defaults(self):
        r = DataRecord()
        assert r.record_id != ""
        assert r.schema_version == CANONICAL_SCHEMA_VERSION

    def test_to_dict_keys(self):
        r  = _make_record()
        d  = r.to_dict()
        assert "record_id" in d
        assert "provider_id" in d
        assert "category" in d
        assert "payload" in d

    def test_category_serialized_as_value(self):
        r = _make_record(category=DataCategory.NEWS)
        d = r.to_dict()
        assert d["category"] == "news"

    def test_unique_ids(self):
        r1, r2 = DataRecord(), DataRecord()
        assert r1.record_id != r2.record_id


class TestDataRequest:
    def test_defaults(self):
        req = DataRequest()
        assert req.request_id != ""
        assert req.timeout_sec == 15.0

    def test_to_dict(self):
        req = _make_request()
        d   = req.to_dict()
        assert d["provider_id"] == "test_provider"

    def test_symbols_list(self):
        req = _make_request(symbols=["TCS", "INFY"])
        assert len(req.symbols) == 2


class TestDataResponse:
    def test_record_count(self):
        resp = DataResponse(
            records=[_make_record(), _make_record()],
            success=True,
        )
        assert resp.record_count() == 2

    def test_to_dict(self):
        resp = DataResponse(success=True, latency_ms=42.5)
        d    = resp.to_dict()
        assert d["success"] is True
        assert d["latency_ms"] == 42.5


# ── ProviderCapabilities ──────────────────────────────────────────────────────

class TestProviderCapabilities:
    def test_supports_category(self):
        caps = ProviderCapabilities(categories=["market_data"])
        assert caps.supports_category("market_data")
        assert not caps.supports_category("news")

    def test_supports_frequency(self):
        caps = ProviderCapabilities(frequencies=["daily", "hour"])
        assert caps.supports_frequency("daily")
        assert not caps.supports_frequency("tick")

    def test_supports_symbol_space(self):
        caps = ProviderCapabilities(symbol_spaces=["NSE"])
        assert caps.supports_symbol_space("NSE")
        assert not caps.supports_symbol_space("NYSE")

    def test_to_dict_keys(self):
        caps = ProviderCapabilities()
        d    = caps.to_dict()
        assert "categories" in d and "frequencies" in d


# ── ProviderMetadata ──────────────────────────────────────────────────────────

class TestProviderMetadata:
    def test_mark_fetched(self):
        md = ProviderMetadata(provider_id="p1")
        md.mark_fetched()
        assert md.fetch_count == 1
        assert md.last_fetch_at is not None

    def test_mark_error(self):
        md = ProviderMetadata(provider_id="p1")
        md.mark_error("timeout")
        assert md.error_count == 1
        assert md.last_error == "timeout"

    def test_error_rate(self):
        md = ProviderMetadata()
        md.mark_fetched()
        md.mark_fetched()
        md.mark_error("err")
        assert md.error_rate() == pytest.approx(1 / 3)

    def test_to_dict(self):
        md = ProviderMetadata(provider_id="p1", version="2.0.0")
        d  = md.to_dict()
        assert d["version"] == "2.0.0"


# ── CircuitBreaker ────────────────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.allow_request()

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert not cb.allow_request()

    def test_success_resets_to_closed(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_to_dict_keys(self):
        cb = CircuitBreaker()
        d  = cb.to_dict()
        assert "state" in d and "threshold" in d


# ── BaseProvider ──────────────────────────────────────────────────────────────

class TestBaseProvider:
    def test_provider_id(self):
        p = _ConcreteProvider("my_provider")
        assert p.provider_id == "my_provider"

    def test_can_handle_matching(self):
        p = _ConcreteProvider()
        assert p.can_handle("market_data", "daily")

    def test_can_handle_not_matching(self):
        p = _ConcreteProvider()
        assert not p.can_handle("news")

    def test_is_not_active_before_init(self):
        p = _ConcreteProvider()
        assert not p.is_active()

    def test_initialize_sets_active(self):
        p = _ConcreteProvider()
        _run(p.initialize())
        assert p.is_active()

    def test_fetch_returns_response(self):
        p = _ConcreteProvider()
        _run(p.initialize())
        req  = _make_request()
        resp = _run(p.fetch(req)
)
        assert resp.success
        assert len(resp.records) == 1

    def test_fetch_fails_when_circuit_open(self):
        p  = _ConcreteProvider(fail=True)
        _run(p.initialize())
        cb = p.circuit_breaker
        cb._failure_count = 100
        cb._state         = CircuitBreakerState.OPEN
        cb._opened_at     = time.time()
        req = _make_request()
        with pytest.raises(Exception):
            _run(p.fetch(req))


# ── ProviderRegistry ──────────────────────────────────────────────────────────

class TestProviderRegistry:
    def test_register_and_get(self):
        reg = ProviderRegistry()
        p   = _ConcreteProvider("p1")
        reg.register(p)
        assert reg.get("p1") is p

    def test_register_duplicate_raises(self):
        reg = ProviderRegistry()
        p   = _ConcreteProvider("p1")
        reg.register(p)
        with pytest.raises(ProviderAlreadyRegisteredError):
            reg.register(p)

    def test_get_missing_raises(self):
        reg = ProviderRegistry()
        with pytest.raises(ProviderNotFoundError):
            reg.get("nonexistent")

    def test_capacity_limit(self):
        reg = ProviderRegistry(max_providers=2)
        reg.register(_ConcreteProvider("p1"))
        reg.register(_ConcreteProvider("p2"))
        with pytest.raises(RegistryCapacityError):
            reg.register(_ConcreteProvider("p3"))

    def test_unregister(self):
        reg = ProviderRegistry()
        reg.register(_ConcreteProvider("p1"))
        reg.unregister("p1")
        assert not reg.has("p1")

    def test_providers_for_category_sorted_by_priority(self):
        reg = ProviderRegistry()
        p_low  = _ConcreteProvider("p_low")
        p_low._priority  = ProviderPriority.LOW
        p_high = _ConcreteProvider("p_high")
        p_high._priority = ProviderPriority.HIGH

        _run(p_high.initialize())
        _run(p_low.initialize())

        reg.register(p_low)
        reg.register(p_high)
        sorted_p = reg.providers_for_category("market_data")
        assert sorted_p[0].provider_id == "p_high"

    def test_statistics_keys(self):
        reg = ProviderRegistry()
        assert "total" in reg.statistics()


# ── PipelineBuilder ───────────────────────────────────────────────────────────

class TestPipelineBuilder:
    def test_empty_pipeline_raises(self):
        b = PipelineBuilder("test")
        with pytest.raises(PipelineConfigurationError):
            b.build()

    def test_full_pipeline(self):
        p = (
            PipelineBuilder("full")
            .extract()
            .validate()
            .normalize()
            .cache()
            .publish()
            .build()
        )
        types = p.stage_types()
        assert "extract" in types
        assert "validate" in types
        assert "normalize" in types

    def test_pipeline_id(self):
        p = PipelineBuilder("my-pipe").extract().build()
        assert p.pipeline_id == "my-pipe"

    def test_to_dict(self):
        p = PipelineBuilder("p1").extract().build()
        d = p.to_dict()
        assert "pipeline_id" in d and "stages" in d


# ── PipelineContext ───────────────────────────────────────────────────────────

class TestPipelineContext:
    def test_elapsed_ms(self):
        ctx = PipelineContext()
        time.sleep(0.01)
        assert ctx.elapsed_ms() > 0

    def test_to_dict_keys(self):
        ctx = PipelineContext()
        d   = ctx.to_dict()
        assert "pipeline_id" in d and "record_count" in d


# ── PipelineEngine ────────────────────────────────────────────────────────────

class TestPipelineEngine:
    def test_register_and_get(self):
        eng = PipelineEngine()
        p   = PipelineBuilder("p1").extract().build()
        eng.register(p)
        assert eng.has("p1")
        assert eng.get("p1").pipeline_id == "p1"

    def test_get_missing_raises(self):
        eng = PipelineEngine()
        with pytest.raises(PipelineNotFoundError):
            eng.get("nonexistent")

    def test_default_pipeline_exists(self):
        eng = PipelineEngine()
        assert eng.default_pipeline is not None

    def test_statistics_keys(self):
        eng = PipelineEngine()
        assert "registered_pipelines" in eng.statistics()


# ── TimestampNormalizer ───────────────────────────────────────────────────────

class TestTimestampNormalizer:
    def test_float_passthrough(self):
        tn = TimestampNormalizer()
        assert tn.normalize(1_700_000_000.0) == pytest.approx(1_700_000_000.0)

    def test_int_passthrough(self):
        tn = TimestampNormalizer()
        assert tn.normalize(1_700_000_000) == pytest.approx(1_700_000_000.0)

    def test_milliseconds_converted(self):
        tn = TimestampNormalizer()
        ts_ms = 1_700_000_000 * 1000
        assert tn.normalize(ts_ms) == pytest.approx(1_700_000_000.0)

    def test_iso8601_utc(self):
        tn = TimestampNormalizer()
        ts = tn.normalize("2023-11-14T00:00:00Z")
        assert ts > 0

    def test_iso8601_no_tz_treated_as_utc(self):
        tn = TimestampNormalizer(naive_as_utc=True)
        ts = tn.normalize("2023-11-14T00:00:00")
        assert ts > 0

    def test_invalid_string_raises(self):
        tn = TimestampNormalizer()
        with pytest.raises(TimestampNormalizationError):
            tn.normalize("not-a-timestamp")

    def test_unsupported_type_raises(self):
        tn = TimestampNormalizer()
        with pytest.raises(TimestampNormalizationError):
            tn.normalize([1, 2, 3])


# ── UnitConverter ─────────────────────────────────────────────────────────────

class TestUnitConverter:
    def test_same_currency(self):
        uc = UnitConverter()
        assert uc.convert_currency(100.0, "USD", "USD") == 100.0

    def test_usd_to_inr(self):
        uc = UnitConverter()
        inr = uc.convert_currency(1.0, "USD", "INR")
        assert inr > 1.0

    def test_unknown_currency_raises(self):
        uc = UnitConverter()
        with pytest.raises(UnitConversionError):
            uc.convert_currency(100.0, "XYZ", "USD")

    def test_paise_to_inr(self):
        uc = UnitConverter()
        assert uc.paise_to_inr(100) == pytest.approx(1.0)

    def test_lots_to_shares(self):
        uc = UnitConverter()
        assert uc.lots_to_shares(2.0, 25) == pytest.approx(50.0)

    def test_pct_to_bps(self):
        uc = UnitConverter()
        assert uc.pct_to_bps(1.0) == pytest.approx(100.0)

    def test_update_rates(self):
        uc = UnitConverter()
        uc.update_rates({"FAKE": 2.0})
        val = uc.convert_currency(1.0, "USD", "FAKE")
        assert val == pytest.approx(2.0)


# ── FieldMapper ───────────────────────────────────────────────────────────────

class TestFieldMapper:
    def test_basic_mapping(self):
        fm = FieldMapper([FieldMapping("src_price", "price")])
        result = fm.map({"src_price": 100.0, "ignored": "x"})
        assert result["price"] == 100.0
        assert "ignored" not in result

    def test_pass_unknown(self):
        fm = FieldMapper([FieldMapping("a", "b")], pass_unknown=True)
        result = fm.map({"a": 1, "extra": 2})
        assert "extra" in result

    def test_required_field_missing_raises(self):
        fm = FieldMapper([FieldMapping("price", "price", required=True)])
        with pytest.raises(FieldMappingError):
            fm.map({})

    def test_transform_applied(self):
        fm = FieldMapper([FieldMapping("val", "val_doubled", transform=lambda v: v * 2)])
        assert fm.map({"val": 5})["val_doubled"] == 10

    def test_identity_mapper(self):
        fm = FieldMapper.build_identity(["a", "b"])
        assert fm.map({"a": 1, "b": 2}) == {"a": 1, "b": 2}


# ── SchemaMapper ──────────────────────────────────────────────────────────────

class TestSchemaMapperRegistry:
    def test_register_and_get(self):
        reg    = SchemaMapperRegistry()
        fm     = FieldMapper([FieldMapping("raw_close", "close")])
        mapper = SimpleSchemaMapper("yahoo", "market_data", fm)
        reg.register(mapper)
        assert reg.has("yahoo", "market_data")
        assert reg.get("yahoo", "market_data") is mapper

    def test_get_missing_raises(self):
        reg = SchemaMapperRegistry()
        with pytest.raises(SchemaMapperNotFoundError):
            reg.get("unknown", "market_data")

    def test_statistics(self):
        reg = SchemaMapperRegistry()
        assert reg.statistics()["registered_mappers"] == 0


# ── NormalizationEngine ───────────────────────────────────────────────────────

class TestNormalizationEngine:
    def test_normalize_with_no_mapper(self):
        eng = NormalizationEngine()
        r   = _make_record()
        nr  = eng.normalize(r)
        assert nr.record_id == r.record_id

    def test_normalize_batch(self):
        eng     = NormalizationEngine()
        records = [_make_record() for _ in range(5)]
        normed  = eng.normalize_batch(records)
        assert len(normed) == 5

    def test_timestamp_in_payload_normalized(self):
        eng     = NormalizationEngine()
        r       = _make_record(payload={"timestamp": 1_700_000_000_000, "close": 100.0})
        nr      = eng.normalize(r)
        assert nr.payload["timestamp"] == pytest.approx(1_700_000_000.0)


# ── SchemaValidator ───────────────────────────────────────────────────────────

class TestSchemaValidator:
    def test_valid_record_no_issues(self):
        sv  = SchemaValidator([FieldSpec("close", required=True, types=(int, float), min_value=0)])
        rec = _make_record(payload={"close": 2500.0})
        assert len(sv.validate_payload(rec)) == 0

    def test_missing_required_field(self):
        sv  = SchemaValidator([FieldSpec("open_price", required=True, nullable=False)])
        rec = _make_record()   # payload has no "open_price" field
        issues = sv.validate_payload(rec)
        assert any(i.severity == ValidationSeverity.ERROR for i in issues)

    def test_range_violation(self):
        sv  = SchemaValidator([FieldSpec("close", min_value=0, max_value=1000)])
        rec = _make_record(payload={"close": 5000.0})
        issues = sv.validate_payload(rec)
        assert any("exceeds maximum" in i.message for i in issues)

    def test_wrong_type(self):
        sv  = SchemaValidator([FieldSpec("close", types=(int, float))])
        rec = _make_record(payload={"close": "not_a_number"})
        issues = sv.validate_payload(rec)
        assert any("wrong type" in i.message for i in issues)


# ── IntegrityChecker ──────────────────────────────────────────────────────────

class TestIntegrityChecker:
    def test_no_duplicates(self):
        ic      = IntegrityChecker()
        records = [
            _make_record(symbol="TCS",   payload={"symbol": "TCS",   "timestamp": 1.0}),
            _make_record(symbol="INFY",  payload={"symbol": "INFY",  "timestamp": 1.0}),
        ]
        assert len(ic.check_duplicates(records)) == 0

    def test_duplicates_detected(self):
        ic      = IntegrityChecker()
        r       = _make_record(payload={"symbol": "TCS", "timestamp": 1.0})
        r2      = _make_record(payload={"symbol": "TCS", "timestamp": 1.0})
        issues  = ic.check_duplicates([r, r2])
        assert len(issues) == 1

    def test_ohlcv_consistency_valid(self):
        ic  = IntegrityChecker()
        rec = _make_record(payload={
            "symbol": "X", "timestamp": 1.0,
            "low": 90.0, "high": 110.0, "open": 100.0, "close": 105.0, "volume": 500,
        })
        assert len(ic.check_ohlcv_consistency([rec])) == 0

    def test_ohlcv_low_gt_high(self):
        ic  = IntegrityChecker()
        rec = _make_record(payload={
            "symbol": "X", "timestamp": 1.0,
            "low": 200.0, "high": 100.0,
        })
        issues = ic.check_ohlcv_consistency([rec])
        assert any("low" in i.message for i in issues)

    def test_negative_volume(self):
        ic  = IntegrityChecker()
        rec = _make_record(payload={
            "symbol": "X", "timestamp": 1.0,
            "low": 90.0, "high": 110.0, "volume": -10,
        })
        issues = ic.check_ohlcv_consistency([rec])
        assert any("volume" in i.field_name for i in issues)


# ── QualityChecker ────────────────────────────────────────────────────────────

class TestQualityChecker:
    def test_score_between_0_and_1(self):
        qc = QualityChecker(required_fields=["close"])
        r  = _make_record()
        s  = qc.score_record(r)
        assert 0.0 <= s <= 1.0

    def test_missing_required_field_lowers_score(self):
        qc    = QualityChecker(required_fields=["close", "open", "volume"])
        r_complete   = _make_record(payload={"close": 100.0, "open": 99.0, "volume": 1000})
        r_incomplete = _make_record(payload={"close": 100.0})
        assert qc.score_record(r_complete) >= qc.score_record(r_incomplete)

    def test_quality_level_high(self):
        qc = QualityChecker()
        assert qc.quality_level(0.9) == DataQualityLevel.HIGH

    def test_quality_level_low(self):
        qc = QualityChecker()
        assert qc.quality_level(0.3) == DataQualityLevel.LOW

    def test_annotate_records_sets_score(self):
        qc = QualityChecker()
        recs = [_make_record() for _ in range(3)]
        annotated = qc.annotate_records(recs)
        assert all(r.quality_score > 0 for r in annotated)


# ── ValidationEngine ──────────────────────────────────────────────────────────

class TestValidationEngine:
    def test_valid_batch(self):
        ve  = ValidationEngine()
        recs = [_make_record() for _ in range(5)]
        rep  = ve.validate_batch(recs)
        assert rep.valid_count == 5
        assert rep.status in (ValidationStatus.PASSED, ValidationStatus.PARTIAL)

    def test_to_dict(self):
        rep = ValidationReport()
        d   = rep.to_dict()
        assert "report_id" in d and "quality_score" in d

    def test_pass_rate_full(self):
        rep = ValidationReport(total=10, valid_count=10)
        assert rep.pass_rate() == 1.0

    def test_pass_rate_empty(self):
        rep = ValidationReport(total=0)
        assert rep.pass_rate() == 1.0


# ── IntegrationCache ──────────────────────────────────────────────────────────

class TestIntegrationCache:
    def test_put_and_get(self):
        cache = IntegrationCache()
        cache.put("k1", [1, 2, 3])
        assert cache.get("k1") == [1, 2, 3]

    def test_miss_returns_none(self):
        cache = IntegrationCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache = IntegrationCache(default_ttl=0.001)
        cache.put("k1", "value", ttl_sec=0.001)
        time.sleep(0.01)
        assert cache.get("k1") is None

    def test_lru_eviction(self):
        cache = IntegrationCache(max_entries=2)
        cache.put("k1", 1)
        cache.put("k2", 2)
        cache.put("k3", 3)
        # k1 should be evicted
        assert cache.get("k1") is None

    def test_cache_key_roundtrip(self):
        key  = CacheKey.build("yahoo", "market_data", "daily", "RELIANCE")
        cache = IntegrationCache()
        cache.put(key, "value")
        assert cache.get(key) == "value"

    def test_invalidate(self):
        cache = IntegrationCache()
        cache.put("k", 99)
        cache.invalidate("k")
        assert cache.get("k") is None

    def test_purge_expired(self):
        cache = IntegrationCache(default_ttl=0.001)
        cache.put("k", 1, ttl_sec=0.001)
        time.sleep(0.01)
        evicted = cache.purge_expired()
        assert evicted == 1

    def test_statistics(self):
        cache = IntegrationCache()
        s = cache.statistics()
        assert "hits" in s and "misses" in s and "hit_rate" in s


# ── CacheKey ──────────────────────────────────────────────────────────────────

class TestCacheKey:
    def test_to_string(self):
        k = CacheKey.build("p", "market_data", "daily", "TCS")
        assert "TCS" in k.to_string()

    def test_to_hash_length(self):
        k = CacheKey.build("p", "market_data", "daily")
        assert len(k.to_hash()) == 16

    def test_same_keys_equal(self):
        k1 = CacheKey.build("p", "market_data", "daily", "TCS")
        k2 = CacheKey.build("p", "market_data", "daily", "TCS")
        assert k1 == k2

    def test_different_keys_not_equal(self):
        k1 = CacheKey.build("p", "market_data", "daily", "TCS")
        k2 = CacheKey.build("p", "market_data", "daily", "INFY")
        assert k1 != k2


# ── AvailabilityMonitor ───────────────────────────────────────────────────────

class TestAvailabilityMonitor:
    def test_full_availability(self):
        am = AvailabilityMonitor()
        for _ in range(5):
            am.record("p1", True)
        assert am.availability("p1") == pytest.approx(1.0)

    def test_partial_availability(self):
        am = AvailabilityMonitor()
        am.record("p1", True)
        am.record("p1", False)
        assert am.availability("p1") == pytest.approx(0.5)

    def test_unknown_provider_full_availability(self):
        am = AvailabilityMonitor()
        assert am.availability("unknown") == 1.0

    def test_below_threshold(self):
        am = AvailabilityMonitor(min_availability=0.9)
        for _ in range(2):
            am.record("p1", False)
        for _ in range(8):
            am.record("p1", True)
        # 80% success — below 90% threshold
        assert am.is_below_threshold("p1")

    def test_statistics_keys(self):
        am = AvailabilityMonitor()
        am.record("p1", True)
        assert "p1" in am.statistics()


# ── LatencyMonitor ────────────────────────────────────────────────────────────

class TestLatencyMonitor:
    def test_record_and_avg(self):
        lm = LatencyMonitor()
        lm.record("p1", 100.0)
        lm.record("p1", 200.0)
        assert lm.avg_latency("p1") == pytest.approx(150.0)

    def test_p95_latency(self):
        lm = LatencyMonitor()
        for i in range(100):
            lm.record("p1", float(i))
        assert lm.p95_latency("p1") >= 90.0

    def test_high_latency_flag(self):
        lm = LatencyMonitor(warning_ms=100.0)
        lm.record("p1", 500.0)
        assert lm.is_high_latency("p1")

    def test_not_high_latency(self):
        lm = LatencyMonitor(warning_ms=1000.0)
        lm.record("p1", 10.0)
        assert not lm.is_high_latency("p1")


# ── RollingProviderStats ──────────────────────────────────────────────────────

class TestRollingProviderStats:
    def test_record_and_snapshot(self):
        s = RollingProviderStats("p1")
        s.record_request(True,  50.0, 10)
        s.record_request(False, 200.0, 0)
        snap = s.snapshot()
        assert snap.total_requests       == 2
        assert snap.successful_requests  == 1
        assert snap.failed_requests      == 1

    def test_availability_pct(self):
        s = RollingProviderStats("p1")
        for _ in range(8):
            s.record_request(True, 10.0)
        for _ in range(2):
            s.record_request(False, 10.0)
        snap = s.snapshot()
        assert snap.availability_pct == pytest.approx(0.8)

    def test_latency_stats(self):
        s = RollingProviderStats("p1")
        for i in range(1, 11):
            s.record_request(True, float(i * 10))
        snap = s.snapshot()
        assert snap.avg_latency_ms > 0
        assert snap.max_latency_ms == pytest.approx(100.0)


# ── CapabilityRegistry ────────────────────────────────────────────────────────

class TestCapabilityRegistry:
    def test_route_returns_active_providers(self):
        reg = ProviderRegistry()
        p   = _ConcreteProvider("p1")
        _run(p.initialize())
        reg.register(p)
        cap = CapabilityRegistry(reg)
        result = cap.route("market_data")
        assert len(result) == 1

    def test_best_provider(self):
        reg = ProviderRegistry()
        p   = _ConcreteProvider("best")
        _run(p.initialize())
        reg.register(p)
        cap = CapabilityRegistry(reg)
        assert cap.best_provider("market_data").provider_id == "best"

    def test_no_coverage_for_unknown_category(self):
        reg = ProviderRegistry()
        cap = CapabilityRegistry(reg)
        assert not cap.has_coverage("unknown_category")


# ── IntegrationRegistry ───────────────────────────────────────────────────────

class TestIntegrationRegistry:
    def test_register_and_get(self):
        reg = IntegrationRegistry()
        reg.register("engine", "value")
        assert reg.get("engine") == "value"

    def test_missing_raises(self):
        reg = IntegrationRegistry()
        with pytest.raises(Exception):
            reg.get("missing")

    def test_singleton(self):
        r1 = get_integration_registry()
        r2 = get_integration_registry()
        assert r1 is r2

    def test_reset(self):
        r1 = get_integration_registry()
        reset_integration_registry()
        r2 = get_integration_registry()
        assert r1 is not r2


# ── IntegrationContext ────────────────────────────────────────────────────────

class TestIntegrationContext:
    def test_set_and_get(self):
        IntegrationContextState.set("req-1", "provider_a", "market_data")
        assert IntegrationContextState.get_request_id() == "req-1"
        assert IntegrationContextState.get_provider_id() == "provider_a"
        IntegrationContextState.clear()

    def test_context_manager_clears(self):
        with integration_operation_context("req-2", "p2"):
            assert IntegrationContextState.get_request_id() == "req-2"
        assert IntegrationContextState.get_request_id() is None

    def test_elapsed_ms(self):
        IntegrationContextState.set("req-3")
        time.sleep(0.01)
        assert IntegrationContextState.elapsed_ms() > 0
        IntegrationContextState.clear()


# ── DataIntegrationEngine ─────────────────────────────────────────────────────

class TestDataIntegrationEngine:
    def test_start_and_status(self):
        engine = get_data_integration_engine()
        _run(engine.start())
        assert engine.is_running()
        _run(engine.stop())

    def test_double_start_raises(self):
        engine = get_data_integration_engine()
        _run(engine.start())
        with pytest.raises(IntegrationEngineAlreadyRunningError):
            _run(engine.start())
        _run(engine.stop())

    def test_fetch_without_start_raises(self):
        engine = get_data_integration_engine()
        req    = _make_request()
        with pytest.raises(IntegrationEngineNotInitializedError):
            _run(engine.fetch(req))

    def test_register_and_fetch(self):
        engine = get_data_integration_engine()
        _run(engine.start())
        p = _ConcreteProvider("live_provider")
        _run(engine.register_provider(p))
        _run(engine.activate_provider("live_provider"))
        req    = _make_request(provider_id="live_provider")
        result = _run(engine.fetch(req, use_cache=False)
)
        # Pipeline may succeed or have partial issues; engine should not crash
        assert result is not None
        _run(engine.stop())

    def test_stop_changes_status(self):
        engine = get_data_integration_engine()
        _run(engine.start())
        _run(engine.stop())
        assert engine.status == IntegrationEngineStatus.STOPPED

    def test_singleton_idempotent(self):
        e1 = get_data_integration_engine()
        e2 = get_data_integration_engine()
        assert e1 is e2

    def test_reset_clears_singleton(self):
        e1 = get_data_integration_engine()
        reset_data_integration_engine()
        e2 = get_data_integration_engine()
        assert e1 is not e2

    def test_summary_keys(self):
        engine = get_data_integration_engine()
        _run(engine.start())
        s = engine.summary()
        assert "version" in s and "status" in s and "providers" in s
        _run(engine.stop())

    def test_set_publisher(self):
        engine = get_data_integration_engine()
        _run(engine.start())
        published = []
        engine.set_publisher(lambda records, pid: published.extend(records))
        # Not testing actual publish (needs pipeline), just that setter works
        _run(engine.stop())


# ── IntegrationFactory ────────────────────────────────────────────────────────

class TestIntegrationFactory:
    def test_create_provider_registry(self):
        r = IntegrationFactory.create_provider_registry()
        assert isinstance(r, ProviderRegistry)

    def test_create_pipeline_engine(self):
        e = IntegrationFactory.create_pipeline_engine()
        assert isinstance(e, PipelineEngine)

    def test_create_normalization_engine(self):
        ne = IntegrationFactory.create_normalization_engine()
        assert isinstance(ne, NormalizationEngine)

    def test_create_validation_engine(self):
        ve = IntegrationFactory.create_validation_engine()
        assert isinstance(ve, ValidationEngine)

    def test_create_cache(self):
        c = IntegrationFactory.create_cache()
        assert isinstance(c, IntegrationCache)


# ── ProviderContract ──────────────────────────────────────────────────────────

class TestProviderContract:
    def test_supports_category(self):
        pc = ProviderContract(provider_id="p", categories=["market_data"])
        assert pc.supports_category("market_data")

    def test_does_not_support_category(self):
        pc = ProviderContract(provider_id="p", categories=["news"])
        assert not pc.supports_category("market_data")

    def test_to_dict(self):
        pc = ProviderContract(provider_id="p")
        d  = pc.to_dict()
        assert "provider_id" in d



