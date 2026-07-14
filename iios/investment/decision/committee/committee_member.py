"""iios/investment/decision/committee/committee_member.py
CommitteeMember base class + MemberOpinion dataclass.
Each specialist implements _score_domain() to assess their specific domain.
"""
from __future__ import annotations

import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from iios.investment.decision.committee.committee_constants import (
    ChallengeType,
    SpecialistType,
    VoteType,
)
from iios.investment.decision.committee.member_profiles import SpecialistProfile, get_profile
from iios.investment.decision.committee.member_roles import (
    MemberRole,
    RolePolicy,
    get_role_policy,
)
from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory,
    EvidenceSourceType,
)


# ── MemberOpinion (produced after initial review) ────────────────────────────

@dataclass(frozen=True)
class MemberOpinion:
    """Immutable opinion snapshot produced by one specialist in one round."""
    member_id:          str
    specialist_type:    SpecialistType
    role:               MemberRole
    vote:               VoteType
    confidence:         float              # specialist's confidence in their own vote (0–100)
    domain_score:       float              # quality of evidence in their domain (0–100)
    observations:       Tuple[str, ...]    # key findings
    challenges:         Tuple[str, ...]    # concerns / questions raised
    rationale:          str
    updated_vote:       Optional[VoteType]  = None   # revised after deliberation
    updated_confidence: Optional[float]    = None

    @property
    def effective_vote(self) -> VoteType:
        return self.updated_vote if self.updated_vote is not None else self.vote

    @property
    def effective_confidence(self) -> float:
        return self.updated_confidence if self.updated_confidence is not None else self.confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member_id":          self.member_id,
            "specialist_type":    self.specialist_type.value,
            "role":               self.role.value,
            "vote":               self.vote.value,
            "confidence":         round(self.confidence, 2),
            "domain_score":       round(self.domain_score, 2),
            "observations":       list(self.observations),
            "challenges":         list(self.challenges),
            "rationale":          self.rationale,
            "updated_vote":       self.updated_vote.value if self.updated_vote else None,
            "updated_confidence": round(self.updated_confidence, 2) if self.updated_confidence else None,
            "effective_vote":     self.effective_vote.value,
        }


# ── CommitteeContext (lightweight read-only view of upstream snapshots) ───────
# Imported here lazily to avoid circular — the real CommitteeContext is in
# committee_context.py; members only need the fields accessed below.

class _CtxProtocol:
    """Structural interface for CommitteeContext — avoids circular import."""
    @property
    def evidence(self): ...
    @property
    def confidence(self): ...
    @property
    def risk(self): ...
    @property
    def explanation(self): ...


# ── CommitteeMember ABC ───────────────────────────────────────────────────────

