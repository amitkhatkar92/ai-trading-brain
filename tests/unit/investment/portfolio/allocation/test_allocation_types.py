"""test_allocation_types.py — Enums and constants."""
import pytest
from iios.investment.portfolio.allocation.allocation_types import (
    AllocationDirection,
    AllocationMethod,
    AllocationQualityGrade,
    AllocationRunStatus,
    ALLOCATION_PLAN_SCHEMA_VERSION,
    ALLOCATION_RESULT_SCHEMA_VERSION,
    CAPITAL_CONSERVATION_TOLERANCE,
    CapitalDistributionStatus,
    DEFAULT_CASH_RESERVE_PCT,
    DEFAULT_MAX_POSITION_WEIGHT,
    DEFAULT_MIN_POSITION_WEIGHT,
    ExposureStatus,
    MIN_POSITION_DOLLARS,
)


class TestAllocationRunStatus:
    def test_terminal_states(self):
        assert AllocationRunStatus.COMPLETED.is_terminal
        assert AllocationRunStatus.FAILED.is_terminal
        assert AllocationRunStatus.CANCELLED.is_terminal

    def test_non_terminal_states(self):
        assert not AllocationRunStatus.PENDING.is_terminal
        assert not AllocationRunStatus.IN_PROGRESS.is_terminal

    def test_successful(self):
        assert AllocationRunStatus.COMPLETED.is_successful
        assert not AllocationRunStatus.FAILED.is_successful


class TestCapitalDistributionStatus:
    def test_healthy_states(self):
        assert CapitalDistributionStatus.FULLY_INVESTED.is_healthy
        assert CapitalDistributionStatus.PARTIALLY_INVESTED.is_healthy

    def test_unhealthy_states(self):
        assert not CapitalDistributionStatus.OVER_ALLOCATED.is_healthy
        assert not CapitalDistributionStatus.CASH_HEAVY.is_healthy
        assert not CapitalDistributionStatus.UNDER_INVESTED.is_healthy


class TestExposureStatus:
    def test_compliant(self):
        assert ExposureStatus.WITHIN_LIMITS.is_compliant
        assert ExposureStatus.AT_LIMIT.is_compliant

    def test_non_compliant(self):
        assert not ExposureStatus.OVER_LIMIT.is_compliant
        assert not ExposureStatus.UNKNOWN.is_compliant


class TestAllocationQualityGrade:
    def test_all_grades_exist(self):
        for grade in ("A", "B", "C", "D", "F"):
            assert AllocationQualityGrade(grade)


class TestConstants:
    def test_defaults_in_range(self):
        assert 0.0 < DEFAULT_CASH_RESERVE_PCT < 1.0
        assert 0.0 < DEFAULT_MAX_POSITION_WEIGHT < 1.0
        assert 0.0 < DEFAULT_MIN_POSITION_WEIGHT < DEFAULT_MAX_POSITION_WEIGHT
        assert MIN_POSITION_DOLLARS > 0
        assert CAPITAL_CONSERVATION_TOLERANCE > 0

    def test_schema_versions_are_strings(self):
        assert isinstance(ALLOCATION_PLAN_SCHEMA_VERSION, str)
        assert isinstance(ALLOCATION_RESULT_SCHEMA_VERSION, str)


class TestAllocationMethod:
    def test_blueprint_weight_value(self):
        assert AllocationMethod.BLUEPRINT_WEIGHT == "blueprint_weight"

    def test_all_methods_are_string_enum(self):
        for m in AllocationMethod:
            assert isinstance(m.value, str)
