"""tests/unit/investment/decision/integration/test_consistency.py
Tests for ConsistencyValidator, ConsistencyRules, and ValidationReport.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.integration.aggregation_engine import AggregationEngine
from iios.investment.decision.integration.consistency_validator import ConsistencyValidator
from iios.investment.decision.integration.integration_constants import (
    ComponentId,
    ValidationStatus,
)
from iios.investment.decision.integration.validation_report import (
    build_validation_report,
    ValidationCheck,
)


def _make_snap(engine, *args):
    """Helper: build aggregation state snapshot from pipeline outputs."""
    did, sid, ev, rs, cs, ri, ex, cm = args
    state = engine.create(
        decision_id=did + "_DEC", subject_id=sid, subject_type="equity",
        evidence=ev, reasoning=rs, confidence=cs, risk=ri,
        explanation=ex, committee=cm,
    )
    return state.snapshot()


class TestConsistencyValidator:
    def test_validate_returns_report(self, _rich_pipeline):
        did, sid, ev, rs, cs, ri, ex, cm = _rich_pipeline
        eng  = AggregationEngine()
        snap = _make_snap(eng, *_rich_pipeline)
        v    = ConsistencyValidator()
        rep  = v.validate(snap)
        assert rep is not None
        assert rep.overall_status in list(ValidationStatus)

    def test_valid_or_warning_on_good_data(self, _rich_pipeline):
        eng  = AggregationEngine()
        snap = _make_snap(eng, *_rich_pipeline)
        v    = ConsistencyValidator()
        rep  = v.validate(snap)
        # With rich, consistent data — should be VALID or WARNING, never INVALID
        assert rep.overall_status != ValidationStatus.INVALID

    def test_missing_components_skipped(self, _rich_pipeline):
        did, sid, ev, *_ = _rich_pipeline
        eng   = AggregationEngine()
        state = eng.create(did, sid, "equity", evidence=ev)
        snap  = state.snapshot()
        v     = ConsistencyValidator()
        rep   = v.validate(snap)
        # Rules requiring absent components return no checks for those components
        assert rep is not None

    def test_add_custom_rule(self, _rich_pipeline):
        from iios.investment.decision.integration.consistency_rules import ConsistencyRule
        from iios.investment.decision.integration.validation_report import _make_check

        class AlwaysWarnRule(ConsistencyRule):
            def _evaluate(self, snap):
                return _make_check(self.rule_id, self.name, ValidationStatus.WARNING, "test warn")

        v = ConsistencyValidator()
        before = v.rule_count
        v.add_rule(AlwaysWarnRule("X001", "TestWarn", "Always warn", ("evidence",)))
        assert v.rule_count == before + 1

    def test_report_counts_correct(self, _rich_pipeline):
        eng  = AggregationEngine()
        snap = _make_snap(eng, *_rich_pipeline)
        v    = ConsistencyValidator()
        rep  = v.validate(snap)
        total = rep.valid_count + rep.warning_count + rep.invalid_count
        assert total == len(rep.checks)


class TestValidationReport:
    def test_build_all_valid(self):
        checks = [
            ValidationCheck("C1", "R001", "Rule1", ValidationStatus.VALID, "ok"),
            ValidationCheck("C2", "R002", "Rule2", ValidationStatus.VALID, "ok"),
        ]
        rep = build_validation_report("D1", "INFY", checks)
        assert rep.overall_status == ValidationStatus.VALID
        assert rep.is_valid

    def test_build_with_warning(self):
        checks = [
            ValidationCheck("C1", "R001", "Rule1", ValidationStatus.VALID, "ok"),
            ValidationCheck("C2", "R002", "Rule2", ValidationStatus.WARNING, "warn"),
        ]
        rep = build_validation_report("D1", "INFY", checks)
        assert rep.overall_status == ValidationStatus.WARNING
        assert rep.has_warnings

    def test_build_with_invalid(self):
        checks = [
            ValidationCheck("C1", "R001", "Rule1", ValidationStatus.INVALID, "fail"),
        ]
        rep = build_validation_report("D1", "INFY", checks)
        assert rep.overall_status == ValidationStatus.INVALID
        assert not rep.is_valid

    def test_to_dict_structure(self):
        rep = build_validation_report("D1", "INFY", [])
        d   = rep.to_dict()
        assert "report_id"     in d
        assert "overall_status" in d
        assert "checks"         in d

    def test_frozen(self):
        rep = build_validation_report("D1", "INFY", [])
        with pytest.raises((AttributeError, TypeError)):
            rep.valid_count = 99  # type: ignore
