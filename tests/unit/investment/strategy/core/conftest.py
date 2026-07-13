"""tests/unit/investment/strategy/core/conftest.py
Shared fixtures for institutional strategy framework tests.
"""
from __future__ import annotations

import pytest
from typing import Any, Dict, List, Optional

from iios.investment.strategy.core import (
    AssetSupport, Candidate, ConfigurationError, ExecutionPlan,
    InstitutionalBaseStrategy, InstitutionalStrategyRegistry,
    MarketSupport, ParameterSpec, RiskValidationError, Signal,
    StrategyCapability, StrategyConfiguration, StrategyContext,
    StrategyDescriptor, StrategyError, StrategyFramework, StrategyState,
    StrategyVersion, SupportedAssetClass, SupportedExchangeZone,
    SupportedMarketType, SupportedTimeframe, TimeframeSupport, TradingStyle,
)


# ── Concrete strategy implementation ─────────────────────────────────────────

class ConcreteStrategy(InstitutionalBaseStrategy):
    """Minimal concrete implementation for framework testing."""

    def initialize(self) -> None:
        self._ready = True

    def load_configuration(self, config: StrategyConfiguration) -> None:
        self._loaded_config = config

    def validate_inputs(self, context: StrategyContext) -> bool:
        return bool(context.symbols)

    def prepare(self, context: StrategyContext) -> None:
        pass

    def analyze_market(self, context: StrategyContext) -> Dict[str, Any]:
        return {"regime": "bull", "breadth": 0.7}

    def generate_candidates(
        self, context: StrategyContext, analysis: Dict[str, Any]
    ) -> List[Candidate]:
        return [Candidate(ticker=s) for s in context.symbols]

    def evaluate_candidates(
        self,
        candidates: List[Candidate],
        context: StrategyContext,
        analysis: Dict[str, Any],
    ) -> List[Candidate]:
        for c in candidates:
            c.add_score("momentum", 70.0)
        return sorted(candidates, key=lambda c: c.total_score(), reverse=True)

    def generate_signals(
        self,
        candidates: List[Candidate],
        context: StrategyContext,
        analysis: Dict[str, Any],
    ) -> List[Signal]:
        return [
            Signal(
                strategy_id=self.strategy_id,
                ticker=c.ticker,
                direction="long",
                confidence=0.75,
            )
            for c in candidates
        ]

    def validate_signals(
        self, signals: List[Signal], context: StrategyContext
    ) -> List[Signal]:
        return signals

    def position_sizing(
        self, signals: List[Signal], context: StrategyContext
    ) -> Dict[str, float]:
        n = len(signals)
        return {s.ticker: 1.0 / n for s in signals} if n else {}

    def risk_validation(
        self,
        signals: List[Signal],
        sizes: Dict[str, float],
        context: StrategyContext,
    ) -> List[Signal]:
        return signals

    def execution_plan(
        self,
        signals: List[Signal],
        sizes: Dict[str, float],
        context: StrategyContext,
    ) -> ExecutionPlan:
        plan = ExecutionPlan(strategy_id=self.strategy_id, signals=signals)
        for s in signals:
            plan.add_position_size(s.ticker, sizes.get(s.ticker, 0.0))
        return plan

    def post_execution(
        self, plan: ExecutionPlan, context: StrategyContext
    ) -> None:
        pass

    def shutdown(self) -> None:
        pass


class RejectAllStrategy(ConcreteStrategy):
    """Rejects all signals at risk_validation step."""

    def risk_validation(self, signals, sizes, context):
        return []


class FailingStrategy(ConcreteStrategy):
    """Raises RuntimeError during analyze_market."""

    def analyze_market(self, context):
        raise RuntimeError("Simulated market analysis failure.")


class EmptyUniverseStrategy(ConcreteStrategy):
    """Returns no candidates (triggers empty-candidate short-circuit)."""

    def generate_candidates(self, context, analysis):
        return []


class InvalidInputStrategy(ConcreteStrategy):
    """Always rejects inputs."""

    def validate_inputs(self, context):
        return False


# ── Factory helpers ───────────────────────────────────────────────────────────

def make_descriptor(
    strategy_id: str = "test_strategy",
    name: str = "Test Strategy",
    **kwargs,
) -> StrategyDescriptor:
    return StrategyDescriptor(
        strategy_id=strategy_id,
        name=name,
        version=kwargs.get("version", StrategyVersion(1, 0, 0)),
        capabilities=kwargs.get(
            "capabilities", frozenset({StrategyCapability.LONG_ONLY})
        ),
        asset_support=kwargs.get(
            "asset_support",
            AssetSupport(frozenset({SupportedAssetClass.EQUITY})),
        ),
        market_support=kwargs.get(
            "market_support",
            MarketSupport(
                market_types=frozenset({SupportedMarketType.EQUITY_CASH}),
                exchange_zones=frozenset({SupportedExchangeZone.NSE}),
            ),
        ),
        timeframe_support=kwargs.get(
            "timeframe_support",
            TimeframeSupport(
                timeframes=frozenset({SupportedTimeframe.D1}),
                styles=frozenset({TradingStyle.SWING}),
                primary_timeframe=SupportedTimeframe.D1,
            ),
        ),
        tags=kwargs.get("tags", ("test", "unit")),
        dependencies=kwargs.get("dependencies", ()),
        is_experimental=kwargs.get("is_experimental", False),
        is_deprecated=kwargs.get("is_deprecated", False),
    )


def make_config(
    strategy_id: str = "test_strategy",
    environment: str = "paper",
    **params,
) -> StrategyConfiguration:
    return StrategyConfiguration(
        strategy_id=strategy_id,
        parameters=dict(params),
        environment=environment,
    )


def make_context(
    strategy_id: str = "test_strategy",
    symbols: Optional[List[str]] = None,
    session_id: str = "test-sess-001",
) -> StrategyContext:
    return StrategyContext(
        strategy_id=strategy_id,
        session_id=session_id,
        configuration=make_config(strategy_id),
        symbols=symbols if symbols is not None else ["INFY", "TCS", "RELIANCE"],
    )


# ── pytest fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def descriptor():
    return make_descriptor()


@pytest.fixture
def config():
    return make_config()


@pytest.fixture
def context():
    return make_context()


@pytest.fixture
def strategy(descriptor):
    return ConcreteStrategy(descriptor)


@pytest.fixture
def loaded_strategy(descriptor, config):
    s = ConcreteStrategy(descriptor)
    s.load(config)
    s.init()
    s.ready()
    return s


@pytest.fixture
def framework():
    fw = StrategyFramework(max_workers=4)
    yield fw
    fw.shutdown()


@pytest.fixture
def loaded_framework(framework, descriptor):
    framework.register(ConcreteStrategy, descriptor)
    framework.load("test_strategy")
    return framework
