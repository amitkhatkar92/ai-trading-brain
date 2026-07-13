"""tests/unit/investment/strategy/risk/test_risk_engine.py
Integration tests for StrategyRiskEngine.
"""
import pytest
from tests.unit.investment.strategy.risk.conftest import make_risk_input
from iios.investment.strategy.risk.strategy_risk_engine import StrategyRiskEngine
from iios.investment.strategy.risk.strategy_risk_profile import StrategyRiskProfile
from iios.investment.strategy.risk.strategy_risk_snapshot import StrategyRiskSnapshot
from iios.investment.strategy.risk.risk_score import RiskScore
from iios.investment.strategy.risk.risk_health import RiskHealth, RiskHealthStatus
from iios.investment.strategy.risk.risk_events import RiskEventBus, RiskEventType
from iios.investment.strategy.risk.risk_policy import DEFAULT_POLICY


@pytest.fixture()
def engine():
    return StrategyRiskEngine()


@pytest.fixture()
def engine_with_bus():
    bus = RiskEventBus()
    return StrategyRiskEngine(event_bus=bus), bus


class TestStrategyRiskEngineRegistration:
    def test_register_strategy(self, engine):
        profile = engine.register_strategy("s1", "Strategy One")
        assert profile.strategy_id == "s1"

    def test_register_returns_profile(self, engine):
        profile = engine.register_strategy("s2")
        assert isinstance(profile, StrategyRiskProfile)
        assert not profile.is_evaluated

    def test_register_idempotent(self, engine):
        p1 = engine.register_strategy("s3", "Strategy Three")
        p2 = engine.register_strategy("s3", "Strategy Three")
        assert p1 is p2

    def test_unregister(self, engine, risk_input):
        engine.evaluate(risk_input)
        engine.unregister_strategy(risk_input.strategy_id)
        assert engine.get_profile(risk_input.strategy_id) is None


class TestStrategyRiskEngineEvaluation:
    def test_evaluate_returns_profile(self, engine, risk_input):
        profile = engine.evaluate(risk_input)
        assert isinstance(profile, StrategyRiskProfile)
        assert profile.is_evaluated

    def test_evaluate_populates_risk_score(self, engine, risk_input):
        profile = engine.evaluate(risk_input)
        assert profile.risk_score is not None
        assert 0.0 <= profile.overall_risk_score <= 100.0

    def test_evaluate_populates_health(self, engine, risk_input):
        profile = engine.evaluate(risk_input)
        assert profile.health is not None
        assert isinstance(profile.health, RiskHealth)

    def test_evaluate_populates_drawdown(self, engine, risk_input):
        profile = engine.evaluate(risk_input)
        assert profile.drawdown is not None

    def test_evaluate_populates_stress(self, engine, risk_input):
        profile = engine.evaluate(risk_input)
        assert profile.stress_report is not None

    def test_evaluate_increments_count(self, engine, risk_input):
        engine.evaluate(risk_input)
        engine.evaluate(risk_input)
        p = engine.get_profile(risk_input.strategy_id)
        assert p.evaluation_count >= 2

    def test_batch_evaluate(self, engine):
        inputs = [
            make_risk_input(sid="b1", name="Batch1"),
            make_risk_input(sid="b2", name="Batch2"),
            make_risk_input(sid="b3", name="Batch3"),
        ]
        results = engine.batch_evaluate(inputs)
        assert len(results) == 3
        for sid, profile in results.items():
            assert profile.is_evaluated


