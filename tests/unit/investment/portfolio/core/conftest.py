"""tests/unit/investment/portfolio/core/conftest.py

Shared fixtures for Institutional Portfolio Framework Core unit tests.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.core.base_portfolio import BasePortfolio
from iios.investment.portfolio.core.configuration_engine import ConfigurationEngine
from iios.investment.portfolio.core.framework_context import (
    IntegrationRefs,
    PortfolioRuntimeContext,
)
from iios.investment.portfolio.core.portfolio_configuration import PortfolioConfiguration
from iios.investment.portfolio.core.portfolio_events import (
    EventPriority,
    PortfolioEvent,
    PortfolioEventType,
)
from iios.investment.portfolio.core.portfolio_framework import PortfolioFramework
from iios.investment.portfolio.core.portfolio_metadata import build_metadata
from iios.investment.portfolio.core.portfolio_registry import PortfolioClassRegistry
from iios.investment.portfolio.core.portfolio_types import (
    PortfolioCapability,
    PortfolioDomain,
)


# ---------------------------------------------------------------------------
# Minimal concrete portfolio implementation for testing
# ---------------------------------------------------------------------------

class _MinimalPortfolio(BasePortfolio):
    """Concrete portfolio that satisfies all abstract methods."""

    def initialize(self) -> None:
        pass

    def load_configuration(self) -> PortfolioConfiguration:
        engine = ConfigurationEngine()
        return engine.from_domain(
            PortfolioDomain.SWING,
            portfolio_id=self.portfolio_id,
        )

    def validate_inputs(self) -> bool:
        return True

    def prepare(self) -> None:
        pass

    def construct(self) -> None:
        pass

    def allocate(self) -> None:
        pass

    def rebalance(self) -> None:
        pass

    def evaluate(self) -> None:
        pass

    def monitor(self) -> None:
        pass

    def publish(self) -> None:
        pass

    def archive(self) -> None:
        pass


class _LongTermPortfolio(_MinimalPortfolio):
    """Long-term domain portfolio for domain-specific tests."""

    def load_configuration(self) -> PortfolioConfiguration:
        engine = ConfigurationEngine()
        return engine.from_domain(
            PortfolioDomain.LONG_TERM,
            portfolio_id=self.portfolio_id,
        )


class _FailingPortfolio(BasePortfolio):
    """Portfolio whose initialize() always raises."""

    def initialize(self) -> None:
        raise RuntimeError("deliberate init failure")

    def load_configuration(self) -> PortfolioConfiguration:
        engine = ConfigurationEngine()
        return engine.from_domain(
            PortfolioDomain.CUSTOM,
            portfolio_id=self.portfolio_id,
        )

    def validate_inputs(self) -> bool:
        return False

    def prepare(self) -> None:
        pass

    def construct(self) -> None:
        pass

    def allocate(self) -> None:
        pass

    def rebalance(self) -> None:
        pass

    def evaluate(self) -> None:
        pass

    def monitor(self) -> None:
        pass

    def publish(self) -> None:
        pass

    def archive(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def context() -> PortfolioRuntimeContext:
    return PortfolioRuntimeContext(environment="paper")


@pytest.fixture()
def swing_metadata():
    return build_metadata(
        portfolio_id = "TEST-SWING-001",
        name         = "Test Swing Portfolio",
        domain       = PortfolioDomain.SWING,
        capabilities = frozenset({PortfolioCapability.LONG_POSITIONS}),
        tags         = frozenset({"test", "swing"}),
    )


@pytest.fixture()
def swing_portfolio(swing_metadata, context):
    return _MinimalPortfolio(metadata=swing_metadata, context=context)


@pytest.fixture()
def long_term_metadata():
    return build_metadata(
        portfolio_id = "TEST-LONG-001",
        name         = "Test Long Term",
        domain       = PortfolioDomain.LONG_TERM,
        capabilities = frozenset({PortfolioCapability.LONG_POSITIONS,
                                   PortfolioCapability.DIVIDEND_REINVESTMENT}),
    )


@pytest.fixture()
def long_term_portfolio(long_term_metadata, context):
    return _LongTermPortfolio(metadata=long_term_metadata, context=context)


@pytest.fixture()
def failing_portfolio(context):
    meta = build_metadata(
        portfolio_id = "TEST-FAIL-001",
        name         = "Failing Portfolio",
        domain       = PortfolioDomain.CUSTOM,
    )
    return _FailingPortfolio(metadata=meta, context=context)


@pytest.fixture()
def class_registry() -> PortfolioClassRegistry:
    reg = PortfolioClassRegistry()
    reg.register(_MinimalPortfolio,
                 domain=PortfolioDomain.SWING, version="1.0.0")
    reg.register(_LongTermPortfolio,
                 domain=PortfolioDomain.LONG_TERM, version="1.0.0")
    return reg


@pytest.fixture()
def framework() -> PortfolioFramework:
    PortfolioFramework.reset_instance()
    fw = PortfolioFramework(environment="paper")
    fw.start()
    fw.register_class(_MinimalPortfolio,  domain=PortfolioDomain.SWING)
    fw.register_class(_LongTermPortfolio, domain=PortfolioDomain.LONG_TERM)
    fw.register_class(_FailingPortfolio,  domain=PortfolioDomain.CUSTOM,
                      class_name="_FailingPortfolio")
    yield fw
    fw.stop()
    PortfolioFramework.reset_instance()


@pytest.fixture()
def events_received() -> list:
    """Collector for dispatched events — inject as subscriber."""
    return []
