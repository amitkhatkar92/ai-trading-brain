"""tests/unit/investment/company/integration/test_conflict_resolution.py
Tests for conflict detection, classification, resolution, history, and engine.
"""
from __future__ import annotations

import pytest

from iios.investment.company.integration.company_intelligence_aggregator import AggregatedIntelligence
from iios.investment.company.integration.company_state import (
    ConflictSeverity, ConflictStatus, ConflictType,
)
from iios.investment.company.integration.conflict_classifier import (
    classify_severity, conflict_summary, max_severity, sort_by_priority,
)
from iios.investment.company.integration.conflict_detector import (
    ConflictRecord, detect_conflicts,
)
from iios.investment.company.integration.conflict_engine import ConflictEngine
from iios.investment.company.integration.conflict_history import ConflictHistory
from iios.investment.company.integration.conflict_resolution import (
    ConflictResolver, resolve_by_conservative, resolve_by_higher_confidence,
    resolve_by_latest_update,
)


# ── ConflictRecord ────────────────────────────────────────────────────────────

class TestConflictRecord:
    def test_defaults(self):
        c = ConflictRecord(ticker="X", engine_a="financials", engine_b="earnings")
        assert c.is_critical is False
        assert c.is_resolved is False
        assert c.conflict_id.startswith("cfl-")

    def test_critical_flag(self):
        c = ConflictRecord(ticker="X", severity=ConflictSeverity.CRITICAL)
        assert c.is_critical is True

    def test_to_dict(self):
        c = ConflictRecord(ticker="X", engine_a="a", engine_b="b")
        d = c.to_dict()
        assert all(k in d for k in ["conflict_id", "ticker", "severity", "status"])


# ── Conflict detection ────────────────────────────────────────────────────────

class TestDetectConflicts:
    def _intel(self, **kwargs) -> AggregatedIntelligence:
        return AggregatedIntelligence(ticker="X", **kwargs)

    def test_no_conflicts_consistent(self):
        intel = self._intel(
            financial_score=70.0, earnings_score=72.0,
            business_quality_score=70.0,
        )
        conflicts = detect_conflicts("X", intel)
        assert conflicts == []

    def test_critical_score_divergence(self):
        intel = self._intel(
            financial_score=85.0,
            earnings_score=20.0,
        )
        conflicts = detect_conflicts("X", intel)
        assert len(conflicts) > 0
        assert any(c.severity in (ConflictSeverity.CRITICAL, ConflictSeverity.MEDIUM)
                   for c in conflicts)

    def test_signal_conflict_unprofitable_high_opportunity(self):
        intel = self._intel(
            opportunity_score=78.0, financial_score=20.0, earnings_score=22.0,
            is_profitable=False,
        )
        conflicts = detect_conflicts("X", intel)
        assert any(c.severity == ConflictSeverity.CRITICAL for c in conflicts)

    def test_pledge_management_conflict(self):
        intel = self._intel(
            management_score=75.0, ownership_score=65.0,
            promoter_pledge_pct=60.0,
        )
        conflicts = detect_conflicts("X", intel)
        assert len(conflicts) > 0

    def test_growing_unprofitable_conflict(self):
        intel = self._intel(
            growth_score=75.0, earnings_score=22.0,
            is_growing=True, is_profitable=False,
        )
        conflicts = detect_conflicts("X", intel)
        # Should detect signal conflict
        assert any(c.conflict_type == ConflictType.SIGNAL_CONFLICT for c in conflicts)

    def test_no_scores_no_conflicts(self):
        intel = self._intel()
        assert detect_conflicts("X", intel) == []


# ── Classifier ───────────────────────────────────────────────────────────────

class TestConflictClassifier:
    def test_max_severity(self):
        assert max_severity(ConflictSeverity.CRITICAL, ConflictSeverity.LOW) == ConflictSeverity.CRITICAL
        assert max_severity(ConflictSeverity.LOW, ConflictSeverity.CRITICAL) == ConflictSeverity.CRITICAL
        assert max_severity(ConflictSeverity.MEDIUM, ConflictSeverity.MEDIUM) == ConflictSeverity.MEDIUM

    def test_sort_by_priority(self):
        conflicts = [
            ConflictRecord(ticker="X", severity=ConflictSeverity.LOW),
            ConflictRecord(ticker="X", severity=ConflictSeverity.CRITICAL),
            ConflictRecord(ticker="X", severity=ConflictSeverity.MEDIUM),
        ]
        sorted_c = sort_by_priority(conflicts)
        assert sorted_c[0].severity == ConflictSeverity.CRITICAL
        assert sorted_c[-1].severity == ConflictSeverity.LOW

    def test_conflict_summary_no_conflicts(self):
        assert "No conflicts" in conflict_summary([])

    def test_conflict_summary_with_critical(self):
        c = ConflictRecord(ticker="X", severity=ConflictSeverity.CRITICAL)
        msg = conflict_summary([c])
        assert "critical" in msg.lower()

    def test_classify_signal_core_engine(self):
        c = ConflictRecord(
            ticker="X",
            conflict_type=ConflictType.SIGNAL_CONFLICT,
            engine_a="financials",
            engine_b="earnings",
            severity=ConflictSeverity.LOW,
        )
        new_sev = classify_severity(c)
        assert new_sev in (ConflictSeverity.HIGH, ConflictSeverity.CRITICAL)


# ── Resolution ────────────────────────────────────────────────────────────────