class TestStrategyRiskEngineQueries:
    def test_get_risk_score(self, engine, risk_input):
        engine.evaluate(risk_input)
        rs = engine.get_risk_score(risk_input.strategy_id)
        assert isinstance(rs, RiskScore)

    def test_get_health(self, engine, risk_input):
        engine.evaluate(risk_input)
        h = engine.get_health(risk_input.strategy_id)
        assert isinstance(h, RiskHealth)

    def test_get_drawdown_report(self, engine, risk_input):
        engine.evaluate(risk_input)
        d = engine.get_drawdown_report(risk_input.strategy_id)
        assert d is not None

    def test_get_stress_report(self, engine, risk_input):
        engine.evaluate(risk_input)
        s = engine.get_stress_report(risk_input.strategy_id)
        assert s is not None

    def test_get_constraints(self, engine, risk_input):
        engine.evaluate(risk_input)
        c = engine.get_constraints(risk_input.strategy_id)
        assert c is not None

    def test_get_confidence(self, engine, risk_input):
        engine.evaluate(risk_input)
        conf = engine.get_confidence(risk_input.strategy_id)
        assert conf is not None

    def test_missing_strategy_returns_none(self, engine):
        assert engine.get_risk_score("nonexistent") is None

    def test_compare_strategies(self, engine):
        inp1 = make_risk_input(sid="c1")
        inp2 = make_risk_input(sid="c2")
        engine.evaluate(inp1)
        engine.evaluate(inp2)
        result = engine.compare_strategies(["c1", "c2"])
        assert "c1" in result and "c2" in result

    def test_operational_strategies_list(self, engine, low_risk_input):
        engine.evaluate(low_risk_input)
        ops = engine.operational_strategies()
        assert isinstance(ops, list)


class TestStrategyRiskEngineHistory:
    def test_take_snapshot(self, engine, risk_input):
        engine.evaluate(risk_input)
        snap = engine.take_snapshot(risk_input.strategy_id)
        assert isinstance(snap, StrategyRiskSnapshot)

    def test_risk_history(self, engine, risk_input):
        engine.evaluate(risk_input)
        engine.evaluate(risk_input)
        history = engine.risk_history(risk_input.strategy_id, n=5)
        assert len(history) >= 2

    def test_risk_score_trend(self, engine, risk_input):
        engine.evaluate(risk_input)
        trend = engine.risk_score_trend(risk_input.strategy_id)
        assert isinstance(trend, list)
        assert all(0.0 <= s <= 100.0 for s in trend)

    def test_snapshot_is_immutable(self, engine, risk_input):
        engine.evaluate(risk_input)
        snap = engine.take_snapshot(risk_input.strategy_id)
        with pytest.raises((AttributeError, TypeError)):
            snap.overall_risk_score = 99.0


class TestStrategyRiskEngineEvents:
    def test_events_emitted_on_evaluate(self, engine_with_bus, risk_input):
        engine, bus = engine_with_bus
        events = []
        bus.subscribe(events.append)
        engine.evaluate(risk_input)
        assert any(e.event_type == RiskEventType.RISK_EVALUATED for e in events)

    def test_emergency_stop_event_on_very_high_risk(self, engine_with_bus):
        engine, bus = engine_with_bus
        events = []
        bus.subscribe(events.append)
        inp = make_risk_input(
            sid="e1",
            evaluation_score=5.0,
            sharpe_ratio=-1.0,
            max_drawdown=0.80,
            win_rate=0.20,
            robustness_score=0.05,
            confidence_score=5.0,
            annualized_vol=0.90,
            current_regime="ranging",
            supported_regimes=("trending",),
            current_volatility_level="extreme",
            market_liquidity="low",
            portfolio_weight=0.50,
        )
        engine.evaluate(inp)
        # Should emit RISK_EVALUATED and either LIMIT_BREACHED or EMERGENCY_STOP
        risk_events = [e for e in events if e.event_type in (
            RiskEventType.EMERGENCY_STOP,
            RiskEventType.LIMIT_BREACHED,
            RiskEventType.STRESS_TEST_FAILED,
            RiskEventType.REGIME_MISMATCH,
        )]
        assert len(risk_events) > 0


class TestStrategyRiskEngineStats:
    def test_stats_structure(self, engine, risk_input):
        engine.evaluate(risk_input)
        stats = engine.stats()
        assert "total_strategies" in stats
        assert "evaluated_strategies" in stats
        assert "operational" in stats
        assert "by_grade" in stats

    def test_stats_counts_increment(self, engine):
        for i in range(3):
            inp = make_risk_input(sid=f"st{i}")
            engine.evaluate(inp)
        stats = engine.stats()
        assert stats["total_strategies"] >= 3
        assert stats["evaluated_strategies"] >= 3
