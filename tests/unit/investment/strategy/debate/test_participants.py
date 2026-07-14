"""tests/unit/investment/strategy/debate/test_participants.py"""
import pytest
from iios.investment.strategy.debate.debate_constants import ParticipantRole
from iios.investment.strategy.debate.participant_profile import (
    build_profile, DEFAULT_WEIGHTS, ParticipantProfile,
)
from iios.investment.strategy.debate.participant_roles import (
    BaseDebateAgent, TechnicalAnalystAgent, RiskAnalystAgent,
    MarketIntelligenceAgent, ROLE_CLASS_MAP,
)
from iios.investment.strategy.debate.agent_registry import (
    AgentRegistry, create_default_registry,
)


class TestParticipantProfile:
    def test_build_profile_defaults(self):
        profile = build_profile(ParticipantRole.TECHNICAL_ANALYST)
        assert profile.role == ParticipantRole.TECHNICAL_ANALYST
        assert profile.weight == DEFAULT_WEIGHTS[ParticipantRole.TECHNICAL_ANALYST]
        assert len(profile.expertise_areas) > 0

    def test_build_profile_custom_weight(self):
        profile = build_profile(ParticipantRole.RISK_ANALYST, weight=3.0)
        assert profile.weight == 3.0

    def test_profile_is_frozen(self):
        profile = build_profile(ParticipantRole.MACRO_ANALYST)
        with pytest.raises((AttributeError, TypeError)):
            profile.weight = 99.0  # type: ignore

    def test_profile_to_dict(self):
        profile = build_profile(ParticipantRole.RISK_ANALYST)
        d = profile.to_dict()
        assert "role" in d
        assert "weight" in d
        assert "expertise_areas" in d

    def test_default_weights_all_roles(self):
        for role in ParticipantRole:
            if role == ParticipantRole.CUSTOM:
                continue
            assert role in DEFAULT_WEIGHTS


class TestBuiltinAgents:
    def test_technical_analyst_role(self):
        agent = TechnicalAnalystAgent()
        assert agent.role == ParticipantRole.TECHNICAL_ANALYST

    def test_risk_analyst_has_higher_weight(self):
        risk  = RiskAnalystAgent()
        sent  = pytest.importorskip("iios.investment.strategy.debate.participant_roles")
        senti = sent.SentimentAnalystAgent()
        assert risk.weight > senti.weight

    def test_all_roles_have_agent_class(self):
        for role, cls in ROLE_CLASS_MAP.items():
            agent = cls()
            assert agent.role == role

    def test_agents_have_unique_ids(self):
        agents = [TechnicalAnalystAgent() for _ in range(3)]
        ids    = [a.participant_id for a in agents]
        assert len(set(ids)) == 3


class TestAgentRegistry:
    def test_register_and_get(self):
        reg   = AgentRegistry()
        agent = TechnicalAnalystAgent()
        reg.register(agent)
        found = reg.get(agent.participant_id)
        assert found is agent

    def test_by_role(self):
        reg   = AgentRegistry()
        agent = RiskAnalystAgent()
        reg.register(agent)
        agents = reg.by_role(ParticipantRole.RISK_ANALYST)
        assert len(agents) == 1
        assert agents[0] is agent

    def test_count(self):
        reg = AgentRegistry()
        reg.register(TechnicalAnalystAgent())
        reg.register(RiskAnalystAgent())
        assert reg.count() == 2

    def test_remove(self):
        reg   = AgentRegistry()
        agent = TechnicalAnalystAgent()
        reg.register(agent)
        reg.remove(agent.participant_id)
        assert reg.get(agent.participant_id) is None

    def test_create_default_registry(self):
        reg = create_default_registry()
        assert reg.count() == 10  # 10 built-in roles

    def test_default_registry_all_roles(self):
        reg    = create_default_registry()
        agents = reg.all_agents()
        roles  = {a.role for a in agents}
        expected = set(ROLE_CLASS_MAP.keys()) - {ParticipantRole.CUSTOM}
        assert roles == expected

    def test_all_profiles(self):
        reg = create_default_registry()
        profiles = reg.all_profiles()
        assert len(profiles) == 10
        for p in profiles:
            assert isinstance(p, ParticipantProfile)


class TestAgentAsync:
    """Test async agent methods using asyncio.run."""

    def test_technical_analyst_opening(self, debate_context, evidence_registry):
        import asyncio
        agent = TechnicalAnalystAgent()
        args  = asyncio.run(agent.opening_statement(debate_context, evidence_registry))
        assert isinstance(args, list)

    def test_risk_analyst_generates_arguments(self, debate_context, evidence_registry):
        import asyncio
        agent = RiskAnalystAgent()
        args  = asyncio.run(agent.generate_arguments(debate_context, evidence_registry))
        assert isinstance(args, list)

    def test_agents_cast_vote(self, debate_context, evidence_registry):
        import asyncio
        agent = MarketIntelligenceAgent()
        vote  = asyncio.run(agent.cast_vote(debate_context, [], evidence_registry))
        assert vote is not None
        assert vote.participant_id == agent.participant_id

    def test_agent_final_opinion(self, debate_context):
        import asyncio
        agent   = TechnicalAnalystAgent()
        opinion = asyncio.run(agent.final_opinion(debate_context, None))
        assert isinstance(opinion, str)
        assert len(opinion) > 0
