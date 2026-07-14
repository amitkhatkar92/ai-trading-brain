"""Tests for signal comparator and equivalence checker."""
import pytest

from iios.investment.strategy.migration.signal_comparator import (
    SignalComparator,
    SignalField,
    FieldComparison,
    SignalComparison,
)
from iios.investment.strategy.migration.signal_equivalence import (
    SignalEquivalenceChecker,
    EquivalenceResult,
)
from iios.investment.strategy.migration.adapter_factory import AdapterFactory
from iios.investment.strategy.migration.behavior_validator import (
    BehaviorValidator,
    BehaviorTestCase,
    BehaviorReport,
)


class TestSignalComparator:
    def setup_method(self):
        self.comparator = SignalComparator()

    def test_exact_match(self):
        params = {"min_rr": 2.0, "max_loss_pct": 0.02}
        result = self.comparator.compare(
            "id1", "Strategy", params, params.copy()
        )
        assert result.overall_match
        assert result.match_rate == 1.0

    def test_float_mismatch_above_tolerance(self):
        legacy  = {"min_rr": 2.0}
        adapted = {"min_rr": 2.1}
        result  = self.comparator.compare("id1", "S", legacy, adapted)
        assert "min_rr" in result.mismatched_fields

    def test_float_match_within_tolerance(self):
        legacy  = {"min_rr": 2.0}
        adapted = {"min_rr": 2.0 + 1e-9}
        result  = self.comparator.compare("id1", "S", legacy, adapted, tolerance=1e-6)
        assert result.overall_match

    def test_string_mismatch(self):
        legacy  = {"direction": "BUY"}
        adapted = {"direction": "SELL"}
        result  = self.comparator.compare("id1", "S", legacy, adapted)
        assert "direction" in result.mismatched_fields

    def test_both_none_skip(self):
        legacy  = {"min_rr": None, "max_loss_pct": 0.02}
        adapted = {"min_rr": None, "max_loss_pct": 0.02}
        result  = self.comparator.compare("id1", "S", legacy, adapted)
        # None-None pairs are skipped
        assert len(result.field_comparisons) >= 1

    def test_to_dict(self):
        params = {"min_rr": 2.0}
        result = self.comparator.compare("id1", "S", params, params.copy())
        d = result.to_dict()
        assert "strategy_id" in d
        assert "overall_match" in d

    def test_field_comparison_to_dict(self):
        params = {"min_rr": 2.0}
        result = self.comparator.compare("id1", "S", params, params.copy())
        for fc in result.field_comparisons:
            d = fc.to_dict()
            assert "field" in d
            assert "match" in d


class TestSignalEquivalenceChecker:
    def setup_method(self):
        self.checker = SignalEquivalenceChecker()
        self.factory = AdapterFactory()

    def test_equivalent_parameters(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        result  = self.checker.check(basic_metadata, adapter)
        assert isinstance(result, EquivalenceResult)
        assert result.is_equivalent

    def test_result_has_confidence(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        result  = self.checker.check(basic_metadata, adapter)
        assert 0 <= result.confidence <= 100

    def test_result_to_dict(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        result  = self.checker.check(basic_metadata, adapter)
        d = result.to_dict()
        assert "strategy_id" in d
        assert "is_equivalent" in d

    def test_with_test_cases_no_conditions(self, basic_metadata, behavior_test_cases):
        adapter = self.factory.create(basic_metadata)
        result  = self.checker.check(basic_metadata, adapter, behavior_test_cases)
        assert isinstance(result, EquivalenceResult)

    def test_equivalence_with_entry_conditions(self, json_metadata):
        adapter = self.factory.create(json_metadata)
        test_cases = [
            {"rsi": 25.0, "volume_ratio": 2.0},
            {"rsi": 60.0, "volume_ratio": 0.5},
        ]
        result = self.checker.check(json_metadata, adapter, test_cases)
        assert result.is_equivalent

    def test_failed_fields_list(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        result  = self.checker.check(basic_metadata, adapter)
        assert isinstance(result.failed_fields, list)

    def test_summary_string(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        result  = self.checker.check(basic_metadata, adapter)
        assert isinstance(result.summary, str) and len(result.summary) > 0


class TestBehaviorValidator:
    def setup_method(self):
        self.validator = BehaviorValidator()
        self.factory   = AdapterFactory()

    def test_no_test_cases_trivial_pass(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        report  = self.validator.validate(basic_metadata, adapter, [])
        assert report.is_equivalent
        assert report.test_case_count == 0

    def test_with_matching_conditions(self, json_metadata):
        adapter = self.factory.create(json_metadata)
        test_cases = [
            BehaviorTestCase("tc1", {"rsi": 25.0, "volume_ratio": 2.0}, True),
            BehaviorTestCase("tc2", {"rsi": 60.0, "volume_ratio": 0.5}, False),
        ]
        report = self.validator.validate(json_metadata, adapter, test_cases)
        assert isinstance(report, BehaviorReport)
        assert report.passed == 2

    def test_pass_rate(self, json_metadata):
        adapter = self.factory.create(json_metadata)
        test_cases = [
            BehaviorTestCase("tc1", {"rsi": 25.0, "volume_ratio": 2.0}, True),
            BehaviorTestCase("tc2", {"rsi": 60.0, "volume_ratio": 0.5}, False),
        ]
        report = self.validator.validate(json_metadata, adapter, test_cases)
        assert abs(report.pass_rate - 1.0) < 0.01

    def test_report_to_dict(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        report  = self.validator.validate(basic_metadata, adapter, [])
        d = report.to_dict()
        assert "strategy_id" in d
        assert "is_equivalent" in d

    def test_equivalence_threshold(self, basic_metadata):
        validator = BehaviorValidator(pass_threshold=0.80)
        adapter   = self.factory.create(basic_metadata)
        report    = validator.validate(basic_metadata, adapter, [])
        assert report.threshold == 0.80
