"""tests/unit/investment/portfolio/integration/test_integration_types.py

Tests for integration_types.py: enums, constants, parameters, utilities.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.integration.integration_types import (
    ALL_ENGINE_IDS,
    REQUIRED_ENGINES,
    AggregationStatus,
    ConflictResolutionStatus,
    ConflictSeverity,
    EngineId,
    HealthStatus,
    IntegrationParameters,
    QualityGrade,
    SnapshotStatus,
    ValidationStatus,
    hours_since,
    now_utc,
    score_to_grade,
)


class TestEnums:
    def test_engine_id_has_9_values(self):
        assert len(EngineId) == 9

    def test_required_engines_tuple(self):
        assert len(REQUIRED_ENGINES) == 9
        assert all(isinstance(e, EngineId) for e in REQUIRED_ENGINES)

    def test_all_engine_ids_covers_required(self):
        assert set(REQUIRED_ENGINES).issubset(set(ALL_ENGINE_IDS))

    def test_aggregation_status_values(self):
        for v in ("complete", "partial", "stale", "invalid"):
            assert AggregationStatus(v)

    def test_quality_grade_values(self):
        for v in ("A", "B", "C", "D", "F"):
            assert QualityGrade(v)

    def test_health_status_values(self):
        for v in ("healthy", "degraded", "critical", "offline"):
            assert HealthStatus(v)

    def test_snapshot_status_values(self):
        for v in ("draft", "validated", "published", "stale", "archived"):
            assert SnapshotStatus(v)

    def test_str_enum_equality(self):
        assert EngineId.RISK == "risk"


class TestIntegrationParameters:
    def test_defaults(self):
        p = IntegrationParameters()
        assert p.min_completeness == 0.70
        assert p.min_consistency  == 0.75
        assert p.freshness_hours  == 4.0
        assert p.min_quality_to_publish == 0.60

    def test_custom_params(self):
        p = IntegrationParameters(min_completeness=0.90, freshness_hours=2.0)
        assert p.min_completeness == 0.90
        assert p.freshness_hours  == 2.0

    def test_frozen(self):
        p = IntegrationParameters()
        with pytest.raises((AttributeError, TypeError)):
            p.min_completeness = 0.99  # type: ignore

    def test_weights_sum(self):
        p = IntegrationParameters()
        total = (
            p.weight_completeness + p.weight_consistency
            + p.weight_freshness  + p.weight_confidence
            + p.weight_coverage
        )
        assert abs(total - 1.0) < 1e-9


class TestUtilities:
    def test_now_utc_is_string(self):
        s = now_utc()
        assert isinstance(s, str)
        assert "T" in s

    def test_hours_since_recent(self):
        h = hours_since(now_utc())
        assert h < 0.01

    def test_hours_since_invalid(self):
        h = hours_since("not-a-date")
        assert h == float("inf")

    def test_score_to_grade_a(self):
        assert score_to_grade(0.90) == QualityGrade.A

    def test_score_to_grade_b(self):
        assert score_to_grade(0.75) == QualityGrade.B

    def test_score_to_grade_f(self):
        assert score_to_grade(0.10) == QualityGrade.F

    def test_score_to_grade_boundary(self):
        assert score_to_grade(0.85) == QualityGrade.A
        assert score_to_grade(0.84) == QualityGrade.B
