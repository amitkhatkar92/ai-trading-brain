"""iios/investment/strategy/debate/participant_roles.py
BaseDebateAgent ABC and 10 built-in participant implementations.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from iios.investment.strategy.debate.debate_constants import (
    ArgumentType,
    EvidenceSource,
    ParticipantRole,
    RebuttalType,
    VoteOutcome,
)
from iios.investment.strategy.debate.argument_manager import (
    Argument,
    Rebuttal,
    make_argument,
    make_rebuttal,
)
from iios.investment.strategy.debate.participant_profile import (
    ParticipantProfile,
    build_profile,
)

if TYPE_CHECKING:
    from iios.investment.strategy.debate.debate_context import DebateContext
    from iios.investment.strategy.debate.evidence_registry import Evidence, EvidenceRegistry
    from iios.investment.strategy.debate.voting_engine import Vote


class BaseDebateAgent(ABC):
    """
    Abstract base for all debate participants.
    Every built-in and custom agent must implement this interface.
    All methods are async — use asyncio.run() or await them.
    """

    def __init__(self, profile: Optional[ParticipantProfile] = None) -> None:
        self._profile = profile or build_profile(self.role)

    @property
    @abstractmethod
    def role(self) -> ParticipantRole: ...

    @property
    def participant_id(self) -> str:
        return self._profile.participant_id

    @property
    def profile(self) -> ParticipantProfile:
        return self._profile

    @property
    def weight(self) -> float:
        return self._profile.weight

    @abstractmethod
    async def opening_statement(
        self,
        context: "DebateContext",
        registry: "EvidenceRegistry",
    ) -> List[Argument]: ...

    @abstractmethod
    async def generate_arguments(
        self,
        context:  "DebateContext",
        registry: "EvidenceRegistry",
        round_num: int = 1,
    ) -> List[Argument]: ...

    @abstractmethod
    async def generate_rebuttal(
        self,
        target:   Argument,
        context:  "DebateContext",
        registry: "EvidenceRegistry",
    ) -> Optional[Rebuttal]: ...

    @abstractmethod
    async def cast_vote(
        self,
        context:   "DebateContext",
        arguments: List[Argument],
        registry:  "EvidenceRegistry",
    ) -> "Vote": ...

    @abstractmethod
    async def final_opinion(
        self,
        context:   "DebateContext",
        consensus: Any,
    ) -> str: ...

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _relevant_evidence(
        self,
        registry: "EvidenceRegistry",
        sources:  List[EvidenceSource],
    ) -> List["Evidence"]:
        result = []
        for src in sources:
            result.extend(registry.by_source(src))
        return result

    def _average_score(self, items: List["Evidence"]) -> float:
        if not items:
            return 50.0
        return sum(
            (e.score.weighted_score if e.score else e.raw_score) for e in items
        ) / len(items)

    def _make_arg(
        self,
        session_id:    str,
        argument_type: ArgumentType,
        claim:         str,
        reasoning:     str,
        confidence:    float,
        evidence_ids:  Optional[List[str]] = None,
    ) -> Argument:
        return make_argument(
            session_id=session_id,
            participant_id=self.participant_id,
            role=self.role,
            argument_type=argument_type,
            claim=claim,
            reasoning=reasoning,
            confidence=confidence,
            weight=self.weight,
            evidence_ids=evidence_ids,
        )

    def _make_rebuttal(
        self,
        session_id:    str,
        target_arg_id: str,
        claim:         str,
        reasoning:     str,
        confidence:    float,
    ) -> Rebuttal:
        return make_rebuttal(
            session_id=session_id,
            participant_id=self.participant_id,
            role=self.role,
            target_arg_id=target_arg_id,
            rebuttal_type=RebuttalType.DIRECT_COUNTER,
            claim=claim,
            reasoning=reasoning,
            confidence=confidence,
            weight=self.weight,
        )

    def _vote_from_score(self, score: float) -> VoteOutcome:
        """Map an average evidence score (0–100) to a VoteOutcome."""
        if score >= 75:
            return VoteOutcome.STRONG_SUPPORT
        if score >= 60:
            return VoteOutcome.SUPPORT
        if score <= 25:
            return VoteOutcome.STRONG_OPPOSE
        if score <= 40:
            return VoteOutcome.OPPOSE
        return VoteOutcome.NEUTRAL


# ──────────────────────────────────────────────────────────────────────────────
# Built-in Agents
# ──────────────────────────────────────────────────────────────────────────────

class TechnicalAnalystAgent(BaseDebateAgent):
    _SOURCES = [EvidenceSource.TECHNICAL_ANALYSIS]

    @property
    def role(self) -> ParticipantRole:
        return ParticipantRole.TECHNICAL_ANALYST

    async def opening_statement(self, context, registry):
        session_id = context.context_id
        evidence   = self._relevant_evidence(registry, self._SOURCES)
        avg        = self._average_score(evidence)
        direction  = "bullish technical setup" if avg >= 55 else ("bearish technical setup" if avg <= 45 else "neutral technical setup")
        return [self._make_arg(session_id, ArgumentType.NEUTRAL,
            claim=f"Technical opening: {direction}",
            reasoning=f"Average technical score {avg:.0f}/100 from {len(evidence)} indicators.",
            confidence=60.0,
            evidence_ids=[e.evidence_id for e in evidence[:3]],
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        session_id = context.context_id
        evidence   = self._relevant_evidence(registry, self._SOURCES)
        if not evidence:
            return []
        avg = self._average_score(evidence)
        args = []
        if avg >= 60:
            args.append(self._make_arg(session_id, ArgumentType.SUPPORTING,
                claim="Technical indicators are bullish",
                reasoning=f"Composite technical score {avg:.0f}/100 indicates price momentum favours the entry.",
                confidence=min(avg, 90.0),
                evidence_ids=[e.evidence_id for e in evidence],
            ))
        elif avg <= 40:
            args.append(self._make_arg(session_id, ArgumentType.OPPOSING,
                claim="Technical indicators are bearish",
                reasoning=f"Composite technical score {avg:.0f}/100 suggests unfavourable entry conditions.",
                confidence=min(100.0 - avg, 90.0),
                evidence_ids=[e.evidence_id for e in evidence],
            ))
        return args

    async def generate_rebuttal(self, target, context, registry):
        if target.role == self.role:
            return None
        if target.argument_type == ArgumentType.OPPOSING:
            score = self._average_score(self._relevant_evidence(registry, self._SOURCES))
            if score >= 60:
                return self._make_rebuttal(
                    context.context_id, target.argument_id,
                    claim="Technical picture contradicts opposing view",
                    reasoning=f"Technical score {score:.0f}/100 supports entry despite opposing argument.",
                    confidence=65.0,
                )
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate.voting_engine import make_vote
        evidence = self._relevant_evidence(registry, self._SOURCES)
        score    = self._average_score(evidence)
        outcome  = self._vote_from_score(score)
        return make_vote(
            session_id=context.context_id,
            participant_id=self.participant_id,
            role=self.role,
            outcome=outcome,
            confidence=abs(score - 50) + 50,
            rationale=f"Technical analysis score: {score:.0f}/100",
            weight=self.weight,
        )

    async def final_opinion(self, context, consensus):
        evidence = []  # registry not available here; use consensus data
        return f"Technical Analyst: Based on price action and momentum indicators, the technical setup {'supports' if consensus and getattr(consensus, 'winning_outcome', None) and getattr(consensus.winning_outcome, 'is_positive', False) else 'does not clearly support'} this opportunity."


class FundamentalAnalystAgent(BaseDebateAgent):
    _SOURCES = [EvidenceSource.FUNDAMENTAL_ANALYSIS]

    @property
    def role(self) -> ParticipantRole:
        return ParticipantRole.FUNDAMENTAL_ANALYST

    async def opening_statement(self, context, registry):
        session_id = context.context_id
        evidence   = self._relevant_evidence(registry, self._SOURCES)
        avg        = self._average_score(evidence)
        return [self._make_arg(session_id, ArgumentType.NEUTRAL,
            claim=f"Fundamental opening: valuation score {avg:.0f}/100",
            reasoning=f"Reviewing {len(evidence)} fundamental data points.",
            confidence=55.0,
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        if not evidence:
            return []
        avg = self._average_score(evidence)
        if avg >= 62:
            return [self._make_arg(context.context_id, ArgumentType.SUPPORTING,
                claim="Fundamental valuation supports the trade",
                reasoning=f"Fundamental score {avg:.0f}/100 — attractive valuation.",
                confidence=min(avg * 0.9, 90.0),
                evidence_ids=[e.evidence_id for e in evidence],
            )]
        if avg <= 38:
            return [self._make_arg(context.context_id, ArgumentType.OPPOSING,
                claim="Fundamentals do not justify entry",
                reasoning=f"Fundamental score {avg:.0f}/100 — expensive or deteriorating.",
                confidence=min((100.0 - avg) * 0.9, 90.0),
                evidence_ids=[e.evidence_id for e in evidence],
            )]
        return []

    async def generate_rebuttal(self, target, context, registry):
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate.voting_engine import make_vote
        evidence = self._relevant_evidence(registry, self._SOURCES)
        score    = self._average_score(evidence)
        return make_vote(
            session_id=context.context_id,
            participant_id=self.participant_id,
            role=self.role,
            outcome=self._vote_from_score(score),
            confidence=abs(score - 50) + 50,
            rationale=f"Fundamental score: {score:.0f}/100",
            weight=self.weight,
        )

    async def final_opinion(self, context, consensus):
        return "Fundamental Analyst: Valuations and financial metrics reviewed."


class MarketIntelligenceAgent(BaseDebateAgent):
    _SOURCES = [EvidenceSource.MARKET_INTELLIGENCE]

    @property
    def role(self) -> ParticipantRole:
        return ParticipantRole.MARKET_INTELLIGENCE

    async def opening_statement(self, context, registry):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        return [self._make_arg(context.context_id, ArgumentType.NEUTRAL,
            claim=f"Market regime score: {avg:.0f}/100",
            reasoning=f"Market intelligence from {len(evidence)} regime signals.",
            confidence=65.0,
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        if not evidence:
            return []
        avg = self._average_score(evidence)
        a_type = ArgumentType.SUPPORTING if avg >= 55 else ArgumentType.OPPOSING
        claim  = "Market regime is supportive" if avg >= 55 else "Market regime is unfavourable"
        conf   = abs(avg - 50) * 1.5 + 50
        return [self._make_arg(context.context_id, a_type, claim=claim,
            reasoning=f"Market regime composite score: {avg:.0f}/100.",
            confidence=min(conf, 90.0),
            evidence_ids=[e.evidence_id for e in evidence],
        )]

    async def generate_rebuttal(self, target, context, registry):
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate.voting_engine import make_vote
        evidence = self._relevant_evidence(registry, self._SOURCES)
        score    = self._average_score(evidence)
        return make_vote(
            session_id=context.context_id,
            participant_id=self.participant_id,
            role=self.role,
            outcome=self._vote_from_score(score),
            confidence=abs(score - 50) + 50,
            rationale=f"Market intelligence score: {score:.0f}/100",
            weight=self.weight,
        )

    async def final_opinion(self, context, consensus):
        return "Market Intelligence Analyst: Market regime and sector conditions assessed."


class CompanyIntelligenceAgent(BaseDebateAgent):
    _SOURCES = [EvidenceSource.COMPANY_INTELLIGENCE]

    @property
    def role(self) -> ParticipantRole:
        return ParticipantRole.COMPANY_INTELLIGENCE

    async def opening_statement(self, context, registry):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        return [self._make_arg(context.context_id, ArgumentType.NEUTRAL,
            claim=f"Company intelligence score: {avg:.0f}/100",
            reasoning=f"Company-level assessment from {len(evidence)} data points.",
            confidence=55.0,
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        if avg >= 60:
            return [self._make_arg(context.context_id, ArgumentType.SUPPORTING,
                claim="Company-level outlook is positive",
                reasoning=f"Company intelligence score {avg:.0f}/100.",
                confidence=min(avg * 0.85, 90.0),
                evidence_ids=[e.evidence_id for e in evidence],
            )]
        if avg <= 40:
            return [self._make_arg(context.context_id, ArgumentType.OPPOSING,
                claim="Company-level outlook is negative",
                reasoning=f"Company intelligence score {avg:.0f}/100.",
                confidence=min((100.0 - avg) * 0.85, 90.0),
                evidence_ids=[e.evidence_id for e in evidence],
            )]
        return []

    async def generate_rebuttal(self, target, context, registry):
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate.voting_engine import make_vote
        evidence = self._relevant_evidence(registry, self._SOURCES)
        score    = self._average_score(evidence)
        return make_vote(
            session_id=context.context_id,
            participant_id=self.participant_id,
            role=self.role,
            outcome=self._vote_from_score(score),
            confidence=abs(score - 50) + 50,
            rationale=f"Company intelligence score: {score:.0f}/100",
            weight=self.weight,
        )

    async def final_opinion(self, context, consensus):
        return "Company Intelligence Analyst: Company-specific factors and moats reviewed."


class MacroAnalystAgent(BaseDebateAgent):
    _SOURCES = [EvidenceSource.MACRO_ANALYSIS]

    @property
    def role(self) -> ParticipantRole:
        return ParticipantRole.MACRO_ANALYST

    async def opening_statement(self, context, registry):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        return [self._make_arg(context.context_id, ArgumentType.NEUTRAL,
            claim=f"Macro environment score: {avg:.0f}/100",
            reasoning=f"Macro assessment from {len(evidence)} signals.",
            confidence=60.0,
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        if avg >= 58:
            return [self._make_arg(context.context_id, ArgumentType.SUPPORTING,
                claim="Macro tailwinds support this trade",
                reasoning=f"Macro score {avg:.0f}/100.",
                confidence=min(avg * 0.88, 90.0),
            )]
        if avg <= 42:
            return [self._make_arg(context.context_id, ArgumentType.OPPOSING,
                claim="Macro headwinds pose risk to this trade",
                reasoning=f"Macro score {avg:.0f}/100.",
                confidence=min((100.0 - avg) * 0.88, 90.0),
            )]
        return []

    async def generate_rebuttal(self, target, context, registry):
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate.voting_engine import make_vote
        evidence = self._relevant_evidence(registry, self._SOURCES)
        score    = self._average_score(evidence)
        return make_vote(
            session_id=context.context_id,
            participant_id=self.participant_id,
            role=self.role,
            outcome=self._vote_from_score(score),
            confidence=abs(score - 50) + 50,
            rationale=f"Macro score: {score:.0f}/100",
            weight=self.weight,
        )

    async def final_opinion(self, context, consensus):
        return "Macro Analyst: Macro factors including rates, inflation, and currency reviewed."


class RiskAnalystAgent(BaseDebateAgent):
    _SOURCES = [EvidenceSource.RISK_INTELLIGENCE]

    @property
    def role(self) -> ParticipantRole:
        return ParticipantRole.RISK_ANALYST

    async def opening_statement(self, context, registry):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        return [self._make_arg(context.context_id, ArgumentType.NEUTRAL,
            claim=f"Risk assessment score: {avg:.0f}/100",
            reasoning=f"Risk analysis from {len(evidence)} risk signals.",
            confidence=70.0,
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        # Risk analyst is conservative — highlights risk when score is low
        if avg <= 45:
            return [self._make_arg(context.context_id, ArgumentType.OPPOSING,
                claim="Risk profile is unfavourable",
                reasoning=f"Risk score {avg:.0f}/100 — elevated downside risk.",
                confidence=min((100.0 - avg) * 0.95, 95.0),
                evidence_ids=[e.evidence_id for e in evidence],
            )]
        if avg >= 65:
            return [self._make_arg(context.context_id, ArgumentType.SUPPORTING,
                claim="Risk-adjusted outlook is acceptable",
                reasoning=f"Risk score {avg:.0f}/100 — manageable downside.",
                confidence=min(avg * 0.85, 85.0),
                evidence_ids=[e.evidence_id for e in evidence],
            )]
        return []

    async def generate_rebuttal(self, target, context, registry):
        if target.argument_type == ArgumentType.SUPPORTING:
            evidence = self._relevant_evidence(registry, self._SOURCES)
            avg      = self._average_score(evidence)
            if avg <= 45:
                return self._make_rebuttal(
                    context.context_id, target.argument_id,
                    claim="Risk metrics challenge the supporting argument",
                    reasoning=f"Risk score {avg:.0f}/100 — risk manager flags concern.",
                    confidence=80.0,
                )
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate.voting_engine import make_vote
        evidence = self._relevant_evidence(registry, self._SOURCES)
        score    = self._average_score(evidence)
        return make_vote(
            session_id=context.context_id,
            participant_id=self.participant_id,
            role=self.role,
            outcome=self._vote_from_score(score),
            confidence=abs(score - 50) + 50,
            rationale=f"Risk score: {score:.0f}/100",
            weight=self.weight,
        )

    async def final_opinion(self, context, consensus):
        return "Risk Analyst: VaR, drawdown, and volatility metrics reviewed."


class PortfolioAnalystAgent(BaseDebateAgent):
    _SOURCES = [EvidenceSource.STRATEGY_INTELLIGENCE]

    @property
    def role(self) -> ParticipantRole:
        return ParticipantRole.PORTFOLIO_ANALYST

    async def opening_statement(self, context, registry):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        return [self._make_arg(context.context_id, ArgumentType.NEUTRAL,
            claim=f"Portfolio fit score: {avg:.0f}/100",
            reasoning=f"Portfolio analysis from {len(evidence)} signals.",
            confidence=55.0,
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        if avg >= 60:
            return [self._make_arg(context.context_id, ArgumentType.SUPPORTING,
                claim="Portfolio fit is good",
                reasoning=f"Strategy intelligence score {avg:.0f}/100.",
                confidence=min(avg * 0.8, 85.0),
            )]
        return []

    async def generate_rebuttal(self, target, context, registry):
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate.voting_engine import make_vote
        evidence = self._relevant_evidence(registry, self._SOURCES)
        score    = self._average_score(evidence)
        return make_vote(
            session_id=context.context_id,
            participant_id=self.participant_id,
            role=self.role,
            outcome=self._vote_from_score(score),
            confidence=abs(score - 50) + 50,
            rationale=f"Portfolio fit score: {score:.0f}/100",
            weight=self.weight,
        )

    async def final_opinion(self, context, consensus):
        return "Portfolio Analyst: Correlation, sizing, and diversification reviewed."


class ExecutionAnalystAgent(BaseDebateAgent):
    _SOURCES = [EvidenceSource.EXECUTION_ANALYSIS]

    @property
    def role(self) -> ParticipantRole:
        return ParticipantRole.EXECUTION_ANALYST

    async def opening_statement(self, context, registry):
        return [self._make_arg(context.context_id, ArgumentType.NEUTRAL,
            claim="Execution conditions pending review",
            reasoning="Reviewing liquidity, spread, and execution feasibility.",
            confidence=50.0,
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        if avg >= 55:
            return [self._make_arg(context.context_id, ArgumentType.SUPPORTING,
                claim="Execution conditions are favourable",
                reasoning=f"Execution score {avg:.0f}/100 — adequate liquidity.",
                confidence=min(avg * 0.75, 80.0),
            )]
        if avg <= 35:
            return [self._make_arg(context.context_id, ArgumentType.OPPOSING,
                claim="Execution risk is elevated",
                reasoning=f"Execution score {avg:.0f}/100 — poor liquidity or high spread.",
                confidence=min((100.0 - avg) * 0.75, 80.0),
            )]
        return []

    async def generate_rebuttal(self, target, context, registry):
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate.voting_engine import make_vote
        evidence = self._relevant_evidence(registry, self._SOURCES)
        score    = self._average_score(evidence)
        return make_vote(
            session_id=context.context_id,
            participant_id=self.participant_id,
            role=self.role,
            outcome=self._vote_from_score(score),
            confidence=abs(score - 50) + 50,
            rationale=f"Execution score: {score:.0f}/100",
            weight=self.weight,
        )

    async def final_opinion(self, context, consensus):
        return "Execution Analyst: Liquidity, spread, and market impact reviewed."


class SentimentAnalystAgent(BaseDebateAgent):
    _SOURCES = [EvidenceSource.SENTIMENT_ANALYSIS]

    @property
    def role(self) -> ParticipantRole:
        return ParticipantRole.SENTIMENT_ANALYST

    async def opening_statement(self, context, registry):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        return [self._make_arg(context.context_id, ArgumentType.NEUTRAL,
            claim=f"Sentiment score: {avg:.0f}/100",
            reasoning=f"Sentiment analysis from {len(evidence)} signals.",
            confidence=50.0,
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        if avg >= 65:
            return [self._make_arg(context.context_id, ArgumentType.SUPPORTING,
                claim="Sentiment is bullish",
                reasoning=f"Sentiment score {avg:.0f}/100.",
                confidence=min(avg * 0.7, 75.0),
            )]
        if avg <= 35:
            return [self._make_arg(context.context_id, ArgumentType.OPPOSING,
                claim="Sentiment is bearish",
                reasoning=f"Sentiment score {avg:.0f}/100.",
                confidence=min((100.0 - avg) * 0.7, 75.0),
            )]
        return []

    async def generate_rebuttal(self, target, context, registry):
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate.voting_engine import make_vote
        evidence = self._relevant_evidence(registry, self._SOURCES)
        score    = self._average_score(evidence)
        return make_vote(
            session_id=context.context_id,
            participant_id=self.participant_id,
            role=self.role,
            outcome=self._vote_from_score(score),
            confidence=abs(score - 50) + 50,
            rationale=f"Sentiment score: {score:.0f}/100",
            weight=self.weight,
        )

    async def final_opinion(self, context, consensus):
        return "Sentiment Analyst: News and social sentiment factors reviewed."


class StrategyLearningAgent(BaseDebateAgent):
    _SOURCES = [EvidenceSource.LEARNING_ENGINE, EvidenceSource.HISTORICAL_RESULTS]

    @property
    def role(self) -> ParticipantRole:
        return ParticipantRole.STRATEGY_LEARNING

    async def opening_statement(self, context, registry):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        return [self._make_arg(context.context_id, ArgumentType.NEUTRAL,
            claim=f"Historical performance score: {avg:.0f}/100",
            reasoning=f"Strategy learning data from {len(evidence)} historical records.",
            confidence=65.0,
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        evidence = self._relevant_evidence(registry, self._SOURCES)
        avg      = self._average_score(evidence)
        if avg >= 60:
            return [self._make_arg(context.context_id, ArgumentType.SUPPORTING,
                claim="Historical strategy performance supports this opportunity",
                reasoning=f"Learning score {avg:.0f}/100 — strategy has delivered historically.",
                confidence=min(avg * 0.9, 90.0),
                evidence_ids=[e.evidence_id for e in evidence],
            )]
        if avg <= 40:
            return [self._make_arg(context.context_id, ArgumentType.OPPOSING,
                claim="Historical strategy performance raises concern",
                reasoning=f"Learning score {avg:.0f}/100 — strategy underperformed historically.",
                confidence=min((100.0 - avg) * 0.9, 90.0),
                evidence_ids=[e.evidence_id for e in evidence],
            )]
        return []

    async def generate_rebuttal(self, target, context, registry):
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate.voting_engine import make_vote
        evidence = self._relevant_evidence(registry, self._SOURCES)
        score    = self._average_score(evidence)
        return make_vote(
            session_id=context.context_id,
            participant_id=self.participant_id,
            role=self.role,
            outcome=self._vote_from_score(score),
            confidence=abs(score - 50) + 50,
            rationale=f"Learning/historical score: {score:.0f}/100",
            weight=self.weight,
        )

    async def final_opinion(self, context, consensus):
        return "Strategy Learning Analyst: Historical win rates and regime-specific performance reviewed."


# ── Role-to-class mapping ─────────────────────────────────────────────────────

ROLE_CLASS_MAP: Dict[ParticipantRole, type] = {
    ParticipantRole.TECHNICAL_ANALYST:    TechnicalAnalystAgent,
    ParticipantRole.FUNDAMENTAL_ANALYST:  FundamentalAnalystAgent,
    ParticipantRole.MARKET_INTELLIGENCE:  MarketIntelligenceAgent,
    ParticipantRole.COMPANY_INTELLIGENCE: CompanyIntelligenceAgent,
    ParticipantRole.MACRO_ANALYST:        MacroAnalystAgent,
    ParticipantRole.RISK_ANALYST:         RiskAnalystAgent,
    ParticipantRole.PORTFOLIO_ANALYST:    PortfolioAnalystAgent,
    ParticipantRole.EXECUTION_ANALYST:    ExecutionAnalystAgent,
    ParticipantRole.SENTIMENT_ANALYST:    SentimentAnalystAgent,
    ParticipantRole.STRATEGY_LEARNING:    StrategyLearningAgent,
}
