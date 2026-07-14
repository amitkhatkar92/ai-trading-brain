"""iios/investment/decision/committee/member_registry.py
MemberRegistry — thread-safe registry of committee members per session.
"""
from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, List, Optional

from iios.investment.decision.committee.committee_constants import SpecialistType
from iios.investment.decision.committee.committee_member import (
    CommitteeMember,
    create_member,
)
from iios.investment.decision.committee.member_profiles import SPECIALIST_PROFILES
from iios.investment.decision.committee.member_roles import (
    DEFAULT_SPECIALIST_ROLES,
    MemberRole,
)


# ── Default committee composition ─────────────────────────────────────────────

DEFAULT_COMMITTEE_SPEC: List[Dict[str, Any]] = [
    {"type": SpecialistType.RISK_INTELLIGENCE,     "role": MemberRole.CHAIR},
    {"type": SpecialistType.MARKET_INTELLIGENCE,   "role": MemberRole.VOTING_MEMBER},
    {"type": SpecialistType.COMPANY_INTELLIGENCE,  "role": MemberRole.VOTING_MEMBER},
    {"type": SpecialistType.STRATEGY_INTELLIGENCE, "role": MemberRole.VOTING_MEMBER},
    {"type": SpecialistType.PORTFOLIO_INTELLIGENCE,"role": MemberRole.VOTING_MEMBER},
    {"type": SpecialistType.MACRO_INTELLIGENCE,    "role": MemberRole.VOTING_MEMBER},
    {"type": SpecialistType.QUANTITATIVE_ANALYST,  "role": MemberRole.VOTING_MEMBER},
    {"type": SpecialistType.FUNDAMENTAL_ANALYST,   "role": MemberRole.VOTING_MEMBER},
    {"type": SpecialistType.TECHNICAL_ANALYST,     "role": MemberRole.VOTING_MEMBER},
    {"type": SpecialistType.SENTIMENT_ANALYST,     "role": MemberRole.VOTING_MEMBER},
    {"type": SpecialistType.COMPLIANCE,            "role": MemberRole.VOTING_MEMBER},
    {"type": SpecialistType.RESEARCH,              "role": MemberRole.VOTING_MEMBER},
]


class MemberRegistry:
    """
    Thread-safe registry that instantiates and holds committee members
    for a single committee session.
    """

    def __init__(self) -> None:
        self._lock:    threading.RLock    = threading.RLock()
        self._members: Dict[str, CommitteeMember] = {}

    @classmethod
    def default_committee(cls) -> "MemberRegistry":
        """Create a registry pre-populated with the standard 12-member committee."""
        reg = cls()
        for spec in DEFAULT_COMMITTEE_SPEC:
            reg.add_member(spec["type"], spec["role"])
        return reg

    def add_member(
        self,
        specialist_type: SpecialistType,
        role:            Optional[MemberRole]  = None,
        weight:          Optional[float]       = None,
        member_id:       Optional[str]         = None,
    ) -> str:
        effective_role = role or DEFAULT_SPECIALIST_ROLES.get(
            specialist_type, MemberRole.VOTING_MEMBER,
        )
        mid = member_id or f"{specialist_type.value}_{str(uuid.uuid4())[:8]}"
        with self._lock:
            member = create_member(mid, specialist_type, effective_role, weight)
            self._members[mid] = member
        return mid

    def remove_member(self, member_id: str) -> None:
        with self._lock:
            self._members.pop(member_id, None)

    def get_member(self, member_id: str) -> Optional[CommitteeMember]:
        with self._lock:
            return self._members.get(member_id)

    def all_members(self) -> List[CommitteeMember]:
        with self._lock:
            return list(self._members.values())

    def voting_members(self) -> List[CommitteeMember]:
        with self._lock:
            return [
                m for m in self._members.values()
                if m.role_policy.can_vote and m.role != MemberRole.OBSERVER
            ]

    def chair(self) -> Optional[CommitteeMember]:
        with self._lock:
            for m in self._members.values():
                if m.role == MemberRole.CHAIR:
                    return m
        return None

    def member_count(self) -> int:
        with self._lock:
            return len(self._members)

    def voting_member_count(self) -> int:
        return len(self.voting_members())

    def total_voting_weight(self) -> float:
        return sum(m.weight for m in self.voting_members())

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [m.to_dict() for m in self._members.values()]
