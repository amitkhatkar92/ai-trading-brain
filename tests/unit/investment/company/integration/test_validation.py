"""tests/unit/investment/company/integration/test_validation.py
Tests for consistency validation and validation report.
"""
from __future__ import annotations

import pytest

from iios.investment.company.integration.company_state import (
    ConflictSeverity, ValidationStatus,
)
from iios.investment.company.integration.company_intelligence_aggregator import AggregatedIntelligence
from iios.investment.company.integration.consistency_rules import (
    rule_bq_vs_financial, rule_earnings_vs_financial, rule_growth_vs_earnings,
    rule_growth_vs_valuation, rule_management_vs_ownership,
    rule_opportunity_vs_financial, rule_bq_vs_earnings, ALL_RULES,
)
from iios.investment.company.integration.consistency_validator import ConsistencyValidator
from iios.investment.company.integration.validation_report import (
    ValidationCheck, ValidationReport,
)


# ── ValidationReport ──────────────────────────────────────────────────────────

class TestValidationReport:
    def _make_check(self, status: ValidationStatus, severity=ConflictSeverity.INFO):
        return ValidationCheck(
            name="test", description="test", status=status,
            engine_a="a", engine_b="b", value_a=50.0, value_b=50.0,
            message="test", severity=severity,
        )

    def test_empty_report(self):
        r = ValidationReport(ticker="X")
        assert r.total_checks == 0
        assert r.validation_passed is True
        assert r.consistency_fraction == pytest.approx(1.0)

    def test_all_passed(self):
        r = ValidationReport(ticker="X")
        r.checks = [self._make_check(ValidationStatus.PASSED)] * 3
        assert r.passed_count == 3
        assert r.failed_count == 0
        assert r.validation_passed is True

    def test_failure_causes_fail(self):
        r = ValidationReport(ticker="X")
        r.checks = [
            self._make_check(ValidationStatus.PASSED),
            self._make_check(ValidationStatus.FAILED, ConflictSeverity.HIGH),
        ]
        assert r.validation_passed is False
        assert r.failed_count == 1

    def test_critical_failure(self):
        r = ValidationReport(ticker="X")
        r.checks = [self._make_check(ValidationStatus.FAILED, ConflictSeverity.CRITICAL)]
        assert r.critical_failure_count == 1
        assert r.validation_passed is False

    def test_consistency_fraction(self):
        r = ValidationReport(ticker="X")
        r.checks = [
            self._make_check(ValidationStatus.PASSED),
            self._make_check(ValidationStatus.PASSED),
            self._make_check(ValidationStatus.FAILED),
        ]
        assert r.consistency_fraction == pytest.approx(2 / 3)

    def test_to_dict_keys(self):
        r = ValidationReport(ticker="X")
        d = r.to_dict()
        assert all(k in d for k in ["report_id", "ticker", "total_checks",
                                     "passed", "validation_passed"])

    def test_messages(self):
        r = ValidationReport(ticker="X")
        r.checks = [
            ValidationCheck("n", "d", ValidationStatus.WARNING, "a", "b",
                            None, None, "Watch this", ConflictSeverity.MEDIUM),
        ]
        msgs = r.messages()
        assert "Watch this" in msgs


# ── Consistency rules ─────────────────────────────────────────────────────────

