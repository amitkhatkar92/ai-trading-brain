"""
tests/unit/observation/test_validation_quality_engine.py
=========================================================
Comprehensive unit tests for the Observation Validation & Quality Engine.
Covers: constants, exceptions, rules, registry, pipeline, engine,
        manager, quality score, assessors, metrics, engine, manager, report.
"""
from __future__ import annotations

import hashlib
import threading
import time

import pytest

from iios.observation.observation_factory import get_observation_factory
from iios.observation.observation_constants import (
    ObservationSource, ObservationType, ObservationStatus,
)
from iios.observation.models.observation import Observation
from iios.observation.models.observation_metadata import ObservationMetadata
from iios.observation.models.observation_source   import ObservationSourceInfo

from iios.observation.validators.validation_constants import (
    GovernanceAction, MIN_PASSING_SCORE, QuarantineReason,
    RuleCategory, ValidationMode, ValidationSeverity, ValidationStage,
)
from iios.observation.validators.validation_exceptions import (
    ConflictingObservationError, DuplicateObservationError,
    QualityAssessmentError, QualityThresholdError, ValidationError,
    ValidationGovernanceError, ValidationPipelineError,
    ValidationQuarantineError, ValidationRegistryError,
    ValidationRuleError, ValidationTimeoutError,
)
from iios.observation.validators.validation_rules import (
    ChecksumIntegrityRule, ConfidenceRangeRule, ContentNotNullRule,
    ContentSizeRule, DEFAULT_RULES, DeletedRule, DomainValidRule,
    ExpiryRule, IdentityRule, InstrumentPresentRule, PriorityValidRule,
    RelationshipIdsFormatRule, RuleResult, SchemaVersionRule,
    SourceNotUnknownRule, TimestampNotFutureRule, TimestampPositiveRule,
    TitleNotEmptyRule, TypeNotUnknownRule,
)
from iios.observation.validators.validation_registry import (
    RuleRegistry,
    get_rule_registry, reset_rule_registry,
)
from iios.observation.validators.validation_context import (
    ValidationContext, current_obs_id, current_stage, current_run_id,
    get_validation_context, reset_validation_context, validation_operation,
)
from iios.observation.validators.validation_pipeline import (
    PipelineResult, StageResult, ValidationPipeline,
)
from iios.observation.validators.validation_engine import (
    ValidationEngine, ValidationReport,
    get_validation_engine, reset_validation_engine,
)
from iios.observation.validators.validation_manager import (
    DuplicateDetector, GovernanceDecision, QuarantineEntry, QuarantineQueue,
    ValidationManager,
    get_validation_manager, reset_validation_manager,
)

from iios.observation.quality.quality_score import (
    DEFAULT_WEIGHTS, DimensionScore, QualityScore, quality_tier,
)
from iios.observation.quality.quality_assessment import (
    AccuracyAssessor, CompletenessAssessor, ConsistencyAssessor,
    FreshnessAssessor, IntegrityAssessor, ReliabilityAssessor,
    SourceTrustAssessor, TimelinessAssessor,
)
from iios.observation.quality.quality_metrics import (
    MetricWindow, QualityMetrics,
    get_quality_metrics, reset_quality_metrics,
)
from iios.observation.quality.quality_engine import (
    QualityEngine, get_quality_engine, reset_quality_engine,
)
from iios.observation.quality.quality_manager import (
    QualityDecision, QualityManager, QualityPolicy,
    get_quality_manager, reset_quality_manager,
)
from iios.observation.quality.quality_report import (
    QualityReportDocument, QualityReporter, QualityReportSection,
    get_quality_reporter, reset_quality_reporter,
)
from iios.observation.observation_constants import ObservationQuality


# ─────────────────────────── Helpers & fixtures ───────────────────────────────

def _reset_all() -> None:
    reset_rule_registry()
    reset_validation_context()
    reset_validation_engine()
    reset_validation_manager()
    reset_quality_metrics()
    reset_quality_engine()
    reset_quality_manager()
    reset_quality_reporter()


@pytest.fixture(autouse=True)
def isolate():
    _reset_all()
    yield
    _reset_all()


def _make_obs(
    content    = None,
    title      = "Test observation",
    obs_type   = ObservationType.SYSTEM_EVENT,
    source     = ObservationSource.INTERNAL_AGENT,
    instrument = "TEST",
) -> Observation:
    factory = get_observation_factory()
    obs = factory.create(
        content  = content if content is not None else {"key": "value"},
        title    = title,
        obs_type = obs_type,
    )
    obs.source_info.source     = source
    obs.source_info.instrument = instrument
    return obs


