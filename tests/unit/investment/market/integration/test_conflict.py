"""tests/unit/investment/market/integration/test_conflict.py"""
from __future__ import annotations

import pytest

from iios.investment.market.integration.aggregation_engine import AggregationEngine
from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.conflict_classifier import ConflictClassifier
from iios.investment.market.integration.conflict_detector import ConflictDetector
from iios.investment.market.integration.conflict_engine import ConflictEngine
from iios.investment.market.integration.conflict_history import ConflictHistory
from iios.investment.market.integration.conflict_resolution import ConflictResolver
from iios.investment.market.integration.consistency_validator import ConsistencyValidator
from iios.investment.market.integration.models import (
    Conflict,
    ConflictSeverity,
    ConflictType,
    ValidationIssue,
    ValidationReport,
    ValidationStatus,
)


def _state(**kwargs) -> AggregationState:
    defaults = dict(bar_index=1, timestamp=1.0)
    defaults.update(kwargs)
    return AggregationState(**defaults)


def _report_with_issue(
    conflict_type: ConflictType,
    severity: ConflictSeverity,
) -> ValidationReport:
    issue = ValidationIssue(
        "test_rule", conflict_type, severity, "Test issue",
        ["engine_a", "engine_b"],
    )
    return ValidationReport(1, ValidationStatus.FAILED, [issue],
                            failed_rules=1)


class TestConflictDetector:
    def test_detects_from_report(self):
        detector = ConflictDetector()
        state    = _state(market_regime="bear", trend_direction="up", trend_strength=70.0)
        report   = _report_with_issue(ConflictType.TREND_REGIME, ConflictSeverity.HIGH)
        conflicts = detector.detect(state, report)
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type is ConflictType.TREND_REGIME

    def test_no_issues_no_conflicts(self):
        detector = ConflictDetector()
        state    = _state()
        report   = ValidationReport(1, ValidationStatus.PASSED)
        conflicts = detector.detect(state, report)
        assert conflicts == []

    def test_signal_strings_populated(self):
        detector = ConflictDetector()
        state    = _state(market_regime="bear", trend_direction="up@70", trend_strength=70.0)
        report   = _report_with_issue(ConflictType.TREND_REGIME, ConflictSeverity.HIGH)
        conflicts = detector.detect(state, report)
        assert conflicts[0].engine_a_signal != ""
        assert conflicts[0].engine_b_signal != ""

    def test_multiple_issues(self):
        detector = ConflictDetector()
        state    = _state()
        issues   = [
            ValidationIssue("r1", ConflictType.TREND_REGIME,
                            ConflictSeverity.HIGH, "d", ["a", "b"]),
            ValidationIssue("r2", ConflictType.BREADTH_SECTOR,
                            ConflictSeverity.MEDIUM, "d", ["c"]),
        ]
        report    = ValidationReport(1, ValidationStatus.FAILED, issues)
        conflicts = detector.detect(state, report)
        assert len(conflicts) == 2


class TestConflictClassifier:
    def test_upgrades_in_crisis(self):
        clf      = ConflictClassifier()
        state    = _state(market_regime="crisis")
        conflict = Conflict.new(ConflictType.TREND_REGIME, ConflictSeverity.HIGH,
                                [], "d")
        result   = clf.classify(conflict, state)
        assert result.severity is ConflictSeverity.CRITICAL

    def test_no_upgrade_in_normal_regime(self):
        clf      = ConflictClassifier()
        state    = _state(market_regime="bull")
        conflict = Conflict.new(ConflictType.TREND_REGIME, ConflictSeverity.HIGH,
                                [], "d")
        result   = clf.classify(conflict, state)
        assert result.severity is ConflictSeverity.HIGH   # unchanged

    def test_critical_stays_critical(self):
        clf      = ConflictClassifier()
        state    = _state(market_regime="crisis")
        conflict = Conflict.new(ConflictType.TREND_REGIME, ConflictSeverity.CRITICAL,
                                [], "d")
        result   = clf.classify(conflict, state)
        assert result.severity is ConflictSeverity.CRITICAL


