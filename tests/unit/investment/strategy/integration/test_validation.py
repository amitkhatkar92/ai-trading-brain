"""tests/unit/investment/strategy/integration/test_validation.py
Tests for ConsistencyRules, ConflictDetector, ValidationReport, ConsistencyValidator.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.aggregation_state import make_update
from iios.investment.strategy.integration.consistency_rules import (
    ConsistencyRule,
    RuleCheckResult,
    RuleRegistry,
    create_default_rule_registry,
)
from iios.investment.strategy.integration.conflict_detector import ConflictDetector
from iios.investment.strategy.integration.consistency_validator import ConsistencyValidator
from iios.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    ConflictType,
    IntelligenceSource,
    ValidationStatus,
)
from iios.investment.strategy.integration.validation_report import (
    ValidationReport,
    build_validation_report,
)
from tests.unit.investment.strategy.integration.conftest import (
    make_eval_update,
    make_risk_update,
    make_lifecycle_update,
    make_framework_update,
    make_full_state,
)


# ===========================================================================
# RuleRegistry
# ===========================================================================

class TestRuleRegistry:
    def test_default_registry_has_rules(self):
        reg = create_default_rule_registry()
        assert reg.count() >= 7

    def test_register_and_get(self):
        reg = RuleRegistry()

        class DummyRule(ConsistencyRule):
            rule_id = "T001"
            rule_name = "test_rule"
            required_sources = (IntelligenceSource.EVALUATION, IntelligenceSource.RISK)
            def check(self, a, b):
                return self._pass()

        reg.register(DummyRule())
        assert reg.get("T001") is not None
        assert reg.count() == 1

    def test_unregister(self):
        reg = create_default_rule_registry()
        n = reg.count()
        reg.unregister("R001")
        assert reg.count() == n - 1

    def test_all_returns_list(self):
        reg = create_default_rule_registry()
        rules = reg.all()
        assert isinstance(rules, list)


# ===========================================================================
# Built-in Rules
# ===========================================================================

class TestBuiltinRules:
    """Tests each built-in rule fires under its expected conditions."""

    def _engine_with(self, sid, **payloads):
        """payloads: source_enum → dict"""
        eng = AggregationEngine()
        for src, payload in payloads.items():
            eng.apply(make_update(src, sid, payload, confidence=80))
        return eng

    def test_R001_eval_vs_risk_conflict(self):
        sid = "R001"
        eng = self._engine_with(
            sid,
            **{
                IntelligenceSource.EVALUATION: {"score": 75, "status": "active"},
                IntelligenceSource.RISK: {"risk_level": "critical"},
            }
        )
        det = ConflictDetector(create_default_rule_registry())
        failures = det.detect(eng.get_state(sid))
        types = [r.conflict_type for r in failures]
        assert ConflictType.EVALUATION_VS_RISK in types

    def test_R001_no_conflict_when_risk_not_critical(self):
        sid = "R001b"
        eng = self._engine_with(
            sid,
            **{
                IntelligenceSource.EVALUATION: {"score": 75, "status": "active"},
                IntelligenceSource.RISK: {"risk_level": "low"},
            }
        )
        det = ConflictDetector(create_default_rule_registry())
        failures = det.detect(eng.get_state(sid))
        types = [r.conflict_type for r in failures]
        assert ConflictType.EVALUATION_VS_RISK not in types

    def test_R007_lifecycle_vs_eval_conflict(self):
        sid = "R007"
        eng = self._engine_with(
            sid,
            **{
                IntelligenceSource.LIFECYCLE: {"phase": "deprecated", "status": "deprecated"},
                IntelligenceSource.EVALUATION: {"score": 70, "status": "active"},
            }
        )
        det = ConflictDetector(create_default_rule_registry())
        failures = det.detect(eng.get_state(sid))
        types = [r.conflict_type for r in failures]
        assert ConflictType.LIFECYCLE_VS_EVALUATION in types

    def test_no_conflict_missing_source(self):
        """Rules requiring both sources should not fire if one is absent."""
        sid = "MISS"
        eng = AggregationEngine()
        eng.apply(make_eval_update(sid, score=90.0))  # RISK absent
        det = ConflictDetector(create_default_rule_registry())
        failures = det.detect(eng.get_state(sid))
        assert failures == []


# ===========================================================================
# ConflictDetector
# ===========================================================================

class TestConflictDetector:
    def test_no_failures_all_ok(self):
        sid, state, _ = make_full_state("OK1")
        det = ConflictDetector()
        assert det.detect(state) == []

    def test_has_critical_conflict_false_on_clean_state(self):
        sid, state, _ = make_full_state("OK2")
        det = ConflictDetector()
        assert not det.has_critical_conflict(state)

    def test_rule_count(self):
        det = ConflictDetector()
        assert det.rule_count() >= 7

    def test_register_rule(self):
        det = ConflictDetector()
        n = det.rule_count()

        class DummyRule2(ConsistencyRule):
            rule_id = "D002"
            rule_name = "dummy"
            required_sources = (IntelligenceSource.EVALUATION, IntelligenceSource.RISK)
            def check(self, a, b):
                return self._pass()

        det.register_rule(DummyRule2())
        assert det.rule_count() == n + 1


# ===========================================================================
# ValidationReport
# ===========================================================================

class TestValidationReport:
    def test_passed_on_no_failures(self):
        report = build_validation_report("STRAT-X", [], completeness=1.0)
        assert report.status == ValidationStatus.PASSED
        assert report.is_valid

    def test_failed_on_critical(self):
        from datetime import datetime, timezone
        from iios.investment.strategy.integration.consistency_rules import RuleCheckResult
        crit = RuleCheckResult(
            rule_id="R001",
            rule_name="eval_vs_risk",
            passed=False,
            conflict_type=ConflictType.EVALUATION_VS_RISK,
            severity=ConflictSeverity.CRITICAL,
            description="critical conflict",
            source_a=IntelligenceSource.EVALUATION,
            source_b=IntelligenceSource.RISK,
            checked_at=datetime.now(timezone.utc),
        )
        report = build_validation_report("STRAT-C", [crit], completeness=0.9)
        assert report.status == ValidationStatus.FAILED
        assert not report.is_valid
        assert report.critical_conflicts == 1

    def test_consistency_score_decreases_with_conflicts(self):
        from datetime import datetime, timezone
        from iios.investment.strategy.integration.consistency_rules import RuleCheckResult
        med = RuleCheckResult(
            rule_id="R003",
            rule_name="learning_vs_eval",
            passed=False,
            conflict_type=ConflictType.LEARNING_VS_EVALUATION,
            severity=ConflictSeverity.MEDIUM,
            description="medium conflict",
            source_a=IntelligenceSource.LEARNING,
            source_b=IntelligenceSource.EVALUATION,
            checked_at=datetime.now(timezone.utc),
        )
        report = build_validation_report("STRAT-M", [med], completeness=0.8)
        assert report.consistency_score < 100.0

    def test_to_dict_keys(self):
        report = build_validation_report("STRAT-X", [], completeness=0.9)
        d = report.to_dict()
        assert "strategy_id" in d
        assert "consistency_score" in d
        assert "completeness" in d


# ===========================================================================
# ConsistencyValidator
# ===========================================================================

class TestConsistencyValidator:
    def test_validate_clean_state_passes(self):
        sid, state, eng = make_full_state("CV1")
        val = ConsistencyValidator(aggregation_engine=eng)
        report = val.validate(state)
        assert report.is_valid

    def test_validate_with_warnings(self):
        sid, state, eng = make_full_state("CV2")
        val = ConsistencyValidator(aggregation_engine=eng)
        report = val.validate(state, warnings=["test warning"])
        assert "test warning" in report.warnings

    def test_validate_missing_sources_partial_completeness(self):
        eng = AggregationEngine()
        sid = "CV3"
        eng.apply(make_eval_update(sid))
        state = eng.get_state(sid)
        val = ConsistencyValidator(aggregation_engine=eng)
        report = val.validate(state)
        # Completeness < 1 but no rule conflicts
        assert report.completeness < 1.0

    def test_register_rule_propagates(self):
        class DummyPassRule(ConsistencyRule):
            rule_id = "DP1"
            rule_name = "dummy_pass"
            required_sources = (IntelligenceSource.EVALUATION, IntelligenceSource.RISK)
            def check(self, a, b):
                return self._pass()

        val = ConsistencyValidator()
        val.register_rule(DummyPassRule())
        # Should not raise
