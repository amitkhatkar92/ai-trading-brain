"""
test_risk_snapshot.py — tests.unit.risk.snapshot
=================================================
Comprehensive test suite for the Risk Snapshot Framework.
Target: 95%+ coverage across all 15 source files.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from iios.risk.snapshot import (
    # Constants
    VERSION, SnapshotStatus, RiskScope, RiskType, RiskPriority, RiskLevel,
    RiskRating, RiskTrend, IntegrityStatus, SnapshotEventType,
    SnapshotValidationCode,
    # Exceptions
    RiskSnapshotError, RiskSnapshotNotFoundError, RiskSnapshotBuilderError,
    RiskSnapshotValidationError, RiskSnapshotIntegrityError,
    RiskSnapshotRegistryError, RiskSnapshotStoreError, RiskSnapshotCacheError,
    RiskSnapshotCapacityError, RiskSnapshotSerializationError,
    # Metadata
    DomainRiskSummary, AssessmentSummarySection, QuantitativeMetrics,
    StressTestSummary, OptimizationSummary, PolicySummary,
    SystemHealthSummary, SnapshotAudit, SnapshotStatisticsSection, SnapshotMetadata,
    # Core
    RiskSnapshotSummary, RiskSnapshot,
    # Events
    RiskSnapshotEvent,
    make_snapshot_built, make_snapshot_published, make_snapshot_validated,
    make_snapshot_superseded, make_snapshot_archived, make_snapshot_failed,
    make_snapshot_retrieved, make_snapshot_expired, make_snapshot_bundled,
    make_snapshot_stored,
    # Validation
    SnapshotValidationCheck, SnapshotValidationResult, RiskSnapshotValidator,
    # Services
    RiskSnapshotBuilder, RiskSnapshotFactory, RiskSnapshotRegistry,
    RiskSnapshotStore, RiskSnapshotCache, RiskSnapshotHistory,
    RiskSnapshotStatistics,
    # Bundle
    RiskSnapshotBundle, RiskSnapshotBundleBuilder,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_snapshot(
    risk_score: float = 42.0,
    portfolio_id: str = "port-1",
    *,
    risk_session_id:    str = "sess-1",
    risk_assessment_id: str = "assess-1",
    snapshot_id: str | None = None,
) -> RiskSnapshot:
    return RiskSnapshot.create(
        risk_session_id    = risk_session_id,
        risk_assessment_id = risk_assessment_id,
        portfolio_id       = portfolio_id,
        risk_score         = risk_score,
        assessment_status  = "completed",
        snapshot_id        = snapshot_id,
    )


def _make_builder_snapshot(
    risk_score: float = 42.0,
    portfolio_id: str = "port-1",
) -> RiskSnapshot:
    return (
        RiskSnapshotBuilder()
        .set_identity("sess-1", "assess-1", portfolio_id)
        .set_risk_score(risk_score, "completed")
        .build()
    )


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_version(self):
        assert VERSION == "1.0.0"

    def test_snapshot_status_values(self):
        assert SnapshotStatus.PUBLISHED.value == "published"
        assert SnapshotStatus.BUILDING.value  == "building"
        assert SnapshotStatus.FAILED.value    == "failed"

    def test_risk_scope_values(self):
        assert RiskScope.PORTFOLIO.value  == "portfolio"
        assert RiskScope.ENTERPRISE.value == "enterprise"
        assert RiskScope.TRADE.value      == "trade"

    def test_risk_type_values(self):
        assert RiskType.COMPOSITE.value == "composite"
        assert RiskType.MARKET.value    == "market"

    def test_risk_priority_values(self):
        assert RiskPriority.CRITICAL.value == "critical"
        assert RiskPriority.LOW.value      == "low"

    def test_risk_level_values(self):
        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.MINIMAL.value  == "minimal"

    def test_risk_rating_values(self):
        assert RiskRating.EXCELLENT.value == "excellent"
        assert RiskRating.CRITICAL.value  == "critical"

    def test_risk_trend_values(self):
        assert RiskTrend.IMPROVING.value == "improving"
        assert RiskTrend.UNKNOWN.value   == "unknown"

    def test_integrity_status_values(self):
        assert IntegrityStatus.VALID.value   == "valid"
        assert IntegrityStatus.INVALID.value == "invalid"

    def test_event_type_count(self):
        assert len(SnapshotEventType) == 10

    def test_validation_code_count(self):
        assert len(SnapshotValidationCode) == 9


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_error(self):
        e = RiskSnapshotError("test")
        assert "RS-000" in str(e) or e.error_code == "RS-000"

    def test_not_found_error(self):
        e = RiskSnapshotNotFoundError("missing")
        assert e.error_code == "RS-001"

    def test_builder_error(self):
        e = RiskSnapshotBuilderError("build failed")
        assert e.error_code == "RS-002"

    def test_validation_error(self):
        e = RiskSnapshotValidationError("invalid")
        assert e.error_code == "RS-003"

    def test_integrity_error(self):
        e = RiskSnapshotIntegrityError("corrupt")
        assert e.error_code == "RS-004"

    def test_registry_error(self):
        e = RiskSnapshotRegistryError("dup")
        assert e.error_code == "RS-005"

    def test_store_error(self):
        e = RiskSnapshotStoreError("io")
        assert e.error_code == "RS-006"

    def test_cache_error(self):
        e = RiskSnapshotCacheError("cache")
        assert e.error_code == "RS-007"

    def test_capacity_error(self):
        e = RiskSnapshotCapacityError("full")
        assert e.error_code == "RS-008"

    def test_serialization_error(self):
        e = RiskSnapshotSerializationError("bad json")
        assert e.error_code == "RS-009"

    def test_inheritance(self):
        e = RiskSnapshotNotFoundError("x")
        assert isinstance(e, RiskSnapshotError)


# ===========================================================================
# 3. DomainRiskSummary
# ===========================================================================

class TestDomainRiskSummary:
    def test_create(self):
        d = DomainRiskSummary(
            domain="market_risk",
            risk_score=50.0,
            risk_level=RiskLevel.MEDIUM,
            risk_contribution=0.1,
        )
        assert d.domain == "market_risk"
        assert d.risk_score == 50.0
        assert d.is_breached is False

    def test_breached(self):
        d = DomainRiskSummary(
            domain="credit_risk",
            risk_score=90.0,
            risk_level=RiskLevel.CRITICAL,
            risk_contribution=0.2,
            is_breached=True,
        )
        assert d.is_breached is True

    def test_to_dict(self):
        d = DomainRiskSummary("market_risk", 30.0, RiskLevel.LOW, 0.1)
        data = d.to_dict()
        assert data["domain"]      == "market_risk"
        assert data["risk_score"]  == 30.0
        assert data["risk_level"]  == "low"
        assert data["is_breached"] is False

    def test_frozen(self):
        d = DomainRiskSummary("market_risk", 30.0, RiskLevel.LOW, 0.1)
        with pytest.raises(Exception):
            d.risk_score = 99.0  # type: ignore[misc]


# ===========================================================================
# 4. AssessmentSummarySection
# ===========================================================================

class TestAssessmentSummarySection:
    def test_build_uniform(self):
        section = AssessmentSummarySection.build_uniform(50.0)
        assert len(section.all_domains()) == 10
        for d in section.all_domains():
            assert d.risk_score == 50.0

    def test_all_domains_count(self):
        section = AssessmentSummarySection.build_uniform(30.0)
        assert len(section.all_domains()) == 10

    def test_breached_domains_empty_when_none(self):
        section = AssessmentSummarySection.build_uniform(30.0)
        assert len(section.breached_domains()) == 0

    def test_to_dict(self):
        section = AssessmentSummarySection.build_uniform(50.0)
        data = section.to_dict()
        assert len(data) == 10
        assert "market_risk" in data
        assert "exposure"    in data

    def test_explicit_domains(self):
        section = AssessmentSummarySection.build_uniform(80.0)
        assert section.market_risk.risk_level == RiskLevel.HIGH

    def test_critical_score(self):
        section = AssessmentSummarySection.build_uniform(95.0)
        assert section.market_risk.risk_level == RiskLevel.CRITICAL


# ===========================================================================
# 5. QuantitativeMetrics
# ===========================================================================

class TestQuantitativeMetrics:
    def test_defaults(self):
        m = QuantitativeMetrics()
        assert m.var_95 == 0.0
        assert m.portfolio_beta == 1.0
        assert m.liquidity_ratio == 1.0

    def test_explicit_values(self):
        m = QuantitativeMetrics(var_95=50_000.0, var_95_pct=0.05, es_95=70_000.0)
        assert m.var_95     == 50_000.0
        assert m.var_95_pct == 0.05
        assert m.es_95      == 70_000.0

    def test_to_dict(self):
        m = QuantitativeMetrics(var_95=10_000.0)
        data = m.to_dict()
        assert "var_95"               in data
        assert "portfolio_volatility" in data
        assert "exposure_utilization" in data

    def test_frozen(self):
        m = QuantitativeMetrics(var_95=100.0)
        with pytest.raises(Exception):
            m.var_95 = 200.0  # type: ignore[misc]


# ===========================================================================
# 6. StressTestSummary
# ===========================================================================

class TestStressTestSummary:
    def test_defaults(self):
        s = StressTestSummary()
        assert s.tests_executed == 0
        assert s.worst_case_loss == 0.0

    def test_explicit(self):
        s = StressTestSummary(
            tests_executed=8,
            worst_case_loss=500_000.0,
            worst_case_loss_pct=0.35,
            worst_scenario="market_crash",
            recovery_estimate=120.0,
            scenario_count=6,
        )
        assert s.tests_executed == 8
        assert s.worst_scenario == "market_crash"

    def test_to_dict(self):
        s = StressTestSummary(tests_executed=4)
        data = s.to_dict()
        assert data["tests_executed"] == 4
        assert "worst_case_loss"      in data


# ===========================================================================
# 7. OptimizationSummary
# ===========================================================================

class TestOptimizationSummary:
    def test_defaults(self):
        o = OptimizationSummary()
        assert o.status == "not_run"
        assert o.optimization_gain == 0.0

    def test_explicit(self):
        o = OptimizationSummary(
            status                = "completed",
            objective             = "minimize_portfolio_risk",
            risk_score_before     = 70.0,
            risk_score_after      = 50.0,
            optimization_gain     = 20.0,
            recommendations_count = 5,
            priority_actions      = ("reduce_concentration",),
        )
        assert o.status           == "completed"
        assert o.optimization_gain == 20.0

    def test_to_dict(self):
        o = OptimizationSummary(status="completed")
        data = o.to_dict()
        assert data["status"]           == "completed"
        assert "priority_actions"       in data
        assert "recommendations_count"  in data


# ===========================================================================
# 8. PolicySummary
# ===========================================================================

class TestPolicySummary:
    def test_defaults(self):
        p = PolicySummary()
        assert p.violations == 0
        assert p.has_violations is False
        assert p.has_escalations is False

    def test_with_violations(self):
        p = PolicySummary(violations=2, escalations=1)
        assert p.has_violations  is True
        assert p.has_escalations is True

    def test_to_dict(self):
        p = PolicySummary(policy_decision="approve", violations=1)
        data = p.to_dict()
        assert data["policy_decision"] == "approve"
        assert data["violations"]       == 1

    def test_zero_violations(self):
        p = PolicySummary(violations=0)
        assert p.has_violations is False


# ===========================================================================
# 9. SystemHealthSummary
# ===========================================================================

class TestSystemHealthSummary:
    def test_defaults(self):
        h = SystemHealthSummary()
        assert h.is_healthy is True
        assert h.pipeline_health   == "healthy"
        assert h.framework_health  == "healthy"

    def test_unhealthy_integrity(self):
        h = SystemHealthSummary(snapshot_integrity=IntegrityStatus.INVALID.value)
        assert h.is_healthy is False

    def test_to_dict(self):
        h = SystemHealthSummary()
        data = h.to_dict()
        assert "snapshot_integrity" in data
        assert "pipeline_health"    in data


# ===========================================================================
# 10. SnapshotAudit
# ===========================================================================

class TestSnapshotAudit:
    def test_defaults(self):
        a = SnapshotAudit()
        assert a.assessment_version == VERSION

    def test_explicit(self):
        a = SnapshotAudit(
            assessment_version = "2.0.0",
            model_versions     = {"var_model": "1.1"},
            audit_trail        = ("event_1", "event_2"),
        )
        assert a.assessment_version == "2.0.0"
        assert len(a.audit_trail)   == 2

    def test_to_dict(self):
        a = SnapshotAudit(audit_trail=("e1",))
        data = a.to_dict()
        assert "assessment_version" in data
        assert "audit_trail"        in data


# ===========================================================================
# 11. RiskSnapshotSummary
# ===========================================================================

class TestRiskSnapshotSummary:
    def test_score_10_excellent(self):
        s = RiskSnapshotSummary.from_score(10.0, "completed")
        assert s.risk_rating == RiskRating.EXCELLENT
        assert s.risk_level  == RiskLevel.MINIMAL

    def test_score_35_good(self):
        s = RiskSnapshotSummary.from_score(35.0, "completed")
        assert s.risk_rating == RiskRating.GOOD
        assert s.risk_level  == RiskLevel.LOW

    def test_score_55_fair(self):
        s = RiskSnapshotSummary.from_score(55.0, "completed")
        assert s.risk_rating == RiskRating.FAIR
        assert s.risk_level  == RiskLevel.MEDIUM

    def test_score_75_poor(self):
        s = RiskSnapshotSummary.from_score(75.0, "completed")
        assert s.risk_rating == RiskRating.POOR
        assert s.risk_level  == RiskLevel.HIGH

    def test_score_90_critical(self):
        s = RiskSnapshotSummary.from_score(90.0, "failed")
        assert s.risk_rating == RiskRating.CRITICAL
        assert s.risk_level  == RiskLevel.CRITICAL

    def test_confidence_clamped(self):
        s = RiskSnapshotSummary.from_score(50.0, "completed", confidence=2.0)
        assert s.risk_confidence == 1.0
        s2 = RiskSnapshotSummary.from_score(50.0, "completed", confidence=-1.0)
        assert s2.risk_confidence == 0.0

    def test_to_dict(self):
        s = RiskSnapshotSummary.from_score(50.0, "completed")
        data = s.to_dict()
        assert "overall_risk_score" in data
        assert "risk_rating"        in data
        assert "risk_level"         in data
        assert "risk_trend"         in data
        assert "risk_confidence"    in data

    def test_trend_unknown_default(self):
        s = RiskSnapshotSummary.from_score(50.0, "completed")
        assert s.risk_trend == RiskTrend.UNKNOWN

    def test_explicit_trend(self):
        s = RiskSnapshotSummary.from_score(50.0, "completed", trend=RiskTrend.IMPROVING)
        assert s.risk_trend == RiskTrend.IMPROVING


# ===========================================================================
# 12. RiskSnapshot (core)
# ===========================================================================

class TestRiskSnapshot:
    def test_create_minimal(self):
        s = _make_snapshot()
        assert s.portfolio_id       == "port-1"
        assert s.risk_session_id    == "sess-1"
        assert s.risk_assessment_id == "assess-1"
        assert s.risk_status        == SnapshotStatus.PUBLISHED
        assert s.snapshot_version   == 1

    def test_snapshot_id_generated(self):
        s = _make_snapshot()
        assert s.snapshot_id
        assert len(s.snapshot_id) > 0

    def test_explicit_snapshot_id(self):
        sid = "snap-999"
        s   = _make_snapshot(snapshot_id=sid)
        assert s.snapshot_id == sid

    def test_risk_score_property(self):
        s = _make_snapshot(risk_score=65.0)
        assert s.risk_score == 65.0

    def test_risk_level_property(self):
        s = _make_snapshot(risk_score=65.0)
        assert s.risk_level == RiskLevel.HIGH

    def test_risk_rating_property(self):
        s = _make_snapshot(risk_score=65.0)
        assert s.risk_rating == RiskRating.POOR

    def test_is_published(self):
        s = _make_snapshot()
        assert s.is_published is True

    def test_is_valid(self):
        s = _make_snapshot()
        assert s.is_valid is True

    def test_has_policy_violations_false(self):
        s = _make_snapshot()
        assert s.has_policy_violations is False

    def test_has_escalations_false(self):
        s = _make_snapshot()
        assert s.has_escalations is False

    def test_is_high_risk_medium(self):
        s = _make_snapshot(risk_score=50.0)
        assert s.is_high_risk is False

    def test_is_high_risk_high(self):
        s = _make_snapshot(risk_score=85.0)
        assert s.is_high_risk is True

    def test_to_dict_keys(self):
        s    = _make_snapshot()
        data = s.to_dict()
        required = [
            "snapshot_id", "risk_session_id", "risk_assessment_id",
            "portfolio_id", "risk_scope", "risk_type", "risk_priority",
            "risk_status", "lifecycle_state", "risk_version",
            "framework_version", "snapshot_version", "assessment_timestamp",
            "created_time", "updated_time", "summary", "assessment_summary",
            "quantitative_metrics", "stress_test_summary", "optimization_summary",
            "policy_summary", "system_health", "audit", "statistics", "metadata",
        ]
        for key in required:
            assert key in data, f"missing key: {key}"

    def test_previous_snapshot_id_none_default(self):
        s = _make_snapshot()
        assert s.previous_snapshot_id is None

    def test_previous_snapshot_id_set(self):
        s = RiskSnapshot.create(
            risk_session_id    = "sess-1",
            risk_assessment_id = "assess-1",
            portfolio_id       = "port-1",
            risk_score         = 50.0,
            assessment_status  = "completed",
            previous_snapshot_id = "prev-snap-1",
        )
        assert s.previous_snapshot_id == "prev-snap-1"

    def test_frozen(self):
        s = _make_snapshot()
        with pytest.raises(Exception):
            s.risk_score = 99.0  # type: ignore[misc]

    def test_timestamps_set(self):
        before = time.time()
        s      = _make_snapshot()
        after  = time.time()
        assert before <= s.created_time <= after
        assert before <= s.updated_time <= after

    def test_full_creation_with_sections(self):
        qm = QuantitativeMetrics(var_95=10_000.0, var_95_pct=0.02)
        sts = StressTestSummary(tests_executed=8, worst_case_loss=200_000.0)
        opts = OptimizationSummary(status="completed", optimization_gain=10.0)
        ps  = PolicySummary(policy_decision="approve", violations=0)
        meta = SnapshotMetadata(environment="test")
        s = RiskSnapshot.create(
            risk_session_id    = "sess-2",
            risk_assessment_id = "assess-2",
            portfolio_id       = "port-2",
            risk_score         = 55.0,
            assessment_status  = "completed",
            quantitative_metrics = qm,
            stress_test_summary  = sts,
            optimization_summary = opts,
            policy_summary       = ps,
            metadata             = meta,
        )
        assert s.quantitative_metrics.var_95 == 10_000.0
        assert s.stress_test_summary.tests_executed == 8
        assert s.optimization_summary.status == "completed"
        assert s.policy_summary.policy_decision == "approve"
        assert s.metadata.environment == "test"


# ===========================================================================
# 13. Events
# ===========================================================================

class TestSnapshotEvents:
    def test_make_snapshot_built(self):
        e = make_snapshot_built("snap-1", "port-1", "actor:system")
        assert e.event_type  == SnapshotEventType.SNAPSHOT_BUILT
        assert e.snapshot_id == "snap-1"
        assert e.portfolio_id == "port-1"

    def test_make_snapshot_published(self):
        e = make_snapshot_published("snap-1", "port-1", "actor")
        assert e.event_type == SnapshotEventType.SNAPSHOT_PUBLISHED

    def test_make_snapshot_validated(self):
        e = make_snapshot_validated("snap-1", "port-1", "actor")
        assert e.event_type == SnapshotEventType.SNAPSHOT_VALIDATED

    def test_make_snapshot_superseded(self):
        e = make_snapshot_superseded("snap-1", "port-1", "actor")
        assert e.event_type == SnapshotEventType.SNAPSHOT_SUPERSEDED

    def test_make_snapshot_archived(self):
        e = make_snapshot_archived("snap-1", "port-1", "actor")
        assert e.event_type == SnapshotEventType.SNAPSHOT_ARCHIVED

    def test_make_snapshot_failed(self):
        e = make_snapshot_failed("snap-1", "port-1", "actor")
        assert e.event_type == SnapshotEventType.SNAPSHOT_FAILED

    def test_make_snapshot_retrieved(self):
        e = make_snapshot_retrieved("snap-1", "port-1", "actor")
        assert e.event_type == SnapshotEventType.SNAPSHOT_RETRIEVED

    def test_make_snapshot_expired(self):
        e = make_snapshot_expired("snap-1", "port-1", "actor")
        assert e.event_type == SnapshotEventType.SNAPSHOT_EXPIRED

    def test_make_snapshot_bundled(self):
        e = make_snapshot_bundled("snap-1", "port-1", "actor")
        assert e.event_type == SnapshotEventType.SNAPSHOT_BUNDLED

    def test_make_snapshot_stored(self):
        e = make_snapshot_stored("snap-1", "port-1", "actor")
        assert e.event_type == SnapshotEventType.SNAPSHOT_STORED

    def test_event_to_dict(self):
        e    = make_snapshot_built("snap-1", "port-1", "actor", risk_score=42.0)
        data = e.to_dict()
        assert data["event_type"]   == "snapshot_built"
        assert data["snapshot_id"]  == "snap-1"
        assert data["portfolio_id"] == "port-1"

    def test_event_id_unique(self):
        e1 = make_snapshot_built("snap-1", "port-1", "actor")
        e2 = make_snapshot_built("snap-1", "port-1", "actor")
        assert e1.event_id != e2.event_id

    def test_event_frozen(self):
        e = make_snapshot_built("snap-1", "port-1", "actor")
        with pytest.raises(Exception):
            e.event_id = "hacked"  # type: ignore[misc]


# ===========================================================================
# 14. Validation
# ===========================================================================

class TestSnapshotValidation:
    def _valid_snapshot(self) -> RiskSnapshot:
        return _make_snapshot()

    def test_valid_snapshot_passes(self):
        validator = RiskSnapshotValidator()
        result    = validator.validate(self._valid_snapshot())
        assert result.passed is True
        assert result.failed_count == 0

    def test_all_checks_run(self):
        validator = RiskSnapshotValidator()
        result    = validator.validate(self._valid_snapshot())
        assert len(result.checks) == 9

    def test_passed_count(self):
        validator = RiskSnapshotValidator()
        result    = validator.validate(self._valid_snapshot())
        assert result.passed_count == 9

    def test_validate_or_raise_passes(self):
        validator = RiskSnapshotValidator()
        result    = validator.validate_or_raise(self._valid_snapshot())
        assert result.passed is True

    def test_to_summary_pass(self):
        validator = RiskSnapshotValidator()
        result    = validator.validate(self._valid_snapshot())
        summary   = result.to_summary()
        assert "PASS" in summary

    def test_check_dataclass(self):
        check = SnapshotValidationCheck(
            code    = SnapshotValidationCode.IDENTIFIER_CONSISTENT,
            passed  = True,
            message = "",
        )
        assert check.passed is True
        assert check.code == SnapshotValidationCode.IDENTIFIER_CONSISTENT

    def test_result_dataclass(self):
        result = SnapshotValidationResult(snapshot_id="snap-1")
        assert result.passed is True   # no checks means all pass (vacuous)
        assert result.failed_count == 0

    def test_failed_result_to_summary(self):
        result = SnapshotValidationResult(snapshot_id="snap-1")
        result.checks.append(SnapshotValidationCheck(
            code    = SnapshotValidationCode.IDENTIFIER_CONSISTENT,
            passed  = False,
            message = "missing id",
        ))
        assert "FAIL" in result.to_summary()

    def test_invalid_score_fails_metric_check(self):
        s = _make_snapshot()
        # Inject an invalid metric via the quantitative_metrics field
        bad_metrics = QuantitativeMetrics(var_95=-100.0)
        # Re-create snapshot with bad metric
        from iios.risk.snapshot.risk_snapshot import RiskSnapshot as RS
        bad = RS.create(
            risk_session_id    = "sess-1",
            risk_assessment_id = "assess-1",
            portfolio_id       = "port-1",
            risk_score         = 50.0,
            assessment_status  = "completed",
            quantitative_metrics = bad_metrics,
        )
        validator = RiskSnapshotValidator()
        result    = validator.validate(bad)
        assert result.passed is False

    def test_negative_violations_fail(self):
        ps = PolicySummary(violations=-1)
        s  = RiskSnapshot.create(
            risk_session_id="s", risk_assessment_id="a",
            portfolio_id="p", risk_score=50.0,
            assessment_status="completed", policy_summary=ps,
        )
        validator = RiskSnapshotValidator()
        result    = validator.validate(s)
        assert result.passed is False

    def test_validate_or_raise_raises(self):
        bad = QuantitativeMetrics(var_95=-1.0)
        s   = RiskSnapshot.create(
            risk_session_id="s", risk_assessment_id="a",
            portfolio_id="p", risk_score=50.0,
            assessment_status="completed", quantitative_metrics=bad,
        )
        validator = RiskSnapshotValidator()
        with pytest.raises(RiskSnapshotValidationError):
            validator.validate_or_raise(s)


# ===========================================================================
# 15. Builder
# ===========================================================================

class TestRiskSnapshotBuilder:
    def test_minimal_build(self):
        s = _make_builder_snapshot()
        assert s.portfolio_id    == "port-1"
        assert s.risk_score      == 42.0
        assert s.is_published    is True

    def test_all_sections(self):
        s = (
            RiskSnapshotBuilder()
            .set_identity("sess-1", "assess-1", "port-1",
                          workflow_id="wf-1", strategy_id="strat-1", account_id="acc-1")
            .set_classification(risk_scope=RiskScope.ACCOUNT, risk_type=RiskType.MARKET)
            .set_versioning(risk_version="2.0.0", snapshot_version=3)
            .set_risk_score(55.0, "completed", trend=RiskTrend.WORSENING, confidence=0.9)
            .set_quantitative_metrics(var_95=10_000.0, es_95=15_000.0)
            .set_stress_test_summary(tests_executed=8, worst_case_loss=50_000.0)
            .set_optimization_summary(status="completed", optimization_gain=5.0)
            .set_policy_summary(policy_decision="approve", violations=0)
            .set_system_health(pipeline_health="healthy", framework_health="healthy")
            .set_audit(assessment_version="1.0.0")
            .set_statistics(assessment_duration_s=1.5, component_count=10)
            .set_metadata(environment="staging")
            .build()
        )
        assert s.workflow_id                          == "wf-1"
        assert s.strategy_id                          == "strat-1"
        assert s.account_id                           == "acc-1"
        assert s.risk_scope                           == RiskScope.ACCOUNT
        assert s.risk_type                            == RiskType.MARKET
        assert s.risk_version                         == "2.0.0"
        assert s.snapshot_version                     == 3
        assert s.summary.risk_trend                   == RiskTrend.WORSENING
        assert s.summary.risk_confidence              == 0.9
        assert s.quantitative_metrics.var_95          == 10_000.0
        assert s.stress_test_summary.tests_executed   == 8
        assert s.optimization_summary.status          == "completed"
        assert s.policy_summary.policy_decision       == "approve"
        assert s.statistics.assessment_duration_s     == 1.5
        assert s.metadata.environment                 == "staging"

    def test_missing_session_id_raises(self):
        with pytest.raises(RiskSnapshotBuilderError):
            RiskSnapshotBuilder().set_identity("", "a", "p").build()

    def test_missing_assessment_id_raises(self):
        with pytest.raises(RiskSnapshotBuilderError):
            RiskSnapshotBuilder().set_identity("s", "", "p").build()

    def test_missing_portfolio_id_raises(self):
        with pytest.raises(RiskSnapshotBuilder.__class__.__mro__[1] if False else RiskSnapshotBuilderError):
            RiskSnapshotBuilder().set_identity("s", "a", "").build()

    def test_no_identity_raises(self):
        with pytest.raises(RiskSnapshotBuilderError):
            RiskSnapshotBuilder().build()

    def test_obj_setters(self):
        qm  = QuantitativeMetrics(var_95=5_000.0)
        sts = StressTestSummary(tests_executed=4)
        opts = OptimizationSummary(status="skipped")
        ps  = PolicySummary(violations=1)
        sh  = SystemHealthSummary()
        a   = SnapshotAudit()
        stat = SnapshotStatisticsSection(component_count=5)
        meta = SnapshotMetadata(environment="prod")
        s = (
            RiskSnapshotBuilder()
            .set_identity("s", "a", "p")
            .set_risk_score(50.0, "completed")
            .set_quantitative_metrics_obj(qm)
            .set_stress_test_summary_obj(sts)
            .set_optimization_summary_obj(opts)
            .set_policy_summary_obj(ps)
            .set_system_health_obj(sh)
            .set_audit_obj(a)
            .set_statistics_obj(stat)
            .set_metadata_obj(meta)
            .build()
        )
        assert s.quantitative_metrics.var_95     == 5_000.0
        assert s.stress_test_summary.tests_executed == 4
        assert s.optimization_summary.status     == "skipped"
        assert s.policy_summary.violations       == 1
        assert s.statistics.component_count      == 5
        assert s.metadata.environment            == "prod"

    def test_set_previous_snapshot_id(self):
        s = (
            RiskSnapshotBuilder()
            .set_identity("s", "a", "p")
            .set_risk_score(50.0, "completed")
            .set_previous_snapshot_id("prev-snap")
            .build()
        )
        assert s.previous_snapshot_id == "prev-snap"

    def test_set_assessment_timestamp(self):
        ts = 1_700_000_000.0
        s  = (
            RiskSnapshotBuilder()
            .set_identity("s", "a", "p")
            .set_risk_score(50.0, "completed")
            .set_assessment_timestamp(ts)
            .build()
        )
        assert s.assessment_timestamp == ts

    def test_build_no_validate(self):
        """build(validate=False) skips validator — should not raise."""
        s = (
            RiskSnapshotBuilder()
            .set_identity("s", "a", "p")
            .set_risk_score(50.0, "completed")
            .build(validate=False)
        )
        assert s is not None

    def test_explicit_summary(self):
        summary = RiskSnapshotSummary.from_score(30.0, "completed")
        s = (
            RiskSnapshotBuilder()
            .set_identity("s", "a", "p")
            .set_summary(summary)
            .build()
        )
        assert s.risk_score == 30.0


# ===========================================================================
# 16. Factory
# ===========================================================================

class TestRiskSnapshotFactory:
    def _make_mock_report(self, risk_score: float = 50.0) -> MagicMock:
        r = MagicMock()
        r.assessment_id  = "assess-1"
        r.portfolio_id   = "port-1"
        r.risk_score     = risk_score
        r.duration_s     = 1.5
        r.published_at   = time.time()
        r.status         = MagicMock(value="completed")
        r.var_report     = None
        r.es_report      = None
        r.stress_test_report = None
        r.exposure_report    = None
        r.summary            = None
        r.optimization_report = None
        r.mitigation_plan     = None
        r.model_version       = VERSION
        return r

    def test_from_assessment_report_minimal(self):
        factory  = RiskSnapshotFactory()
        report   = self._make_mock_report(50.0)
        snapshot = factory.from_assessment_report(report, "sess-1")
        assert snapshot.portfolio_id       == "port-1"
        assert snapshot.risk_assessment_id == "assess-1"
        assert snapshot.risk_score         == 50.0

    def test_from_assessment_report_with_var(self):
        factory = RiskSnapshotFactory()
        report  = self._make_mock_report(60.0)
        var_rep = MagicMock()
        var_rep.historical_var     = 50_000.0
        var_rep.historical_var_pct = 0.05
        var_rep.parametric_var     = 45_000.0
        var_rep.parametric_var_pct = 0.045
        report.var_report = var_rep
        snapshot = factory.from_assessment_report(report, "sess-1")
        assert snapshot.quantitative_metrics.var_95 == 50_000.0

    def test_from_assessment_report_with_stress(self):
        factory = RiskSnapshotFactory()
        report  = self._make_mock_report(70.0)
        stress  = MagicMock()
        stress.scenarios      = [MagicMock(to_dict=lambda: {"s": 1})] * 3
        stress.worst_loss     = 300_000.0
        stress.worst_loss_pct = 0.30
        stress.worst_scenario = MagicMock(value="market_crash")
        report.stress_test_report = stress
        snapshot = factory.from_assessment_report(report, "sess-1")
        assert snapshot.stress_test_summary.tests_executed == 3
        assert snapshot.stress_test_summary.worst_scenario == "market_crash"

    def test_create_minimal(self):
        factory  = RiskSnapshotFactory()
        snapshot = factory.create_minimal("sess", "assess", "port", 30.0, "completed")
        assert snapshot.risk_score == 30.0
        assert snapshot.is_valid   is True

    def test_environment_passed(self):
        factory  = RiskSnapshotFactory(environment="staging")
        snapshot = factory.create_minimal("s", "a", "p", 50.0, "completed")
        assert snapshot.metadata.environment == "staging"

    def test_with_policy_fields(self):
        factory  = RiskSnapshotFactory()
        report   = self._make_mock_report(55.0)
        snapshot = factory.from_assessment_report(
            report, "sess-1",
            policy_decision="approve",
            violations=1,
            escalations=0,
        )
        assert snapshot.policy_summary.policy_decision == "approve"
        assert snapshot.policy_summary.violations       == 1

    def test_with_optimization(self):
        factory = RiskSnapshotFactory()
        report  = self._make_mock_report(65.0)
        opt_rep = MagicMock()
        opt_rep.recommendations  = [MagicMock()] * 3
        opt_rep.objectives       = []
        opt_rep.risk_score_before = 65.0
        opt_rep.risk_score_after  = 50.0
        opt_rep.optimization_gain = 15.0
        report.optimization_report = opt_rep
        snapshot = factory.from_assessment_report(report, "sess-1")
        assert snapshot.optimization_summary.status == "completed"
        assert snapshot.optimization_summary.optimization_gain == 15.0


# ===========================================================================
# 17. Registry
# ===========================================================================

class TestRiskSnapshotRegistry:
    def test_register_and_get(self):
        reg = RiskSnapshotRegistry()
        s   = _make_snapshot()
        reg.register(s)
        assert reg.get(s.snapshot_id) is s

    def test_get_not_found(self):
        reg = RiskSnapshotRegistry()
        with pytest.raises(RiskSnapshotNotFoundError):
            reg.get("nonexistent")

    def test_get_or_none(self):
        reg = RiskSnapshotRegistry()
        assert reg.get_or_none("nonexistent") is None

    def test_duplicate_raises(self):
        reg = RiskSnapshotRegistry()
        s   = _make_snapshot()
        reg.register(s)
        with pytest.raises(RiskSnapshotRegistryError):
            reg.register(s)

    def test_capacity_exceeded(self):
        reg = RiskSnapshotRegistry(max_snapshots=2)
        reg.register(_make_snapshot(portfolio_id="p1", risk_assessment_id="a1"))
        reg.register(_make_snapshot(portfolio_id="p2", risk_assessment_id="a2"))
        with pytest.raises(RiskSnapshotCapacityError):
            reg.register(_make_snapshot(portfolio_id="p3", risk_assessment_id="a3"))

    def test_latest_for_portfolio(self):
        reg = RiskSnapshotRegistry()
        s1  = _make_snapshot(portfolio_id="port-X", risk_assessment_id="a1")
        s2  = _make_snapshot(portfolio_id="port-X", risk_assessment_id="a2")
        reg.register(s1)
        reg.register(s2)
        latest = reg.latest_for_portfolio("port-X")
        assert latest.snapshot_id == s2.snapshot_id

    def test_latest_for_portfolio_none(self):
        reg = RiskSnapshotRegistry()
        assert reg.latest_for_portfolio("nonexistent") is None

    def test_latest_for_assessment(self):
        reg = RiskSnapshotRegistry()
        s   = _make_snapshot()
        reg.register(s)
        assert reg.latest_for_assessment(s.risk_assessment_id) is s

    def test_versions_for_assessment(self):
        reg = RiskSnapshotRegistry()
        s1  = _make_snapshot(risk_assessment_id="assess-v1")
        s2  = _make_snapshot(risk_assessment_id="assess-v1")
        reg.register(s1)
        reg.register(s2)
        versions = reg.versions_for_assessment("assess-v1")
        assert len(versions) == 2

    def test_all_snapshots(self):
        reg = RiskSnapshotRegistry()
        reg.register(_make_snapshot(portfolio_id="p1", risk_assessment_id="a1"))
        reg.register(_make_snapshot(portfolio_id="p2", risk_assessment_id="a2"))
        assert len(reg.all_snapshots()) == 2

    def test_count(self):
        reg = RiskSnapshotRegistry()
        reg.register(_make_snapshot(portfolio_id="p1", risk_assessment_id="a1"))
        assert reg.count() == 1

    def test_is_empty(self):
        reg = RiskSnapshotRegistry()
        assert reg.is_empty() is True
        reg.register(_make_snapshot())
        assert reg.is_empty() is False

    def test_remove(self):
        reg = RiskSnapshotRegistry()
        s   = _make_snapshot()
        reg.register(s)
        assert reg.remove(s.snapshot_id) is True
        assert reg.get_or_none(s.snapshot_id) is None

    def test_remove_nonexistent(self):
        reg = RiskSnapshotRegistry()
        assert reg.remove("nonexistent") is False

    def test_clear(self):
        reg = RiskSnapshotRegistry()
        reg.register(_make_snapshot())
        reg.clear()
        assert reg.count() == 0

    def test_snapshots_for_portfolio(self):
        reg = RiskSnapshotRegistry()
        reg.register(_make_snapshot(portfolio_id="pA", risk_assessment_id="a1"))
        reg.register(_make_snapshot(portfolio_id="pA", risk_assessment_id="a2"))
        reg.register(_make_snapshot(portfolio_id="pB", risk_assessment_id="a3"))
        result = reg.snapshots_for_portfolio("pA")
        assert len(result) == 2

    def test_portfolio_count(self):
        reg = RiskSnapshotRegistry()
        reg.register(_make_snapshot(portfolio_id="pA", risk_assessment_id="a1"))
        reg.register(_make_snapshot(portfolio_id="pB", risk_assessment_id="a2"))
        assert reg.portfolio_count() == 2


# ===========================================================================
# 18. Store
# ===========================================================================

class TestRiskSnapshotStore:
    def test_store_and_load(self):
        store = RiskSnapshotStore()
        s     = _make_snapshot()
        store.store(s)
        loaded = store.load(s.snapshot_id)
        assert loaded is s

    def test_load_not_found(self):
        store = RiskSnapshotStore()
        with pytest.raises(RiskSnapshotNotFoundError):
            store.load("nonexistent")

    def test_load_or_none(self):
        store = RiskSnapshotStore()
        assert store.load_or_none("nonexistent") is None

    def test_idempotent_store(self):
        store = RiskSnapshotStore()
        s     = _make_snapshot()
        store.store(s)
        store.store(s)   # should not raise
        assert store.count() == 1

    def test_capacity_exceeded(self):
        store = RiskSnapshotStore(max_snapshots=1)
        store.store(_make_snapshot(portfolio_id="p1", risk_assessment_id="a1"))
        with pytest.raises(RiskSnapshotCapacityError):
            store.store(_make_snapshot(portfolio_id="p2", risk_assessment_id="a2"))

    def test_query_by_portfolio(self):
        store = RiskSnapshotStore()
        store.store(_make_snapshot(portfolio_id="portZ", risk_assessment_id="a1"))
        store.store(_make_snapshot(portfolio_id="portZ", risk_assessment_id="a2"))
        store.store(_make_snapshot(portfolio_id="portW", risk_assessment_id="a3"))
        results = store.query_by_portfolio("portZ")
        assert len(results) == 2

    def test_query_by_status(self):
        store = RiskSnapshotStore()
        store.store(_make_snapshot())
        results = store.query_by_status(SnapshotStatus.PUBLISHED)
        assert len(results) == 1

    def test_query_by_score_range(self):
        store = RiskSnapshotStore()
        store.store(_make_snapshot(risk_score=30.0, risk_assessment_id="a1"))
        store.store(_make_snapshot(risk_score=70.0, risk_assessment_id="a2"))
        results = store.query_by_score_range(40.0, 80.0)
        assert len(results) == 1
        assert results[0].risk_score == 70.0

    def test_latest_for_portfolio(self):
        store = RiskSnapshotStore()
        store.store(_make_snapshot(portfolio_id="portX", risk_assessment_id="a1"))
        store.store(_make_snapshot(portfolio_id="portX", risk_assessment_id="a2"))
        latest = store.latest_for_portfolio("portX")
        assert latest is not None

    def test_delete(self):
        store = RiskSnapshotStore()
        s     = _make_snapshot()
        store.store(s)
        assert store.delete(s.snapshot_id) is True
        assert store.count() == 0

    def test_delete_nonexistent(self):
        store = RiskSnapshotStore()
        assert store.delete("nonexistent") is False

    def test_delete_by_portfolio(self):
        store = RiskSnapshotStore()
        store.store(_make_snapshot(portfolio_id="portDel", risk_assessment_id="a1"))
        store.store(_make_snapshot(portfolio_id="portDel", risk_assessment_id="a2"))
        store.store(_make_snapshot(portfolio_id="portKeep", risk_assessment_id="a3"))
        removed = store.delete_by_portfolio("portDel")
        assert removed == 2
        assert store.count() == 1

    def test_count_by_portfolio(self):
        store = RiskSnapshotStore()
        store.store(_make_snapshot(portfolio_id="pX", risk_assessment_id="a1"))
        store.store(_make_snapshot(portfolio_id="pX", risk_assessment_id="a2"))
        assert store.count_by_portfolio("pX") == 2

    def test_store_many(self):
        store = RiskSnapshotStore()
        snaps = [
            _make_snapshot(portfolio_id="p1", risk_assessment_id=f"a{i}")
            for i in range(5)
        ]
        count = store.store_many(snaps)
        assert count == 5
        assert store.count() == 5

    def test_clear(self):
        store = RiskSnapshotStore()
        store.store(_make_snapshot())
        store.clear()
        assert store.count() == 0

    def test_is_empty(self):
        store = RiskSnapshotStore()
        assert store.is_empty() is True

    def test_query_published(self):
        store = RiskSnapshotStore()
        store.store(_make_snapshot())
        assert len(store.query_published()) == 1


# ===========================================================================
# 19. Cache
# ===========================================================================

class TestRiskSnapshotCache:
    def test_put_and_get(self):
        cache = RiskSnapshotCache()
        s     = _make_snapshot()
        cache.put(s)
        assert cache.get(s.snapshot_id) is s

    def test_miss_returns_none(self):
        cache = RiskSnapshotCache()
        assert cache.get("nonexistent") is None

    def test_hit_rate(self):
        cache = RiskSnapshotCache()
        s     = _make_snapshot()
        cache.put(s)
        cache.get(s.snapshot_id)  # hit
        cache.get("missing")       # miss
        rate = cache.hit_rate()
        assert 0.0 < rate <= 1.0

    def test_expiry(self):
        cache = RiskSnapshotCache(ttl_s=0.01)
        s     = _make_snapshot()
        cache.put(s)
        time.sleep(0.05)
        assert cache.get(s.snapshot_id) is None

    def test_custom_ttl_per_entry(self):
        cache = RiskSnapshotCache(ttl_s=1_000.0)
        s     = _make_snapshot()
        cache.put(s, ttl_s=0.01)
        time.sleep(0.05)
        assert cache.get(s.snapshot_id) is None

    def test_capacity_exceeded(self):
        cache = RiskSnapshotCache(max_size=1)
        s1    = _make_snapshot(portfolio_id="p1", risk_assessment_id="a1")
        s2    = _make_snapshot(portfolio_id="p2", risk_assessment_id="a2")
        cache.put(s1)
        with pytest.raises(RiskSnapshotCapacityError):
            cache.put(s2)

    def test_invalidate(self):
        cache = RiskSnapshotCache()
        s     = _make_snapshot()
        cache.put(s)
        assert cache.invalidate(s.snapshot_id) is True
        assert cache.get(s.snapshot_id) is None

    def test_invalidate_nonexistent(self):
        cache = RiskSnapshotCache()
        assert cache.invalidate("nonexistent") is False

    def test_invalidate_for_portfolio(self):
        cache = RiskSnapshotCache()
        s1 = _make_snapshot(portfolio_id="portA", risk_assessment_id="a1")
        s2 = _make_snapshot(portfolio_id="portA", risk_assessment_id="a2")
        s3 = _make_snapshot(portfolio_id="portB", risk_assessment_id="a3")
        cache.put(s1)
        cache.put(s2)
        cache.put(s3)
        removed = cache.invalidate_for_portfolio("portA")
        assert removed == 2
        assert cache.size() == 1

    def test_contains(self):
        cache = RiskSnapshotCache()
        s     = _make_snapshot()
        assert cache.contains(s.snapshot_id) is False
        cache.put(s)
        assert cache.contains(s.snapshot_id) is True

    def test_evict_expired(self):
        cache = RiskSnapshotCache(ttl_s=0.01)
        s     = _make_snapshot()
        cache.put(s)
        time.sleep(0.05)
        removed = cache.evict_expired()
        assert removed >= 1

    def test_stats(self):
        cache = RiskSnapshotCache()
        stats = cache.stats()
        assert "size"      in stats
        assert "hits"      in stats
        assert "misses"    in stats
        assert "evictions" in stats
        assert "hit_rate"  in stats

    def test_clear(self):
        cache = RiskSnapshotCache()
        cache.put(_make_snapshot())
        cache.clear()
        assert cache.size() == 0

    def test_size(self):
        cache = RiskSnapshotCache()
        assert cache.size() == 0
        cache.put(_make_snapshot())
        assert cache.size() == 1


# ===========================================================================
# 20. History
# ===========================================================================

class TestRiskSnapshotHistory:
    def test_record_and_retrieve_snapshot(self):
        history = RiskSnapshotHistory()
        s       = _make_snapshot()
        history.record_snapshot(s)
        recent = history.recent_snapshots(1)
        assert len(recent) == 1
        assert recent[0] is s

    def test_record_event(self):
        history = RiskSnapshotHistory()
        e       = make_snapshot_built("s", "p", "actor")
        history.record_event(e)
        assert len(history.recent_events(1)) == 1

    def test_record_error(self):
        history = RiskSnapshotHistory()
        history.record_error(Exception("test"))
        assert len(history.recent_errors(1)) == 1

    def test_record_superseded(self):
        history = RiskSnapshotHistory()
        s       = _make_snapshot()
        history.record_superseded(s)

    def test_find_snapshot(self):
        history = RiskSnapshotHistory()
        s       = _make_snapshot()
        history.record_snapshot(s)
        found = history.find_snapshot(s.snapshot_id)
        assert found is s

    def test_find_snapshot_not_found(self):
        history = RiskSnapshotHistory()
        assert history.find_snapshot("nonexistent") is None

    def test_find_by_portfolio(self):
        history = RiskSnapshotHistory()
        s1 = _make_snapshot(portfolio_id="portH", risk_assessment_id="a1")
        s2 = _make_snapshot(portfolio_id="portH", risk_assessment_id="a2")
        s3 = _make_snapshot(portfolio_id="portI", risk_assessment_id="a3")
        history.record_snapshot(s1)
        history.record_snapshot(s2)
        history.record_snapshot(s3)
        found = history.find_by_portfolio("portH")
        assert len(found) == 2

    def test_find_by_assessment(self):
        history = RiskSnapshotHistory()
        s = _make_snapshot(risk_assessment_id="assess-X")
        history.record_snapshot(s)
        found = history.find_by_assessment("assess-X")
        assert len(found) == 1

    def test_counts(self):
        history = RiskSnapshotHistory()
        history.record_snapshot(_make_snapshot())
        history.record_event(make_snapshot_built("s", "p", "a"))
        history.record_error(Exception("err"))
        counts = history.counts()
        assert counts["snapshots"] == 1
        assert counts["events"]    == 1
        assert counts["errors"]    == 1

    def test_clear(self):
        history = RiskSnapshotHistory()
        history.record_snapshot(_make_snapshot())
        history.clear()
        assert history.counts()["snapshots"] == 0

    def test_ring_buffer_bounded(self):
        history = RiskSnapshotHistory(max_items=3)
        for i in range(5):
            history.record_snapshot(_make_snapshot(
                portfolio_id=f"p{i}", risk_assessment_id=f"a{i}"
            ))
        assert len(history.recent_snapshots(10)) == 3


# ===========================================================================
# 21. Statistics
# ===========================================================================

class TestRiskSnapshotStatistics:
    def test_initial_state(self):
        stats = RiskSnapshotStatistics()
        snap  = stats.snapshot()
        assert snap["built"]     == 0
        assert snap["published"] == 0
        assert snap["failed"]    == 0

    def test_record_built(self):
        stats = RiskSnapshotStatistics()
        stats.record_built()
        stats.record_built()
        assert stats.total_built() == 2

    def test_record_published(self):
        stats = RiskSnapshotStatistics()
        stats.record_published()
        assert stats.total_published() == 1

    def test_record_failed(self):
        stats = RiskSnapshotStatistics()
        stats.record_failed()
        assert stats.total_failed() == 1

    def test_record_superseded(self):
        stats = RiskSnapshotStatistics()
        stats.record_superseded()
        snap  = stats.snapshot()
        assert snap["superseded"] == 1

    def test_record_archived(self):
        stats = RiskSnapshotStatistics()
        stats.record_archived()
        snap  = stats.snapshot()
        assert snap["archived"] == 1

    def test_record_retrieved(self):
        stats = RiskSnapshotStatistics()
        stats.record_retrieved()
        snap  = stats.snapshot()
        assert snap["retrieved"] == 1

    def test_record_validated(self):
        stats = RiskSnapshotStatistics()
        stats.record_validated()
        snap  = stats.snapshot()
        assert snap["validated"] == 1

    def test_record_bundled(self):
        stats = RiskSnapshotStatistics()
        stats.record_bundled()
        snap  = stats.snapshot()
        assert snap["bundled"] == 1

    def test_record_build_time(self):
        stats = RiskSnapshotStatistics()
        stats.record_build_time(0.5)
        stats.record_build_time(1.5)
        snap = stats.snapshot()
        assert snap["avg_build_s"] == 1.0

    def test_reset(self):
        stats = RiskSnapshotStatistics()
        stats.record_built()
        stats.reset()
        assert stats.total_built() == 0

    def test_snapshot_keys(self):
        stats = RiskSnapshotStatistics()
        snap  = stats.snapshot()
        for key in ("built", "published", "superseded", "archived",
                    "failed", "retrieved", "validated", "bundled",
                    "avg_build_s", "reset_at"):
            assert key in snap


# ===========================================================================
# 22. Bundle
# ===========================================================================

class TestRiskSnapshotBundle:
    def test_create_empty(self):
        bundle = RiskSnapshotBundle.create([])
        assert bundle.bundle_size  == 0
        assert bundle.avg_risk_score == 0.0

    def test_create_with_snapshots(self):
        snaps  = [
            _make_snapshot(risk_score=40.0, portfolio_id="p1", risk_assessment_id="a1"),
            _make_snapshot(risk_score=60.0, portfolio_id="p2", risk_assessment_id="a2"),
        ]
        bundle = RiskSnapshotBundle.create(snaps)
        assert bundle.bundle_size    == 2
        assert bundle.avg_risk_score == 50.0
        assert bundle.max_risk_score == 60.0
        assert bundle.min_risk_score == 40.0

    def test_capacity_exceeded(self):
        snaps = [
            _make_snapshot(portfolio_id=f"p{i}", risk_assessment_id=f"a{i}")
            for i in range(5)
        ]
        with pytest.raises(RiskSnapshotCapacityError):
            RiskSnapshotBundle.create(snaps, max_size=3)

    def test_explicit_bundle_id(self):
        bundle = RiskSnapshotBundle.create([], bundle_id="bundle-1")
        assert bundle.bundle_id == "bundle-1"

    def test_len(self):
        snaps  = [_make_snapshot(portfolio_id=f"p{i}", risk_assessment_id=f"a{i}") for i in range(3)]
        bundle = RiskSnapshotBundle.create(snaps)
        assert len(bundle) == 3

    def test_iter(self):
        snaps  = [_make_snapshot(portfolio_id=f"p{i}", risk_assessment_id=f"a{i}") for i in range(2)]
        bundle = RiskSnapshotBundle.create(snaps)
        count  = sum(1 for _ in bundle)
        assert count == 2

    def test_contains(self):
        s      = _make_snapshot()
        bundle = RiskSnapshotBundle.create([s])
        assert s.snapshot_id in bundle
        assert "nonexistent" not in bundle

    def test_get(self):
        s      = _make_snapshot()
        bundle = RiskSnapshotBundle.create([s])
        assert bundle.get(s.snapshot_id) is s
        assert bundle.get("nonexistent") is None

    def test_filter_by_portfolio(self):
        s1 = _make_snapshot(portfolio_id="portA", risk_assessment_id="a1")
        s2 = _make_snapshot(portfolio_id="portB", risk_assessment_id="a2")
        bundle = RiskSnapshotBundle.create([s1, s2])
        result = bundle.filter_by_portfolio("portA")
        assert len(result) == 1
        assert result[0].portfolio_id == "portA"

    def test_portfolio_ids(self):
        s1 = _make_snapshot(portfolio_id="pA", risk_assessment_id="a1")
        s2 = _make_snapshot(portfolio_id="pB", risk_assessment_id="a2")
        bundle = RiskSnapshotBundle.create([s1, s2])
        assert "pA" in bundle.portfolio_ids
        assert "pB" in bundle.portfolio_ids

    def test_to_dict(self):
        bundle = RiskSnapshotBundle.create([_make_snapshot()])
        data   = bundle.to_dict()
        assert "bundle_id"        in data
        assert "bundle_size"      in data
        assert "avg_risk_score"   in data

    def test_frozen(self):
        bundle = RiskSnapshotBundle.create([])
        with pytest.raises(Exception):
            bundle.bundle_size = 99  # type: ignore[misc]


# ===========================================================================
# 23. BundleBuilder
# ===========================================================================

class TestRiskSnapshotBundleBuilder:
    def test_add_and_build(self):
        builder = RiskSnapshotBundleBuilder()
        s = _make_snapshot()
        builder.add(s)
        bundle = builder.build()
        assert bundle.bundle_size == 1

    def test_size(self):
        builder = RiskSnapshotBundleBuilder()
        assert builder.size() == 0
        builder.add(_make_snapshot())
        assert builder.size() == 1

    def test_capacity_exceeded(self):
        builder = RiskSnapshotBundleBuilder(max_size=1)
        builder.add(_make_snapshot(portfolio_id="p1", risk_assessment_id="a1"))
        with pytest.raises(RiskSnapshotCapacityError):
            builder.add(_make_snapshot(portfolio_id="p2", risk_assessment_id="a2"))

    def test_explicit_bundle_id(self):
        builder = RiskSnapshotBundleBuilder()
        bundle  = builder.build(bundle_id="b-123")
        assert bundle.bundle_id == "b-123"

    def test_chaining(self):
        s1 = _make_snapshot(portfolio_id="p1", risk_assessment_id="a1")
        s2 = _make_snapshot(portfolio_id="p2", risk_assessment_id="a2")
        bundle = (
            RiskSnapshotBundleBuilder()
            .add(s1)
            .add(s2)
            .build()
        )
        assert bundle.bundle_size == 2


# ===========================================================================
# 24. Serialization
# ===========================================================================

class TestSerialization:
    def test_snapshot_to_dict_is_dict(self):
        s    = _make_snapshot()
        data = s.to_dict()
        assert isinstance(data, dict)

    def test_summary_to_dict(self):
        s    = RiskSnapshotSummary.from_score(50.0, "completed")
        data = s.to_dict()
        assert isinstance(data, dict)

    def test_domain_risk_summary_to_dict(self):
        d    = DomainRiskSummary("market_risk", 40.0, RiskLevel.LOW, 0.1)
        data = d.to_dict()
        assert isinstance(data, dict)

    def test_quantitative_metrics_to_dict(self):
        m    = QuantitativeMetrics(var_95=10_000.0)
        data = m.to_dict()
        assert isinstance(data, dict)

    def test_stress_test_summary_to_dict(self):
        s    = StressTestSummary(tests_executed=4)
        data = s.to_dict()
        assert isinstance(data, dict)

    def test_optimization_summary_to_dict(self):
        o    = OptimizationSummary(status="completed")
        data = o.to_dict()
        assert isinstance(data, dict)

    def test_policy_summary_to_dict(self):
        p    = PolicySummary(violations=1)
        data = p.to_dict()
        assert isinstance(data, dict)

    def test_system_health_to_dict(self):
        h    = SystemHealthSummary()
        data = h.to_dict()
        assert isinstance(data, dict)

    def test_audit_to_dict(self):
        a    = SnapshotAudit()
        data = a.to_dict()
        assert isinstance(data, dict)

    def test_metadata_to_dict(self):
        m    = SnapshotMetadata(environment="test")
        data = m.to_dict()
        assert isinstance(data, dict)

    def test_assessment_summary_to_dict(self):
        s    = AssessmentSummarySection.build_uniform(50.0)
        data = s.to_dict()
        assert isinstance(data, dict)

    def test_event_to_dict_is_dict(self):
        e    = make_snapshot_built("s", "p", "a")
        data = e.to_dict()
        assert isinstance(data, dict)

    def test_bundle_to_dict(self):
        bundle = RiskSnapshotBundle.create([_make_snapshot()])
        data   = bundle.to_dict()
        assert isinstance(data, dict)

    def test_statistics_section_to_dict(self):
        s    = SnapshotStatisticsSection(assessment_duration_s=1.0)
        data = s.to_dict()
        assert isinstance(data, dict)


# ===========================================================================
# 25. Versioning
# ===========================================================================

class TestVersioning:
    def test_default_snapshot_version_1(self):
        s = _make_snapshot()
        assert s.snapshot_version == 1

    def test_explicit_snapshot_version(self):
        s = RiskSnapshot.create(
            risk_session_id    = "s",
            risk_assessment_id = "a",
            portfolio_id       = "p",
            risk_score         = 50.0,
            assessment_status  = "completed",
            snapshot_version   = 5,
        )
        assert s.snapshot_version == 5

    def test_version_in_builder(self):
        s = (
            RiskSnapshotBuilder()
            .set_identity("s", "a", "p")
            .set_risk_score(50.0, "completed")
            .set_versioning(risk_version="2.1.0", snapshot_version=7)
            .build()
        )
        assert s.risk_version    == "2.1.0"
        assert s.snapshot_version == 7

    def test_framework_version_default(self):
        s = _make_snapshot()
        assert s.framework_version == VERSION

    def test_versions_in_registry(self):
        reg = RiskSnapshotRegistry()
        s1  = _make_snapshot(risk_assessment_id="assess-ver")
        s2  = _make_snapshot(risk_assessment_id="assess-ver")
        reg.register(s1)
        reg.register(s2)
        versions = reg.versions_for_assessment("assess-ver")
        assert len(versions) == 2


# ===========================================================================
# 26. Regression — full build/validate/publish cycle
# ===========================================================================

class TestRegression:
    def test_full_cycle(self):
        """Build → validate → register → store → cache → retrieve."""
        # Build
        qm   = QuantitativeMetrics(var_95=100_000.0, var_95_pct=0.05)
        sts  = StressTestSummary(tests_executed=8, worst_case_loss=800_000.0)
        opts = OptimizationSummary(status="completed", optimization_gain=12.0)
        ps   = PolicySummary(policy_decision="approve", violations=0)
        meta = SnapshotMetadata(environment="production")

        snapshot = (
            RiskSnapshotBuilder()
            .set_identity("sess-regression", "assess-regression", "port-regression",
                          workflow_id="wf-1", strategy_id="strat-1")
            .set_classification(risk_scope=RiskScope.PORTFOLIO, risk_type=RiskType.COMPOSITE)
            .set_risk_score(48.0, "completed", trend=RiskTrend.STABLE, confidence=0.95)
            .set_quantitative_metrics_obj(qm)
            .set_stress_test_summary_obj(sts)
            .set_optimization_summary_obj(opts)
            .set_policy_summary_obj(ps)
            .set_metadata_obj(meta)
            .build(validate=True)
        )

        # Validate
        validator = RiskSnapshotValidator()
        result    = validator.validate(snapshot)
        assert result.passed is True

        # Register
        registry = RiskSnapshotRegistry()
        registry.register(snapshot)
        assert registry.get(snapshot.snapshot_id) is snapshot

        # Store
        store = RiskSnapshotStore()
        store.store(snapshot)
        loaded = store.load(snapshot.snapshot_id)
        assert loaded is snapshot

        # Cache
        cache = RiskSnapshotCache()
        cache.put(snapshot)
        cached = cache.get(snapshot.snapshot_id)
        assert cached is snapshot

        # History
        history = RiskSnapshotHistory()
        history.record_snapshot(snapshot)
        assert history.find_snapshot(snapshot.snapshot_id) is snapshot

        # Statistics
        stats = RiskSnapshotStatistics()
        stats.record_built()
        stats.record_published()
        stats.record_build_time(0.012)
        snap = stats.snapshot()
        assert snap["built"]     == 1
        assert snap["published"] == 1

        # Bundle
        bundle = RiskSnapshotBundle.create([snapshot])
        assert bundle.bundle_size   == 1
        assert snapshot.snapshot_id in bundle

        # Events
        evt = make_snapshot_published(
            snapshot.snapshot_id, snapshot.portfolio_id, "iios:system"
        )
        assert evt.event_type == SnapshotEventType.SNAPSHOT_PUBLISHED

    def test_factory_to_registry_cycle(self):
        """Use factory to create snapshot, then register and retrieve."""
        factory = RiskSnapshotFactory()
        mock_r  = MagicMock()
        mock_r.assessment_id     = "assess-f1"
        mock_r.portfolio_id      = "port-f1"
        mock_r.risk_score        = 38.0
        mock_r.duration_s        = 0.8
        mock_r.published_at      = time.time()
        mock_r.status            = MagicMock(value="completed")
        mock_r.var_report        = None
        mock_r.es_report         = None
        mock_r.stress_test_report = None
        mock_r.exposure_report   = None
        mock_r.summary           = None
        mock_r.optimization_report = None
        mock_r.mitigation_plan   = None
        mock_r.model_version     = VERSION

        snapshot = factory.from_assessment_report(mock_r, "sess-f1")
        assert snapshot.risk_score == 38.0

        registry = RiskSnapshotRegistry()
        registry.register(snapshot)
        assert registry.latest_for_portfolio("port-f1") is snapshot

    def test_multi_version_history(self):
        """Simulate multiple snapshot versions for the same assessment."""
        registry = RiskSnapshotRegistry()
        history  = RiskSnapshotHistory()
        stats    = RiskSnapshotStatistics()

        for version in range(1, 4):
            s = (
                RiskSnapshotBuilder()
                .set_identity("sess-mv", "assess-mv", "port-mv")
                .set_versioning(snapshot_version=version)
                .set_risk_score(40.0 + version * 5.0, "completed")
                .build()
            )
            registry.register(s)
            history.record_snapshot(s)
            stats.record_built()
            stats.record_published()

        assert len(registry.versions_for_assessment("assess-mv")) == 3
        assert len(history.find_by_assessment("assess-mv"))        == 3
        assert stats.total_built() == 3

    def test_snapshot_immutability_preserved_through_pipeline(self):
        """Snapshot cannot be mutated anywhere in the pipeline."""
        s = _make_snapshot()
        with pytest.raises(Exception):
            object.__setattr__(s, "risk_score", 99.0)

    def test_invalid_snapshot_rejected_at_build(self):
        """Builder with invalid metric rejects during build."""
        bad = QuantitativeMetrics(var_95=-1.0)
        with pytest.raises(RiskSnapshotBuilderError):
            (
                RiskSnapshotBuilder()
                .set_identity("s", "a", "p")
                .set_risk_score(50.0, "completed")
                .set_quantitative_metrics_obj(bad)
                .build(validate=True)
            )

    def test_large_bundle(self):
        """Bundling 100 snapshots in one operation."""
        snaps = [
            _make_snapshot(
                risk_score   = float(i),
                portfolio_id = f"port-{i}",
                risk_assessment_id = f"assess-{i}",
            )
            for i in range(100)
        ]
        bundle = RiskSnapshotBundle.create(snaps)
        assert bundle.bundle_size  == 100
        assert bundle.min_risk_score == 0.0
        assert bundle.max_risk_score == 99.0