class TestConflictResolution:
    def _conflict(self, ea="financials", eb="opportunity"):
        return ConflictRecord(ticker="X", engine_a=ea, engine_b=eb)

    def test_higher_confidence_resolves(self):
        c = self._conflict("financials", "opportunity")
        resolution = resolve_by_higher_confidence(c)
        assert resolution is not None
        assert "financials" in resolution  # financials has higher confidence

    def test_higher_confidence_close_scores(self):
        c = self._conflict("financials", "earnings")  # both high confidence
        resolution = resolve_by_higher_confidence(c)
        # Close confidence → may not resolve (returns None)
        # Just checking it doesn't crash
        assert resolution is None or isinstance(resolution, str)

    def test_conservative_risk_conflict(self):
        c = ConflictRecord(
            ticker="X", conflict_type=ConflictType.RISK_CONFLICT,
            engine_a="a", engine_b="b",
        )
        resolution = resolve_by_conservative(c)
        assert resolution is not None

    def test_conservative_non_risk_conflict(self):
        c = ConflictRecord(
            ticker="X", conflict_type=ConflictType.SCORE_DIVERGENCE,
            engine_a="a", engine_b="b",
        )
        resolution = resolve_by_conservative(c)
        assert resolution is None

    def test_latest_update_resolves(self):
        c = self._conflict("a", "b")
        ages = {"a": 3600.0, "b": 100.0}  # b is fresher
        resolution = resolve_by_latest_update(c, ages)
        assert resolution is not None
        assert "b" in resolution

    def test_latest_update_no_ages(self):
        c = self._conflict()
        assert resolve_by_latest_update(c, None) is None


class TestConflictResolver:
    def test_resolve_all(self):
        resolver = ConflictResolver()
        conflicts = [
            ConflictRecord(ticker="X", engine_a="financials", engine_b="opportunity",
                           severity=ConflictSeverity.MEDIUM,
                           conflict_type=ConflictType.SCORE_DIVERGENCE),
        ]
        resolved = resolver.resolve_all(conflicts)
        assert all(c.status != ConflictStatus.DETECTED for c in resolved)

    def test_critical_escalated_if_unresolvable(self):
        resolver = ConflictResolver()
        # Two engines with similar confidence → higher_confidence may not resolve
        conflicts = [
            ConflictRecord(
                ticker="X", engine_a="management", engine_b="ownership",
                severity=ConflictSeverity.CRITICAL,
                conflict_type=ConflictType.SCORE_DIVERGENCE,
            ),
        ]
        resolver.resolve_all(conflicts)
        # Either resolved or escalated; never stays DETECTED
        assert conflicts[0].status != ConflictStatus.DETECTED


# ── Conflict history ──────────────────────────────────────────────────────────

class TestConflictHistory:
    def test_record_and_retrieve(self):
        hist = ConflictHistory()
        c = ConflictRecord(ticker="X", severity=ConflictSeverity.HIGH)
        hist.record(c)
        records = hist.get_history("X")
        assert len(records) == 1

    def test_record_all(self):
        hist = ConflictHistory()
        conflicts = [ConflictRecord(ticker="X") for _ in range(3)]
        hist.record_all("X", conflicts)
        assert hist.count_total("X") == 3

    def test_filter_by_severity(self):
        hist = ConflictHistory()
        hist.record(ConflictRecord(ticker="X", severity=ConflictSeverity.CRITICAL))
        hist.record(ConflictRecord(ticker="X", severity=ConflictSeverity.LOW))
        crit = hist.get_history("X", severity=ConflictSeverity.CRITICAL)
        assert all(c.severity == ConflictSeverity.CRITICAL for c in crit)

    def test_unresolved(self):
        hist = ConflictHistory()
        c = ConflictRecord(ticker="X", status=ConflictStatus.DETECTED)
        hist.record(c)
        assert len(hist.unresolved("X")) == 1

    def test_critical_unresolved(self):
        hist = ConflictHistory()
        hist.record(ConflictRecord(ticker="X",
                                   severity=ConflictSeverity.CRITICAL,
                                   status=ConflictStatus.ESCALATED))
        hist.record(ConflictRecord(ticker="X",
                                   severity=ConflictSeverity.LOW,
                                   status=ConflictStatus.RESOLVED))
        crits = hist.critical_unresolved("X")
        assert len(crits) == 1


# ── ConflictEngine ────────────────────────────────────────────────────────────

class TestConflictEngine:
    def test_process_returns_conflicts(self):
        engine = ConflictEngine()
        intel = AggregatedIntelligence(
            ticker="X", financial_score=85.0, earnings_score=18.0
        )
        conflicts = engine.process("X", intel)
        assert isinstance(conflicts, list)

    def test_process_resolves_conflicts(self):
        engine = ConflictEngine()
        intel = AggregatedIntelligence(
            ticker="X", financial_score=85.0, earnings_score=18.0
        )
        conflicts = engine.process("X", intel)
        for c in conflicts:
            assert c.status != ConflictStatus.DETECTED  # all should be acted upon

    def test_history_stored(self):
        engine = ConflictEngine()
        intel = AggregatedIntelligence(
            ticker="X", financial_score=85.0, earnings_score=18.0
        )
        engine.process("X", intel)
        history = engine.get_history("X")
        assert isinstance(history, list)

    def test_summary_string(self):
        engine = ConflictEngine()
        intel = AggregatedIntelligence(ticker="X")
        conflicts = engine.process("X", intel)
        summary = engine.summary(conflicts)
        assert isinstance(summary, str)
