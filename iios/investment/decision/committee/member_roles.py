"""iios/investment/decision/committee/member_roles.py
Member role definitions and role-based access rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Set

from iios.investment.decision.committee.committee_constants import SpecialistType


class MemberRole(str, Enum):
    CHAIR          = "chair"          # leads deliberation, casts deciding vote on ties
    VOTING_MEMBER  = "voting_member"  # participates and votes
    OBSERVER       = "observer"       # attends, no vote weight


@dataclass(frozen=True)
class RolePolicy:
    """Per-role behavioural constraints."""
    role:              MemberRole
    vote_weight_scale: float    # multiplier applied to the member's base weight
    can_vote:          bool
    can_challenge:     bool
    can_abstain:       bool
    tie_breaks:        bool     # only CHAIR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role":              self.role.value,
            "vote_weight_scale": self.vote_weight_scale,
            "can_vote":          self.can_vote,
            "can_challenge":     self.can_challenge,
            "can_abstain":       self.can_abstain,
            "tie_breaks":        self.tie_breaks,
        }


ROLE_POLICIES: Dict[MemberRole, RolePolicy] = {
    MemberRole.CHAIR: RolePolicy(
        role=MemberRole.CHAIR,
        vote_weight_scale=1.50,
        can_vote=True,
        can_challenge=True,
        can_abstain=True,
        tie_breaks=True,
    ),
    MemberRole.VOTING_MEMBER: RolePolicy(
        role=MemberRole.VOTING_MEMBER,
        vote_weight_scale=1.00,
        can_vote=True,
        can_challenge=True,
        can_abstain=True,
        tie_breaks=False,
    ),
    MemberRole.OBSERVER: RolePolicy(
        role=MemberRole.OBSERVER,
        vote_weight_scale=0.00,
        can_vote=False,
        can_challenge=True,
        can_abstain=True,
        tie_breaks=False,
    ),
}

# Default role for each specialist type
DEFAULT_SPECIALIST_ROLES: Dict[SpecialistType, MemberRole] = {
    SpecialistType.RISK_INTELLIGENCE:     MemberRole.CHAIR,
    SpecialistType.MARKET_INTELLIGENCE:   MemberRole.VOTING_MEMBER,
    SpecialistType.COMPANY_INTELLIGENCE:  MemberRole.VOTING_MEMBER,
    SpecialistType.STRATEGY_INTELLIGENCE: MemberRole.VOTING_MEMBER,
    SpecialistType.PORTFOLIO_INTELLIGENCE:MemberRole.VOTING_MEMBER,
    SpecialistType.MACRO_INTELLIGENCE:    MemberRole.VOTING_MEMBER,
    SpecialistType.QUANTITATIVE_ANALYST:  MemberRole.VOTING_MEMBER,
    SpecialistType.FUNDAMENTAL_ANALYST:   MemberRole.VOTING_MEMBER,
    SpecialistType.TECHNICAL_ANALYST:     MemberRole.VOTING_MEMBER,
    SpecialistType.SENTIMENT_ANALYST:     MemberRole.VOTING_MEMBER,
    SpecialistType.COMPLIANCE:            MemberRole.VOTING_MEMBER,
    SpecialistType.RESEARCH:              MemberRole.VOTING_MEMBER,
    SpecialistType.CUSTOM:                MemberRole.VOTING_MEMBER,
}


def get_role_policy(role: MemberRole) -> RolePolicy:
    return ROLE_POLICIES[role]
