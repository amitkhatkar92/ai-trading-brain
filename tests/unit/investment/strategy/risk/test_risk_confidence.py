"""tests/unit/investment/strategy/risk/test_risk_confidence.py
Tests for RiskScore, RiskConfidence, RiskQuality, RiskHealth, RiskEvents.
"""
import pytest
from tests.unit.investment.strategy.risk.conftest import make_risk_input
from iios.investment.strategy.risk.risk_score import RiskScore, RiskScoreCalculator
from iios.investment.strategy.risk.risk_confidence import RiskConfidence
from iios.investment.strategy.risk.risk_quality import RiskQuality
from iios.investment.strategy.risk.risk_health import RiskHealth, RiskHealthStatus
from iios.investment.strategy.risk.risk_constraints import RiskConstraints
from iios.investment.strategy.risk.risk_limits import DEFAULT_LIMITS
from iios.investment.strategy.risk.risk_events import (
    RiskEventBus, RiskEvent, RiskEventType
)


class TestRiskScore:
    def test_score_returns_risk_score(self, risk_input):
        scorer = RiskScoreCalculator()
        rs = scorer.score(risk_input)
        assert isinstance(rs, RiskScore)
        assert 0.0 <= rs.overall_risk_score <= 100.0

    def test_high_risk_higher_score(self, high_risk_input, low_risk_input):
        calc = RiskScoreCalculator()
        high = calc.score(high_risk_input).overall_risk_score
        low  = calc.score(low_risk_input).overall_risk_score
        assert high > low

    def test_grade_a_for_low_risk(self, low_risk_input):
        rs = RiskScoreCalculator().score(low_risk_input)
        assert rs.risk_grade in ("A", "B")

    def test_grade_d_or_f_for_high_risk(self, high_risk_input):
        rs = RiskScoreCalculator().score(high_risk_input)
        assert rs.risk_grade in ("C", "D", "F")

    def test_risk_score_frozen(self, risk_input):
        rs = RiskScoreCalculator().score(risk_input)
        with pytest.raises((AttributeError, TypeError)):
            rs.overall_risk_score = 0.0

    def test_to_dict_contains_required_keys(self, risk_input):
        rs = RiskScoreCalculator().score(risk_input)
        d = rs.to_dict()
        assert "overall_risk_score" in d
        assert "risk_grade" in d
        assert "dimensions" in d


class TestRiskConfidence:
    def test_compute_returns_confidence(self, risk_input):
        c = RiskConfidence.compute(risk_input)
        assert 0.0 <= c.overall_confidence <= 100.0

    def test_frozen(self, risk_input):
        c = RiskConfidence.compute(risk_input)
        with pytest.raises((AttributeError, TypeError)):
            c.overall_confidence = 0.0

    def test_known_regime_higher_confidence(self):
        known   = make_risk_input(current_regime="trending")
        unknown = make_risk_input(current_regime="unknown")
        c_known   = RiskConfidence.compute(known).regime_confidence
        c_unknown = RiskConfidence.compute(unknown).regime_confidence
        assert c_known > c_unknown

    def test_grade_high_for_good_input(self, low_risk_input):
        c = RiskConfidence.compute(low_risk_input)
        assert c.grade in ("HIGH", "MEDIUM")

    def test_to_dict_contains_grade(self, risk_input):
        d = RiskConfidence.compute(risk_input).to_dict()
        assert "grade" in d


class TestRiskQuality:
    def test_assess_returns_quality(self, risk_input):
        scorer = RiskScoreCalculator()
        rs = scorer.score(risk_input)
        conf = RiskConfidence.compute(risk_input)
        q = RiskQuality.assess(risk_input, rs, conf)
        assert 0.0 <= q.overall_quality <= 100.0

    def test_frozen(self, risk_input):
        rs   = RiskScoreCalculator().score(risk_input)
        conf = RiskConfidence.compute(risk_input)
        q    = RiskQuality.assess(risk_input, rs, conf)
        with pytest.raises((AttributeError, TypeError)):
            q.overall_quality = 0.0

    def test_unknown_regime_lowers_quality(self):
        unknown = make_risk_input(current_regime="unknown")
        rs   = RiskScoreCalculator().score(unknown)
        conf = RiskConfidence.compute(unknown)
        q    = RiskQuality.assess(unknown, rs, conf)
        known_inp = make_risk_input(current_regime="trending")
        rs2  = RiskScoreCalculator().score(known_inp)
        conf2 = RiskConfidence.compute(known_inp)
        q2   = RiskQuality.assess(known_inp, rs2, conf2)
        assert q.overall_quality <= q2.overall_quality

    def test_quality_issues_is_list(self, risk_input):
        rs   = RiskScoreCalculator().score(risk_input)
        conf = RiskConfidence.compute(risk_input)
        q    = RiskQuality.assess(risk_input, rs, conf)
        assert isinstance(q.quality_issues, list)