class CommitteeMember(ABC):
    """Abstract base for all committee specialists."""

    def __init__(self, member_id: str, specialist_type: SpecialistType,
                 role: MemberRole, weight_override: Optional[float] = None) -> None:
        self._member_id       = member_id
        self._specialist_type = specialist_type
        self._role            = role
        self._profile         = get_profile(specialist_type)
        self._role_policy     = get_role_policy(role)
        self._weight: float   = (
            weight_override
            if weight_override is not None
            else self._profile.base_vote_weight * self._role_policy.vote_weight_scale
        )

    @property
    def member_id(self) -> str:
        return self._member_id

    @property
    def specialist_type(self) -> SpecialistType:
        return self._specialist_type

    @property
    def role(self) -> MemberRole:
        return self._role

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def profile(self) -> SpecialistProfile:
        return self._profile

    @property
    def role_policy(self) -> RolePolicy:
        return self._role_policy

    @property
    def display_name(self) -> str:
        return self._profile.display_name

    def review(self, ctx: _CtxProtocol) -> MemberOpinion:
        """Produce an initial opinion. Called in the OPENING_REVIEW round."""
        domain_score, vote, observations, challenges = self._score_domain(ctx)
        rationale = self._build_rationale(domain_score, vote, ctx)
        return MemberOpinion(
            member_id       = self._member_id,
            specialist_type = self._specialist_type,
            role            = self._role,
            vote            = vote,
            confidence      = self._domain_to_confidence(domain_score),
            domain_score    = domain_score,
            observations    = tuple(observations),
            challenges      = tuple(challenges),
            rationale       = rationale,
        )

    def deliberate(self, initial_opinion: MemberOpinion,
                   challenge_count: int, resolved_count: int) -> MemberOpinion:
        """
        Revise opinion after challenges.  Deterministic: unresolved challenges
        lower confidence; if confidence falls below threshold, vote may shift.
        """
        if not self._role_policy.can_vote:
            # Observer — no vote update
            return initial_opinion

        unresolved = max(0, challenge_count - resolved_count)
        confidence_penalty = min(30.0, unresolved * 8.0)
        new_confidence = max(0.0, initial_opinion.confidence - confidence_penalty)

        new_vote = initial_opinion.vote
        if new_confidence < 30.0 and initial_opinion.vote == VoteType.SUPPORT:
            new_vote = VoteType.ABSTAIN
        elif new_confidence < 15.0 and initial_opinion.vote == VoteType.ABSTAIN:
            new_vote = VoteType.OPPOSE

        return MemberOpinion(
            member_id          = initial_opinion.member_id,
            specialist_type    = initial_opinion.specialist_type,
            role               = initial_opinion.role,
            vote               = initial_opinion.vote,
            confidence         = initial_opinion.confidence,
            domain_score       = initial_opinion.domain_score,
            observations       = initial_opinion.observations,
            challenges         = initial_opinion.challenges,
            rationale          = initial_opinion.rationale,
            updated_vote       = new_vote,
            updated_confidence = round(new_confidence, 2),
        )

    @abstractmethod
    def _score_domain(self, ctx: _CtxProtocol) -> Tuple[float, VoteType, List[str], List[str]]:
        """
        Returns (domain_score 0–100, vote, observations, challenges).
        Subclasses implement domain-specific scoring logic.
        """

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _score_evidence_items(self, ctx: _CtxProtocol) -> Tuple[float, int]:
        """Returns (weighted_score 0-100, count) for items matching this specialist's profile."""
        items = [
            i for i in ctx.evidence.items
            if i.source_type in self._profile.primary_sources
            or i.category in self._profile.primary_categories
        ]
        if not items:
            return 0.0, 0
        avg_conf    = statistics.mean(i.confidence for i in items)
        avg_fresh   = statistics.mean(i.freshness_score for i in items)
        score       = avg_conf * 0.70 + avg_fresh * 100.0 * 0.30
        return round(min(100.0, score), 4), len(items)

    def _domain_to_confidence(self, domain_score: float) -> float:
        """Map domain_score to specialist's confidence in their vote."""
        return round(min(100.0, max(0.0, domain_score)), 2)

    def _vote_from_score(self, score: float, has_data: bool) -> VoteType:
        if not has_data and self._profile.abstain_on_no_data:
            return VoteType.ABSTAIN
        if score >= self._profile.support_threshold:
            return VoteType.SUPPORT
        if score < self._profile.oppose_threshold:
            return VoteType.OPPOSE
        return VoteType.ABSTAIN

    def _build_rationale(self, domain_score: float, vote: VoteType, ctx) -> str:
        return (
            f"{self._profile.display_name} reviewed {self._profile.domain_description}. "
            f"Domain score: {domain_score:.1f}/100. "
            f"Vote: {vote.value.upper()}. "
            f"Overall confidence: {ctx.confidence.overall_confidence:.1f}/100. "
            f"Overall risk: {ctx.risk.overall_risk:.1f}/100."
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member_id":      self._member_id,
            "specialist_type":self._specialist_type.value,
            "role":           self._role.value,
            "weight":         round(self._weight, 4),
            "display_name":   self.display_name,
        }


# ── Concrete specialist implementations ──────────────────────────────────────

class MarketIntelligenceMember(CommitteeMember):
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.MARKET_INTELLIGENCE, role, weight)

    def _score_domain(self, ctx):
        score, count = self._score_evidence_items(ctx)
        conf  = ctx.confidence.overall_confidence
        score = score * 0.70 + conf * 0.30
        obs   = [f"Market evidence items: {count}",
                 f"Overall confidence: {conf:.1f}/100"]
        chal  = []
        if count < 3:
            chal.append("Insufficient market evidence items for reliable analysis")
        if conf < 50.0:
            chal.append("Low overall confidence in market data")
        return round(min(100.0, score), 2), self._vote_from_score(score, count > 0), obs, chal


class CompanyIntelligenceMember(CommitteeMember):
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.COMPANY_INTELLIGENCE, role, weight)

    def _score_domain(self, ctx):
        score, count = self._score_evidence_items(ctx)
        obs  = [f"Company evidence items: {count}"]
        chal = []
        if count < 2:
            chal.append("Thin company fundamental evidence")
        return round(min(100.0, score), 2), self._vote_from_score(score, count > 0), obs, chal


class StrategyIntelligenceMember(CommitteeMember):
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.STRATEGY_INTELLIGENCE, role, weight)

    def _score_domain(self, ctx):
        score, count = self._score_evidence_items(ctx)
        obs  = [f"Strategy evidence items: {count}"]
        chal = []
        if count < 2:
            chal.append("Insufficient strategy performance data")
        return round(min(100.0, score), 2), self._vote_from_score(score, count > 0), obs, chal


