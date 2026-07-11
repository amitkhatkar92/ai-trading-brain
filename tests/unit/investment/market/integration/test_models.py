"""tests/unit/investment/market/integration/test_models.py"""
from __future__ import annotations

import json

import pytest

from iios.investment.market.integration.models import (
    Conflict,
    ConflictSeverity,
    ConflictSummary,
    ConflictType,
    EngineHealthRecord,
    EnginePayload,
    EngineSource,
    HealthStatus,
    IntelligenceBundle,
    MarketIntelligenceSnapshot,
    MarketStateLabel,
    QualityDimension,
    QualityScore,
    ValidationIssue,
    ValidationReport,
    ValidationStatus,
)


class TestEnginePayload:
    def test_get_attr_from_dict(self):
        ep = EnginePayload("regime", EngineSource.MARKET_REGIME,
                           {"regime": "bull"}, 1, 1.0)
        assert ep.get_attr("regime") == "bull"

    def test_get_attr_fallback(self):
        ep = EnginePayload("regime", EngineSource.MARKET_REGIME,
                           {"market_regime": "bear"}, 1, 1.0)
        assert ep.get_attr("regime", "market_regime", default=None) == "bear"

    def test_get_attr_default(self):
        ep = EnginePayload("x", EngineSource.UNKNOWN, {}, 1, 1.0)
        assert ep.get_attr("missing", default="fallback") == "fallback"

    def test_get_attr_from_object(self):
        class Payload:
            regime = "neutral"
        ep = EnginePayload("r", EngineSource.MARKET_REGIME, Payload(), 1, 1.0)
        assert ep.get_attr("regime") == "neutral"


class TestIntelligenceBundle:
    def test_add_and_get(self):
        bundle = IntelligenceBundle(1, 1.0)
        ep = EnginePayload("x", EngineSource.TREND, {}, 1, 1.0)
        bundle.add(ep)
        assert bundle.get("x") is ep

    def test_engine_names(self):
        bundle = IntelligenceBundle(1, 1.0)
        for name in ("a", "b", "c"):
            bundle.add(EnginePayload(name, EngineSource.UNKNOWN, {}, 1, 1.0))
        assert bundle.engine_names == {"a", "b", "c"}

    def test_get_missing_returns_none(self):
        bundle = IntelligenceBundle(1, 1.0)
        assert bundle.get("nope") is None


class TestValidationReport:
    def test_has_critical(self):
        issue = ValidationIssue("r", ConflictType.TREND_REGIME,
                                ConflictSeverity.CRITICAL, "desc", [])
        report = ValidationReport(1, ValidationStatus.FAILED, [issue])
        assert report.has_critical is True

    def test_has_high(self):
        issue = ValidationIssue("r", ConflictType.TREND_REGIME,
                                ConflictSeverity.HIGH, "desc", [])
        report = ValidationReport(1, ValidationStatus.FAILED, [issue])
        assert report.has_high is True

    def test_to_dict(self):
        report = ValidationReport(1, ValidationStatus.PASSED)
        d = report.to_dict()
        assert d["status"] == "passed"

    def test_to_dict_serialisable(self):
        issue  = ValidationIssue("r", ConflictType.CROSS_ENGINE,
                                 ConflictSeverity.MEDIUM, "d", ["a", "b"])
        report = ValidationReport(1, ValidationStatus.WARNING, [issue],
                                  passed_rules=5, warned_rules=1)
        json.dumps(report.to_dict())


class TestConflict:
    def test_new_factory(self):
        c = Conflict.new(ConflictType.TREND_REGIME, ConflictSeverity.HIGH,
                         ["trend", "regime"], "Test", "up@70", "bear")
        assert len(c.conflict_id) == 36
        assert c.resolved is False

    def test_to_dict(self):
        c = Conflict.new(ConflictType.CROSS_ENGINE, ConflictSeverity.LOW,
                         ["a"], "desc")
        d = c.to_dict()
        assert d["resolved"] is False
        assert "conflict_id" in d

    def test_serialisable(self):
        c = Conflict.new(ConflictType.OPPORTUNITY_RISK, ConflictSeverity.CRITICAL,
                         ["opportunity", "regime"], "d")
        json.dumps(c.to_dict())


class TestQualityScore:
    def test_to_dict(self):
        q = QualityScore(1, 85.0, 90.0, 80.0, 88.0, 82.0,
                         [QualityDimension("comp", 90.0, 0.3)])
        d = q.to_dict()
        assert d["overall"] == pytest.approx(85.0)
        assert len(d["dimensions"]) == 1

    def test_serialisable(self):
        q = QualityScore(1, 70.0, 80.0, 75.0, 85.0, 60.0)
        json.dumps(q.to_dict())


class TestMarketIntelligenceSnapshot:
    def test_empty_factory(self):
        snap = MarketIntelligenceSnapshot.empty(1, 1.0)
        assert snap.market_state_label is MarketStateLabel.UNKNOWN
        assert snap.overall_confidence == 0.0

    def test_to_dict_serialisable(self):
        snap = MarketIntelligenceSnapshot.empty(1, 1.0)
        json.dumps(snap.to_dict())

    def test_to_dict_keys(self):
        snap = MarketIntelligenceSnapshot.empty(1, 1.0)
        d    = snap.to_dict()
        assert "snapshot_id" in d
        assert "market_state_label" in d
        assert "overall_confidence" in d
        assert "quality" in d


class TestEnums:
    def test_engine_source_values(self):
        assert EngineSource.MARKET_REGIME.value == "market_regime"
        assert EngineSource.TREND.value == "trend"

    def test_market_state_labels(self):
        labels = {l.value for l in MarketStateLabel}
        assert "risk_on" in labels
        assert "crisis"  in labels
        assert "unknown" in labels

    def test_conflict_severity_ordering(self):
        order = [ConflictSeverity.LOW, ConflictSeverity.MEDIUM,
                 ConflictSeverity.HIGH, ConflictSeverity.CRITICAL]
        assert order == list(ConflictSeverity)[:4]