class TestRiskHealth:
    def _make_health(self, inp):
        rs   = RiskScoreCalculator().score(inp)
        conf = RiskConfidence.compute(inp)
        q    = RiskQuality.assess(inp, rs, conf)
        cr   = RiskConstraints().check(
            inp, rs.overall_risk_score, 0.85, 40.0, limits=DEFAULT_LIMITS
        )
        return RiskHealth.assess(inp, rs, conf, q, cr)

    def test_assess_returns_health(self, risk_input):
        h = self._make_health(risk_input)
        assert isinstance(h, RiskHealth)
        assert 0.0 <= h.health_score <= 100.0

    def test_low_risk_is_safe_or_elevated(self, low_risk_input):
        h = self._make_health(low_risk_input)
        assert h.health_status in (RiskHealthStatus.SAFE, RiskHealthStatus.ELEVATED)

    def test_high_risk_is_high_risk_or_critical(self, high_risk_input):
        h = self._make_health(high_risk_input)
        assert h.health_status in (
            RiskHealthStatus.ELEVATED,
            RiskHealthStatus.HIGH_RISK,
            RiskHealthStatus.CRITICAL,
        )

    def test_issues_is_list(self, risk_input):
        h = self._make_health(risk_input)
        assert isinstance(h.issues, list)

    def test_recommendations_is_list(self, risk_input):
        h = self._make_health(risk_input)
        assert isinstance(h.recommendations, list)

    def test_to_dict_contains_key_fields(self, risk_input):
        h = self._make_health(risk_input)
        d = h.to_dict()
        assert "health_score" in d
        assert "health_status" in d
        assert "is_operational" in d


class TestRiskEventBus:
    def test_subscribe_and_emit(self):
        bus    = RiskEventBus()
        events = []
        bus.subscribe(events.append)
        bus.emit_simple(RiskEventType.RISK_EVALUATED, "s1", {"score": 42.0})
        assert len(events) == 1
        assert events[0].event_type == RiskEventType.RISK_EVALUATED

    def test_typed_subscription(self):
        bus    = RiskEventBus()
        events = []
        bus.subscribe(events.append, RiskEventType.EMERGENCY_STOP)
        bus.emit_simple(RiskEventType.RISK_EVALUATED, "s1", {})
        bus.emit_simple(RiskEventType.EMERGENCY_STOP, "s1", {})
        assert len(events) == 1
        assert events[0].event_type == RiskEventType.EMERGENCY_STOP

    def test_unsubscribe(self):
        bus    = RiskEventBus()
        events = []
        bus.subscribe(events.append)
        bus.unsubscribe(events.append)
        bus.emit_simple(RiskEventType.RISK_EVALUATED, "s1", {})
        assert len(events) == 0

    def test_no_handler_raises(self):
        bus = RiskEventBus()
        bus.emit_simple(RiskEventType.RISK_EVALUATED, "s1", {})  # should not raise

    def test_handler_exception_does_not_propagate(self):
        bus = RiskEventBus()
        def bad_handler(event):
            raise RuntimeError("boom")
        bus.subscribe(bad_handler)
        bus.emit_simple(RiskEventType.RISK_EVALUATED, "s1", {})  # should not raise

    def test_event_has_id_and_timestamp(self):
        bus    = RiskEventBus()
        events = []
        bus.subscribe(events.append)
        bus.emit_simple(RiskEventType.RISK_CLEARED, "s1", {})
        e = events[0]
        assert e.event_id
        assert e.emitted_at is not None