class RiskIntelligenceMember(CommitteeMember):
    """CHAIR — votes based on risk snapshot directly."""
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.RISK_INTELLIGENCE, role, weight)

    def _score_domain(self, ctx):
        risk  = ctx.risk
        if risk.blocks_execution:
            return 0.0, VoteType.OPPOSE, \
                ["Risk controls breached — execution blocked"], \
                ["CRITICAL: Risk policy violation detected"]
        # Invert risk: low risk = high domain score
        domain_score = max(0.0, 100.0 - risk.overall_risk)
        obs  = [f"Overall risk: {risk.overall_risk:.1f}/100 ({risk.risk_level.value})",
                f"Market risk: {risk.decision_risk.market_risk:.1f}/100",
                f"Strategy risk: {risk.decision_risk.strategy_risk:.1f}/100"]
        chal = []
        if risk.overall_risk >= 60.0:
            chal.append(f"Elevated risk ({risk.overall_risk:.1f}/100) requires additional scrutiny")
        if risk.decision_risk.controls_breached:
            chal.append("Risk controls breached")
        return round(domain_score, 2), self._vote_from_score(domain_score, True), obs, chal


class PortfolioIntelligenceMember(CommitteeMember):
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.PORTFOLIO_INTELLIGENCE, role, weight)

    def _score_domain(self, ctx):
        dr   = ctx.risk.decision_risk
        exec_r = dr.execution_risk
        mkt_r  = dr.market_risk
        domain_score = max(0.0, 100.0 - (exec_r * 0.50 + mkt_r * 0.50))
        obs  = [f"Execution risk: {exec_r:.1f}/100",
                f"Market risk: {mkt_r:.1f}/100"]
        chal = []
        if exec_r >= 65.0:
            chal.append(f"High execution risk ({exec_r:.1f}/100)")
        return round(domain_score, 2), self._vote_from_score(domain_score, True), obs, chal


class MacroIntelligenceMember(CommitteeMember):
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.MACRO_INTELLIGENCE, role, weight)

    def _score_domain(self, ctx):
        score, count = self._score_evidence_items(ctx)
        obs  = [f"Macro evidence items: {count}"]
        chal = []
        if count == 0:
            chal.append("No macro evidence items — macro context unknown")
        return round(min(100.0, score), 2), self._vote_from_score(score, count > 0), obs, chal


class QuantitativeAnalystMember(CommitteeMember):
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.QUANTITATIVE_ANALYST, role, weight)

    def _score_domain(self, ctx):
        quality   = ctx.evidence.quality_score
        coverage  = ctx.evidence.coverage_fraction * 100.0
        ev_conf   = ctx.confidence.decision_confidence.evidence_confidence
        domain_score = quality * 0.40 + coverage * 0.30 + ev_conf * 0.30
        obs  = [f"Evidence quality score: {quality:.1f}/100",
                f"Coverage fraction: {ctx.evidence.coverage_fraction:.2f}",
                f"Evidence confidence: {ev_conf:.1f}/100"]
        chal = []
        if quality < 60.0:
            chal.append(f"Below-average evidence quality ({quality:.1f}/100)")
        if ctx.evidence.coverage_fraction < 0.6:
            chal.append("Low evidence coverage — key data sources may be missing")
        return round(min(100.0, domain_score), 2), \
               self._vote_from_score(domain_score, True), obs, chal


class FundamentalAnalystMember(CommitteeMember):
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.FUNDAMENTAL_ANALYST, role, weight)

    def _score_domain(self, ctx):
        score, count = self._score_evidence_items(ctx)
        obs  = [f"Fundamental evidence items: {count}"]
        chal = []
        if count < 2:
            chal.append("Thin fundamental evidence — valuation quality uncertain")
        return round(min(100.0, score), 2), self._vote_from_score(score, count > 0), obs, chal


class TechnicalAnalystMember(CommitteeMember):
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.TECHNICAL_ANALYST, role, weight)

    def _score_domain(self, ctx):
        score, count = self._score_evidence_items(ctx)
        obs  = [f"Technical evidence items: {count}"]
        chal = []
        if count < 2:
            chal.append("Thin technical evidence — signal quality uncertain")
        return round(min(100.0, score), 2), self._vote_from_score(score, count > 0), obs, chal


class SentimentAnalystMember(CommitteeMember):
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.SENTIMENT_ANALYST, role, weight)

    def _score_domain(self, ctx):
        score, count = self._score_evidence_items(ctx)
        obs  = [f"Sentiment evidence items: {count}"]
        chal = []
        if count == 0:
            chal.append("No sentiment data available")
        return round(min(100.0, score), 2), self._vote_from_score(score, count > 0), obs, chal


