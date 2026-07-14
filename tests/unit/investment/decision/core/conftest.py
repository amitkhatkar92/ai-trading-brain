"""tests/unit/investment/decision/core/conftest.py
Shared fixtures and a concrete BaseDecision implementation for testing.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.core.decision_constants import (
    ApprovalStatus,
    DecisionType,
    EnvironmentProfile,
    RecommendationType,
    RiskReviewStatus,
)
from iios.investment.decision.core.decision_configuration import DecisionConfiguration
from iios.investment.decision.core.decision_context import make_context
from iios.investment.decision.core.decision_events import EventDispatcher
from iios.investment.decision.core.base_decision import BaseDecision


# ---------------------------------------------------------------------------
# Minimal concrete decision for testing
# ---------------------------------------------------------------------------

class SimpleBuyDecision(BaseDecision):
    """
    Concrete decision that always approves with STRONG_BUY.
    Used in unit tests — contains NO analysis logic.
    """
    DECISION_KEY = "simple_buy"

    async def initialize(self) -> None:
        pass

    async def collect_evidence(self) -> None:
        pass

    async def validate_inputs(self) -> None:
        pass

    async def prepare(self) -> None:
        pass

    async def evaluate(self) -> None:
        pass

    async def score(self) -> float:
        return 80.0

    async def risk_review(self) -> RiskReviewStatus:
        return RiskReviewStatus.APPROVED

    async def generate_recommendation(self) -> RecommendationType:
        return RecommendationType.STRONG_BUY

    async def generate_explanation(self) -> str:
        return "Test: strong buy signal."

    async def approve(self) -> ApprovalStatus:
        return ApprovalStatus.APPROVED

    async def publish(self) -> None:
        pass

    async def archive(self) -> None:
        pass


class RejectedDecision(BaseDecision):
    """Concrete decision that always rejects."""
    DECISION_KEY = "rejected"

    async def initialize(self) -> None: pass
    async def collect_evidence(self) -> None: pass
    async def validate_inputs(self) -> None: pass
    async def prepare(self) -> None: pass
    async def evaluate(self) -> None: pass

    async def score(self) -> float:
        return 30.0

    async def risk_review(self) -> RiskReviewStatus:
        return RiskReviewStatus.REJECTED

    async def generate_recommendation(self) -> RecommendationType:
        return RecommendationType.SELL

    async def generate_explanation(self) -> str:
        return "Test: sell signal."

    async def approve(self) -> ApprovalStatus:
        return ApprovalStatus.REJECTED

    async def publish(self) -> None: pass
    async def archive(self) -> None: pass


class FailingDecision(BaseDecision):
    """Concrete decision that raises during evaluate()."""
    DECISION_KEY = "failing"

    async def initialize(self) -> None: pass
    async def collect_evidence(self) -> None: pass
    async def validate_inputs(self) -> None: pass
    async def prepare(self) -> None: pass

    async def evaluate(self) -> None:
        raise RuntimeError("Simulated evaluation failure.")

    async def score(self) -> float: return 0.0
    async def risk_review(self) -> RiskReviewStatus: return RiskReviewStatus.PENDING
    async def generate_recommendation(self) -> RecommendationType: return RecommendationType.HOLD
    async def generate_explanation(self) -> str: return ""
    async def approve(self) -> ApprovalStatus: return ApprovalStatus.PENDING
    async def publish(self) -> None: pass
    async def archive(self) -> None: pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dev_config() -> DecisionConfiguration:
    return DecisionConfiguration(
        environment=EnvironmentProfile.DEVELOPMENT,
        auto_approve=True,
    )


@pytest.fixture
def dispatcher() -> EventDispatcher:
    return EventDispatcher()


@pytest.fixture
def investment_context():
    return make_context(
        decision_type=DecisionType.INVESTMENT,
        subject_id="RELIANCE",
        subject_type="equity",
        source="test_suite",
        environment=EnvironmentProfile.DEVELOPMENT,
    )


@pytest.fixture
def simple_buy_decision(investment_context, dev_config, dispatcher):
    return SimpleBuyDecision(
        context=investment_context,
        config=dev_config,
        dispatcher=dispatcher,
    )
