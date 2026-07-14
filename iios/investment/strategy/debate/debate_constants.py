"""iios/investment/strategy/debate/debate_constants.py
All enumerations for the Multi-Agent Strategy Debate Engine.
"""
from __future__ import annotations

from enum import Enum


class DebatePhase(str, Enum):
    INITIALIZATION     = "initialization"
    OPENING_STATEMENTS = "opening_statements"
    EVIDENCE_COLLECTION = "evidence_collection"
    ARGUMENTS          = "arguments"
    REBUTTALS          = "rebuttals"
    COUNTER_ARGUMENTS  = "counter_arguments"
    CONSENSUS_BUILDING = "consensus_building"
    FINAL_OPINIONS     = "final_opinions"
    CLOSED             = "closed"

    @property
    def order(self) -> int:
        return list(DebatePhase).index(self)

    @property
    def is_terminal(self) -> bool:
        return self == DebatePhase.CLOSED


class DebateStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"
    TIMEOUT    = "timeout"

    @property
    def is_terminal(self) -> bool:
        return self in (
            DebateStatus.COMPLETED,
            DebateStatus.FAILED,
            DebateStatus.CANCELLED,
            DebateStatus.TIMEOUT,
        )


class ParticipantRole(str, Enum):
    TECHNICAL_ANALYST    = "technical_analyst"
    FUNDAMENTAL_ANALYST  = "fundamental_analyst"
    MARKET_INTELLIGENCE  = "market_intelligence"
    COMPANY_INTELLIGENCE = "company_intelligence"
    MACRO_ANALYST        = "macro_analyst"
    RISK_ANALYST         = "risk_analyst"
    PORTFOLIO_ANALYST    = "portfolio_analyst"
    EXECUTION_ANALYST    = "execution_analyst"
    SENTIMENT_ANALYST    = "sentiment_analyst"
    STRATEGY_LEARNING    = "strategy_learning"
    CUSTOM               = "custom"

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()


class ArgumentType(str, Enum):
    SUPPORTING  = "supporting"
    OPPOSING    = "opposing"
    NEUTRAL     = "neutral"
    CONDITIONAL = "conditional"

    @property
    def is_directional(self) -> bool:
        return self in (ArgumentType.SUPPORTING, ArgumentType.OPPOSING)


class VoteOutcome(str, Enum):
    STRONG_SUPPORT = "strong_support"    # +2
    SUPPORT        = "support"           # +1
    NEUTRAL        = "neutral"           #  0
    OPPOSE         = "oppose"            # -1
    STRONG_OPPOSE  = "strong_oppose"     # -2
    ABSTAIN        = "abstain"           # excluded

    @property
    def numeric_value(self) -> float:
        mapping = {
            VoteOutcome.STRONG_SUPPORT: 2.0,
            VoteOutcome.SUPPORT:        1.0,
            VoteOutcome.NEUTRAL:        0.0,
            VoteOutcome.OPPOSE:        -1.0,
            VoteOutcome.STRONG_OPPOSE: -2.0,
            VoteOutcome.ABSTAIN:        0.0,
        }
        return mapping[self]

    @property
    def is_positive(self) -> bool:
        return self.numeric_value > 0

    @property
    def is_abstain(self) -> bool:
        return self == VoteOutcome.ABSTAIN


class ConsensusLevel(str, Enum):
    UNANIMOUS    = "unanimous"      # 100% agreement
    STRONG       = "strong"         # >= 75%
    MODERATE     = "moderate"       # >= 60%
    WEAK         = "weak"           # >= 50%
    SPLIT        = "split"          # < 50% — minority report issued
    NO_CONSENSUS = "no_consensus"   # unable to reach consensus


class VotingMechanism(str, Enum):
    WEIGHTED_MAJORITY = "weighted_majority"
    SIMPLE_MAJORITY   = "simple_majority"
    SUPERMAJORITY     = "supermajority"       # 2/3+ required
    UNANIMOUS         = "unanimous_required"
    RANKED_CHOICE     = "ranked_choice"


class EvidenceSource(str, Enum):
    MARKET_INTELLIGENCE    = "market_intelligence"
    COMPANY_INTELLIGENCE   = "company_intelligence"
    STRATEGY_INTELLIGENCE  = "strategy_intelligence"
    RISK_INTELLIGENCE      = "risk_intelligence"
    HISTORICAL_RESULTS     = "historical_results"
    LEARNING_ENGINE        = "learning_engine"
    KNOWLEDGE_LAYER        = "knowledge_layer"
    RESEARCH_FRAMEWORK     = "research_framework"
    TECHNICAL_ANALYSIS     = "technical_analysis"
    FUNDAMENTAL_ANALYSIS   = "fundamental_analysis"
    MACRO_ANALYSIS         = "macro_analysis"
    SENTIMENT_ANALYSIS     = "sentiment_analysis"
    EXECUTION_ANALYSIS     = "execution_analysis"
    PARTICIPANT_GENERATED  = "participant_generated"


class EvidenceReliability(str, Enum):
    VERIFIED   = "verified"    # score 1.0
    HIGH       = "high"        # score 0.8
    MEDIUM     = "medium"      # score 0.6
    LOW        = "low"         # score 0.4
    UNVERIFIED = "unverified"  # score 0.2

    @property
    def score(self) -> float:
        return {"verified": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4, "unverified": 0.2}[self.value]


class EvidenceWeight(str, Enum):
    CRITICAL      = "critical"       # 3.0
    HIGH          = "high"           # 2.0
    MEDIUM        = "medium"         # 1.0
    LOW           = "low"            # 0.5
    INFORMATIONAL = "informational"  # 0.25

    @property
    def multiplier(self) -> float:
        return {"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.5, "informational": 0.25}[self.value]


class RebuttalType(str, Enum):
    DIRECT_COUNTER    = "direct_counter"
    EVIDENCE_CHALLENGE = "evidence_challenge"
    SCOPE_LIMITATION  = "scope_limitation"
    CONDITIONAL_ACCEPT = "conditional_accept"
    REINFORCEMENT     = "reinforcement"


class DebateEventType(str, Enum):
    DEBATE_STARTED        = "debate_started"
    PHASE_CHANGED         = "phase_changed"
    AGENT_JOINED          = "agent_joined"
    ARGUMENT_SUBMITTED    = "argument_submitted"
    REBUTTAL_SUBMITTED    = "rebuttal_submitted"
    VOTE_CAST             = "vote_cast"
    EVIDENCE_ADDED        = "evidence_added"
    CONSENSUS_REACHED     = "consensus_reached"
    MINORITY_REPORT_FILED = "minority_report_filed"
    DEBATE_COMPLETED      = "debate_completed"
    DEBATE_FAILED         = "debate_failed"
    AGENT_TIMEOUT         = "agent_timeout"
