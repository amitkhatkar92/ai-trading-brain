"""tests/unit/investment/portfolio/integration/test_conflict.py

Tests for conflict_detector.py, conflict_classifier.py,
conflict_resolution.py, conflict_history.py, conflict_engine.py.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.integration.conflict_classifier import (
    ConflictClassifier,
)
from iios.investment.portfolio.integration.conflict_detector import (
    ConflictDetector, DetectedConflict,
)
from iios.investment.portfolio.integration.conflict_engine import (
    ConflictEngine, ConflictReport,
)
from iios.investment.portfolio.integration.conflict_history import ConflictHistory
from iios.investment.portfolio.integration.conflict_resolution import (
    ConflictResolver, ConflictResolutionResult,
)
from iios.investment.portfolio.integration.integration_types import (
    ConflictResolutionStatus, ConflictSeverity, now_utc,
)


def _healthy_merged():
    return {
        "construction":   {"construction_quality": 0.80, "n_positions": 20},
        "allocation":     {"equity_weight": 0.60, "equity_drift": 0.02},
        "optimization":   {"is_at_efficient_frontier": True, "optimization_quality": 0.78},
        "risk":           {"risk_budget_utilization": 0.55, "var_utilization": 0.60,
                           "is_risk_within_budget": True, "max_drawdown": 0.08},
        "performance":    {"sharpe_ratio": 0.90, "max_drawdown": 0.08},
        "rebalancing":    {"rebalance_recommended": False, "drift_level": "minor"},
        "recommendation": {"primary_action": "no_action"},
    }


def _conflicted_merged():
    return {
        "construction":   {"construction_quality": 0.30, "n_positions": 10},
        "optimization":   {"is_at_efficient_frontier": True},  # conflict 4
        "risk":           {"risk_budget_utilization": 0.97,    # conflict 1
                           "is_risk_within_budget": True,
                           "var_utilization": 0.88,
                           "max_drawdown": 0.20},
        "performance":    {"sharpe_ratio": 2.0, "max_drawdown": 0.08},  # conflict 5
        "allocation":     {"equity_drift": 0.00},
        "rebalancing":    {"rebalance_recommended": True, "drift_level": "critical"},  # conflict 3
        "recommendation": {"primary_action": "aggressive_positioning"},  # conflict 2
    }


class TestConflictDetector:
    def test_no_conflicts_healthy(self):
        detector   = ConflictDetector()
        conflicts  = detector.detect(_healthy_merged(), "P-OK")
        assert len(conflicts) == 0

    def test_detects_internal_inconsistency(self):
        merged   = _conflicted_merged()
        detector = ConflictDetector()
        conflicts = detector.detect(merged, "P-C")
        types = [c.conflict_type for c in conflicts]
        assert "internal_inconsistency" in types

    def test_detects_direction_conflict(self):
        merged   = _conflicted_merged()
        detector = ConflictDetector()
        conflicts = detector.detect(merged, "P-C")
        types = [c.conflict_type for c in conflicts]
        assert "direction_conflict" in types

    def test_detects_value_mismatch(self):
        merged   = _conflicted_merged()
        detector = ConflictDetector()
        conflicts = detector.detect(merged, "P-C")
        types = [c.conflict_type for c in conflicts]
        assert "value_mismatch" in types

    def test_conflict_has_severity(self):
        detector  = ConflictDetector()
        conflicts = detector.detect(_conflicted_merged(), "P-S")
        for c in conflicts:
            assert isinstance(c.severity, ConflictSeverity)

    def test_conflict_to_dict(self):
        detector  = ConflictDetector()
        conflicts = detector.detect(_conflicted_merged(), "P-D")
        if conflicts:
            d = conflicts[0].to_dict()
            assert "conflict_id" in d
            assert "severity" in d


class TestConflictClassifier:
    def test_classifies_all(self):
        detector   = ConflictDetector()
        conflicts  = detector.detect(_conflicted_merged(), "P-C")
        classifier = ConflictClassifier()
        classified = classifier.classify(conflicts)
        assert len(classified) == len(conflicts)

    def test_sorted_by_severity(self):
        detector   = ConflictDetector()
        conflicts  = detector.detect(_conflicted_merged(), "P-C")
        classifier = ConflictClassifier()
        classified = classifier.classify(conflicts)
        if len(classified) >= 2:
            order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            for i in range(len(classified) - 1):
                a = order.get(classified[i].severity.value, 99)
                b = order.get(classified[i + 1].severity.value, 99)
                assert a <= b

    def test_critical_requires_action(self):
        from iios.investment.portfolio.integration.conflict_detector import DetectedConflict
        dc = DetectedConflict(
            conflict_id="x", portfolio_id="P", detected_at=now_utc(),
            severity=ConflictSeverity.CRITICAL, engine_pair="risk:rec",
            conflict_type="direction_conflict", description="test",
        )
        classifier = ConflictClassifier()
        classified = classifier.classify([dc])
        assert classified[0].action_required is True

    def test_info_no_action_required(self):
        from iios.investment.portfolio.integration.conflict_detector import DetectedConflict
        dc = DetectedConflict(
            conflict_id="y", portfolio_id="P", detected_at=now_utc(),
            severity=ConflictSeverity.INFO, engine_pair="misc",
            conflict_type="threshold_violation", description="minor",
        )
        classifier = ConflictClassifier()
        classified = classifier.classify([dc])
        assert classified[0].action_required is False


class TestConflictResolver:
    def test_resolves_critical_as_escalated(self):
        from iios.investment.portfolio.integration.conflict_detector import DetectedConflict
        from iios.investment.portfolio.integration.conflict_classifier import ClassifiedConflict
        dc = DetectedConflict(
            conflict_id="z", portfolio_id="P", detected_at=now_utc(),
            severity=ConflictSeverity.CRITICAL, engine_pair="risk:recommendation",
            conflict_type="direction_conflict", description="critical conflict",
        )
        cc = ClassifiedConflict(dc, "direction_conflict", "...", action_required=True)
        resolver = ConflictResolver()
        result   = resolver.resolve(cc)
        assert result.status == ConflictResolutionStatus.ESCALATED

    def test_resolves_internal_inconsistency(self):
        from iios.investment.portfolio.integration.conflict_detector import DetectedConflict
        from iios.investment.portfolio.integration.conflict_classifier import ClassifiedConflict
        dc = DetectedConflict(
            conflict_id="q", portfolio_id="P", detected_at=now_utc(),
            severity=ConflictSeverity.HIGH, engine_pair="risk",
            conflict_type="internal_inconsistency", description="...",
        )
        cc = ClassifiedConflict(dc, "internal_inconsistency", "...", action_required=True)
        resolver = ConflictResolver()
        result   = resolver.resolve(cc)
        assert result.status == ConflictResolutionStatus.RESOLVED

    def test_resolves_value_mismatch(self):
        from iios.investment.portfolio.integration.conflict_detector import DetectedConflict
        from iios.investment.portfolio.integration.conflict_classifier import ClassifiedConflict
        dc = DetectedConflict(
            conflict_id="r", portfolio_id="P", detected_at=now_utc(),
            severity=ConflictSeverity.MEDIUM, engine_pair="performance:risk",
            conflict_type="value_mismatch", description="...",
        )
        cc = ClassifiedConflict(dc, "value_mismatch", "...", action_required=False)
        resolver = ConflictResolver()
        result   = resolver.resolve(cc)
        assert result.status == ConflictResolutionStatus.RESOLVED

    def test_resolution_has_rationale(self):
        from iios.investment.portfolio.integration.conflict_detector import DetectedConflict
        from iios.investment.portfolio.integration.conflict_classifier import ClassifiedConflict
        dc = DetectedConflict(
            conflict_id="s", portfolio_id="P", detected_at=now_utc(),
            severity=ConflictSeverity.LOW, engine_pair="misc",
            conflict_type="threshold_violation", description="minor",
        )
        cc = ClassifiedConflict(dc, "threshold_violation", "...", action_required=False)
        result = ConflictResolver().resolve(cc)
        assert len(result.rationale) > 0


class TestConflictEngine:
    def test_healthy_no_conflicts(self):
        engine = ConflictEngine()
        report = engine.process(_healthy_merged(), "P-OK")
        assert report.n_detected == 0
        assert not report.has_unresolved

    def test_conflicted_detects_conflicts(self):
        engine = ConflictEngine()
        report = engine.process(_conflicted_merged(), "P-C")
        assert report.n_detected >= 2

    def test_report_resolution_counts(self):
        engine = ConflictEngine()
        report = engine.process(_conflicted_merged(), "P-C")
        assert report.n_resolved + report.n_escalated + report.n_ignored == report.n_detected

    def test_critical_escalated(self):
        engine = ConflictEngine()
        report = engine.process(_conflicted_merged(), "P-E")
        # Direction conflict (aggressive + high risk) → CRITICAL → escalated
        assert report.n_escalated >= 1

    def test_recent_conflicts_history(self):
        engine = ConflictEngine()
        engine.process(_conflicted_merged(), "P-H")
        history = engine.recent_conflicts("P-H", 10)
        assert len(history) >= 1

    def test_report_to_dict(self):
        engine = ConflictEngine()
        report = engine.process(_healthy_merged(), "P-D")
        d      = report.to_dict()
        assert "n_detected" in d
        assert "has_unresolved" in d