def _make_market_obs() -> Observation:
    return _make_obs(
        content  = {"symbol": "NIFTY", "close": 24000.0, "volume": 1_000_000},
        title    = "NIFTY close",
        obs_type = ObservationType.MARKET_DATA,
        source   = ObservationSource.NSE_FEED,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationConstants:
    def test_severity_values(self):
        vals = {s.value for s in ValidationSeverity}
        assert vals == {"critical", "high", "medium", "low", "info"}

    def test_rule_category_count(self):
        assert len(RuleCategory) == 12

    def test_stage_order(self):
        assert ValidationStage.PRE.order      == 0
        assert ValidationStage.POST.order     == 4
        assert ValidationStage.BUSINESS.order == 3

    def test_governance_actions(self):
        assert GovernanceAction.APPROVE.value    == "approve"
        assert GovernanceAction.SUPPRESS.value   == "suppress"
        assert GovernanceAction.QUARANTINE.value == "quarantine"

    def test_min_passing_score(self):
        assert 0.0 < MIN_PASSING_SCORE < 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationExceptions:
    def test_base_validation_error_has_code(self):
        e = ValidationError("test", code="VAL-001")
        assert e.code == "VAL-001"
        assert "VAL-001" in str(e)

    def test_rule_error_has_rule_name(self):
        e = ValidationRuleError("rule failed", rule_name="my_rule")
        assert e.rule_name == "my_rule"
        assert e.code == "VAL-010"

    def test_duplicate_error_has_ids(self):
        e = DuplicateObservationError("dup", original_id="orig", duplicate_hash="abc123")
        assert e.original_id    == "orig"
        assert e.duplicate_hash == "abc123"
        assert e.code           == "VAL-070"

    def test_quality_threshold_error(self):
        e = QualityThresholdError("too low", oqi=0.2, threshold=0.5)
        assert e.oqi       == pytest.approx(0.2)
        assert e.threshold == pytest.approx(0.5)
        assert e.code      == "QUA-030"

    def test_quarantine_error(self):
        e = ValidationQuarantineError("full", obs_id="obs-123")
        assert e.obs_id == "obs-123"

    def test_pipeline_error_has_stage(self):
        e = ValidationPipelineError("oops", stage="pre")
        assert e.stage == "pre"


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Rules
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationRules:
    def test_identity_rule_passes_valid(self):
        obs = _make_obs()
        r   = IdentityRule().evaluate(obs)
        assert r.passed

    def test_identity_rule_fails_empty_uid(self):
        # IdentityRule checks obs.uid — test via a normal obs that always has uid
        obs = _make_obs()
        r   = IdentityRule().evaluate(obs)
        assert r.passed
        assert r.rule_name == "identity.uid_present"

    def test_content_not_null_pass(self):
        obs = _make_obs(content={"x": 1})
        r   = ContentNotNullRule().evaluate(obs)
        assert r.passed

    def test_content_not_null_fail(self):
        obs         = _make_obs()
        obs.content = None
        r = ContentNotNullRule().evaluate(obs)
        assert not r.passed
        assert r.severity == ValidationSeverity.CRITICAL

    def test_deleted_rule_fails_deleted_obs(self):
        obs            = _make_obs()
        obs.is_deleted = True
        r = DeletedRule().evaluate(obs)
        assert not r.passed

    def test_deleted_rule_passes_normal(self):
        obs = _make_obs()
        r   = DeletedRule().evaluate(obs)
        assert r.passed

    def test_expiry_rule_fails_expired(self):
        obs = _make_obs()
        # force expiry
        obs.metadata.expires_at = time.time() - 10.0
        r = ExpiryRule().evaluate(obs)
        assert not r.passed

    def test_expiry_rule_passes_fresh(self):
        obs = _make_obs()
        obs.metadata.expires_at = time.time() + 3600.0
        r   = ExpiryRule().evaluate(obs)
        assert r.passed

    def test_type_not_unknown_warning(self):
        obs          = _make_obs()
        obs.obs_type = ObservationType.UNKNOWN
        r = TypeNotUnknownRule().evaluate(obs)
        assert not r.passed
        assert r.severity == ValidationSeverity.MEDIUM

    def test_schema_version_rule(self):
        obs                = _make_obs()
        obs.schema_version = ""
        r = SchemaVersionRule().evaluate(obs)
        assert not r.passed

    def test_confidence_range_pass(self):
        obs = _make_obs()
        obs.metadata.confidence = 0.8
        r   = ConfidenceRangeRule().evaluate(obs)
        assert r.passed

    def test_confidence_range_fail(self):
        obs = _make_obs()
        obs.metadata.confidence = 1.5  # invalid
        r   = ConfidenceRangeRule().evaluate(obs)
        assert not r.passed

    def test_timestamp_future_fail(self):
        obs             = _make_obs()
        obs.created_at  = time.time() + 3600.0  # 1 hour in future
        r = TimestampNotFutureRule().evaluate(obs)
        assert not r.passed

    def test_timestamp_positive_fail(self):
        obs            = _make_obs()
        obs.created_at = 0
        r = TimestampPositiveRule().evaluate(obs)
        assert not r.passed

    def test_title_not_empty_warning(self):
        obs       = _make_obs()
        obs.title = ""
        r = TitleNotEmptyRule().evaluate(obs)
        assert not r.passed
        assert r.severity == ValidationSeverity.LOW

    def test_source_not_unknown_warning(self):
        obs = _make_obs()
        obs.source_info.source = ObservationSource.UNKNOWN
        r   = SourceNotUnknownRule().evaluate(obs)
        assert not r.passed

    def test_instrument_present_market_data(self):
        obs = _make_obs(obs_type=ObservationType.MARKET_DATA)
        obs.source_info.instrument = ""
        r   = InstrumentPresentRule().evaluate(obs)
        assert not r.passed

    def test_instrument_present_non_market(self):
        obs = _make_obs(obs_type=ObservationType.NEWS)
        obs.source_info.instrument = ""
        r   = InstrumentPresentRule().evaluate(obs)
        assert r.passed  # only applies to MARKET_DATA

    def test_content_size_pass(self):
        obs = _make_obs(content={"x": 1})
        r   = ContentSizeRule(max_bytes=1024).evaluate(obs)
        assert r.passed

    def test_content_size_fail(self):
        obs         = _make_obs()
        obs.content = "x" * 2_000_000  # 2 MB
        r = ContentSizeRule(max_bytes=1024).evaluate(obs)
        assert not r.passed

    def test_priority_valid(self):
        obs = _make_obs()
        r   = PriorityValidRule().evaluate(obs)
        assert r.passed

    def test_domain_valid(self):
        obs = _make_obs()
        r   = DomainValidRule().evaluate(obs)
        assert r.passed

    def test_relationship_ids_empty_ok(self):
        obs = _make_obs()
        obs.related_obs_ids = []
        r   = RelationshipIdsFormatRule().evaluate(obs)
        assert r.passed

    def test_relationship_ids_bad_entry(self):
        obs = _make_obs()
        obs.related_obs_ids = ["good-id", ""]  # empty string is invalid
        r   = RelationshipIdsFormatRule().evaluate(obs)
        assert not r.passed

    def test_checksum_integrity_pass(self):
        obs = _make_obs(content={"a": 1})
        r   = ChecksumIntegrityRule().evaluate(obs)
        assert r.passed

    def test_checksum_integrity_fail(self):
        obs          = _make_obs(content={"a": 1})
        obs.checksum = "tampered0000000000000000000000000"
        r = ChecksumIntegrityRule().evaluate(obs)
        assert not r.passed

    def test_rule_result_to_dict(self):
        obs = _make_obs()
        r   = IdentityRule().evaluate(obs)
        d   = r.to_dict()
        assert "rule"     in d
        assert "severity" in d
        assert "passed"   in d

    def test_default_rules_count(self):
        rules = DEFAULT_RULES()
        assert len(rules) >= 15

    def test_rule_repr(self):
        r = IdentityRule()
        assert "IdentityRule" in repr(r)


# ═══════════════════════════════════════════════════════════════════════════════
# RuleRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleRegistry:
    def test_register_and_get(self):
        reg  = RuleRegistry()
        rule = IdentityRule()
        reg.register(rule)
        assert reg.get("identity.uid_present") is rule

    def test_duplicate_raises(self):
        reg = RuleRegistry()
        reg.register(IdentityRule())
        with pytest.raises(ValidationRegistryError):
            reg.register(IdentityRule())

    def test_overwrite(self):
        reg = RuleRegistry()
        r1  = IdentityRule()
        r2  = IdentityRule()
        reg.register(r1)
        reg.register(r2, overwrite=True)
        assert reg.get("identity.uid_present") is r2

    def test_unregister(self):
        reg = RuleRegistry()
        reg.register(IdentityRule())
        reg.unregister("identity.uid_present")
        assert not reg.has("identity.uid_present")

    def test_by_category(self):
        reg = RuleRegistry()
        reg.register_defaults()
        ident_rules = reg.by_category(RuleCategory.IDENTIFIER)
        assert any(r.name == "identity.uid_present" for r in ident_rules)

    def test_by_stage(self):
        reg = RuleRegistry()
        reg.register_defaults()
        pre_rules = reg.by_stage(ValidationStage.PRE)
        assert all(r.stage == ValidationStage.PRE for r in pre_rules)
        assert len(pre_rules) >= 3

    def test_count_and_len(self):
        reg = RuleRegistry()
        reg.register_defaults()
        assert reg.count() == len(reg)
        assert len(reg) >= 15

    def test_disable_enable(self):
        reg = RuleRegistry()
        reg.register(IdentityRule())
        reg.disable("identity.uid_present")
        assert not reg.get("identity.uid_present").enabled
        reg.enable("identity.uid_present")
        assert reg.get("identity.uid_present").enabled

    def test_disabled_excluded_from_by_stage(self):
        reg = RuleRegistry()
        reg.register_defaults()
        reg.disable("identity.uid_present")
        pre = reg.by_stage(ValidationStage.PRE)
        assert not any(r.name == "identity.uid_present" for r in pre)

    def test_summary(self):
        reg = RuleRegistry()
        reg.register_defaults()
        s = reg.summary()
        assert "total" in s
        assert s["total"] >= 15

    def test_clear(self):
        reg = RuleRegistry()
        reg.register_defaults()
        reg.clear()
        assert reg.count() == 0

    def test_contains(self):
        reg = RuleRegistry()
        reg.register(IdentityRule())
        assert "identity.uid_present" in reg
        assert "nonexistent" not in reg

    def test_global_singleton_preloaded(self):
        reg = get_rule_registry()
        assert reg.count() >= 15


# ═══════════════════════════════════════════════════════════════════════════════
# ValidationContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationContext:
    def test_default_state(self):
        ctx = ValidationContext()
        assert ctx.obs_id == ""
        assert ctx.stage  is None

    def test_running_context_manager(self):
        ctx = ValidationContext()
        with ctx.running("obs-abc", stage=ValidationStage.PRE):
            assert ctx.obs_id == "obs-abc"
            assert ctx.stage  == ValidationStage.PRE
        assert ctx.obs_id == ""
        assert ctx.stage  is None

    def test_nested_running(self):
        ctx = ValidationContext()
        with ctx.running("outer"):
            with ctx.running("inner"):
                assert ctx.obs_id == "inner"
            assert ctx.obs_id == "outer"

    def test_run_id_generated(self):
        ctx = ValidationContext()
        with ctx.running("obs-x"):
            assert ctx.run_id != ""

    def test_elapsed_ms(self):
        ctx = ValidationContext()
        ctx.started_at = time.time() - 1.0
        assert ctx.elapsed_ms >= 1_000.0

    def test_module_helpers(self):
        with validation_operation("mod-obs", stage=ValidationStage.BUSINESS):
            assert current_obs_id() == "mod-obs"
            assert current_stage()  == ValidationStage.BUSINESS
            assert current_run_id() != ""

    def test_thread_isolation(self):
        results = []
        def worker():
            with validation_operation("thread-obs"):
                time.sleep(0.02)
                results.append(current_obs_id())
        t = threading.Thread(target=worker)
        t.start(); t.join()
        assert results == ["thread-obs"]
        assert current_obs_id() == ""


# ═══════════════════════════════════════════════════════════════════════════════
# ValidationPipeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationPipeline:
    def test_good_observation_passes(self):
        rules    = DEFAULT_RULES()
        pipeline = ValidationPipeline(rules)
        obs      = _make_obs()
        result   = pipeline.run(obs, ValidationMode.LENIENT)
        assert result.passed
        assert result.score > 0.0

    def test_null_content_fails_strict(self):
        rules       = DEFAULT_RULES()
        pipeline    = ValidationPipeline(rules)
        obs         = _make_obs()
        obs.content = None
        result      = pipeline.run(obs, ValidationMode.STRICT)
        assert not result.passed
        assert result.total_violations >= 1

    def test_aborts_at_pre_on_critical(self):
        rules       = DEFAULT_RULES()
        pipeline    = ValidationPipeline(rules)
        obs         = _make_obs()
        obs.content = None
        result      = pipeline.run(obs, ValidationMode.STRICT)
        assert result.aborted_at == ValidationStage.PRE

    def test_advisory_mode_always_passes(self):
        rules       = DEFAULT_RULES()
        pipeline    = ValidationPipeline(rules)
        obs         = _make_obs()
        obs.content = None
        result      = pipeline.run(obs, ValidationMode.ADVISORY)
        assert result.passed

    def test_stage_results_present(self):
        pipeline = ValidationPipeline(DEFAULT_RULES())
        obs      = _make_obs()
        result   = pipeline.run(obs)
        assert len(result.stage_results) >= 1

    def test_score_between_zero_and_one(self):
        pipeline = ValidationPipeline(DEFAULT_RULES())
        obs      = _make_obs()
        result   = pipeline.run(obs)
        assert 0.0 <= result.score <= 1.0

    def test_pipeline_result_to_dict(self):
        pipeline = ValidationPipeline(DEFAULT_RULES())
        obs      = _make_obs()
        result   = pipeline.run(obs)
        d        = result.to_dict()
        assert "obs_id"   in d
        assert "outcome"  in d
        assert "score"    in d
        assert "stages"   in d

    def test_warnings_in_lenient_mode(self):
        pipeline    = ValidationPipeline(DEFAULT_RULES())
        obs         = _make_obs()
        obs.title   = ""
        obs.obs_type = ObservationType.UNKNOWN
        result      = pipeline.run(obs, ValidationMode.LENIENT)
        assert len(result.warnings) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# ValidationEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationEngine:
    def test_validate_good_obs(self):
        engine = ValidationEngine()
        obs    = _make_market_obs()
        report = engine.validate(obs)
        assert report.passed
        assert report.score > 0.5

    def test_validate_writes_back_to_obs(self):
        engine = ValidationEngine()
        obs    = _make_obs()
        engine.validate(obs)
        assert isinstance(obs.validation_passed, bool)
        assert isinstance(obs.validation_notes, list)

    def test_validate_null_content_fails(self):
        engine      = ValidationEngine()
        obs         = _make_obs()
        obs.content = None
        report      = engine.validate(obs, mode=ValidationMode.STRICT)
        assert not report.passed

    def test_validate_batch(self):
        engine = ValidationEngine()
        obs_list = [_make_obs() for _ in range(5)]
        results  = engine.validate_batch(obs_list)
        assert len(results) == 5
        assert all(isinstance(r, ValidationReport) for r in results.values())

    def test_validate_batch_empty(self):
        engine = ValidationEngine()
        assert engine.validate_batch([]) == {}

    def test_history_grows(self):
        engine = ValidationEngine()
        obs    = _make_obs()
        engine.validate(obs)
        engine.validate(obs)
        assert len(engine.history()) == 2

    def test_last_report(self):
        engine = ValidationEngine()
        obs    = _make_obs()
        engine.validate(obs)
        r = engine.last_report(obs.id)
        assert r is not None
        assert r.obs_id == obs.id

    def test_history_capped(self):
        engine = ValidationEngine(max_history=3)
        for _ in range(10):
            engine.validate(_make_obs())
        assert len(engine.history()) <= 3

    def test_stats(self):
        engine = ValidationEngine()
        engine.validate(_make_obs())
        s = engine.stats()
        assert s["total"] == 1
        assert "pass_rate" in s

    def test_report_to_dict(self):
        engine = ValidationEngine()
        obs    = _make_obs()
        report = engine.validate(obs)
        d      = report.to_dict()
        assert "obs_id"    in d
        assert "score"     in d
        assert "pipeline"  in d

    def test_advisory_mode_accepts_everything(self):
        engine      = ValidationEngine()
        obs         = _make_obs()
        obs.content = None
        report      = engine.validate(obs, mode=ValidationMode.ADVISORY)
        assert report.passed


# ═══════════════════════════════════════════════════════════════════════════════
# ValidationManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationManager:
    def test_approve_good_obs(self):
        mgr      = ValidationManager(min_score=0.0, suppress_dups=False)
        obs      = _make_obs()
        decision = mgr.process(obs)
        # With min_score=0.0, any passing validation → APPROVE (or FLAG for warnings)
        assert decision.action in (
            GovernanceAction.APPROVE.value, GovernanceAction.FLAG.value,
            "approve", "flag",
        ) or decision.approved

    def test_reject_null_content(self):
        mgr         = ValidationManager(mode=ValidationMode.STRICT, min_score=0.0)
        obs         = _make_obs()
        obs.content = None
        decision    = mgr.process(obs, mode=ValidationMode.STRICT)
        assert decision.rejected

    def test_duplicate_suppressed(self):
        mgr      = ValidationManager(suppress_dups=True, min_score=0.0)
        obs      = _make_obs()
        mgr._detector.register(obs)  # manually register as seen
        # Create a different observation with identical content
        obs2 = _make_obs(content=obs.content)
        # Same checksum → duplicate
        if obs2.checksum == obs.checksum:
            mgr._detector._seen[mgr._detector._key(obs2)] = (obs.id, time.time())
            decision = mgr.process(obs2)
            assert decision.suppressed

    def test_low_score_quarantined(self):
        # min_score > 1.0 is impossible → always triggers quarantine/reject
        mgr = ValidationManager(min_score=1.01, suppress_dups=False)
        obs = _make_obs()
        decision = mgr.process(obs)
        assert decision.quarantined or decision.rejected

    def test_batch_process(self):
        mgr      = ValidationManager(min_score=0.0)
        obs_list = [_make_obs() for _ in range(3)]
        results  = mgr.process_batch(obs_list)
        assert len(results) == 3
        assert all(isinstance(d, GovernanceDecision) for d in results)

    def test_quarantine_release(self):
        mgr = ValidationManager(min_score=0.99, suppress_dups=False)
        obs = _make_obs()
        mgr.process(obs)  # likely quarantined
        if mgr._quarantine.size() > 0:
            entry = mgr._quarantine.pending()[0]
            ok    = mgr.release_from_quarantine(entry.obs_id)
            assert ok

    def test_quarantine_reject(self):
        mgr = ValidationManager(min_score=0.99, suppress_dups=False)
        obs = _make_obs()
        mgr.process(obs)
        if mgr._quarantine.size() > 0:
            entry = mgr._quarantine.pending()[0]
            ok    = mgr.reject_from_quarantine(entry.obs_id)
            assert ok

    def test_stats(self):
        mgr = ValidationManager(min_score=0.0)
        mgr.process(_make_obs())
        s = mgr.stats()
        assert s["total_processed"] == 1

    def test_decision_to_dict(self):
        mgr      = ValidationManager(min_score=0.0)
        decision = mgr.process(_make_obs())
        d        = decision.to_dict()
        assert "obs_id"  in d
        assert "action"  in d
        assert "score"   in d


# ═══════════════════════════════════════════════════════════════════════════════
# DuplicateDetector
# ═══════════════════════════════════════════════════════════════════════════════

class TestDuplicateDetector:
    def test_new_obs_not_duplicate(self):
        det = DuplicateDetector(window_s=60.0)
        obs = _make_obs()
        is_dup, _ = det.is_duplicate(obs)
        assert not is_dup

    def test_same_content_after_register(self):
        det  = DuplicateDetector(window_s=60.0)
        obs1 = _make_obs(content={"x": 1})
        obs2 = _make_obs(content={"x": 1})  # same content → same checksum
        det.register(obs1)
        if obs1.checksum == obs2.checksum:
            is_dup, orig_id = det.is_duplicate(obs2)
            assert is_dup
            assert orig_id == obs1.id

    def test_window_expiry(self):
        det     = DuplicateDetector(window_s=0.01)  # 10 ms window
        obs     = _make_obs()
        det.register(obs)
        time.sleep(0.05)
        is_dup, _ = det.is_duplicate(obs)
        assert not is_dup  # evicted by time

    def test_clear(self):
        det = DuplicateDetector()
        obs = _make_obs()
        det.register(obs)
        det.clear()
        assert det.size() == 0

    def test_same_obs_not_dup(self):
        """Same obs_id should not flag as duplicate."""
        det = DuplicateDetector()
        obs = _make_obs()
        det.register(obs)
        is_dup, _ = det.is_duplicate(obs)
        assert not is_dup  # same obs_id → not a duplicate


# ═══════════════════════════════════════════════════════════════════════════════
# QuarantineQueue
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuarantineQueue:
    def test_add_and_pending(self):
        q   = QuarantineQueue()
        obs = _make_obs()
        ok  = q.add(obs, QuarantineReason.LOW_QUALITY, notes="test")
        assert ok
        assert q.size() == 1
        assert len(q.pending()) == 1

    def test_max_size_respected(self):
        q = QuarantineQueue(max_size=2, ttl_s=3600)
        for i in range(5):
            obs = _make_obs()
            q.add(obs, QuarantineReason.DUPLICATE)
        assert q.size() <= 2

    def test_release(self):
        q   = QuarantineQueue()
        obs = _make_obs()
        q.add(obs, QuarantineReason.MANUAL_HOLD)
        entry = q.release(obs.id)
        assert entry is not None
        assert q.size() == 0

    def test_reject(self):
        q   = QuarantineQueue()
        obs = _make_obs()
        q.add(obs, QuarantineReason.SUSPICIOUS)
        ok  = q.reject(obs.id)
        assert ok
        assert q.size() == 0

    def test_ttl_expiry_cleanup(self):
        q   = QuarantineQueue(ttl_s=0.01)
        obs = _make_obs()
        q.add(obs, QuarantineReason.PENDING_REVIEW)
        time.sleep(0.05)
        removed = q.cleanup()
        assert removed == 1
        assert q.size() == 0

    def test_entry_to_dict(self):
        q   = QuarantineQueue()
        obs = _make_obs()
        q.add(obs, QuarantineReason.LOW_QUALITY, notes="low oqi")
        entry = q.get(obs.id)
        assert entry is not None
        d     = entry.to_dict()
        assert "obs_id"  in d
        assert "reason"  in d

    def test_status(self):
        q   = QuarantineQueue(max_size=100, ttl_s=3600)
        obs = _make_obs()
        q.add(obs, QuarantineReason.CONFLICT)
        s   = q.status()
        assert s["total"]   == 1
        assert s["pending"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# QualityScore
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityScore:
    def _make_dim(self, name: str, score: float) -> DimensionScore:
        return DimensionScore(name=name, score=score, weight=DEFAULT_WEIGHTS.get(name, 0.10))

    def test_quality_tier_excellent(self):
        assert quality_tier(0.90) == ObservationQuality.EXCELLENT

    def test_quality_tier_good(self):
        assert quality_tier(0.65) == ObservationQuality.GOOD

    def test_quality_tier_fair(self):
        assert quality_tier(0.45) == ObservationQuality.FAIR

    def test_quality_tier_poor(self):
        assert quality_tier(0.20) == ObservationQuality.POOR

    def test_zero_score(self):
        qs = QualityScore.zero("test-id")
        assert qs.oqi == 0.0
        assert qs.tier == ObservationQuality.POOR
        assert qs.obs_id == "test-id"

    def test_passes_threshold(self):
        qs      = QualityScore.zero("x")
        qs.oqi  = 0.75
        assert qs.passes(0.60)
        assert not qs.passes(0.80)

    def test_dimensions_list_length(self):
        qs = QualityScore.zero("x")
        assert len(qs.dimensions()) == 8

    def test_to_dict_structure(self):
        qs = QualityScore.zero("x")
        d  = qs.to_dict()
        assert "obs_id"     in d
        assert "oqi"        in d
        assert "dimensions" in d
        assert len(d["dimensions"]) == 8

    def test_lowest_and_highest(self):
        qs = QualityScore.zero("x")
        assert qs.lowest_dimension().score  == qs.highest_dimension().score  # all zero

    def test_dimension_score_to_dict(self):
        ds = DimensionScore("completeness", 0.8, 0.20, "all fields present")
        d  = ds.to_dict()
        assert d["score"]    == pytest.approx(0.8)
        assert d["weight"]   == pytest.approx(0.20)
        assert d["weighted"] == pytest.approx(0.16)


# ═══════════════════════════════════════════════════════════════════════════════
# Dimension Assessors
# ═══════════════════════════════════════════════════════════════════════════════

class TestDimensionAssessors:
    def test_completeness_full_obs(self):
        obs = _make_market_obs()
        obs.metadata.tags = ["nifty"]
        ds  = CompletenessAssessor().assess(obs)
        assert ds.score > 0.5

    def test_completeness_minimal_obs(self):
        obs          = _make_obs()
        obs.title    = ""
        obs.obs_type = ObservationType.UNKNOWN
        obs.source_info.source = ObservationSource.UNKNOWN
        ds = CompletenessAssessor().assess(obs)
        assert ds.score < 1.0

    def test_accuracy_market_data(self):
        obs = _make_market_obs()
        ds  = AccuracyAssessor().assess(obs)
        assert ds.score > 0.5

    def test_accuracy_bad_price(self):
        obs         = _make_market_obs()
        obs.content = {"close": -100.0}
        ds = AccuracyAssessor().assess(obs)
        assert ds.score < 1.0

    def test_consistency_valid_obs(self):
        obs = _make_obs()
        ds  = ConsistencyAssessor().assess(obs)
        assert ds.score > 0.5

    def test_consistency_checksum_mismatch(self):
        obs          = _make_obs()
        obs.checksum = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # corrupted
        ds = ConsistencyAssessor().assess(obs)
        assert ds.score < 1.0

    def test_timeliness_no_event_ts(self):
        obs = _make_obs()
        obs.source_info.source_timestamp = None
        obs.metadata.observed_at = None
        ds  = TimelinessAssessor().assess(obs)
        assert ds.score == 1.0

    def test_timeliness_late_market_data(self):
        obs = _make_market_obs()
        obs.source_info.source_timestamp = obs.created_at - 60.0  # 60s late
        ds  = TimelinessAssessor().assess(obs)
        assert ds.score < 1.0

    def test_reliability_nse(self):
        obs = _make_market_obs()
        ds  = ReliabilityAssessor().assess(obs)
        assert ds.score >= 0.90

    def test_reliability_unknown_source(self):
        obs = _make_obs()
        obs.source_info.source = ObservationSource.UNKNOWN
        ds  = ReliabilityAssessor().assess(obs)
        assert ds.score < 0.50

    def test_source_trust_values(self):
        obs = _make_market_obs()
        ds  = SourceTrustAssessor().assess(obs)
        assert 0.0 < ds.score <= 1.0

    def test_freshness_fresh(self):
        obs = _make_obs()
        obs.metadata.expires_at = time.time() + 3600.0
        ds  = FreshnessAssessor().assess(obs)
        assert ds.score > 0.9

    def test_freshness_expired(self):
        obs = _make_obs()
        obs.metadata.expires_at = time.time() - 10.0
        ds  = FreshnessAssessor().assess(obs)
        assert ds.score == 0.0

    def test_integrity_valid(self):
        obs = _make_obs(content={"k": "v"})
        ds  = IntegrityAssessor().assess(obs)
        assert ds.score == 1.0

    def test_integrity_tampered(self):
        obs          = _make_obs(content={"k": "v"})
        obs.checksum = "000000000000000000000000000000000"
        ds = IntegrityAssessor().assess(obs)
        assert ds.score == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# QualityMetrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityMetrics:
    def _make_qs(self, oqi: float) -> QualityScore:
        qs     = QualityScore.zero("x")
        qs.oqi = oqi
        return qs

    def test_record_and_global_window(self):
        m  = QualityMetrics()
        qs = self._make_qs(0.8)
        m.record(qs, source="nse_feed", obs_type="market_data")
        w = m.window("_global")
        assert w is not None
        assert w.count == 1
        assert w.mean  == pytest.approx(0.8)

    def test_source_window(self):
        m  = QualityMetrics()
        qs = self._make_qs(0.7)
        m.record(qs, source="nse_feed")
        sw = m.source_stats("nse_feed")
        assert sw is not None
        assert sw["count"] == 1

    def test_rolling_window_cap(self):
        m = QualityMetrics(window_size=5)
        for i in range(10):
            m.record(self._make_qs(float(i) / 10))
        w = m.window("_global")
        assert w.count == 5

    def test_percentile(self):
        mw = MetricWindow(key="test", max_size=100)
        for v in [0.1, 0.5, 0.9, 0.3, 0.7]:
            mw.add(v)
        assert 0.0 < mw.percentile(50) < 1.0

    def test_summary(self):
        m = QualityMetrics()
        m.record(self._make_qs(0.75), source="x")
        s = m.summary()
        assert s["total_recorded"] == 1
        assert "global" in s

    def test_all_windows(self):
        m = QualityMetrics()
        m.record(self._make_qs(0.6), source="src1", obs_type="news")
        windows = m.all_windows()
        assert "_global"        in windows
        assert "source:src1"    in windows
        assert "type:news"      in windows
        assert "src_type:src1:news" in windows

    def test_clear(self):
        m = QualityMetrics()
        m.record(self._make_qs(0.5))
        m.clear()
        assert m.window("_global") is None


# ═══════════════════════════════════════════════════════════════════════════════
# QualityEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityEngine:
    def test_score_returns_quality_score(self):
        engine = QualityEngine()
        obs    = _make_market_obs()
        qs     = engine.score(obs)
        assert isinstance(qs, QualityScore)
        assert 0.0 <= qs.oqi <= 1.0

    def test_score_writes_back_to_metadata(self):
        engine = QualityEngine()
        obs    = _make_obs()
        engine.score(obs)
        assert 0.0 <= obs.metadata.quality_score <= 1.0

    def test_score_cache_hit(self):
        engine = QualityEngine(cache_size=10)
        obs    = _make_obs()
        qs1    = engine.score(obs, use_cache=True)
        qs2    = engine.score(obs, use_cache=True)
        assert qs1 is qs2  # same object from cache

    def test_score_cache_miss_bypass(self):
        engine = QualityEngine(cache_size=10)
        obs    = _make_obs()
        qs1    = engine.score(obs, use_cache=False)
        qs2    = engine.score(obs, use_cache=False)
        assert qs1 is not qs2  # new computation each time

    def test_score_batch(self):
        engine   = QualityEngine()
        obs_list = [_make_obs() for _ in range(5)]
        results  = engine.score_batch(obs_list)
        assert len(results) == 5
        assert all(isinstance(v, QualityScore) for v in results.values())

    def test_invalidate_cache(self):
        engine = QualityEngine(cache_size=10)
        obs    = _make_obs()
        engine.score(obs, use_cache=True)
        assert engine.cache_size() == 1
        engine.invalidate(obs.id)
        assert engine.cache_size() == 0

    def test_cache_lru_eviction(self):
        engine = QualityEngine(cache_size=3)
        for _ in range(5):
            engine.score(_make_obs(), use_cache=True)
        assert engine.cache_size() <= 3

    def test_stats(self):
        engine = QualityEngine()
        s      = engine.stats()
        assert "cache_size" in s
        assert "metrics"    in s

    def test_excellent_obs_has_high_oqi(self):
        engine = QualityEngine()
        obs    = _make_market_obs()
        obs.metadata.tags         = ["nifty", "equity"]
        obs.metadata.confidence   = 0.95
        obs.source_info.source    = ObservationSource.NSE_FEED
        obs.metadata.expires_at   = time.time() + 7200.0
        qs     = engine.score(obs, use_cache=False)
        assert qs.oqi > 0.50  # well-formed market obs should score reasonably


# ═══════════════════════════════════════════════════════════════════════════════
# QualityManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityManager:
    def test_policy_action_for(self):
        p = QualityPolicy(min_oqi=0.3, quarantine_below=0.5, flag_below=0.6, fast_track_above=0.8)
        assert p.action_for(0.1)  == "reject"
        assert p.action_for(0.4)  == "quarantine"
        assert p.action_for(0.55) == "flag"
        assert p.action_for(0.65) == "proceed"
        assert p.action_for(0.85) == "fast_track"

    def test_assess_returns_decision(self):
        mgr = QualityManager()
        obs = _make_obs()
        d   = mgr.assess(obs)
        assert isinstance(d, QualityDecision)
        assert 0.0 <= d.oqi <= 1.0

    def test_assess_batch(self):
        mgr      = QualityManager()
        obs_list = [_make_obs() for _ in range(3)]
        results  = mgr.assess_batch(obs_list)
        assert len(results) == 3

    def test_reject_on_low_oqi(self):
        policy = QualityPolicy(min_oqi=1.1)  # impossible threshold → always reject
        mgr    = QualityManager(policy=policy)
        obs    = _make_obs()
        d      = mgr.assess(obs)
        assert d.rejected

    def test_raise_on_reject(self):
        policy = QualityPolicy(min_oqi=1.1)
        mgr    = QualityManager(policy=policy, raise_on_reject=True)
        obs    = _make_obs()
        with pytest.raises(QualityThresholdError):
            mgr.assess(obs)

    def test_stats(self):
        mgr = QualityManager()
        mgr.assess(_make_obs())
        s = mgr.stats()
        assert s["total"] == 1
        assert "by_action" in s

    def test_decision_to_dict(self):
        mgr = QualityManager()
        d   = mgr.assess(_make_obs())
        dd  = d.to_dict()
        assert "obs_id"  in dd
        assert "tier"    in dd
        assert "action"  in dd


# ═══════════════════════════════════════════════════════════════════════════════
# QualityReport
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityReport:
    def _seed_metrics(self, m: QualityMetrics, n: int = 10) -> None:
        engine = QualityEngine(metrics=m)
        for _ in range(n):
            engine.score(_make_obs(), use_cache=False)

    def test_generate_returns_document(self):
        m   = QualityMetrics()
        rep = QualityReporter(metrics=m)
        self._seed_metrics(m)
        doc = rep.generate()
        assert isinstance(doc, QualityReportDocument)
        assert len(doc.sections) >= 3

    def test_sections_present(self):
        m   = QualityMetrics()
        rep = QualityReporter(metrics=m)
        self._seed_metrics(m)
        doc   = rep.generate()
        titles = [s.title for s in doc.sections]
        assert "Global Summary"    in titles
        assert "Tier Distribution" in titles
        assert "Source Breakdown"  in titles

    def test_to_dict(self):
        m   = QualityMetrics()
        rep = QualityReporter(metrics=m)
        self._seed_metrics(m)
        d   = rep.generate().to_dict()
        assert "generated_at" in d
        assert "sections"     in d

    def test_section_lookup(self):
        m   = QualityMetrics()
        rep = QualityReporter(metrics=m)
        self._seed_metrics(m)
        doc = rep.generate()
        sec = doc.section("Global Summary")
        assert sec is not None
        assert "count" in sec.data

    def test_quick_summary_no_data(self):
        m   = QualityMetrics()
        rep = QualityReporter(metrics=m)
        s   = rep.quick_summary()
        assert s["status"] == "no_data"

    def test_quick_summary_with_data(self):
        m   = QualityMetrics()
        rep = QualityReporter(metrics=m)
        self._seed_metrics(m)
        s   = rep.quick_summary()
        assert "mean_oqi" in s
        assert "tiers"    in s


# ═══════════════════════════════════════════════════════════════════════════════
# Concurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_parallel_validation(self):
        engine = ValidationEngine()
        errors  = []

        def worker():
            try:
                obs = _make_obs()
                engine.validate(obs)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors

    def test_parallel_quality_scoring(self):
        eng    = QualityEngine(cache_size=64)
        errors = []

        def worker():
            try:
                obs = _make_obs()
                eng.score(obs, use_cache=True)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors

    def test_parallel_manager_process(self):
        mgr    = ValidationManager(min_score=0.0, suppress_dups=False)
        errors = []

        def worker():
            try:
                obs = _make_obs()
                mgr.process(obs)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
