"""tests/unit/investment/market/integration/test_consistency.py"""
from __future__ import annotations

import pytest

from iios.investment.market.integration.aggregation_engine import AggregationEngine
from iios.investment.market.integration.consistency_rules import (
    BUILT_IN_RULES,
    ConsistencyRule,
    _both_present,
)
from iios.investment.market.integration.consistency_validator import ConsistencyValidator
from iios.investment.market.integration.models import (
    ConflictSeverity,
    ConflictType,
    ValidationStatus,
)


class TestBuiltInRules:
    def test_trend_up_in_bear_regime_fires(self):
        from iios.investment.market.integration.aggregation_state import AggregationState
        state = AggregationState(
            bar_index=1, timestamp=1.0,
            market_regime="bear",
            trend_direction="up",
            trend_strength=75.0,
        )
        rule = next(r for r in BUILT_IN_RULES if r.name == "trend_up_in_bear_regime")
        assert rule.check(state) is True

    def test_trend_up_in_bear_regime_no_fire_weak_trend(self):
        from iios.investment.market.integration.aggregation_state import AggregationState
        state = AggregationState(
            bar_index=1, timestamp=1.0,
            market_regime="bear",
            trend_direction="up",
            trend_strength=50.0,    # below 65 threshold
        )
        rule = next(r for r in BUILT_IN_RULES if r.name == "trend_up_in_bear_regime")
        assert rule.check(state) is False

    def test_correlation_crisis_in_bull_fires(self):
        from iios.investment.market.integration.aggregation_state import AggregationState
        state = AggregationState(
            bar_index=1, timestamp=1.0,
            correlation_regime="crisis",
            market_regime="bull",
        )
        rule = next(r for r in BUILT_IN_RULES if r.name == "correlation_crisis_in_bull_regime")
        assert rule.check(state) is True

    def test_opportunity_crisis_regime_fires(self):
        from iios.investment.market.integration.aggregation_state import AggregationState
        state = AggregationState(
            bar_index=1, timestamp=1.0,
            market_regime="crisis",
            active_opportunities=7,
        )
        rule = next(r for r in BUILT_IN_RULES if r.name == "many_opportunities_crisis_regime")
        assert rule.check(state) is True

    def test_opportunity_crisis_regime_no_fire_few_opps(self):
        from iios.investment.market.integration.aggregation_state import AggregationState
        state = AggregationState(
            bar_index=1, timestamp=1.0,
            market_regime="crisis",
            active_opportunities=3,
        )
        rule = next(r for r in BUILT_IN_RULES if r.name == "many_opportunities_crisis_regime")
        assert rule.check(state) is False

    def test_all_rules_have_check_callable(self):
        for rule in BUILT_IN_RULES:
            assert callable(rule.check)

    def test_both_present_helper(self):
        from iios.investment.market.integration.aggregation_state import AggregationState
        s = AggregationState(1, 1.0, market_regime="bull")
        assert _both_present(s, "market_regime") is True
        assert _both_present(s, "market_regime", "trend_direction") is False


class TestConsistencyValidator:
    def test_clean_bundle_passes(self, full_bundle):
        engine    = AggregationEngine()
        state     = engine.aggregate(full_bundle)
        validator = ConsistencyValidator()
        report    = validator.validate(state)
        # Bull regime + up trend + normal vol should mostly pass
        assert report.status in (ValidationStatus.PASSED, ValidationStatus.WARNING)

    def test_crisis_bundle_has_issues(self, crisis_bundle):
        engine    = AggregationEngine()
        state     = engine.aggregate(crisis_bundle)
        validator = ConsistencyValidator()
        report    = validator.validate(state)
        assert len(report.issues) > 0

    def test_crisis_status_is_failed_or_warning(self, crisis_bundle):
        engine    = AggregationEngine()
        state     = engine.aggregate(crisis_bundle)
        validator = ConsistencyValidator()
        report    = validator.validate(state)
        assert report.status in (ValidationStatus.FAILED, ValidationStatus.WARNING)

    def test_passed_plus_failed_plus_warned_equals_total_rules(self, full_bundle):
        engine    = AggregationEngine()
        state     = engine.aggregate(full_bundle)
        validator = ConsistencyValidator()
        report    = validator.validate(state)
        total = report.passed_rules + report.failed_rules + report.warned_rules
        assert total == len(validator.rules)

    def test_custom_rule_injected(self):
        from iios.investment.market.integration.aggregation_state import AggregationState
        from iios.investment.market.integration.models import ValidationIssue
        always_fire = ConsistencyRule(
            name="always_fire",
            conflict_type=ConflictType.CROSS_ENGINE,
            severity=ConflictSeverity.LOW,
            engines=[],
            description="Always fires",
            check=lambda _: True,
        )
        validator = ConsistencyValidator(extra_rules=[always_fire])
        state     = AggregationState(1, 1.0)
        report    = validator.validate(state)
        assert any(i.rule_name == "always_fire" for i in report.issues)

    def test_add_rule(self):
        validator = ConsistencyValidator()
        initial_count = len(validator.rules)
        new_rule = ConsistencyRule(
            name="test_rule", conflict_type=ConflictType.CROSS_ENGINE,
            severity=ConflictSeverity.LOW, engines=[], description="Test",
            check=lambda _: False,
        )
        validator.add_rule(new_rule)
        assert len(validator.rules) == initial_count + 1

    def test_rule_exception_does_not_crash(self):
        from iios.investment.market.integration.aggregation_state import AggregationState
        bad_rule = ConsistencyRule(
            name="explodes", conflict_type=ConflictType.CROSS_ENGINE,
            severity=ConflictSeverity.LOW, engines=[], description="Bad",
            check=lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        validator = ConsistencyValidator(extra_rules=[bad_rule])
        state     = AggregationState(1, 1.0)
        report    = validator.validate(state)   # must not raise

    def test_high_severity_issue_leads_to_failed_status(self):
        from iios.investment.market.integration.aggregation_state import AggregationState
        high_rule = ConsistencyRule(
            name="high_sev", conflict_type=ConflictType.TREND_REGIME,
            severity=ConflictSeverity.HIGH, engines=[], description="High",
            check=lambda _: True,
        )
        validator = ConsistencyValidator(extra_rules=[high_rule])
        state     = AggregationState(1, 1.0)
        report    = validator.validate(state)
        assert report.status is ValidationStatus.FAILED

    def test_medium_severity_issue_leads_to_warning(self):
        from iios.investment.market.integration.aggregation_state import AggregationState
        # Only add a medium rule, no high/critical
        medium_rule = ConsistencyRule(
            name="medium_sev", conflict_type=ConflictType.BREADTH_SECTOR,
            severity=ConflictSeverity.MEDIUM, engines=[], description="Med",
            check=lambda _: True,
        )
        # Use only this one rule (no built-in rules that might fire HIGH)
        validator = ConsistencyValidator.__new__(ConsistencyValidator)
        validator._rules = [medium_rule]
        state = AggregationState(1, 1.0)
        report = validator.validate(state)
        assert report.status is ValidationStatus.WARNING