class ComplianceMember(CommitteeMember):
    """Hard-rule voter: any policy violation → OPPOSE."""
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.COMPLIANCE, role, weight)

    def _score_domain(self, ctx):
        from iios.investment.decision.risk.risk_constants import RiskPolicyStatus
        risk = ctx.risk
        if risk.blocks_execution:
            return 0.0, VoteType.OPPOSE, \
                ["Execution blocked by risk controls"], \
                ["COMPLIANCE BLOCK: controls breached — must be resolved before proceeding"]
        if risk.policy_status == RiskPolicyStatus.VIOLATION:
            return 0.0, VoteType.OPPOSE, \
                [f"Policy status: {risk.policy_status.value}"], \
                ["COMPLIANCE BLOCK: policy violation"]
        domain_score = max(0.0, 100.0 - risk.overall_risk * 0.50)
        obs  = [f"Policy status: {risk.policy_status.value}",
                f"Controls breached: {risk.decision_risk.controls_breached}"]
        chal = []
        if risk.overall_risk >= 70.0:
            chal.append("High risk level may breach compliance thresholds")
        return round(domain_score, 2), self._vote_from_score(domain_score, True), obs, chal


class ResearchMember(CommitteeMember):
    def __init__(self, member_id: str, role: MemberRole, weight: Optional[float] = None):
        super().__init__(member_id, SpecialistType.RESEARCH, role, weight)

    def _score_domain(self, ctx):
        expl_score = ctx.explanation.explainability_score
        consistency= ctx.explanation.explanation.logic_consistency * 100.0
        step_count = ctx.explanation.explanation.reasoning_step_count
        step_bonus = min(20.0, step_count * 4.0)
        domain_score = expl_score * 0.50 + consistency * 0.30 + step_bonus * 0.20
        obs  = [f"Explainability score: {expl_score:.1f}/100",
                f"Logic consistency: {consistency:.1f}/100",
                f"Reasoning steps: {step_count}"]
        chal = []
        if expl_score < 50.0:
            chal.append("Low explainability — decision logic not sufficiently transparent")
        if step_count < 2:
            chal.append("Short reasoning chain — depth of analysis may be insufficient")
        return round(min(100.0, domain_score), 2), \
               self._vote_from_score(domain_score, True), obs, chal


# ── Custom specialist template ────────────────────────────────────────────────

class CustomSpecialistMember(CommitteeMember):
    """
    Pluggable custom specialist.  Override _score_domain() to implement
    domain-specific analysis.
    """
    def __init__(self, member_id: str, role: MemberRole,
                 weight: Optional[float] = None) -> None:
        super().__init__(member_id, SpecialistType.CUSTOM, role, weight)

    def _score_domain(self, ctx):
        # Default: use overall confidence as domain score
        score = ctx.confidence.overall_confidence
        obs   = [f"Overall confidence: {score:.1f}/100"]
        return round(score, 2), self._vote_from_score(score, True), obs, []


# ── Factory ───────────────────────────────────────────────────────────────────

_MEMBER_CLASSES = {
    SpecialistType.MARKET_INTELLIGENCE:  MarketIntelligenceMember,
    SpecialistType.COMPANY_INTELLIGENCE: CompanyIntelligenceMember,
    SpecialistType.STRATEGY_INTELLIGENCE:StrategyIntelligenceMember,
    SpecialistType.RISK_INTELLIGENCE:    RiskIntelligenceMember,
    SpecialistType.PORTFOLIO_INTELLIGENCE:PortfolioIntelligenceMember,
    SpecialistType.MACRO_INTELLIGENCE:   MacroIntelligenceMember,
    SpecialistType.QUANTITATIVE_ANALYST: QuantitativeAnalystMember,
    SpecialistType.FUNDAMENTAL_ANALYST:  FundamentalAnalystMember,
    SpecialistType.TECHNICAL_ANALYST:    TechnicalAnalystMember,
    SpecialistType.SENTIMENT_ANALYST:    SentimentAnalystMember,
    SpecialistType.COMPLIANCE:           ComplianceMember,
    SpecialistType.RESEARCH:             ResearchMember,
    SpecialistType.CUSTOM:               CustomSpecialistMember,
}


def create_member(
    member_id:       str,
    specialist_type: SpecialistType,
    role:            MemberRole,
    weight:          Optional[float] = None,
) -> CommitteeMember:
    cls = _MEMBER_CLASSES.get(specialist_type, CustomSpecialistMember)
    return cls(member_id, role, weight)