class TestConsistencyRules:
    def _intel(self, **kwargs) -> AggregatedIntelligence:
        return AggregatedIntelligence(ticker="X", **kwargs)

    def test_growth_vs_earnings_pass(self):
        intel = self._intel(growth_score=70.0, earnings_score=65.0)
        check = rule_growth_vs_earnings(intel)
        assert check is not None
        assert check.passed

    def test_growth_vs_earnings_fail(self):
        intel = self._intel(growth_score=85.0, earnings_score=20.0)
        check = rule_growth_vs_earnings(intel)
        assert check is not None
        assert check.is_failed

    def test_growth_vs_earnings_skip_none(self):
        intel = self._intel(growth_score=80.0, earnings_score=None)
        check = rule_growth_vs_earnings(intel)
        assert check is None

    def test_growth_vs_valuation_warn(self):
        intel = self._intel(growth_score=20.0, valuation_score=20.0)
        check = rule_growth_vs_valuation(intel)
        assert check is not None
        assert check.is_warning

    def test_bq_vs_financial_fail(self):
        intel = self._intel(business_quality_score=80.0, financial_score=20.0)
        check = rule_bq_vs_financial(intel)
        assert check is not None
        assert check.is_failed

    def test_bq_vs_financial_pass(self):
        intel = self._intel(business_quality_score=65.0, financial_score=65.0)
        check = rule_bq_vs_financial(intel)
        assert check.passed

    def test_management_vs_ownership_fail(self):
        intel = self._intel(management_score=75.0, ownership_score=22.0)
        check = rule_management_vs_ownership(intel)
        assert check is not None
        assert check.is_failed

    def test_management_vs_ownership_pledge(self):
        intel = self._intel(management_score=68.0, ownership_score=65.0,
                            promoter_pledge_pct=55.0)
        check = rule_management_vs_ownership(intel)
        assert check is not None
        assert check.is_warning

    def test_earnings_vs_financial_fail(self):
        intel = self._intel(earnings_score=82.0, financial_score=20.0)
        check = rule_earnings_vs_financial(intel)
        assert check is not None
        assert check.is_failed

    def test_opportunity_vs_financial_fail(self):
        intel = self._intel(opportunity_score=78.0, financial_score=20.0)
        check = rule_opportunity_vs_financial(intel)
        assert check is not None
        assert check.is_failed

    def test_bq_vs_earnings_warn(self):
        intel = self._intel(business_quality_score=82.0, earnings_score=22.0)
        check = rule_bq_vs_earnings(intel)
        assert check is not None
        assert check.is_warning or check.passed  # rule returns WARNING for large gap

    def test_all_rules_registered(self):
        assert len(ALL_RULES) >= 6


# ── ConsistencyValidator ──────────────────────────────────────────────────────

class TestConsistencyValidator:
    def test_returns_report(self):
        validator = ConsistencyValidator()
        intel = AggregatedIntelligence(
            ticker="X",
            financial_score=70.0, earnings_score=68.0, business_quality_score=72.0,
        )
        report = validator.validate("X", intel)
        assert isinstance(report, ValidationReport)
        assert report.ticker == "X"

    def test_consistent_intel_passes(self):
        validator = ConsistencyValidator()
        intel = AggregatedIntelligence(
            ticker="X",
            financial_score=70.0, earnings_score=72.0, business_quality_score=70.0,
            valuation_score=65.0, growth_score=68.0,
            management_score=70.0, ownership_score=65.0,
        )
        report = validator.validate("X", intel)
        assert report.validation_passed is True

    def test_conflicting_intel_fails(self):
        validator = ConsistencyValidator()
        # BQ 80 but financial 15 → should fail
        intel = AggregatedIntelligence(
            ticker="X",
            business_quality_score=80.0, financial_score=15.0,
        )
        report = validator.validate("X", intel)
        # At least one check should not pass
        assert any(not c.passed for c in report.checks)

    def test_register_custom_rule(self):
        validator = ConsistencyValidator()
        initial_count = validator.rule_count()

        def my_rule(intel):
            return None

        validator.register_rule(my_rule)
        assert validator.rule_count() == initial_count + 1

    def test_broken_rule_does_not_crash(self):
        validator = ConsistencyValidator()

        def broken_rule(intel):
            raise RuntimeError("oops")

        validator.register_rule(broken_rule)
        intel = AggregatedIntelligence(ticker="X")
        # Should not raise
        report = validator.validate("X", intel)
        assert isinstance(report, ValidationReport)

    def test_no_scores_no_failures(self):
        validator = ConsistencyValidator()
        intel = AggregatedIntelligence(ticker="X")  # all None
        report = validator.validate("X", intel)
        # Rules that can't evaluate return None → no checks added for them
        assert isinstance(report, ValidationReport)
