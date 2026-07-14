"""tests/unit/investment/strategy/debate/conftest.py
Shared fixtures for debate engine tests.
"""
import asyncio
import pytest
from datetime import datetime, timezone

from iios.investment.strategy.debate.debate_constants import (
    ArgumentType, EvidenceSource, EvidenceReliability, EvidenceWeight,
    ParticipantRole, VoteOutcome, VotingMechanism, ConsensusLevel,
)
from iios.investment.strategy.debate.debate_context import (
    DebateContext, StrategyDebateInput, OpportunityDebateInput, MarketSnapshot,
)
from iios.investment.strategy.debate.debate_session import DebateSession
from iios.investment.strategy.debate.debate_events import DebateEventBus
from iios.investment.strategy.debate.evidence_registry import EvidenceRegistry, make_evidence
from iios.investment.strategy.debate.argument_manager import (
    ArgumentManager, make_argument, make_rebuttal,
)
from iios.investment.strategy.debate.voting_engine import make_vote
from iios.investment.strategy.debate.participant_profile import build_profile, DEFAULT_WEIGHTS
from iios.investment.strategy.debate.agent_registry import create_default_registry
from iios.investment.strategy.debate.consensus_engine import ConsensusPolicy
from iios.investment.strategy.debate.debate_orchestrator import OrchestratorConfig


# ── Context fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_strategy():
    return StrategyDebateInput(
        strategy_id="strat-001",
        strategy_name="NIFTY Breakout",
        category="momentum",
        direction="BUY",
        min_rr=2.0,
        max_loss_pct=2.0,
    )


@pytest.fixture
def sample_opportunity():
    return OpportunityDebateInput(
        opportunity_id="opp-001",
        symbol="RELIANCE",
        asset_class="equity",
        entry_price=2450.0,
        target_price=2550.0,
        stop_price=2400.0,
    )


@pytest.fixture
def sample_market():
    return MarketSnapshot(
        regime="bullish",
        nifty_level=22000.0,
        vix=14.5,
        sector="energy",
        sector_trend="up",
    )


@pytest.fixture
def debate_context(sample_strategy, sample_opportunity, sample_market):
    return DebateContext(
        strategy=sample_strategy,
        opportunity=sample_opportunity,
        market=sample_market,
    )


# ── Evidence fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def session_id():
    return "test-session-001"


@pytest.fixture
def evidence_registry(session_id):
    reg = EvidenceRegistry(session_id)
    reg.add(make_evidence(session_id, EvidenceSource.TECHNICAL_ANALYSIS, "technical",
                          "RSI Oversold", "RSI at 32 — potential reversal", 70.0))
    reg.add(make_evidence(session_id, EvidenceSource.MARKET_INTELLIGENCE, "market",
                          "Bullish Regime", "Market regime is bullish", 72.0))
    reg.add(make_evidence(session_id, EvidenceSource.RISK_INTELLIGENCE, "risk",
                          "Low Risk", "VaR within limits", 65.0))
    return reg


# ── Argument fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def argument_manager(session_id):
    mgr = ArgumentManager(session_id)
    mgr.add_argument(make_argument(
        session_id, "agent-1", ParticipantRole.TECHNICAL_ANALYST,
        ArgumentType.SUPPORTING, "Price is bullish", "RSI confirms", 75.0,
    ))
    mgr.add_argument(make_argument(
        session_id, "agent-2", ParticipantRole.RISK_ANALYST,
        ArgumentType.OPPOSING, "Risk too high", "VaR elevated", 65.0,
    ))
    return mgr


# ── Vote fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_votes(session_id):
    return [
        make_vote(session_id, "a1", ParticipantRole.TECHNICAL_ANALYST,
                  VoteOutcome.SUPPORT, 80.0, "Technical supports", 1.5),
        make_vote(session_id, "a2", ParticipantRole.RISK_ANALYST,
                  VoteOutcome.SUPPORT, 70.0, "Risk acceptable", 2.0),
        make_vote(session_id, "a3", ParticipantRole.MACRO_ANALYST,
                  VoteOutcome.NEUTRAL, 55.0, "Macro neutral", 1.8),
        make_vote(session_id, "a4", ParticipantRole.FUNDAMENTAL_ANALYST,
                  VoteOutcome.OPPOSE, 60.0, "Valuation stretched", 1.5),
        make_vote(session_id, "a5", ParticipantRole.MARKET_INTELLIGENCE,
                  VoteOutcome.STRONG_SUPPORT, 90.0, "Regime strongly bullish", 1.3),
    ]


# ── Registry fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def default_registry():
    return create_default_registry()


@pytest.fixture
def debate_session(debate_context):
    return DebateSession(debate_context)


@pytest.fixture
def event_bus():
    return DebateEventBus()


@pytest.fixture
def fast_config():
    """Config with very fast timeouts for testing."""
    return OrchestratorConfig(
        max_argument_rounds=1,
        enable_rebuttals=True,
        rebuttal_rounds=1,
        agent_timeout_seconds=5.0,
        min_quorum_fraction=0.3,
    )
