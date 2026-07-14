"""iios/investment/strategy/debate/__init__.py
Public API for the Institutional Multi-Agent Strategy Debate Engine.
"""

# ── Core enumerations ─────────────────────────────────────────────────────────
from iios.investment.strategy.debate.debate_constants import (
    ArgumentType,
    ConsensusLevel,
    DebateEventType,
    DebatePhase,
    DebateStatus,
    EvidenceReliability,
    EvidenceSource,
    EvidenceWeight,
    ParticipantRole,
    RebuttalType,
    VoteOutcome,
    VotingMechanism,
)

# ── Event bus ─────────────────────────────────────────────────────────────────
from iios.investment.strategy.debate.debate_events import (
    DebateEvent,
    DebateEventBus,
)

# ── Context and state ─────────────────────────────────────────────────────────
from iios.investment.strategy.debate.debate_context import (
    DebateContext,
    MarketSnapshot,
    OpportunityDebateInput,
    StrategyDebateInput,
)
from iios.investment.strategy.debate.debate_state import DebateState, DebateStateError

# ── Session ───────────────────────────────────────────────────────────────────
from iios.investment.strategy.debate.debate_session import DebateSession
from iios.investment.strategy.debate.debate_history import DebateHistory

# ── Arguments and Rebuttals ───────────────────────────────────────────────────
from iios.investment.strategy.debate.argument_manager import (
    Argument,
    ArgumentManager,
    Rebuttal,
    make_argument,
    make_rebuttal,
)

# ── Evidence ──────────────────────────────────────────────────────────────────
from iios.investment.strategy.debate.evidence_registry import (
    Evidence,
    EvidenceRegistry,
    make_evidence,
)
from iios.investment.strategy.debate.evidence_score import EvidenceScore, compute_evidence_score
from iios.investment.strategy.debate.evidence_validator import EvidenceValidator, ValidationResult
from iios.investment.strategy.debate.evidence_collector import (
    EvidenceCollector,
    CollectionResult,
    MarketIntelligencePort,
    CompanyIntelligencePort,
    RiskIntelligencePort,
    LearningEnginePort,
    KnowledgeLayerPort,
)

# ── Participants ──────────────────────────────────────────────────────────────
from iios.investment.strategy.debate.participant_profile import (
    ParticipantProfile,
    build_profile,
    DEFAULT_WEIGHTS,
)
from iios.investment.strategy.debate.participant_roles import (
    BaseDebateAgent,
    CompanyIntelligenceAgent,
    ExecutionAnalystAgent,
    FundamentalAnalystAgent,
    MacroAnalystAgent,
    MarketIntelligenceAgent,
    PortfolioAnalystAgent,
    ROLE_CLASS_MAP,
    RiskAnalystAgent,
    SentimentAnalystAgent,
    StrategyLearningAgent,
    TechnicalAnalystAgent,
)
from iios.investment.strategy.debate.agent_registry import (
    AgentRegistry,
    create_default_registry,
)

# ── Voting and Consensus ──────────────────────────────────────────────────────
from iios.investment.strategy.debate.voting_engine import (
    Vote,
    VotingEngine,
    VotingResult,
    make_vote,
)
from iios.investment.strategy.debate.agreement_analysis import (
    AgreementAnalysis,
    AgreementMetrics,
)
from iios.investment.strategy.debate.consensus_engine import (
    ConsensusEngine,
    ConsensusPolicy,
    ConsensusResult,
)
from iios.investment.strategy.debate.consensus_statistics import (
    ConsensusStatistics,
    ConsensusStatisticsTracker,
)

# ── Reports ───────────────────────────────────────────────────────────────────
from iios.investment.strategy.debate.recommendation_summary import (
    RecommendationSummary,
    build_recommendation_summary,
)
from iios.investment.strategy.debate.debate_explanation import (
    DebateExplanation,
    DebateExplainer,
)
from iios.investment.strategy.debate.executive_summary import (
    ExecutiveSummary,
    ExecutiveSummaryBuilder,
)
from iios.investment.strategy.debate.debate_report import (
    DebateReport,
    build_report,
)

# ── Orchestration ─────────────────────────────────────────────────────────────
from iios.investment.strategy.debate.debate_orchestrator import (
    DebateOrchestrator,
    OrchestratorConfig,
)

# ── Engine (main entry point) ─────────────────────────────────────────────────
from iios.investment.strategy.debate.strategy_debate_engine import StrategyDebateEngine


__all__ = [
    # Enums
    "ArgumentType",
    "ConsensusLevel",
    "DebateEventType",
    "DebatePhase",
    "DebateStatus",
    "EvidenceReliability",
    "EvidenceSource",
    "EvidenceWeight",
    "ParticipantRole",
    "RebuttalType",
    "VoteOutcome",
    "VotingMechanism",
    # Events
    "DebateEvent",
    "DebateEventBus",
    # Context
    "DebateContext",
    "MarketSnapshot",
    "OpportunityDebateInput",
    "StrategyDebateInput",
    # State
    "DebateState",
    "DebateStateError",
    # Session
    "DebateSession",
    "DebateHistory",
    # Arguments
    "Argument",
    "ArgumentManager",
    "Rebuttal",
    "make_argument",
    "make_rebuttal",
    # Evidence
    "Evidence",
    "EvidenceRegistry",
    "EvidenceScore",
    "EvidenceValidator",
    "ValidationResult",
    "EvidenceCollector",
    "CollectionResult",
    "MarketIntelligencePort",
    "CompanyIntelligencePort",
    "RiskIntelligencePort",
    "LearningEnginePort",
    "KnowledgeLayerPort",
    "make_evidence",
    "compute_evidence_score",
    # Participants
    "BaseDebateAgent",
    "ParticipantProfile",
    "build_profile",
    "DEFAULT_WEIGHTS",
    "AgentRegistry",
    "create_default_registry",
    "ROLE_CLASS_MAP",
    "TechnicalAnalystAgent",
    "FundamentalAnalystAgent",
    "MarketIntelligenceAgent",
    "CompanyIntelligenceAgent",
    "MacroAnalystAgent",
    "RiskAnalystAgent",
    "PortfolioAnalystAgent",
    "ExecutionAnalystAgent",
    "SentimentAnalystAgent",
    "StrategyLearningAgent",
    # Voting & Consensus
    "Vote",
    "VotingEngine",
    "VotingResult",
    "make_vote",
    "AgreementAnalysis",
    "AgreementMetrics",
    "ConsensusEngine",
    "ConsensusPolicy",
    "ConsensusResult",
    "ConsensusStatistics",
    "ConsensusStatisticsTracker",
    # Reports
    "RecommendationSummary",
    "build_recommendation_summary",
    "DebateExplanation",
    "DebateExplainer",
    "ExecutiveSummary",
    "ExecutiveSummaryBuilder",
    "DebateReport",
    "build_report",
    # Orchestration
    "DebateOrchestrator",
    "OrchestratorConfig",
    # Engine
    "StrategyDebateEngine",
]