class TestConflictResolver:
    def test_low_severity_auto_resolved(self):
        resolver = ConflictResolver()
        conflict = Conflict.new(ConflictType.TREND_REGIME, ConflictSeverity.LOW,
                                ["market_regime", "trend"], "d")
        state    = _state()
        resolver.resolve([conflict], state)
        assert conflict.resolved is True
        assert conflict.resolution is not None

    def test_medium_severity_auto_resolved(self):
        resolver = ConflictResolver()
        conflict = Conflict.new(ConflictType.BREADTH_SECTOR, ConflictSeverity.MEDIUM,
                                ["breadth", "sector_rotation"], "d")
        state    = _state()
        resolver.resolve([conflict], state)
        assert conflict.resolved is True

    def test_trend_regime_high_resolved_with_breadth(self):
        resolver = ConflictResolver()
        conflict = Conflict.new(ConflictType.TREND_REGIME, ConflictSeverity.HIGH,
                                ["market_regime", "trend"], "d")
        state    = _state(market_regime="bear", breadth_regime="negative")
        resolver.resolve([conflict], state)
        assert conflict.resolved is True

    def test_trend_regime_high_unresolved_without_breadth(self):
        resolver = ConflictResolver()
        conflict = Conflict.new(ConflictType.TREND_REGIME, ConflictSeverity.HIGH,
                                ["market_regime", "trend"], "d")
        state    = _state(market_regime="bear", breadth_regime=None)
        resolver.resolve([conflict], state)
        assert conflict.resolved is False
        assert "Unresolved" in conflict.resolution

    def test_opportunity_risk_critical_resolved_in_crisis(self):
        resolver = ConflictResolver()
        conflict = Conflict.new(ConflictType.OPPORTUNITY_RISK, ConflictSeverity.CRITICAL,
                                ["opportunity", "market_regime"], "d")
        state    = _state(market_regime="crisis")
        resolver.resolve([conflict], state)
        assert conflict.resolved is True


class TestConflictHistory:
    def test_append_and_latest(self):
        from iios.investment.market.integration.models import ConflictSummary
        hist = ConflictHistory()
        cs   = ConflictSummary(1, 2, 0, 1, 1, 0, 1, 1)
        hist.append(cs)
        assert hist.latest() is cs

    def test_critical_series(self):
        from iios.investment.market.integration.models import ConflictSummary
        hist = ConflictHistory()
        for i, crit in enumerate([1, 0, 1]):
            hist.append(ConflictSummary(i + 1, 1, crit, 0, 0, 0, 0, 1))
        assert hist.critical_series(3) == [1, 0, 1]

    def test_has_persistent_critical_true(self):
        from iios.investment.market.integration.models import ConflictSummary
        hist = ConflictHistory()
        for i in range(3):
            hist.append(ConflictSummary(i + 1, 2, 1, 1, 0, 0, 0, 2))
        assert hist.has_persistent_critical(3) is True

    def test_has_persistent_critical_false(self):
        from iios.investment.market.integration.models import ConflictSummary
        hist = ConflictHistory()
        for i in range(3):
            hist.append(ConflictSummary(i + 1, 2, 0, 1, 1, 0, 1, 1))
        assert hist.has_persistent_critical(3) is False


class TestConflictEngine:
    def test_process_crisis_bundle(self, crisis_bundle):
        engine    = AggregationEngine()
        state     = engine.aggregate(crisis_bundle)
        validator = ConsistencyValidator()
        report    = validator.validate(state)
        conflict_eng = ConflictEngine()
        summary   = conflict_eng.process(state, report)
        assert summary.total >= 0   # may be 0 if all resolved
        assert summary.total == summary.resolved + summary.unresolved

    def test_process_clean_bundle(self, full_bundle):
        engine    = AggregationEngine()
        state     = engine.aggregate(full_bundle)
        validator = ConsistencyValidator()
        report    = validator.validate(state)
        conflict_eng = ConflictEngine()
        summary   = conflict_eng.process(state, report)
        assert isinstance(summary.total, int)

    def test_history_grows(self, make_bundle):
        conflict_eng = ConflictEngine()
        validator    = ConsistencyValidator()
        agg_engine   = AggregationEngine()
        for i in range(3):
            state   = agg_engine.aggregate(make_bundle(bar_index=i + 1))
            report  = validator.validate(state)
            conflict_eng.process(state, report)
        assert len(conflict_eng.history) == 3

    def test_summary_counts_consistent(self, crisis_bundle):
        engine    = AggregationEngine()
        state     = engine.aggregate(crisis_bundle)
        validator = ConsistencyValidator()
        report    = validator.validate(state)
        conflict_eng = ConflictEngine()
        summary   = conflict_eng.process(state, report)
        assert (summary.critical + summary.high + summary.medium + summary.low
                == summary.total)
