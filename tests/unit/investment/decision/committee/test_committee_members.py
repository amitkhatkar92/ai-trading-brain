"""tests/unit/investment/decision/committee/test_committee_members.py
Tests for specialist members, member registry, profiles, and roles.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.committee.committee_constants import (
    SpecialistType,
    VoteType,
)
from iios.investment.decision.committee.committee_member import (
    CommitteeMember,
    ComplianceMember,
    MarketIntelligenceMember,
    MemberOpinion,
    RiskIntelligenceMember,
    create_member,
)
from iios.investment.decision.committee.member_profiles import (
    SPECIALIST_PROFILES,
    get_profile,
)
from iios.investment.decision.committee.member_registry import MemberRegistry
from iios.investment.decision.committee.member_roles import (
    DEFAULT_SPECIALIST_ROLES,
    MemberRole,
    ROLE_POLICIES,
    get_role_policy,
)


class TestMemberProfiles:
    def test_all_built_in_have_profiles(self):
        for t in SpecialistType:
            if t == SpecialistType.CUSTOM:
                continue
            p = get_profile(t)
            assert p.specialist_type == t

    def test_risk_is_highest_weight(self):
        risk_p = SPECIALIST_PROFILES[SpecialistType.RISK_INTELLIGENCE]
        other_weights = [
            p.base_vote_weight for t, p in SPECIALIST_PROFILES.items()
            if t != SpecialistType.RISK_INTELLIGENCE
        ]
        assert risk_p.base_vote_weight >= max(other_weights)

    def test_compliance_stricter_thresholds(self):
        comp   = SPECIALIST_PROFILES[SpecialistType.COMPLIANCE]
        market = SPECIALIST_PROFILES[SpecialistType.MARKET_INTELLIGENCE]
        assert comp.oppose_threshold >= market.oppose_threshold

    def test_profile_to_dict(self):
        p = get_profile(SpecialistType.MARKET_INTELLIGENCE)
        d = p.to_dict()
        assert "specialist_type" in d
        assert "base_vote_weight" in d


class TestMemberRoles:
    def test_chair_has_highest_weight_scale(self):
        chair  = ROLE_POLICIES[MemberRole.CHAIR].vote_weight_scale
        member = ROLE_POLICIES[MemberRole.VOTING_MEMBER].vote_weight_scale
        assert chair > member

    def test_observer_cannot_vote(self):
        obs = ROLE_POLICIES[MemberRole.OBSERVER]
        assert not obs.can_vote
        assert obs.vote_weight_scale == 0.0

    def test_chair_can_tie_break(self):
        assert ROLE_POLICIES[MemberRole.CHAIR].tie_breaks

    def test_voting_member_cannot_tie_break(self):
        assert not ROLE_POLICIES[MemberRole.VOTING_MEMBER].tie_breaks

    def test_default_risk_role_is_chair(self):
        assert DEFAULT_SPECIALIST_ROLES[SpecialistType.RISK_INTELLIGENCE] == MemberRole.CHAIR


class TestCreateMember:
    def test_creates_correct_type(self):
        m = create_member("M1", SpecialistType.MARKET_INTELLIGENCE, MemberRole.VOTING_MEMBER)
        assert isinstance(m, CommitteeMember)
        assert m.specialist_type == SpecialistType.MARKET_INTELLIGENCE

    def test_creates_risk_chair(self):
        m = create_member("C1", SpecialistType.RISK_INTELLIGENCE, MemberRole.CHAIR)
        assert m.role == MemberRole.CHAIR

    def test_weight_override(self):
        m = create_member("M2", SpecialistType.COMPLIANCE, MemberRole.VOTING_MEMBER, weight=2.0)
        assert m.weight == pytest.approx(2.0)

    def test_all_types_creatable(self):
        for t in SpecialistType:
            m = create_member(f"m_{t.value}", t, MemberRole.VOTING_MEMBER)
            assert m is not None


class TestMemberReview:
    def test_review_returns_opinion(self, rich_context):
        m = MarketIntelligenceMember("M1", MemberRole.VOTING_MEMBER)
        op = m.review(rich_context)
        assert isinstance(op, MemberOpinion)

    def test_opinion_vote_is_valid(self, rich_context):
        for t in list(SpecialistType)[:5]:
            m = create_member(f"m_{t.value}", t, MemberRole.VOTING_MEMBER)
            op = m.review(rich_context)
            assert op.vote in list(VoteType)

    def test_opinion_confidence_range(self, rich_context):
        m = RiskIntelligenceMember("C1", MemberRole.CHAIR)
        op = m.review(rich_context)
        assert 0.0 <= op.confidence <= 100.0

    def test_opinion_domain_score_range(self, rich_context):
        m = MarketIntelligenceMember("M1", MemberRole.VOTING_MEMBER)
        op = m.review(rich_context)
        assert 0.0 <= op.domain_score <= 100.0

    def test_compliance_opposes_blocked(self, rich_context):
        # only if execution is actually blocked — otherwise may SUPPORT
        comp = ComplianceMember("CL1", MemberRole.VOTING_MEMBER)
        op   = comp.review(rich_context)
        if rich_context.risk.blocks_execution:
            assert op.vote == VoteType.OPPOSE

    def test_risk_opposes_blocked(self, rich_context):
        risk_m = RiskIntelligenceMember("R1", MemberRole.CHAIR)
        op     = risk_m.review(rich_context)
        if rich_context.risk.blocks_execution:
            assert op.vote == VoteType.OPPOSE

    def test_review_observations_populated(self, rich_context):
        m  = create_member("M3", SpecialistType.QUANTITATIVE_ANALYST, MemberRole.VOTING_MEMBER)
        op = m.review(rich_context)
        assert len(op.observations) >= 1

    def test_rationale_non_empty(self, rich_context):
        m  = MarketIntelligenceMember("M4", MemberRole.VOTING_MEMBER)
        op = m.review(rich_context)
        assert len(op.rationale) > 0


class TestMemberDeliberate:
    def test_no_challenges_unchanged(self, rich_context):
        m  = MarketIntelligenceMember("M1", MemberRole.VOTING_MEMBER)
        op = m.review(rich_context)
        up = m.deliberate(op, 0, 0)
        assert up.updated_confidence == pytest.approx(op.confidence, abs=1.0)

    def test_many_unresolved_challenges_reduce_confidence(self, rich_context):
        m  = MarketIntelligenceMember("M1", MemberRole.VOTING_MEMBER)
        op = m.review(rich_context)
        up = m.deliberate(op, 5, 0)
        conf = up.updated_confidence if up.updated_confidence is not None else op.confidence
        assert conf <= op.confidence

    def test_resolved_challenges_less_penalty(self, rich_context):
        m  = MarketIntelligenceMember("M1", MemberRole.VOTING_MEMBER)
        op = m.review(rich_context)
        up_all_resolved = m.deliberate(op, 5, 5)
        up_none_resolved= m.deliberate(op, 5, 0)
        c_res  = up_all_resolved.updated_confidence  or op.confidence
        c_none = up_none_resolved.updated_confidence or op.confidence
        assert c_res >= c_none


class TestMemberRegistry:
    def test_default_committee_has_12_members(self):
        r = MemberRegistry.default_committee()
        assert r.member_count() == 12

    def test_one_chair(self):
        r = MemberRegistry.default_committee()
        assert r.chair() is not None
        assert r.chair().role == MemberRole.CHAIR

    def test_voting_members_count(self):
        r = MemberRegistry.default_committee()
        assert r.voting_member_count() == 12  # all 12 can vote (chair included)

    def test_add_member(self):
        r = MemberRegistry()
        mid = r.add_member(SpecialistType.COMPLIANCE, MemberRole.VOTING_MEMBER)
        assert r.get_member(mid) is not None

    def test_remove_member(self):
        r   = MemberRegistry()
        mid = r.add_member(SpecialistType.RESEARCH, MemberRole.VOTING_MEMBER)
        r.remove_member(mid)
        assert r.get_member(mid) is None

    def test_total_voting_weight_positive(self):
        r = MemberRegistry.default_committee()
        assert r.total_voting_weight() > 0.0

    def test_snapshot_returns_list(self):
        r = MemberRegistry.default_committee()
        s = r.snapshot()
        assert len(s) == 12
